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
		
		self.driver.get(product_url)
		
		# We use a convenient JS object that the developers of Ali left us :3
		script_element = self.driver.find_element(By.XPATH, '//script[contains(text(),"window.runParams")]')
		script = script_element.get_attribute('innerHTML')
		# Put product data into a separate variable so it is left untouched by Ali
		script = script.replace('runParams', 'hijackedRunParams')
		self.driver.execute_script(script)
		data = self.driver.execute_script('return window.hijackedRunParams.data')

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

		return product
