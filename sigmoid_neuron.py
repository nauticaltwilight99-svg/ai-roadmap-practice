import numpy as np

# Сигмоида — функция активации
def sigmoid(x):
    return 1 / (1 + np.exp(-x))

# Входные данные
inputs = np.array([0.9, 0.2, 0.8])

# Веса
weights = np.array([0.7, -0.3, 0.6])

# Смещение
bias = 0.1

# Линейная комбинация: сумма(вход * вес) + смещение
linear_output = np.dot(inputs, weights) + bias

# Пропускаем результат через сигмоиду
output = sigmoid(linear_output)

# Выводим результаты
print("Линейный выход (до сигмоиды):", linear_output)
print("После функции сигмоиды:", output)
