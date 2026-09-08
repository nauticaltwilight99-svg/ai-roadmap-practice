import numpy as np

# Входные данные (например, признаки объекта)
inputs = np.array([0.6, 0.8])
weights = np.array([0.5, 0.3])

# Список разных смещений (bias)
bias_values = [-1.0, 0.0, 1.0]

print("Входы:", inputs)
print("Веса:", weights)
print()

for b in bias_values:
    # Взвешенная сумма входов
    weighted_sum = np.dot(inputs, weights) + b

    # Простая активация: если результат > 0 → нейрон включился
    if weighted_sum > 0:
        output = 1
    else:
        output = 0

    print(f"Bias = {b:+.1f} → Взвешенная сумма = {weighted_sum:.2f} → Выход = {output}")
