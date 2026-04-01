"""Pytest coverage for Naive Bayes."""

import pytest
import torch

from models.naive_bayes import NaiveBayes


def test_naive_bayes_fit_predict():
    X = torch.tensor(
        [
            [2.0, 0.0, 1.0],
            [1.0, 0.0, 0.0],
            [0.0, 2.0, 1.0],
            [0.0, 1.0, 0.0],
        ]
    )
    y = torch.tensor([0, 0, 1, 1])
    model = NaiveBayes(alpha=1.0)
    model.fit(X, y)

    preds = model.predict(torch.tensor([[1.0, 0.0, 0.0], [0.0, 2.0, 0.0]]))
    assert preds.tolist() == [0, 1]


def test_naive_bayes_predict_before_fit_raises():
    model = NaiveBayes(alpha=1.0)
    with pytest.raises(RuntimeError):
        model.predict(torch.tensor([[1.0, 0.0, 0.0]]))


def test_naive_bayes_properties_return_copies():
    X = torch.tensor(
        [
            [2.0, 0.0, 1.0],
            [1.0, 0.0, 0.0],
            [0.0, 2.0, 1.0],
            [0.0, 1.0, 0.0],
        ]
    )
    y = torch.tensor([0, 0, 1, 1])
    model = NaiveBayes(alpha=1.0)
    model.fit(X, y)

    class_probs = model.class_probs
    class_probs[0] = 999.0
    assert model.class_probs[0] != 999.0

    feature_probs = model.feature_probs
    feature_probs[0][0] = -1.0
    assert model.feature_probs[0][0] != -1.0
