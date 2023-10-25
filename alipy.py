from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import json, re
from dataclasses import dataclass

@dataclass
class Product:
	@dataclass
	class PropertyValue:
		image_url: str
		value: str

	@dataclass
	class Property:
		name: str
		values: list['Product.PropertyValue']

	@dataclass
	class StockKeepingUnit:
		id: int
		full_price: float
		discount_price: float
		calculated_price: float
		available_count: int
		prop_values: list['Product.PropertyValue']
	
	name: str
	id: int
	images: list[str]
	currency: str
	shipping_fee: float
	props: list[Property]
	skus: list[StockKeepingUnit]


class Importer:
	def __init__(self):
		# Set up the Selenium headless web driver (browser)
		print('Setting up headless browser...')
		options = Options()
		options.headless = True
		self.driver = webdriver.Chrome(options=options)

	def __del__(self):
		print('Cleaning up...')
		self.driver.quit()
		print('Done!')

	def import_from_url(self, product_url) -> Product:
		assert self.driver

		print(f'Scraping {product_url}...')
		self.driver.get(product_url)

		# Wait for the page to load the necessary element
		wait = WebDriverWait(self.driver, 10)
		wait.until(EC.presence_of_element_located((By.XPATH, '//script[contains(text(),"window.runParams")]')))
		
		# We use a convenient json object with all the info about the product inside of `window.runParams` variable. This variable is inaccessible from our DOM but the definition of it is inside some `script` tag
		data_text = self.driver.find_element(By.XPATH, '//script[contains(text(),"window.runParams")]').get_attribute('innerHTML').strip()
		data_match = re.search('data: ({.+?}),\n', data_text)

		if not data_match:
			raise ValueError(f'Failed to parse product data from {product_url}. Are you on a product page?')
		
		data = json.loads(data_match.group(1))

		if 'skuModule' not in data:
			raise ValueError(f'Failed to find product variants on {product_url}. Are you on a product variant page instead of the parent product page?')

		# Set up our own product
		prop_count = len(data['skuModule']['productSKUPropertyList'])
		variant_count = len(data['skuModule']['skuPriceList'])
		shipping_info = data['shippingModule']['generalFreightInfo']['originalLayoutResultList'][0]['bizData']

		product = Product(
			name = data['titleModule']['subject'],
			id = data['actionModule']['productId'],
			images = data['imageModule']['imagePathList'],
			currency = data['commonModule']['currencyCode'],
			shipping_fee = 0 if shipping_info['shippingFee'].lower() == 'free' else shipping_info['displayAmount'],
			props = [None] * prop_count,
			skus = [None] * variant_count
		)

		# Fill in info about product stock keeping units
		for i, sku_info in enumerate(data['skuModule']['skuPriceList']):
			product.skus[i] = Product.StockKeepingUnit(
				prop_values = [var.split('#', 1)[1] for var in sku_info['skuAttr'].split(';')],
				id = sku_info['skuId'],
				available_count = sku_info['skuVal']['availQuantity'],
				full_price = sku_info['skuVal']['skuAmount']['value'], # Full price which almost never is the price you pay, due to permanent discounts
				calculated_price = float(sku_info['skuVal']['skuCalPrice']), # Almost always the true price
				discount_price = sku_info['skuVal']['skuActivityAmount']['value'] # First order discounted price
			)

		# Fill in info about product picakble parameters (e.g. color, size)
		for i, prop_data in enumerate(data['skuModule']['productSKUPropertyList']):
			prop_value_count = len(prop_data['skuPropertyValues'])

			prop = Product.Property(
				name = prop_data['skuPropertyName'],
				values = [None] * prop_value_count
			)

			# Fill in possible values for the product parameter
			for j, prop_value_data in enumerate(prop_data['skuPropertyValues']):
				prop.values[j] = Product.PropertyValue(
					value = prop_value_data['propertyValueDefinitionName'],
					image_url = prop_value_data['skuPropertyImagePath'] if 'skuPropertyImagePath' in prop_value_data else None
				)

			product.props[i] = prop
		
		with open('data.json', 'w+') as f:
			json.dump(data, f, sort_keys=True, indent='\t')
		with open('product.json', 'w+') as f:
			json.dump(product, f, sort_keys=True, indent='\t')

		return product
