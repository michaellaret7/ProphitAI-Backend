# PyTorch (Python) Cheatsheet — from the provided slides

> Focus: tensors → layers → activations → forward pass → loss → optimizers → parameter counting.

---

## 1) Imports & quick setup

```python
import torch
import torch.nn as nn
```

Device helper:

```python
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
```

---

## 2) Tensors (basics)

Create a tensor from a Python list:

```python
my_list = [[1, 2, 3], [4, 5, 6]]
x = torch.tensor(my_list)
print(x)
```

Shape + dtype:

```python
print(x.shape)   # torch.Size([2, 3])
print(x.dtype)   # e.g., torch.int64
```

Common constructors:

```python
zeros = torch.zeros((3, 4))
ones  = torch.ones((3, 4))
randn = torch.randn((3, 4))   # normal
rand  = torch.rand((3, 4))    # uniform
```

Move to device / cast dtype:

```python
x = x.to(device)
x = x.float()
```

---

## 3) Tensor operations

### Element-wise add / subtract (requires compatible shapes)

```python
a = torch.tensor([[1, 1], [2, 2]])
b = torch.tensor([[2, 2], [3, 3]])
print(a + b)
```

### Element-wise multiplication

```python
a = torch.tensor([[1, 1], [2, 2]])
b = torch.tensor([[2, 2], [3, 3]])
print(a * b)
```

### Matrix multiplication

```python
a = torch.tensor([[1, 1], [2, 2]])
b = torch.tensor([[2, 2], [3, 3]])
print(a @ b)          # preferred
print(torch.matmul(a, b))
```

---

## 4) Layers: `nn.Linear`

A linear layer maps: `out = x @ W.T + b`

```python
linear = nn.Linear(in_features=3, out_features=2)
x = torch.tensor([0.3471, 0.8547, -0.2356])  # 3 features
y = linear(x)
print(y)  # tensor of shape [2]
```

Inspect weights and bias:

```python
print(linear.weight)  # shape: [out_features, in_features]
print(linear.bias)    # shape: [out_features]
```

---

## 5) Building models with `nn.Sequential`

```python
n_features = 6      # number of input features
n_classes  = 3      # number of output classes

model = nn.Sequential(
    nn.Linear(n_features, 8),
    nn.Linear(8, 4),
    nn.Linear(4, n_classes),
)
```

---

## 6) Activation functions

Activation functions add non-linearity.

### Sigmoid (binary classification)
- Output is in (0, 1)
- Often treat `> 0.5` as class 1, else class 0

```python
sigmoid = nn.Sigmoid()
x = torch.tensor([[6.0]])
p = sigmoid(x)
print(p)  # probability-like output
```

Sigmoid as last layer example:

```python
model = nn.Sequential(
    nn.Linear(6, 4),
    nn.Linear(4, 1),
    nn.Sigmoid(),
)
```

### Softmax (multi-class classification)
- Turns a vector of scores (logits) into probabilities that sum to 1
- `dim=-1` applies softmax to the last dimension

```python
probs = nn.Softmax(dim=-1)
logits = torch.tensor([[4.3, 6.1, 2.3]])
p = probs(logits)
print(p)           # probabilities
print(p.sum(-1))   # == 1
```

---

## 7) Forward pass (get predictions)

### Binary classification forward pass

```python
input_data = torch.randn(5, 6)  # 5 samples, 6 features

model = nn.Sequential(
    nn.Linear(6, 4),
    nn.Linear(4, 1),
    nn.Sigmoid(),
)

output = model(input_data)
print(output.shape)  # torch.Size([5, 1])
```

### Multi-class classification forward pass

```python
n_classes = 3
input_data = torch.randn(5, 6)

model = nn.Sequential(
    nn.Linear(6, 4),
    nn.Linear(4, n_classes),
    nn.Softmax(dim=-1),
)

output = model(input_data)
print(output.shape)  # torch.Size([5, 3])
```

