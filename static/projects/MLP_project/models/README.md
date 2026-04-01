"""Models package README."""

# Models

This folder contains all model implementations used in the project. The code
follows a common interface so models can be swapped easily during experiments.

## Requirements

- Python 3.12+.
- PyTorch for the torch-backed models and tensor utilities.
- scikit-learn for the random forest wrapper.
- Pytest for the unittests

Install project dependencies from the root of the repo using the tooling you
already use (requirements.txt or pyproject.toml).

## Assumptions

- Inputs are torch tensors for all model `fit` and `predict` methods.
- Labels are integer class indices for classification.
- For Naive Bayes, features are non-negative counts or frequencies and labels
	represent class indices.
- KNN uses Euclidean distance and stores training data in memory.
- Torch models expect batch-first tensors.

## Base Models

### BaseModel

`BaseModel` defines the minimal interface: `fit`, `predict`, `predict_prob`
and `to`. It tracks training state via `is_trained` and provides a no operation method
`to` for non-torch models.

### TorchModel

`TorchModel` wraps a torch module, loss function, and optimizer. It provides a
simple training loop for classification and implements `predict` and
`predict_prob` using softmax. Use this as a base for new torch-backed models.

### EnsembleBase

`EnsembleBase` stores a list of base models and defines the common interface
for ensembles. Concrete ensemble classes inherit from it.

## Individual Models

### LogisticRegression

A single linear layer trained with cross-entropy loss and an optimizer. It is
implemented as a `TorchModel`.

### NaiveBayes

Multinomial Naive Bayes with Laplace smoothing. It estimates class priors and
feature likelihoods and predicts by maximizing log-posterior scores.

### KNN

K-Nearest Neighbors classifier using Euclidean distance. It stores the
training set and predicts by majority vote over the nearest neighbors.

### RandomForest

Wrapper around scikit-learn's `RandomForestClassifier` that accepts torch
inputs and returns torch tensors.

## Ensemble Models

### HardVotingEnsemble

Fits each base model independently and predicts by majority vote over the
base predictions.

### SoftVotingEnsemble

Fits each base model independently and predicts by averaging class
probabilities.

### WeightedEnsemble

Like soft voting but applies fixed weights to each model's probabilities.

### StackingEnsemble

Fits base models, concatenates their probability outputs, then trains a
meta-model on those features.

### BaggingEnsemble

Trains multiple models on bootstrap samples of the training data and predicts
by majority vote.

## When to Use Which Model

- LogisticRegression: Strong baseline for linearly separable problems and
	fast training with good interpretability.
- NaiveBayes: Works well for count-based features (text or bag-of-words) and
	small datasets where independence assumptions are acceptable.
- KNN: Useful for small datasets with complex decision boundaries and when
	you can afford the memory cost of storing all training data.
- RandomForest: Good general-purpose classifier with nonlinear decision
	boundaries and strong performance on tabular data.
- HardVotingEnsemble: Use when base models are diverse and you want a simple
	majority vote.
- SoftVotingEnsemble: Use when base models can output probabilities and you
	want smoother decisions than hard voting.
- WeightedEnsemble: Use when you know some models are more reliable and want
	to bias the combined prediction.
- StackingEnsemble: Use when you want a learned combination of model outputs
	and can afford the extra training cost.
- BaggingEnsemble: Use to reduce variance and improve stability with noisy
	data.

## Notes

- All models follow the same interface to simplify experiments.
- Ensembles assume base models follow the same class label conventions.
