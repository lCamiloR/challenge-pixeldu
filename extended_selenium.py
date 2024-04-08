from RPA.Browser.Selenium import Selenium
from RPA.HTTP import HTTP
from SeleniumLibrary.errors import ElementNotFound
from news import News
import logging
import re
import pandas as pd
import zipfile
import os
import datetime
from dateutil.relativedelta import relativedelta


class ExtendedSelenium(Selenium):

    def __init__(self, *args, **kwargs):
        Selenium.__init__(self, *args, **kwargs)
        self.logger = logging.getLogger(__name__)
    
    def start_driver(self, *args, **kwargs) -> None:
        """Opens available Chrome and starts the driver.

        Args:
            url (str): Url to be requested.
        """
        self.open_chrome_browser(*args, **kwargs)
        self.logger.info("WebDriver started.")
        
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
    
    def calc_search_time_range(self, number_of_months:int) -> tuple[str]:
        """Calculate the time range that must be applied at the search filter

        Args:
            number_of_months (int): Number os months to be considered at the filter

        Returns:
            tuple[str]: Maximum date (Most recent) followed by the minimum date (Oldest date)
        """

        max_date_obj = datetime.datetime.now().date()
        if isinstance(number_of_months, int) and number_of_months > 1:
            min_date_obj = max_date_obj - relativedelta(months=number_of_months - 1)
            min_date_obj = min_date_obj.replace(day=1)
        else:
            min_date_obj = datetime.datetime.now().replace(day=1)

        return max_date_obj.strftime("%m/%d/%Y"), min_date_obj.strftime("%m/%d/%Y")

    def execute_search(self, url:str, category:str, max_date_str:str, min_date_str:str) -> None:
        """Opens the news website and search for the search frase, than adds the specified filters.

        Args:
            url (str): Url to be requested
            category (str): News category to be selected during result filter
            max_date_str (str): Maximum date of the time range of search (Most recent date)
            min_date_str (str): Minimum date of the time range of search (Oldest date)
        """

        self.start_driver(url, headless=True, maximized=True)

        # Reject cookies
        self.wait_element_enabled_and_click('id:fides-banner-button-primary')

        # Order by newest
        sort_by_relevance_xpath = '//select[@data-testid="SearchForm-sortBy"]'
        self.wait_element_enabled_and_click(f'{sort_by_relevance_xpath}')
        self.wait_element_enabled_and_click(f'{sort_by_relevance_xpath}/option[@value="newest"]')

        # Open calendar
        self.wait_element_enabled_and_click('//button[@data-testid="search-date-dropdown-a"]')
        self.wait_element_enabled_and_click('//button[@aria-label="Specific Dates"]')

        # Enter time range
        self.wait_element_enabled_and_input_text('id:startDate', min_date_str)
        self.wait_element_enabled_and_input_text('id:endDate', max_date_str)
        self.press_keys('id:endDate', "ENTER")

        # Select desired category inside 'Section', if available
        if category:
            category = category.capitalize().replace(" ","")
            section_btn_xpath = f'//button[@data-testid="search-multiselect-button"]'
            target_section_xpath = f'//ul[@data-testid="multi-select-dropdown-list"]//span[contains(text(), "{category}")]'
            try:
                self.find_element(section_btn_xpath)
                self.wait_element_enabled_and_click(section_btn_xpath,
                                                    timeout=5)
            except ElementNotFound:
                self.logger.warning('The "Section" filter is not available.')
            else:
                try:
                    self.find_element(target_section_xpath)
                    self.wait_element_enabled_and_click(target_section_xpath, timeout=5)
                except ElementNotFound:
                    self.logger.warning(f'Category: {category} is not an valid option.')
                self.wait_element_enabled_and_click(section_btn_xpath)

        self.wait_until_page_does_not_contain_element(f'//p[@data-testid="SearchForm-status" and contains(text(), "Loading")]')
        self.logger.info('Search is completed.')

    def get_number_total_news(self) -> int:
        """Returns the number of total news found during search.

        Returns:
            int: number of news.
        """
        results_for_search = self.wait_element_enabled_and_get_attribute('//p[@data-testid="SearchForm-status"]',
                                                                         'innerText')
        macth_obj = re.search(r"out\sof\s(?P<value>[0-9\.\,]+)\sresults", results_for_search)
        if macth_obj:
            total_results = int(macth_obj.group('value').replace(",", "."))
        else:
            total_results = 0
        self.logger.info(f"Total news: {total_results}")
        return total_results

    def get_all_returned_news(self, total_results:int) -> list[News]:
        """Iterate all returned news capturing their titles, description and images.

        Args:
            total_results (int): Number of news to iterate.

        Returns:
            list[News]: List of News objects.
        """

        news_payload = []
        for iteration in range(1, total_results, 10):

            if (total_results - iteration) < 10:
                max_idx = total_results + 1
            else:
                max_idx = iteration + 10

            for idx in range(iteration, max_idx):
                news_xpath = f'//li[@data-testid="search-bodega-result"][position()={idx}]'
                title = self.wait_element_enabled_and_get_attribute(f'{news_xpath}//a/h4',
                                                                    'innerText')
                date = self.wait_element_enabled_and_get_attribute(f'{news_xpath}//span[@data-testid="todays-date"]',
                                                                    'innerText')

                try:
                    description_element = self.find_element(f'{news_xpath}//a/p[position()=1]')
                except ElementNotFound:
                    self.logger.warning(f"News at index {idx} doesn`t have description.")
                    description = None
                else:
                    description = self.wait_element_enabled_and_get_attribute(description_element, 'innerText')

                try:
                    image_element = self.find_element(f'{news_xpath}//div[@data-testid="imageContainer-children-Image"]/img')
                except ElementNotFound:
                    self.logger.warning(f"News at index {idx} doesn`t have image.")
                    img_url = None
                else:
                    img_url = self.wait_element_enabled_and_get_attribute(image_element, 'src')
                
                news_payload.append(
                    News(title, date, description, img_url)
                )

            try:
                show_more_btn = self.find_element('//button[@data-testid="search-show-more-button"]')
                self.wait_element_enabled_and_click(show_more_btn, timeout=3)
            except ElementNotFound:
                self.logger.info('The button "SHOW MORE" wasn`t found, no more news.')
                break

        return news_payload
    
    def download_images(self, returned_news:list[News], zip_name:str) -> None:
        """Downloads the image of each found news.

        Args:
            returned_news (list): News returned after search.
            zip_name (str): Name of the zip folder.
        """
        http = HTTP()
        with zipfile.ZipFile(f"output/{zip_name}", "w") as zf:
            for news in returned_news:
                if not news.img_url:
                    continue
                img_path = news.create_image_name('output')
                http.download(url=news.img_url, target_file = img_path, overwrite=True)
                zf.write(img_path, os.path.basename(img_path))
                os.remove(img_path)
        
        self.logger.info(f"Images ziped at output dir.")

    def write_output_excel(self, returned_news:list[News], search_phrase:str, file_name:str) -> None:
        """Writes the output excel.

        Args:
            returned_news (list): News returned after search.
            search_phrase (str): Phrase that will be searched on the website.
            file_name (str): Base name of the excel file.
        """
        new_list = []
        for news in returned_news:
            new_list.append(
                {
                    "Title": news.title,
                    "Date": news.date,
                    "Description": news.description if news.description else "** No description on Website **",
                    "Image name": os.path.basename(news.img_local_path) if news.img_url else "** No image on Website **",
                    "Search frase count": news.count_search_phrase(search_phrase),
                    "Is money mentioned?": news.is_money_mentioned()
                }
            )
        df = pd.DataFrame(new_list)
        df.to_excel(f'output/{file_name}', index=False)
        self.logger.info(f'Excel file created at path: output/{file_name}')


if __name__ == "__main__":
    pass