### Regression forward pass (no final activation)

```python
input_data = torch.randn(5, 6)

model = nn.Sequential(
    nn.Linear(6, 4),
    nn.Linear(4, 1),
)

y_hat = model(input_data)
print(y_hat.shape)  # torch.Size([5, 1])
```

---

## 8) Loss functions (assess predictions)

A loss compares model prediction `y_hat` with ground-truth `y` and returns a single number (float tensor).

### Common practical pairings
- **Binary classification:** use `nn.BCEWithLogitsLoss()` with **raw logits** (recommended)
- **Multi-class classification:** use `nn.CrossEntropyLoss()` with **raw logits** (recommended)
- **Regression:** use `nn.MSELoss()` (or MAE / Huber)

**Binary (recommended pattern):**
```python
model = nn.Sequential(
    nn.Linear(6, 4),
    nn.Linear(4, 1),
)  # NO sigmoid here

criterion = nn.BCEWithLogitsLoss()

x = torch.randn(5, 6)
y = torch.randint(0, 2, (5, 1)).float()

logits = model(x)
loss = criterion(logits, y)
print(loss.item())
```

**Multi-class (recommended pattern):**
```python
model = nn.Sequential(
    nn.Linear(6, 4),
    nn.Linear(4, 3),
)  # NO softmax here

criterion = nn.CrossEntropyLoss()

x = torch.randn(5, 6)
y = torch.randint(0, 3, (5,))  # class indices, NOT one-hot

logits = model(x)
loss = criterion(logits, y)
print(loss.item())
```

### One-hot encoding (concept)
If you ever need one-hot targets:

```python
y = torch.tensor([0, 2, 1])          # class indices
y_oh = torch.nn.functional.one_hot(y, num_classes=3).float()
print(y_oh)
```

---

## 9) Optimizers (training step loop)

The standard training step:

1) Forward pass  
2) Compute loss  
3) Zero gradients  
4) Backprop (`loss.backward()`)  
5) Optimizer step (`optimizer.step()`)

Example (SGD):

```python
model = nn.Sequential(nn.Linear(6, 4), nn.ReLU(), nn.Linear(4, 3))
optimizer = torch.optim.SGD(model.parameters(), lr=1e-2)
criterion = nn.CrossEntropyLoss()

x = torch.randn(32, 6)
y = torch.randint(0, 3, (32,))

# 1) forward
logits = model(x)

# 2) loss
loss = criterion(logits, y)

# 3) zero grads
optimizer.zero_grad()

# 4) backward
loss.backward()

# 5) update
optimizer.step()
```

Example (Adam):

```python
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)
```

Common optimizer knobs:
- `lr` (learning rate)
- `weight_decay` (L2 regularization)

---

## 10) Count parameters (model size)

Total trainable parameters:

```python
total_params = sum(p.numel() for p in model.parameters())
trainable_params = sum(p.numel() for p in model.parameters() if p.requires_grad)

print("total:", total_params)
print("trainable:", trainable_params)
```

Parameter count per layer:

```python
for name, p in model.named_parameters():
    print(name, p.shape, p.numel())
```

---

## 11) Tiny “starter template” you can copy/paste

```python
import torch
import torch.nn as nn

# data
x = torch.randn(128, 6)
y = torch.randint(0, 3, (128,))

# model (logits, no softmax)
model = nn.Sequential(
    nn.Linear(6, 16),
    nn.ReLU(),
    nn.Linear(16, 3),
)

criterion = nn.CrossEntropyLoss()
optimizer = torch.optim.Adam(model.parameters(), lr=1e-3)

for step in range(200):
    logits = model(x)
    loss = criterion(logits, y)

    optimizer.zero_grad()
    loss.backward()
    optimizer.step()

    if step % 50 == 0:
        print(step, loss.item())
```

---

## Sources
- Slides: *Using the PyTorch optimizer* fileciteturn0file0  
- Slides: *Counting the number of parameters* fileciteturn0file1  
