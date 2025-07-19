# PyGetURL

Sebuah tools untuk dapat menggunakan module python melalui url seperti layaknya Golang.

## How to install

```bash
pip install ./pygeturl
# or
pip install -e .
```

## How to run

```bash
# contoh
pygeturl install https://raw.githubusercontent.com/fadhelmurphy/sheesh-man/refs/heads/master/app.py as url_mod
# atau
pygeturl install fadhelmurphy/sheesh-man/app.py as sheesh_man # berlaku hanya di github
```

otomatis akan generate file py.mod di project. seperti ini hasil dari file py.mod

```bash
[project]
name = "pyget_project"
version = "0.1.0"

[dependencies]
url_mod = "https://raw.githubusercontent.com/fadhelmurphy/sheesh-man/refs/heads/master/app.py"
sheesh_man = "fadhelmurphy/sheesh-man@master/app.py"
```

## lalu bagaimana penggunaannya?

misalkan disini saya memiliki file `example.py`

```python
import pandas
import pygeturl.importer # ini wajib di import agar dapat menggunakan url module
import url_mod # nama alias module
import sheesh_man
import numpy

print(url_mod.list_ssh_keys())
print(sheesh_man.list_ssh_keys())

```

maka ketika menjalankan `example.py` akan menghasilkan output yang berasal dari url module
```bash
python example.py
```