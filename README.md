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
Fetches product data from URLs specified in `urls.txt` (separated by line break). Then copies an Excel table to the clipboard, which you can then paste into any excel table.

Usage:
```powershell
py ./to_excel.py <urls.txt>
```
