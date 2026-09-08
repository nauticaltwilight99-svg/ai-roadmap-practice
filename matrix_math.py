import numpy as np

# Создаём матрицу 3x3
matrix = np.array([
    [2, 4, 6],
    [8, 10, 12],
    [14, 16, 18]
])

print("Исходная матрица:\n", matrix)

# 1️⃣ Среднее значение всей матрицы
mean_value = np.mean(matrix)
print("\nСреднее значение:", mean_value)

# 2️⃣ Минимум и максимум
min_value = np.min(matrix)
max_value = np.max(matrix)
print("Минимум:", min_value)
print("Максимум:", max_value)

# 3️⃣ Стандартное отклонение (показывает разброс значений)
std_dev = np.std(matrix)
print("Стандартное отклонение:", std_dev)

# 4️⃣ Транспонирование (поворачивает матрицу)
transposed = matrix.T
print("\nТранспонированная матрица:\n", transposed)

# 5️⃣ Умножение матриц
B = np.array([
    [1, 0, 2],
    [0, 1, 2],
    [1, 0, 1]
])
product = np.dot(matrix, B)
print("\nРезультат умножения матриц:\n", product)
