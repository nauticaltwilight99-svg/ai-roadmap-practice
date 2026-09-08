import numpy as np

# Матрицы A и B
A = np.array([
    [2, 4, 6],
    [8, 10, 12],
    [14, 16, 18]
])

B = np.array([
    [1, 0, 2],
    [0, 1, 2],
    [1, 0, 1]
])

print("Матрица A:\n", A)
print("\nМатрица B:\n", B)
print("\n--- Пошаговое умножение ---\n")

# Создаём пустую матрицу для результата
rows, cols = A.shape[0], B.shape[1]
C = np.zeros((rows, cols), dtype=int)

# Поэлементное вычисление результата
for i in range(rows):
    for j in range(cols):
        # Берём i-ю строку из A и j-й столбец из B
        row = A[i, :]
        col = B[:, j]

        # Перемножаем элементы и суммируем
        products = row * col
        value = np.sum(products)

        # Сохраняем результат
        C[i, j] = value

        # Печатаем шаги
        print(f"C[{i},{j}] = ({row}) × ({col}) = {products} → сумма = {value}")

print("\nИтоговая матрица C = A @ B:\n", C)