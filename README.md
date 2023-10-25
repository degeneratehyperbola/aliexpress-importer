# Aliexpress Importer
Retrieve product info from AliExpress in a form of a Python dictionary, or whatever the hell you want.


# Usage
### Setting up
```py
from aliexpress_importer import *

IMPORTER = Importer()
```

### Retrieving product data
```py
product: Product = IMPORTER.import_from_url(url)
```
Every data type comes with hinting.

### Turning data into a dictionary (JSON)
```py
product.asdict()
```


# Sample scripts
## `to_excel.py`

Copies an Excel format table to the clipboard, based on the input text file

Usage:
```bash
py ./to_excel.py <urls_separated_by_newlines.txt>
```
