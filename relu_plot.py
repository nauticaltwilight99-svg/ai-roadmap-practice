import numpy as np
import matplotlib.pyplot as plt

# Функция ReLU
def relu(x):
    return np.maximum(0, x)

# Диапазон входов
x = np.linspace(-6, 6, 200)
y = relu(x)

# Рисуем
plt.plot(x, y, label="ReLU", color="orange")
plt.title("ReLU (Rectified Linear Unit)")
plt.xlabel("Сигнал (x)")
plt.ylabel("Выход нейрона (f(x))")
plt.axhline(0, color="black", linewidth=0.7)
plt.axvline(0, color="black", linewidth=0.7)
plt.legend()
plt.grid(True)
plt.show()
