"""Pytest coverage for ensemble models."""

import torch

from models.basemodel import EnsembleBase
from models.ensamble import (
    BaggingEnsemble,
    HardVotingEnsemble,
    SoftVotingEnsemble,
    StackingEnsemble,
    WeightedEnsemble,
)
from models.KNN import KNN
from models.logistic_regression import LogisticRegression
from models.naive_bayes import NaiveBayes


def test_hard_voting_ensemble():
    X = torch.tensor([[0.0], [1.0], [2.0], [3.0]])
    y = torch.tensor([0, 0, 1, 1])
    model = HardVotingEnsemble([KNN(k=1), KNN(k=3)])
    model.fit(X, y)

    preds = model.predict(torch.tensor([[0.1], [2.9]]))
    assert preds.tolist() == [0, 1]


def test_soft_voting_ensemble():
    X = torch.tensor(
        [
            [0.0, 0.0],
            [0.2, 0.1],
            [1.0, 1.0],
            [1.1, 0.9],
        ]
    )
    y = torch.tensor([0, 0, 1, 1])
    model = SoftVotingEnsemble(
        [
            LogisticRegression(input_dim=2, num_classes=2, lr=0.1),
            LogisticRegression(input_dim=2, num_classes=2, lr=0.1),
        ]
    )
    model.fit(X, y)

    preds = model.predict(X)
    probs = model.predict_proba(X)
    assert preds.shape == y.shape
    assert probs.shape == (X.shape[0], 2)


def test_weighted_ensemble():
    X = torch.tensor(
        [
            [0.0, 0.0],
            [0.1, 0.2],
            [1.0, 1.0],
            [1.2, 0.9],
        ]
    )
    y = torch.tensor([0, 0, 1, 1])
    model = WeightedEnsemble(
        [
            LogisticRegression(input_dim=2, num_classes=2, lr=0.1),
            LogisticRegression(input_dim=2, num_classes=2, lr=0.1),
        ],
        weights=[0.6, 0.4],
    )
    model.fit(X, y)

    preds = model.predict(X)
    assert preds.shape == y.shape


def test_stacking_ensemble():
    X = torch.tensor(
        [
            [0.0, 0.0],
            [0.2, 0.1],
            [1.0, 1.0],
            [1.1, 0.9],
        ]
    )
    y = torch.tensor([0, 0, 1, 1])
    base_models = [
        LogisticRegression(input_dim=2, num_classes=2, lr=0.1),
        LogisticRegression(input_dim=2, num_classes=2, lr=0.1),
    ]
    meta_model = LogisticRegression(input_dim=4, num_classes=2, lr=0.1)
    model = StackingEnsemble(base_models=base_models, meta_model=meta_model)
    model.fit(X, y)

    preds = model.predict(X)
    assert preds.shape == y.shape


def test_bagging_ensemble():
    X = torch.tensor(
        [
            [2.0, 0.0, 1.0],
            [1.0, 0.0, 0.0],
            [0.0, 2.0, 1.0],
            [0.0, 1.0, 0.0],
        ]
    )
    y = torch.tensor([0, 0, 1, 1])
    model = BaggingEnsemble(base_model_class=NaiveBayes, n_models=3)
    model.fit(X, y)

    preds = model.predict(X)
    assert preds.shape == y.shape


def test_weighted_ensemble_weights_are_copied():
    model = WeightedEnsemble([KNN(k=1), KNN(k=3)], weights=[0.7, 0.3])
    weights = model.weights
    weights[0] = 0.0
    assert model.weights[0] != 0.0


def test_ensembles_inherit_base():
    models = [KNN(k=1), KNN(k=3)]
    assert isinstance(HardVotingEnsemble(models), EnsembleBase)
    assert isinstance(SoftVotingEnsemble(models), EnsembleBase)
    assert isinstance(WeightedEnsemble(models, weights=[0.5, 0.5]), EnsembleBase)
    assert isinstance(StackingEnsemble(models, meta_model=KNN(k=1)), EnsembleBase)
    assert isinstance(BaggingEnsemble(base_model_class=KNN, n_models=2), EnsembleBase)
