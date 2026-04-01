"""Pytest coverage for base model utilities."""

import torch

from models.basemodel import BaseModel, TorchModel


class DummyModel(BaseModel):
    def fit(self, X: torch.Tensor, y: torch.Tensor) -> None:
        self._set_trained(True)

    def predict(self, X: torch.Tensor) -> torch.Tensor:
        return torch.zeros(X.shape[0], dtype=torch.long)

    def predict_prob(self, X: torch.Tensor) -> torch.Tensor:
        return torch.ones((X.shape[0], 2), dtype=X.dtype)


def test_base_model_predict_proba_alias():
    X = torch.zeros((3, 2))
    model = DummyModel()
    probs = model.predict_prob(X)
    probs_alias = model.predict_proba(X)
    assert torch.allclose(probs, probs_alias)


def test_torch_model_device_and_fit():
    model = torch.nn.Linear(2, 2)
    loss_fn = torch.nn.CrossEntropyLoss()
    optimizer = torch.optim.SGD(model.parameters(), lr=0.1)
    wrapper = TorchModel(model, loss_fn, optimizer)

    wrapper.device = "cpu"
    assert str(wrapper.device) == "cpu"

    X = torch.tensor([[0.0, 0.0], [1.0, 1.0]])
    y = torch.tensor([0, 1])
    wrapper.fit(X, y, epochs=1)

    assert wrapper.is_trained is True
    assert wrapper.to("cpu") is wrapper
