from CustomWebdriver import ChromeBrowser

from robocorp import workitems
from robocorp.tasks import task
import datetime
from dateutil.relativedelta import relativedelta
from selenium.webdriver.common.by import By
from selenium.common import exceptions as selenium_exceptions
import urllib
import logging
from pathlib import Path
import os

import time

logging.basicConfig(level=logging.DEBUG,
                    format='[%(levelname)s] %(asctime)s - %(message)s')

RESULT_FILE_NAME = "search_result.xlsx"

WORKING_DIR = os.getcwd()

@task
def scrap_news_data():
    
    work_item = workitems.inputs.current
    item_payload = work_item.payload
    logging.info(f'item_payload: {item_payload}')
    excel_path = work_item.get_file(RESULT_FILE_NAME)

    if not os.path.isdir(fr'{WORKING_DIR}\output\images'):
        os.makedirs(fr'{WORKING_DIR}\output\images')

    # Calc search time range
    # ============================================
    max_date_str, min_date_str = calc_search_time_range(number_of_months=item_payload['number_of_months'])
    logging.info(f'max_date_str: {max_date_str} - min_date_str: {min_date_str}')

    # Search 'The New York Times'
    # ============================================
    browser = ChromeBrowser()
    browser.start_driver()

    execute_search(browser, item_payload['search_phrase'], item_payload['category'],
                   max_date_str, min_date_str)
    
    # Get search result in excel
    # ============================================
    get_all_returned_news(browser, excel_path)

    # time.sleep(10)


def execute_search(browser:ChromeBrowser, search_phrase:str, category:str,
                   max_date_str:str, min_date_str:str) -> dict:

    new_url = f'https://www.nytimes.com/search?query={urllib.parse.quote_plus(search_phrase)}'
    browser.get_wait_page(new_url)

    # Reject cookies
    browser.element(By.ID, 'fides-banner-button-primary').click()

    # Open calendar
    browser.element(By.XPATH, '//button[@data-testid="search-date-dropdown-a"]').click()
    browser.element(By.XPATH, '//button[@aria-label="Specific Dates"]').click()

    # Enter time range
    browser.element(By.ID, 'startDate').send_keys(min_date_str)
    browser.element(By.ID, 'endDate').send_keys(max_date_str)
    browser.element(By.ID, 'endDate').send_action_key_enter()

    # Check if time range is set
    time_range_xpath = f'//button[@facet-name="date" and contains(text(), "{min_date_str} – {max_date_str}")]'
    browser.element(By.XPATH, time_range_xpath).wait_element_to_be_present()

    # Select desired category inside 'Section', if available
    category = category.capitalize().replace(" ","")
    section_dropdown = browser.element(By.XPATH, '//button[@data-testid="search-multiselect-button"]')
    section_dropdown.click()
    try:
        browser.element(By.XPATH, 
                        f'//ul[@data-testid="multi-select-dropdown-list"]//span[contains(text(), "{category}")]').click(timeout=3)
    except selenium_exceptions.TimeoutException:
        logging.exception(f'Category: {category} is not an valid option.')
    section_dropdown.click()

    # //li[@data-testid="search-bodega-result"][position()>=1 and position()<= 10]


def get_all_returned_news(browser:ChromeBrowser, file_name:str) -> str:
    
    news_payload = []
    min_index = 1
    max_index = 10
    while True:

        # news_xpath = f'//li[@data-testid="search-bodega-result"][position()>={min_index} and position()<= {max_index}]'
        # try:
        #     news_element = browser.element(By.XPATH, news_xpath).get_all_elements(timeout=1)
        # except selenium_exceptions.TimeoutException:
        #     logging.info(f'No more news found for idexes {min_index} - {max_index}')

        for idx in range(min_index, max_index):
            print("Index: ", idx)

            news_xpath = f'//li[@data-testid="search-bodega-result"][position()={idx}]'

            title = browser.element(By.XPATH, f'{news_xpath}//h4[@class="css-2fgx4k"]').get_element_attribute('innerText', timeout=1)
            data = browser.element(By.XPATH, f'{news_xpath}//span[@data-testid="todays-date"]').get_element_attribute('innerText', timeout=1)
            description = browser.element(By.XPATH, f'{news_xpath}//p[@class="css-16nhkrn"]').get_element_attribute('innerText', timeout=1)
            image_element = browser.element(By.XPATH, f'{news_xpath}//img[@class="css-rq4mmj"]')
            img_url = image_element.get_element_attribute('src', timeout=1)

            img_name = img_url.rsplit("?", 1)
            img_name = img_name[0].rsplit("/", 1)[-1].replace(".jpg", ".png")
            full_img_path = fr'{WORKING_DIR}\output\images\{img_name}'
            if os.path.isfile(full_img_path):
                os.remove(full_img_path)
            
            image_element.save_image_to_path(full_img_path, timeout=1)
            
            news_payload.append(
                {
                    "title": title,
                    "data": data,
                    "description": description,
                    "file_name": img_name
                }
            )
            
        min_index += 10
        max_index += 10

        try:
            browser.element(By.XPATH, '//button[@data-testid="search-show-more-button"]').click(timeout=1)
        except selenium_exceptions.TimeoutException:
            logging.info('The button "SHOW MORE" wasn`t found, no more news.')
            break
    
    print(news_payload)

def calc_search_time_range(*, number_of_months:int) -> tuple:

    max_date_obj = datetime.datetime.now().date()
    if isinstance(number_of_months, int) and number_of_months > 1:
        min_date_obj = max_date_obj - relativedelta(months=number_of_months - 1)
    else:
        min_date_obj = datetime.datetime.now().replace(day=1)

    return max_date_obj.strftime("%m/%d/%Y"), min_date_obj.strftime("%m/%d/%Y")



if __name__ == "__main__":
    scrap_news_data()