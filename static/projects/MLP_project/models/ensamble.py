"""Ensemble model implementations."""

from typing import Sequence

import torch

from .basemodel import BaseModel, EnsembleBase


class HardVotingEnsemble(EnsembleBase):
    """Hard-voting ensemble that takes the mode of base predictions.

    Fits each base model independently and aggregates predictions via majority
    vote across models.
    """

    def __init__(self, models: Sequence[BaseModel]):
        """Initialize the hard-voting ensemble.

        Args:
            models: Base models to ensemble.
        """
        super().__init__(models)

    def fit(self, X: torch.Tensor, y: torch.Tensor) -> None:
        """Fit all base models on the same data.

        Args:
            X: Feature tensor.
            y: Target tensor.
        """
        for m in self._models:
            m.fit(X, y)
        self._set_trained(True)

    def predict(self, X: torch.Tensor) -> torch.Tensor:
        """Predict labels by majority vote.

        Args:
            X: Feature tensor.

        Returns:
            Predicted labels.
        """
        preds = torch.stack([m.predict(X) for m in self._models])
        return torch.mode(preds, dim=0).values


class SoftVotingEnsemble(EnsembleBase):
    """Soft-voting ensemble that averages class probabilities.

    Fits each base model independently and averages predicted probabilities
    before taking an argmax over classes.
    """

    def __init__(self, models: Sequence[BaseModel]):
        """Initialize the soft-voting ensemble.

        Args:
            models: Base models to ensemble.
        """
        super().__init__(models)

    def fit(self, X: torch.Tensor, y: torch.Tensor) -> None:
        """Fit all base models on the same data.

        Args:
            X: Feature tensor.
            y: Target tensor.
        """
        for m in self._models:
            m.fit(X, y)
        self._set_trained(True)

    def predict(self, X: torch.Tensor) -> torch.Tensor:
        """Predict labels by averaging probabilities.

        Args:
            X: Feature tensor.

        Returns:
            Predicted labels.
        """
        probs = torch.stack([m.predict_proba(X) for m in self._models])
        avg_probs = probs.mean(dim=0)
        return torch.argmax(avg_probs, dim=1)

    def predict_proba(self, X: torch.Tensor) -> torch.Tensor:
        """Predict averaged class probabilities.

        Args:
            X: Feature tensor.

        Returns:
            Per-class probability tensor.
        """
        probs = torch.stack([m.predict_proba(X) for m in self._models])
        return probs.mean(dim=0)


class WeightedEnsemble(EnsembleBase):
    """Weighted soft-voting ensemble.

    Averages base-model probabilities with a fixed weight per model.
    """

    def __init__(
        self, models: Sequence[BaseModel], weights: torch.Tensor | Sequence[float]
    ):
        """Initialize the weighted ensemble.

        Args:
            models: Base models to ensemble.
            weights: Per-model weights, broadcastable to model outputs.
        """
        super().__init__(models)
        self._weights: torch.Tensor = torch.tensor(weights)

    @property
    def weights(self) -> torch.Tensor:
        """Per-model weight tensor."""
        return self._weights.clone()

    def fit(self, X: torch.Tensor, y: torch.Tensor) -> None:
        """Fit all base models on the same data.

        Args:
            X: Feature tensor.
            y: Target tensor.
        """
        for m in self._models:
            m.fit(X, y)
        self._set_trained(True)

    def predict(self, X: torch.Tensor) -> torch.Tensor:
        """Predict labels by weighted probability averaging.

        Args:
            X: Feature tensor.

        Returns:
            Predicted labels.
        """
        probs = torch.stack([m.predict_proba(X) for m in self._models])
        weighted = probs * self._weights[:, None, None]
        summed = weighted.sum(dim=0)
        return torch.argmax(summed, dim=1)


class StackingEnsemble(EnsembleBase):
    """Stacked ensemble with a meta-model.

    Trains base models, concatenates their probability outputs, and trains a
    meta-model on the resulting features.
    """

    def __init__(self, base_models: Sequence[BaseModel], meta_model: BaseModel):
        """Initialize the stacking ensemble.

        Args:
            base_models: Base models to generate meta-features.
            meta_model: Meta-model trained on base predictions.
        """
        super().__init__(base_models)
        self._base_models: tuple[BaseModel, ...] = tuple(base_models)
        self._meta_model: BaseModel = meta_model

    @property
    def base_models(self) -> tuple[BaseModel, ...]:
        """Base models used for stacking."""
        return self._base_models

    def fit(self, X: torch.Tensor, y: torch.Tensor) -> None:
        """Fit base models and train the meta-model.

        Args:
            X: Feature tensor.
            y: Target tensor.
        """
        base_preds = []

        for m in self._base_models:
            m.fit(X, y)
            probs = m.predict_proba(X)
            base_preds.append(probs)

        meta_X = torch.cat(base_preds, dim=1)
        self._meta_model.fit(meta_X, y)

        self._set_trained(True)

    def predict(self, X: torch.Tensor) -> torch.Tensor:
        """Predict labels using base model outputs and the meta-model.

        Args:
            X: Feature tensor.

        Returns:
            Predicted labels.
        """
        base_preds = [m.predict_proba(X) for m in self._base_models]
        meta_X = torch.cat(base_preds, dim=1)
        return self._meta_model.predict(meta_X)


class BaggingEnsemble(EnsembleBase):
    """Bagging ensemble that trains models on bootstrap samples."""

    def __init__(self, base_model_class: type[BaseModel], n_models: int = 10):
        """Initialize the bagging ensemble.

        Args:
            base_model_class: Model class used to build each estimator.
            n_models: Number of bootstrap models to train.
        """
        super().__init__(tuple(base_model_class() for _ in range(n_models)))
        self._base_model_class: type[BaseModel] = base_model_class
        self._n_models: int = n_models
        self._models: tuple[BaseModel, ...] = self.models

    @property
    def n_models(self) -> int:
        """Number of models in the bagging ensemble."""
        return self._n_models

    @property
    def models(self) -> tuple[BaseModel, ...]:
        """Ensemble members."""
        return self._models

    def fit(self, X: torch.Tensor, y: torch.Tensor) -> None:
        """Fit each model on a bootstrap sample.

        Args:
            X: Feature tensor.
            y: Target tensor.
        """
        n = X.shape[0]

        for m in self._models:
            idx = torch.randint(0, n, (n,))
            m.fit(X[idx], y[idx])

        self._set_trained(True)

    def predict(self, X: torch.Tensor) -> torch.Tensor:
        """Predict labels by majority vote across ensemble members.

        Args:
            X: Feature tensor.

        Returns:
            Predicted labels.
        """
        preds = torch.stack([m.predict(X) for m in self._models])
        return torch.mode(preds, dim=0).values
