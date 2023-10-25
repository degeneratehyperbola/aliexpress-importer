from logging import LogRecord
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from dataclasses import dataclass
import json, re, logging

__all__ = [
	'Product', 'Importer'
]


# Package init
LOGGER = logging.getLogger('aliexpress_importer')
LOGGER.setLevel(logging.DEBUG)

class _CustomHandler(logging.StreamHandler):
	def	format(self, record: LogRecord) -> str:
		color = '\033[1m'
		reset = '\033[0m'
		if record.levelno >= logging.FATAL:
			color += '\033[93m\033[41m'
		elif record.levelno >= logging.ERROR:
			color += '\033[31m'
		elif record.levelno >= logging.WARNING:
			color += '\033[33m'
		elif record.levelno >= logging.INFO:
			color += '\033[34m'
		
		return f'[{color + record.levelname.upper() + reset}] {record.name} : {record.msg}'

LOGGER.addHandler(_CustomHandler())


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
		LOGGER.info('Setting up headless browser')
		options = Options()
		options.add_argument('--headless')
		self.driver = webdriver.Chrome(options=options)

	def __del__(self):
		LOGGER.info('Cleaning up')
		self.driver.quit()
		LOGGER.info('Done!')

	def import_from_url(self, product_url) -> Product:
		assert self.driver

		LOGGER.info(f'Waiting for {product_url}')
		self.driver.get(product_url)
		
		# We use a convenient JS object that the developers of Ali left us :3
		script_element = self.driver.find_element(By.XPATH, '//script[contains(text(),"window.runParams")]')
		script = script_element.get_attribute('innerHTML')
		# Put product data into a separate variable so it is left untouched by Ali
		script = script.replace('runParams', 'hijackedRunParams')
		self.driver.execute_script(script)
		data: dict = self.driver.execute_script('return window.hijackedRunParams.data')

		# Set up needed product data
		LOGGER.info('Filling product data')

		shipping_data = data['webGeneralFreightCalculateComponent']['originalLayoutResultList'][0]['bizData']
		product = Product(
			name = data['productInfoComponent']['subject'],
			id = data['productInfoComponent']['id'],
			images = data['imageComponent']['imagePathList'],
			currency = data['currencyComponent']['currencyCode'],
			shipping_fee = 0 if shipping_data['shippingFee'].lower() == 'free' else shipping_data['displayAmount'],
			props = [None] * len(data['skuComponent']['productSKUPropertyList']),
			skus = [None] * len(data['priceComponent']['skuPriceList'])
		)

		LOGGER.debug(f'Product "{product.name}"')
		LOGGER.debug(f'Properties: {len(product.props)}')
		LOGGER.debug(f'SKUs: {len(product.skus)}')

		# Fill in info about product stock keeping units
		for i, sku_data in enumerate(data['priceComponent']['skuPriceList']):
			product.skus[i] = Product.StockKeepingUnit(
				prop_values = [var.split('#', 1)[1] for var in sku_data['skuAttr'].split(';')],
				id = sku_data['skuId'],
				available_count = sku_data['skuVal']['availQuantity'],
				
				# Full price which almost never is the price you pay, due to permanent discounts
				full_price = sku_data['skuVal']['skuAmount']['value'],
				# Almost always the true price
				calculated_price = float(sku_data['skuVal']['skuCalPrice']),
				# First order discount price
				discount_price = sku_data['skuVal']['skuActivityAmount']['value']
				if 'skuActivityAmount' in sku_data['skuVal']
				else -1
			)

		# Fill in info about product picakble parameters (e.g. color, size)
		for i, prop_data in enumerate(data['skuComponent']['productSKUPropertyList']):
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

		# with open('data.json', 'w+', encoding='utf-8') as f: json.dump(data, f, sort_keys=True, indent='\t', ensure_ascii=False)

		return product
