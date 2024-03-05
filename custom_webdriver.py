from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver import Keys, ActionChains
from selenium.common import exceptions as selenium_exceptions
from selenium.webdriver.remote.webdriver import WebElement
import logging
from RPA.core.webdriver import download, start


class ChromeBrowser:

    def __init__(self, *, default_language: str = None, default_download_path=None):

        self.driver = None
        self.logger = logging.getLogger(__name__)
        self.__chrome_options = webdriver.ChromeOptions()
        self.__chrome_options.add_argument("--no-first-run")
        self.__chrome_options.add_argument('--disable-infobars')
        self.__chrome_options.add_argument('--ignore-certificate-errors')
        self.__chrome_options.add_argument('--disable-component-update')
        self.__chrome_options.add_argument("--no-default-browser-check")
        self.__chrome_options.add_argument("--disable-session-crashed-bubble")
        self.__chrome_options.add_argument('--start-maximized')
        self.__chrome_options.add_argument('--no-sandbox')
        self.__chrome_options.add_argument('--remote-debugging-port=9222')
        self.__chrome_options.add_argument('--disable-web-security')
        self.__chrome_options.add_argument("--disable-extensions")
        self.__chrome_options.add_argument("--disable-gpu")
        self.__chrome_options.add_argument('--headless')
        self.__preferences = {'download.directory_upgrade': True}

        self.__preferences['profile.default_content_settings.cookies'] = False

        if not default_language:
            self.__chrome_options.add_argument(f"--lang=en-us")
        else:
            self.__chrome_options.add_argument(f"--lang={default_language}")

        if default_download_path:
            self.__preferences['download.default_directory'] = default_download_path

    def start_driver(self):
        """Downloads driver for available Chrome version and starts the driver.
        """

        downloaded_driver_path = download("Chrome")
        driver_service = Service(downloaded_driver_path)

        self.driver = start("Chrome", driver_service,
                            options=self.__chrome_options)
        self.logger.info("WebDriver started.")

    def kill(self):
        if self.driver:
            self.driver.close()

    def get_wait_page(self, url: str, parameter: dict = None, *, timeout=30) -> str:
        """This function will access the given URL and wait it to load based on a given parameter.

        Args:
            url (str): Url to be requested
            parameter (dict, optional): EC function to used as the parameter for the WebDriverWait. Defaults to None.
            timeout (int, optional): WebDriverWait timeout. Defaults to 30.

        Returns:
            url (str): Return the given url arg when successful
        """
        old_url = self.driver.current_url
        self.driver.get(url)
        wait = WebDriverWait(self.driver, timeout)
        wait.until(EC.url_changes(old_url))
        if parameter is not None:
            parameter = parameter.popitem()
            search_parameter = eval(f'EC.{parameter[0]}')
            search_parameter_value = parameter[1]
            if wait.until(search_parameter(search_parameter_value)):
                return url
        else:
            return url

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

    @property
    def driver(self):
        return self._driver

    @driver.setter
    def driver(self, value):
        types = (webdriver.chrome.webdriver.WebDriver, webdriver.remote.webdriver.WebDriver)
        if value is None or isinstance(value, types):
            self._driver = value
        else:
            raise ValueError(f"Driver value can't be instance of {type(value)}")


class Error(Exception):
    """Base class for other exceptions"""
    pass


class InvalidInputError(Exception):
    def __init__(self, message, received_type=None, received_value=None):
        self.message = message
        self.received_type = received_type
        self.received_value = received_value
        super().__init__(self.message)


class NoElementFoundError(Error):
    """Raised when no file is found"""
    pass

if __name__ == "__main__":
    pass