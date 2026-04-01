"""Pytest coverage for Logistic Regression."""

import torch

from models.logistic_regression import LogisticRegression


def test_logistic_regression_fit_predict():
    X = torch.tensor(
        [
            [0.0, 0.0],
            [0.1, 0.2],
            [1.0, 1.0],
            [1.1, 0.9],
        ]
    )
    y = torch.tensor([0, 0, 1, 1])
    model = LogisticRegression(input_dim=2, num_classes=2, lr=0.1)
    model.fit(X, y, epochs=1)

    preds = model.predict(X)
    assert preds.shape == y.shape


def test_logistic_regression_properties_are_copies():
    model = LogisticRegression(input_dim=2, num_classes=2)

    optimizer_kwargs = model.optimizer_kwargs
    optimizer_kwargs["lr"] = 10.0
    assert model.optimizer_kwargs.get("lr") != 10.0

    linear_kwargs = model.linear_kwargs
    linear_kwargs["bias"] = False
    assert model.linear_kwargs.get("bias") is None
