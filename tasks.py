from custom_webdriver import ChromeBrowser
from news import News

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
from RPA.HTTP import HTTP

logging.basicConfig(level=logging.DEBUG,
                    format='[%(levelname)s] %(asctime)s - %(message)s')

RESULT_FILE_NAME = "search_result.xlsx"

@task
def scrap_news_data():
    
    try:
        for item in workitems.inputs:
            
            item_payload = item.payload
            logging.info(f'item_payload: {item_payload}')
            excel_path = item.get_file(RESULT_FILE_NAME)
            excel_name = os.path.basename(excel_path)

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
            total_news = get_number_total_news(browser)
            returned_news = get_all_returned_news(browser, total_news)
            browser.kill()
            download_images(returned_news)
            write_output_excel(returned_news, item_payload['search_phrase'], excel_name)

            item.done()
        
    except Exception as err:
        workitems.inputs.current.fail(
            exception_type='APPLICATION',
            code='UNCAUGHT_ERROR',
            message=str(err)
        )


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
            logging.warning(f'Category: {category} is not an valid option.')
        section_dropdown.click()

    browser.element(By.XPATH, f'//p[@data-testid="SearchForm-status" and not(contains(text(), "Loading"))]')\
    .get_element_attribute('innerText', timeout=10)
    logging.info(f'Search for "{search_phrase}" is completed.')


def get_number_total_news(browser:ChromeBrowser) -> int:
    """Returns the number of total news found during search.

    Args:
        browser (ChromeBrowser): Object responsable for managing the Webdriver

    Returns:
        int: number of news.
    """
    results_for_search = browser.element(By.XPATH, '//p[@data-testid="SearchForm-status"]').get_element_attribute('innerText', timeout=10)
    macth_obj = re.search(r"out\sof\s(?P<value>\d+[\.\,]?\d*)\sresults", results_for_search)
    total_results = int(macth_obj.group('value').replace(",", "."))
    logging.info(f"Total news: {total_results}")
    return total_results


def get_all_returned_news(browser:ChromeBrowser, total_results:int) -> list[News]:
    """Iterate all returned news capturing their titles, description and images.

    Args:
        browser (ChromeBrowser): Object responsable for managing the Webdriver
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
            title = browser.element(By.XPATH, f'{news_xpath}//h4[@class="css-2fgx4k"]').get_element_attribute('innerText')
            date = browser.element(By.XPATH, f'{news_xpath}//span[@data-testid="todays-date"]').get_element_attribute('innerText')

            description_element = browser.element(By.XPATH, f'{news_xpath}//p[@class="css-16nhkrn"]')
            try:
                description_element.find_element()
            except selenium_exceptions.NoSuchElementException:
                logging.warning(f"News at index {idx} doesn`t have description.")
                description = None
            else:
                description = description_element.get_element_attribute('innerText')

            image_element = browser.element(By.XPATH, f'{news_xpath}//img[@class="css-rq4mmj"]')
            try:
                image_element.find_element()
            except selenium_exceptions.NoSuchElementException:
                logging.warning(f"News at index {idx} doesn`t have image.")
                img_url = None
            else:
                img_url = image_element.get_element_attribute('src', timeout=3)
            
            news_payload.append(
                News(title, date, description, img_url)
            )

        try:
            browser.element(By.XPATH, '//button[@data-testid="search-show-more-button"]').click(timeout=3)
        except selenium_exceptions.TimeoutException:
            logging.info('The button "SHOW MORE" wasn`t found, no more news.')
            break

    return news_payload


def download_images(returned_news:list) -> None:
    """Downloads the image of each found news.

    Args:
        returned_news (list): News returned after search.
    """
    http = HTTP()
    for news in returned_news:
        if not news.has_img:
            continue
        img_path = f'output/{news.get_image_name()}'
        http.download(url=news.img_url, target_file = img_path, overwrite=True)
        logging.info(f"Image saved at path: {img_path}")


def write_output_excel(returned_news:list, search_phrase:str, file_name:str) -> None:
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
                "Description": news.description,
                "Image name": news.get_image_name(),
                "Search frase count": news.count_key_words(search_phrase),
                "Is money metioned?": news.is_money_mentioned()
            }
        )

    df = pd.DataFrame(new_list)
    df.to_excel(f'output/{file_name}', index=False)
    logging.info(f'Excel file created at path: output/{file_name}')


if __name__ == "__main__":
    scrap_news_data()