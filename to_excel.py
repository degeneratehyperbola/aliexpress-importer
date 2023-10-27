import sys, pyperclip
from aliexpress_importer import *

print('=' * 60)
print('DOUBLE CHECK PRODUCT PRICES!!! THEY MAY BE WRONG!!!')
print('=' * 60)

if len(sys.argv) != 2:
	print(f'Usage: py {sys.argv[0]} <urls_separated_by_newline.txt>')
	print(f'Creates and copies an excel table with some product info that is fetched from a given url')
	quit(1)

with open(sys.argv[1], 'r') as f:
	urls = [url for url in f.read().splitlines() if url.strip()[0] != '#']

IMPORTER = Importer()

excel_table = ""

with open('backup_clipboard.txt', 'w+', encoding='utf-8') as f:
	for url in urls:
		tries = 0
		p = None
		while tries < 10:
			try:
				p = IMPORTER.import_product(url)
			except Exception as e:
				print(type(e).__name__, e)
				print('Retrying...' if tries < 9 else 'Proceeding...')
			else:
				break
			tries += 1

		if not p:
			continue

		line = [
			p.name,
			f'"=HYPERLINK(""{url}"",""X"")"',
			min(max(p.skus[0].discount_price, p.skus[0].calculated_price), p.skus[0].full_price),
			p.shipping_fee,
			'#',
			'#',
			'9.99',
			'10',
			'.13'
		]
		linestr = '\t'.join([str(v) for v in line]) + '\n'
		excel_table += linestr
		f.write(linestr)

pyperclip.copy(excel_table)
