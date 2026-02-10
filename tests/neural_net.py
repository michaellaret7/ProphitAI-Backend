import numpy as np
from scipy.special import expit


def sigmoid(x: np.ndarray) -> np.ndarray:
    """Sigmoid activation function."""
    return expit(x)


def sigmoid_derivative(x: np.ndarray) -> np.ndarray:
    """Derivative of sigmoid, assuming x is already sigmoid output."""
    return x * (1 - x)


class NeuralNetwork:
    def __init__(self, x, y):
        self.input      = x
        self.weights1   = np.random.rand(self.input.shape[1],4) 
        self.weights2   = np.random.rand(4,1)                 
        self.y          = y
        self.output     = np.zeros(self.y.shape)

    def feedforward(self):
        self.layer1 = sigmoid(np.dot(self.input, self.weights1))
        self.output = sigmoid(np.dot(self.layer1, self.weights2))

    def backprop(self):
        # application of the chain rule to find derivative of the loss function with respect to weights2 and weights1
        d_weights2 = np.dot(self.layer1.T, (2*(self.y - self.output) * sigmoid_derivative(self.output)))
        d_weights1 = np.dot(self.input.T,  (np.dot(2*(self.y - self.output) * sigmoid_derivative(self.output), self.weights2.T) * sigmoid_derivative(self.layer1)))

        # update the weights with the derivative (slope) of the loss function
        self.weights1 += d_weights1
        self.weights2 += d_weights2


if __name__ == "__main__":
    # XOR-style training data
    X = np.array([[0, 0, 1],
                  [0, 1, 1],
                  [1, 0, 1],
                  [1, 1, 1]])

    y = np.array([[0], [1], [1], [0]])

    nn = NeuralNetwork(X, y)

    iterations = 150000
    for i in range(iterations):
        nn.feedforward()
        nn.backprop()
        if i % 500 == 0:
            loss = np.mean(np.square(y - nn.output))
            print(f"Iteration {i:>5d} | Loss: {loss:.6f}")

    print(f"\nFinal loss after {iterations} iterations: {np.mean(np.square(y - nn.output)):.6f}")
    print(f"\nPredictions:\n{nn.output}")
    print(f"\nExpected:\n{y}")