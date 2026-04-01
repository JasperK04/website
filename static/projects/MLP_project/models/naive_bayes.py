"""Multinomial Naive Bayes classifier."""

import torch

from .basemodel import BaseModel


class NaiveBayes(BaseModel):
    """Multinomial Naive Bayes with Laplace smoothing.

    Estimates per-class priors and per-feature likelihoods, then predicts by
    maximizing the log-posterior probability.
    """

    def __init__(self, *, alpha: float = 1.0, is_trained: bool = False):
        """Initialize the Naive Bayes model.

        Args:
            alpha: Laplace smoothing factor.
            is_trained: Whether the model starts in a trained state.
        """
        super().__init__(is_trained=is_trained)
        self._alpha: float = alpha
        self._classes: torch.Tensor | None = None
        self._class_probs: dict[int, float] = {}
        self._feature_probs: dict[int, torch.Tensor] = {}

    @property
    def alpha(self) -> float:
        """Laplace smoothing factor."""
        return self._alpha

    @property
    def classes(self) -> torch.Tensor | None:
        """Known class labels after training."""
        if self._classes is None:
            return None
        return self._classes.clone()

    @property
    def class_probs(self) -> dict[int, float]:
        """Class prior probabilities."""
        return dict(self._class_probs)

    @property
    def feature_probs(self) -> dict[int, torch.Tensor]:
        """Per-class feature likelihoods."""
        return {k: v.clone() for k, v in self._feature_probs.items()}

    def fit(self, X: torch.Tensor, y: torch.Tensor) -> None:
        """Estimate class priors and feature likelihoods.

        Args:
            X: Feature tensor.
            y: Target tensor.
        """
        classes = torch.unique(y)
        self._classes = classes
        self._class_probs = {}
        self._feature_probs = {}

        for c in classes:
            X_c = X[y == c]
            class_id = int(c.item())
            self._class_probs[class_id] = X_c.shape[0] / X.shape[0]
            self._feature_probs[class_id] = (X_c.sum(dim=0) + self._alpha) / (
                X_c.sum() + self._alpha * X.shape[1]
            )

        self._set_trained(True)

    def predict(self, X: torch.Tensor) -> torch.Tensor:
        """Predict labels using log-posterior scores.

        Args:
            X: Feature tensor.

        Returns:
            Predicted labels.

        Raises:
            RuntimeError: If called before fit.
        """
        if not self._is_trained or self._classes is None:
            raise RuntimeError("Model must be fit before predict")
        probs = []
        for c in self._classes:
            class_id = int(c.item())
            class_prob = torch.tensor(
                self._class_probs[class_id], device=X.device, dtype=X.dtype
            )
            log_prob = torch.log(class_prob) + (
                X * torch.log(self._feature_probs[class_id])
            ).sum(dim=1)
            probs.append(log_prob)
        return torch.stack(probs).argmax(dim=0)
