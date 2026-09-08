import numpy as np
import matplotlib.pyplot as plt

# функция сигмоида с параметром "чувствительности" k
def sigmoid(x, k=1):
    return 1 / (1 + np.exp(-k * x))

# диапазон входных значений
x = np.linspace(-6, 6, 200)

# три варианта чувствительности
y1 = sigmoid(x, k=0.5)  # "ленивый" нейрон
y2 = sigmoid(x, k=1)    # обычный
y3 = sigmoid(x, k=3)    # "вспыльчивый" нейрон

# рисуем графики
plt.plot(x, y1, label='k = 0.5 (плавный)')
plt.plot(x, y2, label='k = 1 (нормальный)')
plt.plot(x, y3, label='k = 3 (резкий)')

plt.title('Влияние чувствительности (k) на форму сигмоиды')
plt.xlabel('Сигнал (x)')
plt.ylabel('Выход нейрона (σ)')
plt.legend()
plt.grid(True)
plt.show()
