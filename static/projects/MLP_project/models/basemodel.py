"""Base model interfaces and torch-backed implementation."""

from abc import ABC, abstractmethod
from typing import Sequence

import torch


class BaseModel(ABC):
    """Abstract base for all models.

    Provides a minimal training/prediction interface and a common trained-state
    flag used by concrete implementations.
    """

    def __init__(self, *, is_trained: bool = False):
        """Initialize the base model.

        Args:
            is_trained: Whether the model should start in a trained state.
        """
        self._is_trained: bool = is_trained

    @property
    def is_trained(self) -> bool:
        """Whether the model has been trained."""
        return self._is_trained

    def _set_trained(self, value: bool) -> None:
        """Update the internal trained flag.

        Args:
            value: New trained-state value.
        """
        self._is_trained = value

    @abstractmethod
    def fit(self, X: torch.Tensor, y: torch.Tensor) -> None:
        """Fit the model on a training set.

        Args:
            X: Feature tensor.
            y: Target tensor.
        """
        pass

    @abstractmethod
    def predict(self, X: torch.Tensor) -> torch.Tensor:
        """Predict labels for inputs.

        Args:
            X: Feature tensor.

        Returns:
            Predicted labels.
        """
        pass

    def predict_prob(self, X: torch.Tensor) -> torch.Tensor:
        """Predict class probabilities.

        Args:
            X: Feature tensor.

        Returns:
            Per-class probability tensor.
        """
        raise NotImplementedError("Model does not support probability outputs")

    def predict_proba(self, X: torch.Tensor) -> torch.Tensor:
        """Alias for predict_prob for scikit-learn-style naming."""
        return self.predict_prob(X)

    def to(self, device: str | torch.device) -> "BaseModel":
        """Move model to device (no-op for non-torch models).

        Args:
            device: Target device.

        Returns:
            Self, for chaining.
        """
        return self


class EnsembleBase(BaseModel, ABC):
    """Abstract base class for ensembles.

    Stores base models and defines the common interface for fitting and
    prediction across ensemble variants.
    """

    def __init__(self, models: Sequence[BaseModel]):
        """Initialize the ensemble base.

        Args:
            models: Base models to ensemble.
        """
        super().__init__()
        self._models: tuple[BaseModel, ...] = tuple(models)

    @property
    def models(self) -> tuple[BaseModel, ...]:
        """Base models in the ensemble."""
        return self._models

    @abstractmethod
    def fit(self, X: torch.Tensor, y: torch.Tensor) -> None:
        """Fit the ensemble on training data.

        Args:
            X: Feature tensor.
            y: Target tensor.
        """
        raise NotImplementedError

    @abstractmethod
    def predict(self, X: torch.Tensor) -> torch.Tensor:
        """Predict labels from input features.

        Args:
            X: Feature tensor.

        Returns:
            Predicted labels.
        """
        raise NotImplementedError


class TorchModel(BaseModel):
    """Torch-backed model wrapper with standard training and inference.

    Holds a torch module, loss function, optimizer, and device. Provides basic
    training loop for classification with a softmax output.
    """

    def __init__(
        self,
        model: torch.nn.Module,
        loss_fn: torch.nn.Module,
        optimizer: torch.optim.Optimizer,
        *,
        device: str | torch.device = "cpu",
        is_trained: bool = False,
    ):
        """Initialize a torch-backed model wrapper.

        Args:
            model: Torch module to train.
            loss_fn: Loss function module.
            optimizer: Optimizer instance.
            device: Device to run the model on.
            is_trained: Whether the model starts in a trained state.
        """
        super().__init__(is_trained=is_trained)
        self._model: torch.nn.Module = model
        self._loss_fn: torch.nn.Module = loss_fn
        self._optimizer: torch.optim.Optimizer = optimizer
        self._device: torch.device = torch.device(device)

    @property
    def device(self) -> torch.device:
        """Current torch device."""
        return self._device

    @device.setter
    def device(self, value: str | torch.device) -> None:
        """Update device and move the underlying model.

        Args:
            value: New device spec.
        """
        self._device = torch.device(value)
        self._model.to(self._device)

    def to(self, device: str | torch.device) -> "TorchModel":
        """Move model to device.

        Args:
            device: Target device.

        Returns:
            Self, for chaining.
        """
        self._device = torch.device(device)
        self._model.to(device)
        return self

    def fit(self, X: torch.Tensor, y: torch.Tensor, epochs: int = 10) -> None:
        """Train the model for a fixed number of epochs.

        Args:
            X: Feature tensor.
            y: Target tensor.
            epochs: Number of training epochs.
        """
        self._model.train()
        X, y = X.to(self._device), y.to(self._device)

        for _ in range(epochs):
            self._optimizer.zero_grad()
            outputs = self._model(X)
            loss = self._loss_fn(outputs, y)
            loss.backward()
            self._optimizer.step()

        self._set_trained(True)

    def predict(self, X: torch.Tensor) -> torch.Tensor:
        """Predict labels using argmax over logits.

        Args:
            X: Feature tensor.

        Returns:
            Predicted labels.
        """
        self._model.eval()
        X = X.to(self._device)
        with torch.no_grad():
            logits = self._model(X)
        return torch.argmax(logits, dim=1)

    def predict_prob(self, X: torch.Tensor) -> torch.Tensor:
        """Predict class probabilities using softmax.

        Args:
            X: Feature tensor.

        Returns:
            Per-class probability tensor.
        """
        self._model.eval()
        X = X.to(self._device)
        with torch.no_grad():
            logits = self._model(X)
        return torch.softmax(logits, dim=1)

    def predict_proba(self, X: torch.Tensor) -> torch.Tensor:
        """Alias for predict_prob for scikit-learn-style naming."""
        return self.predict_prob(X)
