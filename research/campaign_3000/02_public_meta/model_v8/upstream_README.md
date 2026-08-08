<img src="https://files.catbox.moe/un9yo6.jpg" width="100%">

# 🌾 Kaggriculture PyTorch DQN Baseline

Welcome to the **most advanced starting point** for the Global AI Agriculture Competition! This model instance provides pre-trained weights for a state-of-the-art Deep Q-Network (DQN) designed for the Kaggriculture simulation environment.

## 🌟 Why Use This Baseline?
- **Highly Optimized**: Tuned hyperparameters designed specifically for dynamic agricultural environments.
- **Fast Iteration**: Skip the costly initial training phase and immediately start experimenting with policy adjustments.
- **Robust Architecture**: Built on PyTorch, ready to integrate into your existing pipelines.

## 🚀 Quick Start Example
Get started in under 5 minutes:

```python
import torch
import torch.nn as nn

# Define your architecture (must match the baseline)
class DQNAgent(nn.Module):
    def __init__(self, input_dim, output_dim):
        super(DQNAgent, self).__init__()
        self.fc = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Linear(128, output_dim)
        )
    def forward(self, x):
        return self.fc(x)

# Initialize and load weights
model = DQNAgent(input_dim=10, output_dim=4)
model.load_state_dict(torch.load("/kaggle/input/kaggriculture-dqn-weights/pytorch/pytorch-v1/3/dqn_baseline_weights.pth"))
model.eval()

print("🚜 Model loaded successfully and ready for inference!")
```

## 📊 Performance Metrics
- **Initial Elo**: ~1200+ (Out-of-the-box performance)
- **Convergence**: Achieved in 5M frames during pre-training.

If you find this model helpful, please give it an **Upvote**! Happy farming! 🌾
