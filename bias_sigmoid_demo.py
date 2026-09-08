import numpy as np

# Функция активации — сигмоида
def sigmoid(x):
    return 1 / (1 + np.exp(-x))

# Входы и веса (примерные)
inputs = np.array([0.6, 0.8])
weights = np.array([0.5, 0.3])

# Три разных смещения
bias_values = [-1.0, 0.0, 1.0]

print("Входы:", inputs)
print("Веса:", weights)
print()

for b in bias_values:
    # Взвешенная сумма + bias
    weighted_sum = np.dot(inputs, weights) + b

    # Пропускаем через сигмоиду
    output = sigmoid(weighted_sum)

    print(f"Bias = {b:+.1f} → Взвешенная сумма = {weighted_sum:.2f} → Сигмоида = {output:.3f}")
