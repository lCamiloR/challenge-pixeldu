from RPA.Browser.Selenium import Selenium

class ExtendedSelenium(Selenium):

    def __init__(self, *args, **kwargs):
        Selenium.__init__(self, *args, **kwargs)
    
    def start_driver(self, *args, **kwargs) -> None:
        """Opens available Chrome and starts the driver.

        Args:
            url (str): Url to be requested.
        """
        self.open_chrome_browser(*args, **kwargs)
        
    def wait_element_enabled_and_click(self, locator:str, *, timeout=30) -> None:
        """Wait for DOM element enabled according to given locator, then waits for it to be clickable.
            If true, executes click.

        Args:
            timeout (int, optional): WebDriverWait timeout. Defaults to 30.
        """
        self.wait_until_element_is_enabled(locator, timeout)
        self.click_element_when_clickable(locator, timeout)
    
    def wait_element_enabled_and_input_text(self, locator:str, text:str, *,  timeout=30) -> None:
        """Wait for DOM element enabled according to given locator, when enabled sends input text.

        Args:
            locator (str): Targets the element to be clicked.
            text (str): Text to inserted.
            timeout (int, optional): WebDriverWait timeout. Defaults to 30.
        """
        self.wait_until_element_is_enabled(locator, timeout)
        self.input_text_when_element_is_visible(locator, text)
    
    def wait_element_enabled_and_get_attribute(self, locator:str, attribute:str, *,  timeout=30):
        """Wait for DOM element enabled according to given locator, when enabled get the given attribute.

        Args:
            locator (str): Targets the element to be clicked.
            attribute (str): Target attribute.
            timeout (int, optional): WebDriverWait timeout. Defaults to 30.
        """
        self.wait_until_element_is_enabled(locator, timeout)
        return self.get_element_attribute(locator, attribute)


if __name__ == "__main__":
    pass