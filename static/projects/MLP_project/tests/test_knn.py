"""Pytest coverage for KNN."""

import pytest
import torch

from models.KNN import KNN


def test_knn_fit_predict():
    X = torch.tensor([[0.0], [1.0], [2.0], [3.0]])
    y = torch.tensor([0, 0, 1, 1])
    model = KNN(k=1)
    model.fit(X, y)

    preds = model.predict(torch.tensor([[0.1], [2.9]]))
    assert preds.tolist() == [0, 1]


def test_knn_predict_before_fit_raises():
    model = KNN(k=1)
    with pytest.raises(RuntimeError):
        model.predict(torch.tensor([[0.0], [1.0]]))


def test_knn_fit_copies_inputs():
    X = torch.tensor([[0.0], [1.0], [2.0], [3.0]])
    y = torch.tensor([0, 0, 1, 1])
    model = KNN(k=1)
    model.fit(X, y)

    X[0, 0] = 100.0
    y[0] = 9

    preds = model.predict(torch.tensor([[0.1], [2.9]]))
    assert preds.tolist() == [0, 1]
