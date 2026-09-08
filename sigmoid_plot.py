import numpy as np
import matplotlib.pyplot as plt

# Функция сигмоида
def sigmoid(x):
    return 1 / (1 + np.exp(-x))

# Диапазон входных значений
x = np.linspace(-6, 6, 200)

# Три варианта смещения (bias)
bias_values = [-2, 0, 2]

# Рисуем графики
plt.figure(figsize=(8, 5))
for b in bias_values:
    y = sigmoid(x + b)
    plt.plot(x, y, label=f"bias = {b}")

# Украшаем график
plt.title("Влияние смещения (bias) на сигмоиду")
plt.xlabel("Взвешенная сумма (x)")
plt.ylabel("Выход нейрона (сигмоида)")
plt.legend()
plt.grid(True)

plt.show()
