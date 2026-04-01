"""Pytest coverage for Random Forest."""

import torch

from models.random_forest import RandomForest


def test_random_forest_fit_predict():
    X = torch.tensor(
        [
            [0.0, 0.0],
            [0.2, 0.1],
            [1.0, 1.0],
            [1.2, 0.9],
        ]
    )
    y = torch.tensor([0, 0, 1, 1])
    model = RandomForest(n_estimators=10, max_depth=2)
    model.fit(X, y)

    preds = model.predict(X)
    probs = model.predict_proba(X)
    assert preds.shape == y.shape
    assert probs.shape == (X.shape[0], 2)
    assert model.is_trained is True
