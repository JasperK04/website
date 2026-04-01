"""Torch-based logistic regression model."""

from typing import Any, Callable

import torch

from .basemodel import TorchModel


class LogisticRegression(TorchModel):
    """Single-layer linear classifier trained with cross-entropy.

    Uses a torch linear layer and an optimizer to learn a linear decision
    boundary for multi-class classification.
    """

    def __init__(
        self,
        input_dim: int,
        num_classes: int,
        *,
        lr: float = 1e-3,
        optimizer_cls: Callable[..., torch.optim.Optimizer] = torch.optim.Adam,
        optimizer_kwargs: dict[str, Any] | None = None,
        loss_fn_cls: Callable[..., torch.nn.Module] = torch.nn.CrossEntropyLoss,
        loss_fn_kwargs: dict[str, Any] | None = None,
        linear_kwargs: dict[str, Any] | None = None,
        device: str | torch.device = "cpu",
    ):
        """Initialize the logistic regression model.

        Args:
            input_dim: Number of input features.
            num_classes: Number of output classes.
            lr: Learning rate for the optimizer.
            optimizer_cls: Optimizer constructor.
            optimizer_kwargs: Extra optimizer keyword arguments.
            loss_fn_cls: Loss function constructor.
            loss_fn_kwargs: Extra loss function keyword arguments.
            linear_kwargs: Extra keyword arguments for the linear layer.
            device: Device for model parameters and computation.
        """
        if optimizer_kwargs is None:
            optimizer_kwargs = {}
        if loss_fn_kwargs is None:
            loss_fn_kwargs = {}
        if linear_kwargs is None:
            linear_kwargs = {}

        self._lr: float = lr
        self._optimizer_cls: Callable[..., torch.optim.Optimizer] = optimizer_cls
        self._optimizer_kwargs: dict[str, Any] = dict(optimizer_kwargs)
        self._loss_fn_cls: Callable[..., torch.nn.Module] = loss_fn_cls
        self._loss_fn_kwargs: dict[str, Any] = dict(loss_fn_kwargs)
        self._linear_kwargs: dict[str, Any] = dict(linear_kwargs)

        model = torch.nn.Linear(input_dim, num_classes, **self._linear_kwargs)
        loss_fn = self._loss_fn_cls(**self._loss_fn_kwargs)
        optimizer_kwargs = {"lr": self._lr, **self._optimizer_kwargs}
        optimizer = self._optimizer_cls(model.parameters(), **optimizer_kwargs)
        super().__init__(model, loss_fn, optimizer, device=device)

    @property
    def lr(self) -> float:
        """Learning rate used by the optimizer."""
        return self._lr

    @property
    def optimizer_kwargs(self) -> dict[str, Any]:
        """Optimizer keyword arguments."""
        return dict(self._optimizer_kwargs)

    @property
    def loss_fn_kwargs(self) -> dict[str, Any]:
        """Loss function keyword arguments."""
        return dict(self._loss_fn_kwargs)

    @property
    def linear_kwargs(self) -> dict[str, Any]:
        """Linear layer keyword arguments."""
        return dict(self._linear_kwargs)
