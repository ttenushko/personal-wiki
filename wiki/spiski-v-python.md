---
title: "Списки в Python"
tags: ["mutable", "heterogeneous", "indexed", "range", "string", "tuple", "append", "insert"]
source_url: ""
source_type: "text"
created_at: "2026-08-02T20:39:40.987203"
updated_at: "2026-08-02T20:41:50.638187"
---

# Списки в Python

## Основные характеристики

**Список (list)** — это упорядоченная, изменяемая коллекция объектов произвольных типов. В Python списки являются одной из самых используемых структур данных.

### Ключевые свойства
- **Упорядоченность** — элементы сохраняют порядок добавления
- **Изменяемость** — можно добавлять, удалять и менять элементы
- **Гетерородность** — могут содержать объекты разных типов
- **Индексация** — доступ к элементам по индексу (начиная с 0)
- **Динамический размер** — размер меняется по мере необходимости

---

## Создание списков

```python
# Пустой список
empty_list = []
empty_list = list()

# Список с элементами
numbers = [1, 2, 3, 4, 5]
mixed = [1, "hello", 3.14, True, [1, 2]]
from_range = list(range(5))        # [0, 1, 2, 3, 4]
from_string = list("hello")        # ['h', 'e', 'l', 'l', 'o']
from_tuple = list((1, 2, 3))       # [1, 2, 3]

# Генераторы списков (list comprehensions)
squares = [x**2 for x in range(10)]
evens = [x for x in range(20) if x % 2 == 0]
matrix = [[0 for _ in range(3)] for _ in range(3)]
```

---

## Доступ к элементам

### Индексация
```python
fruits = ["apple", "banana", "cherry", "date"]

fruits[0]    # "apple" (первый элемент)
fruits[-1]   # "date" (последний элемент)
fruits[-2]   # "cherry" (предпоследний)
```

### Срезы (slicing)
```python
fruits[1:3]      # ["banana", "cherry"] — с 1 по 2 (3 не включается)
fruits[:2]       # ["apple", "banana"] — от начала до 1
fruits[2:]       # ["cherry", "date"] — с 2 до конца
fruits[::2]      # ["apple", "cherry"] — каждый второй
fruits[::-1]     # ["date", "cherry", "banana", "apple"] — реверс
fruits[1:4:2]    # ["banana", "date"] — с 1 до 3 с шагом 2
```

---

## Изменение списков

### Изменение элементов
```python
fruits[0] = "apricot"
fruits[1:3] = ["blueberry", "cranberry"]  # замена среза
```

### Добавление элементов
```python
fruits.append("elderberry")           # в конец
fruits.insert(1, "blackberry")        # по индексу
fruits.extend(["fig", "grape"])       # расширение итерируемым объектом
fruits += ["honeydew"]                # конкатенация (in-place)
```

### Удаление элементов
```python
fruits.remove("banana")               # по значению (первое вхождение)
popped = fruits.pop()                 # удаляет и возвращает последний
popped = fruits.pop(1)                # удаляет и возвращает по индексу
del fruits[0]                         # удаление по индексу
del fruits[1:3]                       # удаление среза
fruits.clear()                        # полная очистка
```

---

## Основные методы списка

| Метод | Описание | Возвращает |
|-------|----------|------------|
| `append(x)` | Добавить x в конец | `None` |
| `extend(iterable)` | Расширить элементами iterable | `None` |
| `insert(i, x)` | Вставить x перед индексом i | `None` |
| `remove(x)` | Удалить первое вхождение x | `None` |
| `pop([i])` | Удалить и вернуть элемент i (по умолчанию последний) | элемент |
| `clear()` | Очистить список | `None` |
| `index(x[, start[, end]])` | Индекс первого вхождения x | int |
| `count(x)` | Количество вхождений x | int |
| `sort(key=None, reverse=False)` | Сортировка на месте | `None` |
| `reverse()` | Реверс на месте | `None` |
| `copy()` | Поместная копия (shallow) | новый список |

---

## Полезные функции и операции

```python
numbers = [3, 1, 4, 1, 5, 9, 2, 6]

len(numbers)           # 8 — длина
max(numbers)           # 9 — максимум
min(numbers)           # 1 — минимум
sum(numbers)           # 31 — сумма
sorted(numbers)        # [1, 1, 2, 3, 4, 5, 6, 9] — новый отсортированный список
reversed(numbers)      # итератор в обратном порядке
any(numbers)           # True — хотя бы один truthy
all(numbers)           # True — все truthy
enumerate(numbers)     # (0, 3), (1, 1), ...
zip([1,2], [3,4])      # (1, 3), (2, 4)
```

