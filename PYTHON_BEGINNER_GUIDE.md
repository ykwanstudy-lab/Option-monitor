## Python Beginner Guide (Hands-on, No Jargon)

This short course gets you productive with Python fast. You’ll learn the core syntax, data types, control flow (if/for/while), functions, classes, error handling, files, and packaging. Examples are simple and copy‑paste friendly.

### 1) Running Python
- Check version: `python --version`
- Run a file: `python your_script.py`
- REPL (interactive): run `python` and type expressions to see results.

### 2) Variables and Types
- Dynamic typing: variable types are inferred.
```python
name = "Ada"          # str
age = 36               # int
height = 1.70          # float (meters)
is_engineer = True     # bool
```
- None means “no value”.
```python
middle_name = None
```

### 3) Strings and f-strings
- Strings use quotes; f-strings inject variables.
```python
first = "Ada"
last = 'Lovelace'
full = f"{first} {last}"   # "Ada Lovelace"
greeting = f"Hi {first}, 2+3={2+3}"
```

### 4) Lists, Tuples, Dicts, Sets
```python
# List (ordered, mutable)
nums = [10, 20, 30]
nums.append(40)

# Tuple (ordered, immutable)
point = (10, 20)

# Dict (key/value map)
person = {"name": "Ada", "age": 36}
person["role"] = "pioneer"

# Set (unique items)
unique = {"A", "B", "A"}  # {"A", "B"}
```

### 5) If, Elif, Else
```python
score = 87
if score >= 90:
    grade = "A"
elif score >= 80:
    grade = "B"
else:
    grade = "C"
```

### 6) For and While Loops
```python
# For over list
for n in [1, 2, 3]:
    print(n)

# Range of numbers (0..4)
for i in range(5):
    print(i)

# While until condition breaks
i = 0
while i < 3:
    print(i)
    i += 1
```

### 7) Functions
```python
def add(a, b):
    return a + b

def greet(name: str, excited: bool = False) -> str:
    msg = f"Hello, {name}"
    return msg + "!" if excited else msg

print(add(2, 3))            # 5
print(greet("Ada", True))  # Hello, Ada!
```

### 8) Exceptions (try/except)
```python
try:
    x = int("not-a-number")
except ValueError as e:
    print("Conversion failed:", e)
finally:
    print("This always runs")
```

### 9) Files and JSON
```python
from pathlib import Path
import json

data = {"name": "Ada", "skills": ["math", "programming"]}
Path("data.json").write_text(json.dumps(data, indent=2))

loaded = json.loads(Path("data.json").read_text())
print(loaded["name"])  # Ada
```

### 10) Classes and Objects
```python
class Counter:
    def __init__(self, start: int = 0):
        self.value = start

    def inc(self, step: int = 1) -> None:
        self.value += step

    def __repr__(self) -> str:
        return f"Counter(value={self.value})"

c = Counter()
c.inc()
print(c)  # Counter(value=1)
```

### 11) Modules and Imports
- Put reusable code in a file, import it elsewhere.
```python
# utils.py
def double(x):
    return x * 2

# main.py
from utils import double
print(double(5))
```

### 12) Virtual Environments (good practice)
```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 13) Popular Libraries (used in your app)
- tkinter/ttkbootstrap: GUI and themed widgets
- yfinance: Yahoo Finance data
- pandas: tables and dataframes
- python-telegram-bot: send alerts
- futu-api: live option quotes

### 14) Style and Tips
- Use meaningful names (`entry_cost`, not `ec`).
- Small functions that do one thing.
- Catch exceptions you expect; don’t hide all errors.
- Prefer f-strings for readable formatting.

### 15) Mini Exercises
1) Write a function `is_even(n)` that returns True/False.
2) Read a JSON file of users `{name, age}` and print names of users age ≥ 18.
3) Class `Timer` that stores `start_time` and has method `elapsed()` in seconds.

You’re ready. Keep this guide handy and practice by editing small bits of your app.
