from CustomWebdriver import ChromeBrowser

from robocorp import workitems
from robocorp.tasks import task
import datetime
from dateutil.relativedelta import relativedelta
from selenium.webdriver.common.by import By
from selenium.common import exceptions as selenium_exceptions
import urllib
import logging
import os
import re
import pandas as pd

logging.basicConfig(level=logging.DEBUG,
                    format='[%(levelname)s] %(asctime)s - %(message)s')

RESULT_FILE_NAME = "search_result.xlsx"

WORKING_DIR = os.getcwd()

@task
def scrap_news_data():
    
    try:
        for item in workitems.inputs:
            
            item_payload = item.payload
            logging.info(f'item_payload: {item_payload}')
            excel_path = item.get_file(RESULT_FILE_NAME)

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
            get_all_returned_news(browser, item_payload['search_phrase'], excel_path)

            item.done()
        
    except Exception as err:
        workitems.inputs.current.fail(
            exception_type='APPLICATION',
            code='UNCAUGHT_ERROR',
            message=str(err)
        )


def execute_search(browser:ChromeBrowser, search_phrase:str, category:str,
                   max_date_str:str, min_date_str:str) -> None:
    """Opens the news website and search for the search frase, than adds the specified filters.

    Args:
        browser (ChromeBrowser): Object responsable for managing the Webdriver
        search_phrase (str): Phrase that will be searched on the website
        category (str): News category to be selected during result filter
        max_date_str (str): Maximum date of the time range of search (Most recent date)
        min_date_str (str): Minimum date of the time range of search (Oldest date)
    """

    new_url = f'https://www.nytimes.com/search?query={urllib.parse.quote_plus(search_phrase)}'
    browser.get_wait_page(new_url)

    # Reject cookies
    browser.element(By.ID, 'fides-banner-button-primary').click()

    # Order by newest
    browser.element(By.XPATH, '//select[@data-testid="SearchForm-sortBy"]').click()
    browser.element(By.XPATH, '//select[@data-testid="SearchForm-sortBy"]/option[@value="newest"]').click()

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
    if category:
        category = category.capitalize().replace(" ","")
        section_dropdown = browser.element(By.XPATH, '//button[@data-testid="search-multiselect-button"]')
        section_dropdown.click()
        try:
            browser.element(By.XPATH, 
                            f'//ul[@data-testid="multi-select-dropdown-list"]//span[contains(text(), "{category}")]').click(timeout=2)
        except selenium_exceptions.TimeoutException:
            logging.exception(f'Category: {category} is not an valid option.')
        section_dropdown.click()

    browser.element(By.XPATH, f'//p[@data-testid="SearchForm-status" and not(contains(text(), "Loading"))]')\
    .get_element_attribute('innerText', timeout=10)


def get_all_returned_news(browser:ChromeBrowser, search_phrase:str, file_name:str) -> None:
    """Iterate all returned news capturing their titles, description and images, saving the data in a excel file.

    Args:
        browser (ChromeBrowser): Object responsable for managing the Webdriver
        search_phrase (str): Phrase that will be searched on the website
        file_name (str): Excel file name
    """
    MONEY_RGX_PATTERNS = (
        r"\$\d+[\.|,]?\d+\.{0,1}\d*",
        r"\d+\s(dollars|USD)"
    )

    results_for_search = browser.element(By.XPATH, '//p[@data-testid="SearchForm-status"]').get_element_attribute('innerText', timeout=10)
    macth_obj = re.search(r"out\sof\s(?P<value>\d+[\.\,]?\d*)\sresults", results_for_search)
    if macth_obj:
        total_results = int(macth_obj.group('value').replace(",", "."))
    else:
        total_results = 0

    logging.info(f"Total news: {total_results}")
    
    news_payload = []
    for iteration in range(1, total_results, 10):

        if (total_results - iteration) < 10:
            max_idx = total_results + 1
        else:
            max_idx = iteration + 10

        for idx in range(iteration, max_idx):

            news_xpath = f'//li[@data-testid="search-bodega-result"][position()={idx}]'
            
            title = browser.element(By.XPATH, f'{news_xpath}//h4[@class="css-2fgx4k"]').get_element_attribute('innerText')
            date = browser.element(By.XPATH, f'{news_xpath}//span[@data-testid="todays-date"]').get_element_attribute('innerText')

            description_element = browser.element(By.XPATH, f'{news_xpath}//p[@class="css-16nhkrn"]')
            try:
                description_element.find_element()
            except selenium_exceptions.NoSuchElementException:
                logging.warning(f"News at index {idx} doesn`t have description.")
                description = "** No description on Website **"
            else:
                description = description_element.get_element_attribute('innerText')

            image_element = browser.element(By.XPATH, f'{news_xpath}//img[@class="css-rq4mmj"]')
            try:
                image_element.find_element()
            except selenium_exceptions.NoSuchElementException:
                logging.warning(f"News at index {idx} doesn`t have image.")
                img_name = "** No image on Website **"
            else:
                img_url = image_element.get_element_attribute('src', timeout=3)
                img_name = img_url.rsplit("?", 1)
                img_name = img_name[0].rsplit("/", 1)[-1].replace(".jpg", ".png")
                img_name = fr'output\images\{img_name}'
                full_img_path = fr'{WORKING_DIR}\{img_name}'
                if os.path.isfile(full_img_path):
                    os.remove(full_img_path)
                
                image_element.save_image_to_path(full_img_path)

            # Search for money
            is_money_present = False
            for rgx_pattern in MONEY_RGX_PATTERNS:
                if re.search(rgx_pattern, title) or re.search(rgx_pattern, description):
                    is_money_present = True
                    break

            # Count search parameter
            search_phrase = search_phrase.lower().strip()
            total_count = title.lower().count(search_phrase) + description.lower().count(search_phrase)
            
            news_payload.append(
                {
                    "Title": title,
                    "Date": date,
                    "Description": description,
                    "Image name": img_name,
                    "Search frase count": total_count,
                    "Is money metioned?": is_money_present
                }
            )

        try:
            browser.element(By.XPATH, '//button[@data-testid="search-show-more-button"]').click(timeout=3)
        except selenium_exceptions.TimeoutException:
            logging.info('The button "SHOW MORE" wasn`t found, no more news.')
            break

    df = pd.DataFrame(news_payload)
    df.to_excel(file_name, index=False)
    logging.info(f'Excel file created at path: {file_name}')


def calc_search_time_range(*, number_of_months:int) -> tuple[str]:
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


if __name__ == "__main__":
    scrap_news_data()