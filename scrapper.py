from extended_selenium import ExtendedSelenium
from locators import Locators
from news import News
from SeleniumLibrary.errors import ElementNotFound
from RPA.HTTP import HTTP
import zipfile
import os
import datetime
import re
import pandas as pd
from dateutil.relativedelta import relativedelta
import logging

class Scrapper:

    def __init__(self) -> None:
        self.browser = ExtendedSelenium()
        self.logger = logging.getLogger(__name__)

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

        self.browser.start_driver(url, headless=False, maximized=True)

        # Reject cookies
        self.browser.wait_element_enabled_and_click(Locators.REJECT_COOKIES_BTN)

        # Order by newest
        self.browser.wait_element_enabled_and_click(Locators.SORT_BY_DROPDOWN)
        self.browser.wait_element_enabled_and_click(Locators.SORT_BY_NEWEST)

        # Open calendar
        self.browser.wait_element_enabled_and_click(Locators.DATE_RANGE_DROPDOWN)
        self.browser.wait_element_enabled_and_click(Locators.SPECIFIC_DATES_BTN)

        # Enter time range
        self.browser.wait_element_enabled_and_input_text(Locators.START_DATE_INPUT, min_date_str)
        self.browser.wait_element_enabled_and_input_text(Locators.END_DATE_INPUT, max_date_str)
        self.browser.press_keys(Locators.END_DATE_INPUT, "ENTER")

        # Select desired category inside 'Section', if available
        if category:
            category = category.capitalize().replace(" ","")
            target_section_xpath = f'{Locators.SECTION_DROPDOWN_OPTIONS}[contains(text(),"{category}")]'
            try:
                self.browser.find_element(Locators.SECTION_DROPDOWN)
                self.browser.wait_element_enabled_and_click(Locators.SECTION_DROPDOWN, timeout=5)
            except ElementNotFound:
                self.logger.warning('The "Section" filter is not available.')
            else:
                try:
                    self.browser.find_element(target_section_xpath)
                    self.browser.wait_element_enabled_and_click(target_section_xpath, timeout=5)
                except ElementNotFound:
                    self.logger.warning(f'Category: {category} is not an valid option.')
                self.browser.wait_element_enabled_and_click(Locators.SECTION_DROPDOWN)

        self.browser.wait_until_element_does_not_contain(Locators.RESULT_COUNT, 'Loading')
        self.logger.info('Search is completed.')

    def get_number_total_news(self) -> int:
        """Returns the number of total news found during search.

        Returns:
            int: number of news.
        """
        results_for_search = self.browser.wait_element_enabled_and_get_attribute(Locators.RESULT_COUNT, 'innerText')
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
                news_xpath = f'{Locators.NEWS_LIST_ITEM}[position()={idx}]'
                title = self.browser.wait_element_enabled_and_get_attribute(f'{news_xpath}//a/h4',
                                                                            'innerText')
                date = self.browser.wait_element_enabled_and_get_attribute(f'{news_xpath}//span[@data-testid="todays-date"]',
                                                                           'innerText')

                try:
                    description_element = self.browser.find_element(f'{news_xpath}//a/p[position()=1]')
                except ElementNotFound:
                    self.logger.warning(f"News at index {idx} doesn`t have description.")
                    description = None
                else:
                    description = self.browser.wait_element_enabled_and_get_attribute(description_element, 'innerText')

                try:
                    image_element = self.browser.find_element(f'{news_xpath}//img[ancestor::figure[@aria-label="media"]]')
                except ElementNotFound:
                    self.logger.warning(f"News at index {idx} doesn`t have image.")
                    img_url = None
                else:
                    img_url = self.browser.wait_element_enabled_and_get_attribute(image_element, 'src')
                
                news_payload.append(
                    News(title, date, description, img_url)
                )

            try:
                show_more_btn = self.browser.find_element(Locators.SHOW_MORE_BTN)
                self.browser.wait_element_enabled_and_click(show_more_btn, timeout=3)
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