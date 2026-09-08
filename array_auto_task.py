import numpy as np

# Создадим массив чисел от 1 до 10
arr = np.arange(1, 11)

print("Исходный массив:", arr)

# Арифметические операции
print("Умножаем на 2:", arr * 2)
print("Прибавляем 5:", arr + 5)
print("Вычитаем 3:", arr - 3)
print("Делим на 2:", arr / 2)

# Агрегация (обработка массива целиком)
print("Сумма элементов:", np.sum(arr))
print("Среднее значение:", np.mean(arr))
print("Максимум:", np.max(arr))
print("Минимум:", np.min(arr))