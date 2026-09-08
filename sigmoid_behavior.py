import numpy as np

# Функция сигмоида
def sigmoid(x):
    return 1 / (1 + np.exp(-x))

# Разные значения "сигнала"
signals = np.array([-5, -2, -1, 0, 1, 2, 5])

# Применяем сигмоиду к каждому значению
outputs = sigmoid(signals)

# Выводим результаты
for s, o in zip(signals, outputs):
    print(f"Сигнал: {s:>2} → После сигмоиды: {o:.4f}")
