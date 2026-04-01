"""K-Nearest Neighbors classifier."""

import torch

from .basemodel import BaseModel


class KNN(BaseModel):
    """Lazy k-nearest neighbors classifier.

    Stores training examples and predicts by majority vote among the k closest
    points using Euclidean distance.
    """

    def __init__(self, *, k: int = 5, is_trained: bool = False):
        """Initialize the KNN model.

        Args:
            k: Number of neighbors to consider.
            is_trained: Whether the model starts in a trained state.
        """
        super().__init__(is_trained=is_trained)
        self._k: int = k
        self._X: torch.Tensor | None = None
        self._y: torch.Tensor | None = None
        self.k = k

    @property
    def k(self) -> int:
        """Number of neighbors used for prediction."""
        return self._k

    @k.setter
    def k(self, value: int) -> None:
        """Set the number of neighbors.

        Args:
            value: Positive integer for k.

        Raises:
            ValueError: If k is not a positive integer.
        """
        if not isinstance(value, int) or value <= 0:
            raise ValueError("k must be a positive integer")
        self._k = value

    def fit(self, X: torch.Tensor, y: torch.Tensor) -> None:
        """Store training data for distance-based lookup.

        Args:
            X: Feature tensor.
            y: Target tensor.
        """
        self._X = X.clone()
        self._y = y.clone()
        self._set_trained(True)

    def predict(self, X: torch.Tensor) -> torch.Tensor:
        """Predict labels by majority vote among nearest neighbors.

        Args:
            X: Feature tensor.

        Returns:
            Predicted labels.

        Raises:
            RuntimeError: If called before fit.
        """
        if not self._is_trained or self._X is None or self._y is None:
            raise RuntimeError("Model must be fit before predict")
        dists = torch.cdist(X, self._X)
        knn_idx = torch.topk(dists, self._k, largest=False).indices
        knn_labels = self._y[knn_idx]
        return torch.mode(knn_labels, dim=1).values
