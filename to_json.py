import sys, json
from aliexpress_importer import *


print('=' * 60)
print('DOUBLE CHECK PRODUCT PRICES!!! THEY MAY BE WRONG!!!')
print('=' * 60)

if len(sys.argv) != 2:
	print(f'Usage: py {sys.argv[0]} <url>')
	quit(1)

IMPORTER = Importer()

tries = 0
p: Product = None
raw: dict = None
while tries < 10:
	try:
		raw = IMPORTER._import_product_raw(sys.argv[1])
		p = IMPORTER.import_product(sys.argv[1])
	except Exception as e:
		print(type(e).__name__, e)
		print('Retrying...' if tries < 9 else 'Proceeding...')
	else:
		break

	tries += 1

with open('raw.json', 'w+', encoding='utf-8') as f:
	json.dump(raw, f, indent='\t', ensure_ascii=False)

with open('product.json', 'w+', encoding='utf-8') as f:
	json.dump(p.asdict(), f, indent='\t', ensure_ascii=False)
