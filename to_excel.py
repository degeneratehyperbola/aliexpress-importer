import sys, pyperclip
from aliexpress_importer import *

print('=' * 60)
print('DOUBLE CHECK PRODUCT PRICES!!! THEY MAY BE WRONG!!!')
print('=' * 60)

if len(sys.argv) != 2:
	print(f'Usage: py {sys.argv[0]} <urls.txt>')
	quit(1)

with open(sys.argv[1], 'r') as f:
	urls = [url for url in f.read().splitlines() if url.strip()[0] != '#']

IMPORTER = Importer()

excel_table = ''

with open('backup_clipboard.txt', 'w+', encoding='utf-8') as f:
	for url in urls:
		p: Product = None
		for tries in range(10):
			try:
				p = IMPORTER.import_product(url)
			except Exception as e:
				print(type(e).__name__, e)
				print('Retrying...' if tries < 9 else 'Proceeding...')
			else:
				break

		if p:
			line = [
				p.name,
				f'=HYPERLINK("{url}","X")',
				p.skus[1].full_price,
				p.shipping_fee,
				1,
				(p.shipping_fee + p.skus[1].full_price) * 1.5 + .13 * 9.99,
				.13
			]
			line = '\t'.join([str(v) for v in line]) + '\n'
			excel_table += line

			f.write(line)

pyperclip.copy(excel_table)
