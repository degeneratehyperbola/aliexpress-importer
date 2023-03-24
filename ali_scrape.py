from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json, re, sys

try:
	if len(sys.argv) < 2:
		raise ValueError(f'Usage: py {sys.argv[0]} <url>')

	url = sys.argv[1]

	# Set up the Selenium headless web driver (browser)
	print('Setting up headless Chrome...')

	chrome_options = Options()
	chrome_options.add_argument('--headless')
	driver = webdriver.Chrome(options=chrome_options)

	print(f'Fetching {url}...')
	driver.get(url)

	# Wait for the page to load the necessary element
	print('Waiting for data...')

	wait = WebDriverWait(driver, 10)
	wait.until(EC.presence_of_element_located((By.XPATH, '//script[contains(text(),"window.runParams")]')))

	print('Found tag!')

	# We use a convenient json object with all the info about the product inside of `window.runParams` variable. This variable is inaccessible from our DOM but the definition of it is inside some `script` tag
	print('Parsing...')

	data_text = driver.find_element(By.XPATH, '//script[contains(text(),"window.runParams")]').get_attribute('innerHTML').strip()
	data_match = re.search('data: ({.+?}),\n', data_text)

	if not data_match:
		raise ValueError('Failed to parse product data. Are you on a product page?')

	data = json.loads(data_match.group(1))

	print('Checking product variants...')

	if 'skuModule' not in data:
		raise ValueError('Failed to find product variants. Are you on a product variant page instead of the parent product page?')
	variant_count = len(data['skuModule']['skuPriceList'])

	print(f'{variant_count} variant(s) found')
	print('Searching for shipping info...')
	
	if 'shippingModule' not in data:
		raise ValueError('Failed to find shipping info. Are you on a product variant page instead of the parent product page?')
	
	shipping_info = data['shippingModule']['generalFreightInfo']['originalLayoutResultList'][0]['bizData']

	# Set up our own product dictionary
	product = {
		'name': data['titleModule']['subject'],
		'id': data['actionModule']['productId'],
		'currency': data['commonModule']['currencyCode'],
		'shipping_fee': 0 if shipping_info['shippingFee'].lower() == 'free' else shipping_info['displayAmount'],
		'variants': [None] * variant_count
	}

	print('\nProduct info:')
	for key, value in product.items():
		if key == 'variants':
			continue

		print(f'\t{" ".join(key.split("_")).capitalize()}: {value}')

	# Fill in the info about product variants
	print('Iterating through product variants...')

	for i, sku in enumerate(data['skuModule']['skuPriceList']):
		product['variants'][i] = {
			'name': sku['skuAttr'].split('#', 1)[1].split(';', 1)[0],
			'id': sku['skuId'],
			'available': sku['skuVal']['availQuantity'],
			'full_price': sku['skuVal']['skuAmount']['value'],
			'discount_price': sku['skuVal']['skuActivityAmount']['value'],
			'unknown_price': float(sku['skuVal']['skuCalPrice'])
		}

	# Dump it into json
	# Idk for reading purposes
	print('Writing to file...')

	with open('product.json', 'wt') as f:
		json.dump(product, f, indent='\t')

	driver.quit()
	print('Done!')

except Exception as e:
	print(f'An error occured: {e}')
