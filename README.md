# PyImport

Sebuah tools untuk dapat menggunakan module python melalui url seperti layaknya Golang.

## How to install

```bash
pip install ./pyimporter
# or
pip install -e .
```

## How to run

```bash
# contoh
pyget install fadhelmurphy/monorepo-python-and-javascript-package@master/py/packages/python-package1/python_package1/module.py as hello_mod
```

otomatis akan generate file py.mod di project. seperti ini hasil dari file py.mod

```bash
[project]
name = "pyget_project"
version = "0.1.0"

[dependencies]
hello_mod = "fadhelmurphy/monorepo-python-and-javascript-package@master/py/packages/python-package1/python_package1/module.py"
```

## lalu bagaimana penggunaannya?

misalkan disini saya memiliki file `example.py`

```python
import pandas
import pyimporter.importer # ini wajib di import agar dapat menggunakan url module
import hello_mod # nama alias module
import numpy

print(hello_mod.hello())
```

maka ketika menjalankan `example.py` akan menghasilkan output yang berasal dari url module
```bash
python example.py
# outputnya : Hello, World!
```