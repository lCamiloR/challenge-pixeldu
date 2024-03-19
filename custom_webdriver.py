from RPA.Browser.Selenium import Selenium
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver import Keys, ActionChains
from selenium.common import exceptions as selenium_exceptions
from selenium.webdriver.remote.webdriver import WebElement
import logging


class ChromeBrowser:

    def __init__(self):
        self.driver = None
        self.logger = logging.getLogger(__name__)

    def start_driver(self, url:str) -> None:
        """Opens available Chrome and starts the driver.

        Args:
            url (str): Url to be requested.
        """
        browser = Selenium(auto_close=False)
        browser.open_chrome_browser(url, headless=True)
        self.driver = browser.driver
        self.logger.info("WebDriver started.")

    def kill(self) -> None:
        if self.driver:
            self.driver.close()

    def element(self, find_by=By.ID, value: str = None):
        return self.__Element(web_props=self, find_by=find_by, value=value)

    class __Element:
        def __init__(self, *, web_props, find_by, value):
            self.web_props = web_props
            self.find_by=find_by
            self.search_value=value

            self.ignorable_exceptions = [selenium_exceptions.ElementNotInteractableException,
                                         selenium_exceptions.ElementClickInterceptedException,
                                         selenium_exceptions.StaleElementReferenceException]
            
        def find_element(self) -> WebElement:
            """Search web element according to given locators.

            Returns:
                WebElement: Located web element.
            """
            element = self.web_props.driver.find_element(self.find_by, self.search_value)
            return element
            
        def wait_element_to_be_present(self, *, timeout=30) -> WebElement:
            """Wait web element to be present in the DOM according to given locators.

            Args:
                timeout (int, optional): WebDriverWait timeout. Defaults to 30.

            Returns:
                WebElement: Located web element.
            """
            wait = WebDriverWait(self.web_props.driver, timeout, ignored_exceptions=self.ignorable_exceptions)
            element = wait.until(EC.presence_of_element_located((self.find_by, self.search_value)))
            return element
        
        def wait_element_to_be_clickable(self, *, timeout=30) -> WebElement:
            """Search element in the DOM according to given locators, then waits for it to be clickable.

            Args:
                timeout (int, optional): WebDriverWait timeout. Defaults to 30.

            Returns:
                WebElement: Located web element.
            """
            wait = WebDriverWait(self.web_props.driver, timeout, ignored_exceptions=self.ignorable_exceptions)
            element = wait.until(EC.element_to_be_clickable((self.find_by, self.search_value)))
            return element
        
        def click(self, *, timeout=30) -> None:
            """Search element in the DOM according to given locators, then waits for it to be clickable.
               If true, executes click.

            Args:
                timeout (int, optional): WebDriverWait timeout. Defaults to 30.
            """
            wait = WebDriverWait(self.web_props.driver, timeout, ignored_exceptions=self.ignorable_exceptions)
            element = wait.until(EC.element_to_be_clickable((self.find_by, self.search_value)))
            self.web_props.driver.execute_script("arguments[0].scrollIntoView();", element)
            wait.until(lambda d : element.click() or True)
        
        def send_keys(self, keys:str, *, timeout=30) -> None:
            """Wait for element in the DOM according to given locators, then sends the given keys to the element.

            Args:
                keys (str): Desired key combination.
                timeout (int, optional): WebDriverWait timeout. Defaults to 30.
            """
            wait = WebDriverWait(self.web_props.driver, timeout, ignored_exceptions=self.ignorable_exceptions)
            element = wait.until(EC.presence_of_element_located((self.find_by, self.search_value)))
            self.web_props.driver.execute_script("arguments[0].scrollIntoView();", element)
            wait.until(lambda d : element.send_keys(keys) or True)

        def send_action_key_enter(self, *, timeout=30) -> None:
            """Wait for element in the DOM according to given locators, then simulates the 'ENTER' key to the element.

            Args:
                timeout (int, optional): WebDriverWait timeout. Defaults to 30.
            """
            wait = WebDriverWait(self.web_props.driver, timeout, ignored_exceptions=self.ignorable_exceptions)
            element = wait.until(EC.presence_of_element_located((self.find_by, self.search_value)))
            self.web_props.driver.execute_script("arguments[0].scrollIntoView();", element)
            ActionChains(self.web_props.driver)\
                .key_down(Keys.ENTER)\
                .key_up(Keys.ENTER)\
                .perform()
        
        def get_element_attribute(self, attribute:str, *, timeout=30) -> str:
            """Wait for element in the DOM according to given locators, then returns the value of the given attribute name.

            Args:
                attribute (str): Name of the desired attribute.
                timeout (int, optional): WebDriverWait timeout. Defaults to 30.

            Returns:
                str: Return value of the get_attribute() function.
            """
            wait = WebDriverWait(self.web_props.driver, timeout, ignored_exceptions=self.ignorable_exceptions)
            element = wait.until(EC.presence_of_element_located((self.find_by, self.search_value)))
            attribute_value = wait.until(lambda d : element.get_attribute(attribute) or True)
            return attribute_value


if __name__ == "__main__":
    pass