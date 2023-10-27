from logging import LogRecord
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import *
from dataclasses import dataclass, asdict
import webbrowser
import logging

__all__ = [
	'Product', 'Importer'
]


# Package init
LOGGER = logging.getLogger('aliexpress_importer')
LOGGER.setLevel(logging.DEBUG)

class _CustomHandler(logging.StreamHandler):
	def	format(self, record: LogRecord) -> str:
		bold = '\033[1m'
		color = bold
		reset = '\033[0m'
		if record.levelno >= logging.FATAL:
			color += '\033[93m\033[41m'
		elif record.levelno >= logging.ERROR:
			color += '\033[31m'
		elif record.levelno >= logging.WARNING:
			color += '\033[33m'
		elif record.levelno >= logging.INFO:
			color += '\033[34m'
		elif record.levelno >= logging.DEBUG:
			color += '\033[90m'
		
		return f'[{color}{record.levelname.upper():>8s}{reset} {bold}{record.name}{reset}] {record.msg}'

LOGGER.addHandler(_CustomHandler())


@dataclass
class Product:
	'''Describes and holds data about an AliExpress product.

	### Usage:
	```py
	product = IMPORTER.import_product('https://www.aliexpress.com/item/1005002013381252.html')
	json = product.asdict() # To turn this into a dictionary
	```
	'''

	@dataclass
	class PropertyValue:
		'''Possible value for a property (e.g. red, blue, plastic, metal).'''
		name: str
		id: int
		image_url: str

	@dataclass
	class Property:
		'''Property (e.g. color, material, size) of a product.'''
		name: str
		id: int
		values: list['Product.PropertyValue']
		'''Possible values for a property (e.g. red, blue, plastic, metal).'''

	@dataclass
	class PropValuePair:
		'''Used to match a property and its value.'''
		prop_id: int
		value_id: int

	@dataclass
	class StockKeepingUnit:
		id: int
		full_price: float
		'''Full price before the disount.'''
		discount_price: float
		'''Price after the discount.

		Note: this value is `-1` if no discount is present.
		'''
		calculated_price: float
		'''Unknown'''
		available_count: int
		prop_values: list['Product.PropValuePair']
		'''Properties of this product.
		
		See: `Product.Property`.
		'''
	
	asdict = asdict

	name: str
	id: int
	images: list[str]
	currency: str
	'''e.g. 'USD', 'PLN'.'''
	shipping_fee: float
	props: list[Property]
	'''Properties (e.g. color, material, size) of a product.'''
	skus: list[StockKeepingUnit]


class Importer:
	'''AliExpress importer.
	
	### Usage:
	```py
	IMPORTER = Importer()
	IMPORTER.import_product('https://www.aliexpress.com/item/1005002013381252.html')
	```
	'''

	def __init__(self):
		LOGGER.info('Setting up headless browser')
		options = Options()
		options.add_argument('--headless')
		options.add_argument('--remote-debugging-port=9222')
		self.driver = webdriver.Chrome(options=options)

	def __del__(self):
		LOGGER.info('Cleaning up')
		self.driver.quit()
		LOGGER.info('Done!')

	def _import_product_raw(self, url):
		LOGGER.info(f'Waiting for {url}')
		self.driver.get(url)

		# We use a convenient JS object that the developers of Ali left us :3
		try:
			wait = WebDriverWait(self.driver, 5)
			script_element = wait.until(EC.presence_of_element_located(
				(By.XPATH, '//script[contains(text(), "window.runParams")]')
			))
		except NoSuchElementException as e:
			LOGGER.fatal('Could not locate product data. Are you on a product page?')
			raise RuntimeError('Could not locate product data')
		
		script = script_element.get_attribute('innerHTML')

		# Put product data into a separate variable so it is left untouched by Ali
		script = script.replace('runParams', 'hijackedRunParams')
		self.driver.execute_script(script)

		return self.driver.execute_script('return window.hijackedRunParams.data')

	def import_product(self, url) -> Product:
		data = self._import_product_raw(url)

		LOGGER.info('Filling product data')

		shipping_data = data['webGeneralFreightCalculateComponent']['originalLayoutResultList'][0]['bizData']
		product = Product(
			name=data['productInfoComponent']['subject'],
			id=data['productInfoComponent']['id'],
			images=data['imageComponent']['imagePathList'],
			currency=data['currencyComponent']['currencyCode'],
			shipping_fee=0 if shipping_data['shippingFee'].lower() == 'free' else shipping_data['displayAmount'],
			props=[],
			skus=[]
		)

		LOGGER.debug(f'Product "{product.name}"')

		# Props
		for prop_data in data['skuComponent']['productSKUPropertyList']:
			values = []

			for prop_value_pair in prop_data['skuPropertyValues']:
				values.append(Product.PropertyValue(
					name=prop_value_pair['propertyValueDefinitionName'],
					id=prop_value_pair['propertyValueId'],
					image_url=prop_value_pair['skuPropertyImagePath'] if 'skuPropertyImagePath' in prop_value_pair else None
				))

			product.props.append(Product.Property(
				name=prop_data['skuPropertyName'],
				id=prop_data['skuPropertyId'],
				values=values
			))
		
		LOGGER.debug(f'Properties: {len(product.props)}')

		# SKUs
		for sku_data in data['priceComponent']['skuPriceList']:
			prop_values = []
			
			# property:value pairs
			for prop_value_pair in sku_data['skuAttr'].split(';'):
				prop_value_pair = prop_value_pair.split(':', 1)
				prop_value_pair[1] = prop_value_pair[1].split('#', 1)[0]
				prop_values.append(Product.PropValuePair(
					prop_id=int(prop_value_pair[0]),
					value_id=int(prop_value_pair[1])
				))

			product.skus.append(Product.StockKeepingUnit(
				prop_values=prop_values,
				id=sku_data['skuId'],
				available_count = sku_data['skuVal']['availQuantity'],
				full_price=sku_data['skuVal']['skuAmount']['value'],
				# Almost always the true price
				calculated_price=float(sku_data['skuVal']['skuCalPrice']),
				# First order discount price
				discount_price=sku_data['skuVal']['skuActivityAmount']['value']
				if 'skuActivityAmount' in sku_data['skuVal']
				else -1
			))

		LOGGER.debug(f'SKUs: {len(product.skus)}')

		return product
