from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json, re

driver = None

def setup():
	# Set up the Selenium headless web driver (browser)
	print('Setting up headless browser...')
	options = Options()
	options.headless = True
	global driver
	driver = webdriver.Chrome(options=options)

def cleanup():
	print('Cleaning up...')
	driver.quit()
	print('Done!')

def get_json(product_url):
	assert driver

	print(f'Scraping {product_url}...')
	driver.get(product_url)

	# Wait for the page to load the necessary element
	wait = WebDriverWait(driver, 10)
	wait.until(EC.presence_of_element_located((By.XPATH, '//script[contains(text(),"window.runParams")]')))
	
	# We use a convenient json object with all the info about the product inside of `window.runParams` variable. This variable is inaccessible from our DOM but the definition of it is inside some `script` tag
	data_text = driver.find_element(By.XPATH, '//script[contains(text(),"window.runParams")]').get_attribute('innerHTML').strip()
	data_match = re.search('data: ({.+?}),\n', data_text)

	if not data_match:
		raise ValueError(f'Failed to parse product data from {product_url}. Are you on a product page?')
	
	data = json.loads(data_match.group(1))

	if 'skuModule' not in data:
		raise ValueError(f'Failed to find product variants on {product_url}. Are you on a product variant page instead of the parent product page?')

	variant_count = len(data['skuModule']['skuPriceList'])

	if 'shippingModule' not in data:
		raise ValueError('Failed to find shipping info. Are you on a product variant page instead of the parent product page?')

	shipping_info = data['shippingModule']['generalFreightInfo']['originalLayoutResultList'][0]['bizData']

	# Set up our own product dictionary
	product = {
		'name': data['titleModule']['subject'],
		'id': data['actionModule']['productId'],
		'images': data['imageModule']['imagePathList'],
		'currency': data['commonModule']['currencyCode'],
		'shipping_fee': 0 if shipping_info['shippingFee'].lower() == 'free' else shipping_info['displayAmount'],
		'variants': [None] * variant_count
	}


	# Fill in the info about product variants
	for i, sku in enumerate(data['skuModule']['skuPriceList']):
		product['variants'][i] = {
			'name': sku['skuAttr'].split(';')[0].split('#', 1)[1],
			'id': sku['skuId'],
			'available': sku['skuVal']['availQuantity'],
			'full_price': sku['skuVal']['skuAmount']['value'], # Almost always false price, only truthful if `original_price==full_price`
			'original_price': float(sku['skuVal']['skuCalPrice']),
			'discount_price': sku['skuVal']['skuActivityAmount']['value']
		}

	# We need to iterate over another list containing product variants info and match names to the list created and filled earlier in order to fill image data
	for sku in data['skuModule']['productSKUPropertyList'][0]['skuPropertyValues']:
		try:
			name = sku['propertyValueDefinitionName']
			variant = next(v for v in product['variants'] if v['name'] == name)
		except:
			print(f"{name} failed to match image data!")
			continue

		variant['image'] = sku['skuPropertyImagePath']
	
	with open('data.json', 'w+') as f:
		json.dump(data, f, sort_keys=True, indent='\t')
	with open('product.json', 'w+') as f:
		json.dump(product, f, sort_keys=True, indent='\t')

	return product
