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

	prop_count = len(data['skuModule']['productSKUPropertyList'])
	variant_count = len(data['skuModule']['skuPriceList'])
	shipping_info = data['shippingModule']['generalFreightInfo']['originalLayoutResultList'][0]['bizData']

	# Set up our own product dictionary
	product = {
		'name': data['titleModule']['subject'],
		'id': data['actionModule']['productId'],
		'images': data['imageModule']['imagePathList'],
		'currency': data['commonModule']['currencyCode'],
		'shipping_fee': 0 if shipping_info['shippingFee'].lower() == 'free' else shipping_info['displayAmount'],
		'property_list': [None] * prop_count,
		'sku_list': [None] * variant_count
	}

	# Fill in info about product SKUs
	for i, sku_info in enumerate(data['skuModule']['skuPriceList']):
		product['sku_list'][i] = {
			'sku_properties': [var.split('#', 1)[1] for var in sku_info['skuAttr'].split(';')],
			'sku_id': sku_info['skuId'],
			'sku_available': sku_info['skuVal']['availQuantity'],
			# 'full_price': sku_info['skuVal']['skuAmount']['value'], # Almost always false price, only truthful if `original_price==full_price`
			'sku_original_price': float(sku_info['skuVal']['skuCalPrice']),
			'sku_discount_price': sku_info['skuVal']['skuActivityAmount']['value']
		}

	# Fill in info about product picakble parameters (e.g. color, size)
	for i, prop_definition in enumerate(data['skuModule']['productSKUPropertyList']):
		prop_value_count = len(prop_definition['skuPropertyValues'])
		
		product['property_list'][i] = {
			'prop_name': prop_definition['skuPropertyName'],
			'prop_values': [None] * prop_value_count
		}

		# Fill in possible values for the product parameter
		for j, prop_value_definition in enumerate(prop_definition['skuPropertyValues']):
			product['property_list'][i]['prop_values'][j] = {
				'prop_value_name': prop_value_definition['propertyValueDefinitionName'],
				'prop_value_image': prop_value_definition['skuPropertyImagePath'] if 'skuPropertyImagePath' in prop_value_definition else None
			}
	
	with open('data.json', 'w+') as f:
		json.dump(data, f, sort_keys=True, indent='\t')
	with open('product.json', 'w+') as f:
		json.dump(product, f, sort_keys=True, indent='\t')

	return product
