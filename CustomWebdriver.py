from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from webdriver_manager.core.download_manager import WDMDownloadManager
from webdriver_manager.core.http import HttpClient
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.core.logger import log
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver import Keys, ActionChains
from selenium.common import exceptions as selenium_exceptions
from selenium.webdriver.remote.webdriver import WebElement
import requests
import os


class ChromeBrowser:

    def __init__(self, *, default_language: str = None, default_download_path=None, **kwargs):

        self.driver = None
        self.__chrome_options = webdriver.ChromeOptions()
        self.__chrome_options.add_argument("--no-first-run")
        self.__chrome_options.add_argument('--disable-infobars')
        self.__chrome_options.add_argument('--ignore-certificate-errors')
        self.__chrome_options.add_argument('--disable-component-update')
        self.__chrome_options.add_argument("--no-default-browser-check")
        self.__chrome_options.add_argument("--disable-session-crashed-bubble")
        self.__chrome_options.add_argument('--start-maximized')
        self.__preferences = {'download.directory_upgrade': True}

        self.__preferences['profile.default_content_settings.cookies'] = False

        if not default_language:
            self.__chrome_options.add_argument(f"--lang=en-us")
        else:
            self.__chrome_options.add_argument(f"--lang={self._default_language}")

        if default_download_path:
            self.__preferences['download.default_directory'] = self.default_download_path

        if kwargs.get("driver_manager_proxy"):
            self.__driver_manager_proxy = kwargs.get("driver_manager_proxy")
        else:
            self.__driver_manager_proxy = None

    class __CustomHttpClient(HttpClient):

        def __init__(self, *, proxies=None):
            self.proxies = proxies

        def get(self, url, params=None, **kwargs) -> requests.Response:
            log("The call will be done with custom HTTP client.")
            return requests.get(url, params, proxies=self.proxies, verify=False, **kwargs)

    def start_driver(self):

        if self.__driver_manager_proxy:
            http_client = self.__CustomHttpClient(proxies=self.__driver_manager_proxy)
            download_manager = WDMDownloadManager(http_client)
        else:
            download_manager = None
        
        downloaded_driver_path = ChromeDriverManager(download_manager=download_manager).install()
        driver_service = Service(downloaded_driver_path)

        self.driver = webdriver.Chrome(service=driver_service,
                                       options=self.__chrome_options)
        log("WebDriver started.")

    def kill(self):
        if self.driver:
            self.driver.close()

    def get_wait_page(self, url: str, parameter: dict = None, *, timeout=30):
        """
        This function will access the given URL and wait it to load based on a given parameter.
        :param parameter: dict
        :param timeout: int
        :param url: str
        :return: int
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
            element = self.web_props.driver.find_element(self.find_by, self.search_value)
            return element
            
        def wait_element_to_be_present(self, *, timeout=30) -> WebElement:
            wait = WebDriverWait(self.web_props.driver, timeout, ignored_exceptions=self.ignorable_exceptions)
            element = wait.until(EC.presence_of_element_located((self.find_by, self.search_value)))
            return element
        
        def wait_element_to_be_clickable(self, *, timeout=30) -> WebElement:
            wait = WebDriverWait(self.web_props.driver, timeout, ignored_exceptions=self.ignorable_exceptions)
            element = wait.until(EC.element_to_be_clickable((self.find_by, self.search_value)))
            return element
        
        def click(self, *, timeout=30) -> None:
            wait = WebDriverWait(self.web_props.driver, timeout, ignored_exceptions=self.ignorable_exceptions)
            element = wait.until(EC.element_to_be_clickable((self.find_by, self.search_value)))
            self.web_props.driver.execute_script("arguments[0].scrollIntoView();", element)
            wait.until(lambda d : element.click() or True)
        
        def send_keys(self, keys:str, *, timeout=30) -> None:
            wait = WebDriverWait(self.web_props.driver, timeout, ignored_exceptions=self.ignorable_exceptions)
            element = wait.until(EC.presence_of_element_located((self.find_by, self.search_value)))
            self.web_props.driver.execute_script("arguments[0].scrollIntoView();", element)
            wait.until(lambda d : element.send_keys(keys) or True)

        def send_action_key_enter(self, *, timeout=30) -> None:
            wait = WebDriverWait(self.web_props.driver, timeout, ignored_exceptions=self.ignorable_exceptions)
            element = wait.until(EC.presence_of_element_located((self.find_by, self.search_value)))
            self.web_props.driver.execute_script("arguments[0].scrollIntoView();", element)
            ActionChains(self.web_props.driver)\
                .key_down(Keys.ENTER)\
                .key_up(Keys.ENTER)\
                .perform()
            
        def get_all_elements(self, *, timeout=30) -> list:
            wait = WebDriverWait(self.web_props.driver, timeout, ignored_exceptions=self.ignorable_exceptions)
            elements = wait.until(EC.presence_of_all_elements_located((self.find_by, self.search_value)))
            return elements
        
        def get_element_attribute(self, attribute:str, *, timeout=30) -> str:
            wait = WebDriverWait(self.web_props.driver, timeout, ignored_exceptions=self.ignorable_exceptions)
            element = wait.until(EC.presence_of_element_located((self.find_by, self.search_value)))
            attribute_value = wait.until(lambda d : element.get_attribute(attribute) or True)
            return attribute_value
        
        def save_image_to_path(self, file_path:str, *, timeout=30) -> str:
            wait = WebDriverWait(self.web_props.driver, timeout, ignored_exceptions=self.ignorable_exceptions)
            element = wait.until(EC.presence_of_element_located((self.find_by, self.search_value)))
            wait.until(lambda d : element.is_displayed() or True)
            with open(file_path, 'wb') as file:
                file.write(element.screenshot_as_png)


    @property
    def default_download_path(self):
        return self._default_download_path

    @default_download_path.setter
    def default_download_path(self, dir_path):
        if dir_path and not os.path.isdir(dir_path):
            raise InvalidInputError("Argument 'dir_path' is not a valid system path.")
        self._default_download_path = dir_path

    @property
    def default_language(self):
        return self._default_language

    @default_language.setter
    def default_language(self, language):
        if not isinstance(language, str):
            raise InvalidInputError("Argument 'language' is not a string.")
        self._default_language = language


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
    # minimal_task()
    pass