"""Random forest classifier wrapper."""

from typing import Any

import torch
from sklearn.ensemble import RandomForestClassifier

from .basemodel import BaseModel


class RandomForest(BaseModel):
    """Ensemble of decision trees trained with bagging.

    Wraps scikit-learn's RandomForestClassifier and adapts it to the torch-based
    interface used in this project.
    """

    def __init__(
        self,
        *,
        n_estimators: int = 100,
        max_depth: int | None = None,
        model_kwargs: dict[str, Any] | None = None,
        is_trained: bool = False,
    ):
        """Initialize the random forest model.

        Args:
            n_estimators: Number of trees in the forest.
            max_depth: Optional maximum tree depth.
            model_kwargs: Extra keyword arguments for the sklearn estimator.
            is_trained: Whether the model starts in a trained state.
        """
        super().__init__(is_trained=is_trained)
        if model_kwargs is None:
            model_kwargs = {}
        self._n_estimators: int = n_estimators
        self._max_depth: int | None = max_depth
        self._model: RandomForestClassifier = RandomForestClassifier(
            n_estimators=n_estimators, max_depth=max_depth, **model_kwargs
        )

    @property
    def n_estimators(self) -> int:
        """Number of trees in the forest."""
        return self._n_estimators

    @property
    def max_depth(self) -> int | None:
        """Maximum depth of individual trees, if set."""
        return self._max_depth

    def fit(self, X: torch.Tensor, y: torch.Tensor) -> None:
        """Fit the underlying sklearn model.

        Args:
            X: Feature tensor.
            y: Target tensor.
        """
        X_np = X.cpu().numpy()
        y_np = y.cpu().numpy()
        self._model.fit(X_np, y_np)
        self._set_trained(True)

    def predict(self, X: torch.Tensor) -> torch.Tensor:
        """Predict labels using the trained forest.

        Args:
            X: Feature tensor.

        Returns:
            Predicted labels.
        """
        X_np = X.cpu().numpy()
        preds = self._model.predict(X_np)
        return torch.tensor(preds)

    def predict_prob(self, X: torch.Tensor) -> torch.Tensor:
        """Predict class probabilities using the trained forest.

        Args:
            X: Feature tensor.

        Returns:
            Per-class probability tensor.
        """
        X_np = X.cpu().numpy()
        probs = self._model.predict_proba(X_np)
        return torch.tensor(probs)