### Операторы
```python
[1, 2] + [3, 4]        # [1, 2, 3, 4] — конкатенация
[1, 2] * 3             # [1, 2, 1, 2, 1, 2] — повторение
2 in [1, 2, 3]         # True — проверка вхождения
5 not in [1, 2, 3]     # True — проверка отсутствия
[1, 2] == [1, 2]       # True — поэлементное сравнение
[1, 2] < [1, 3]        # True — лексикографическое сравнение
```

---

## Копирование списков

```python
original = [1, [2, 3], 4]

# Поместная копия (shallow copy)
shallow = original.copy()
shallow = original[:]
shallow = list(original)
shallow = [*original]

# Глубокая копия (deep copy)
import copy
deep = copy.deepcopy(original)
```

**Важно:** поместная копия копирует ссылки на вложенные объекты. Изменение вложенного объекта в копии отразится на оригинале.

---

## Типичные паттерны и идиомы

### Перебор с индексом
```python
for i, item in enumerate(items):
    print(f"{i}: {item}")

# С пользовательским стартом
for i, item in enumerate(items, start=1):
    ...
```

### Перебор нескольких списков
```python
names = ["Alice", "Bob", "Carol"]
ages = [25, 30, 35]

for name, age in zip(names, ages):
    print(f"{name} is {age} years old")
```

### Фильтрация и трансформация
```python
# Только чётные, в квадрате
result = [x**2 for x in numbers if x % 2 == 0]

# С ветвлением
labels = ["even" if x % 2 == 0 else "odd" for x in numbers]
```

### Распаковка
```python
first, *middle, last = [1, 2, 3, 4, 5]
# first=1, middle=[2, 3, 4], last=5

head, *tail = [1, 2, 3]
# head=1, tail=[2, 3]
```

### Удаление дубликатов с сохранением порядка
```python
# Python 3.7+ (dict сохраняет порядок)
unique = list(dict.fromkeys(items))

# Через set (порядок не сохраняется)
unique = list(set(items))
```

---

## Производительность

| Операция | Сложность |
|----------|-----------|
| `list[i]` / `list[i] = x` | O(1) |
| `append()` | O(1)* амортизированное |
| `insert(i, x)` / `pop(i)` | O(n) |
| `remove(x)` / `index(x)` | O(n) |
| `x in list` | O(n) |
| `sort()` | O(n log n) |
| `len(list)` | O(1) |

*При превышении выделенной памяти происходит реаллокация (обычно увеличение в ~1.125 раза).

### Советы по оптимизации
- Используйте `append()` вместо конкатенации `+` в циклах
- Для очередей используйте `collections.deque` (O(1) для `popleft()`)
- Для частого поиска `in` — рассмотрите `set`
- Генераторы списков быстрее циклов с `append()`

---

## Распространенные ошибки

```python
# ОШИБКА: изменение списка при итерации
for item in items:
    if condition(item):
        items.remove(item)  # Пропускает элементы!

# ПРАВИЛЬНО: создание нового списка
items = [item for item in items if not condition(item)]

# Или итерация по копии
for item in items[:]:
    if condition(item):
        items.remove(item)

# ОШИБКА: мутация аргумента по умолчанию
def add_item(item, lst=[]):
    lst.append(item)
    return lst

# ПРАВИЛЬНО
def add_item(item, lst=None):
    if lst is None:
        lst = []
    lst.append(item)
    return lst
```

---

## Связанные темы

- [[Кортежи (tuple)]] — неизменяемые последовательности
- [[Словари (dict)]] — ассоциативные массивы
- [[Множества (set)]] — уникальные коллекции
- [[Генераторы списков (list comprehensions)]]
- [[collections.deque]] — двусторонняя очередь
- [[itertools]] — инструменты для итераторов
- [[Сортировка в Python]] — `sorted()`, `list.sort()`, `key`
- [[Копирование объектов]] — shallow vs deep copy

---

## Краткая шпаргалка

```python
# Создание
lst = [1, 2, 3]

# Доступ
lst[0]        # первый
lst[-1]       # последний
lst[1:4]      # срез

# Изменение
lst.append(4)
lst.insert(0, 0)
lst.extend([5, 6])
lst.remove(2)
lst.pop()
del lst[0]

# Информация
len(lst)
lst.count(1)
lst.index(3)

# Порядок
lst.sort()
lst.reverse()
sorted(lst)   # новый список
```