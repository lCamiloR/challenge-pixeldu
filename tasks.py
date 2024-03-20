from custom_webdriver import ExtendedSelenium
from news import News
from robocorp import workitems
from robocorp.tasks import task
import datetime
from dateutil.relativedelta import relativedelta
from SeleniumLibrary.errors import ElementNotFound
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

            if not item_payload['search_phrase']:
                raise ValueError('The "search_phrase" is not valid.')
            search_phrase = str(item_payload['search_phrase'])

            # Calc search time range
            # ============================================
            max_date_str, min_date_str = calc_search_time_range(number_of_months=item_payload['number_of_months'])
            logging.info(f'max_date_str: {max_date_str} - min_date_str: {min_date_str}')

            # Search 'The New York Times'
            # ============================================
            browser = ExtendedSelenium()

            execute_search(browser, search_phrase, item_payload['category'],
                           max_date_str, min_date_str)
            
            # Get search result in excel
            # ============================================
            total_news = get_number_total_news(browser)
            if total_news == 0:
                browser.close_all_browsers()
                item.done()
                logging.warning(f'No results found for this search.')
                continue

            returned_news = get_all_returned_news(browser, total_news)
            browser.close_all_browsers()
            download_images(returned_news)
            write_output_excel(returned_news, search_phrase, excel_name)

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


def execute_search(browser:ExtendedSelenium, search_phrase:str, category:str,
                   max_date_str:str, min_date_str:str) -> None:
    """Opens the news website and search for the search frase, than adds the specified filters.

    Args:
        browser (ExtendedSelenium): Object responsable for managing the Webdriver
        search_phrase (str): Phrase that will be searched on the website
        category (str): News category to be selected during result filter
        max_date_str (str): Maximum date of the time range of search (Most recent date)
        min_date_str (str): Minimum date of the time range of search (Oldest date)
    """

    new_url = f'https://www.nytimes.com/search?query={urllib.parse.quote_plus(search_phrase)}'
    browser.start_driver(new_url, headless=True, maximized=True)

    # Reject cookies
    browser.wait_element_enabled_and_click('id:fides-banner-button-primary')

    # Order by newest
    sort_by_relevance_xpath = '//select[@data-testid="SearchForm-sortBy"]'
    browser.wait_element_enabled_and_click(f'xpath:{sort_by_relevance_xpath}')
    browser.wait_element_enabled_and_click(f'xpath:{sort_by_relevance_xpath}/option[@value="newest"]')

    # Open calendar
    browser.wait_element_enabled_and_click('xpath://button[@data-testid="search-date-dropdown-a"]')
    browser.wait_element_enabled_and_click('xpath://button[@aria-label="Specific Dates"]')

    # Enter time range
    browser.wait_element_enabled_and_input_text('id:startDate', min_date_str)
    browser.wait_element_enabled_and_input_text('id:endDate', max_date_str)
    browser.press_keys('id:endDate', "ENTER")

    # Check if time range is set
    time_range_xpath = f'//button[@facet-name="date" and contains(text(), "{min_date_str} – {max_date_str}")]'
    browser.wait_until_page_contains_element(f'xpath:{time_range_xpath}', 15)

    # Select desired category inside 'Section', if available
    if category:
        category = category.capitalize().replace(" ","")
        try:
            browser.wait_element_enabled_and_click(f'xpath://button[@data-testid="search-multiselect-button"]',
                                                   timeout=5)
        except AssertionError:
            logging.warning('The "Section" filter is not available.')
        else:
            try:
                browser.wait_element_enabled_and_click(f'xpath://ul[@data-testid="multi-select-dropdown-list"]//span[contains(text(), "{category}")]',
                                                       timeout=2)
            except AssertionError:
                logging.warning(f'Category: {category} is not an valid option.')
            browser.wait_element_enabled_and_click(f'xpath://button[@data-testid="search-multiselect-button"]')

    browser.wait_until_page_does_not_contain_element(f'xpath://p[@data-testid="SearchForm-status" and contains(text(), "Loading")]')
    logging.info(f'Search for "{search_phrase}" is completed.')


def get_number_total_news(browser:ExtendedSelenium) -> int:
    """Returns the number of total news found during search.

    Args:
        browser (ExtendedSelenium): Object responsable for managing the Webdriver

    Returns:
        int: number of news.
    """
    results_for_search = browser.wait_element_enabled_and_get_attribute('xpath://p[@data-testid="SearchForm-status"]',
                                                                        'innerText')
    macth_obj = re.search(r"out\sof\s(?P<value>[0-9\.\,]+)\sresults", results_for_search)
    if macth_obj:
        total_results = int(macth_obj.group('value').replace(",", "."))
    else:
        total_results = 0
    logging.info(f"Total news: {total_results}")
    return total_results


def get_all_returned_news(browser:ExtendedSelenium, total_results:int) -> list[News]:
    """Iterate all returned news capturing their titles, description and images.

    Args:
        browser (ExtendedSelenium): Object responsable for managing the Webdriver
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
            title = browser.wait_element_enabled_and_get_attribute(f'xpath:{news_xpath}//h4[@class="css-2fgx4k"]',
                                                                   'innerText')
            date = browser.wait_element_enabled_and_get_attribute(f'xpath:{news_xpath}//span[@data-testid="todays-date"]',
                                                                  'innerText')

            try:
                description_element = browser.find_element(f'xpath:{news_xpath}//p[@class="css-16nhkrn"]')
            except ElementNotFound:
                logging.warning(f"News at index {idx} doesn`t have description.")
                description = None
            else:
                description = browser.wait_element_enabled_and_get_attribute(description_element, 'innerText')

            try:
                image_element = browser.find_element(f'xpath:{news_xpath}//img[@class="css-rq4mmj"]')
            except ElementNotFound:
                logging.warning(f"News at index {idx} doesn`t have image.")
                img_url = None
            else:
                img_url = browser.wait_element_enabled_and_get_attribute(image_element, 'src')
            
            news_payload.append(
                News(title, date, description, img_url)
            )

        try:
            browser.wait_element_enabled_and_click(f'xpath://button[@data-testid="search-show-more-button"]',
                                                   timeout=3)
        except AssertionError:
            logging.info('The button "SHOW MORE" wasn`t found, no more news.')
            break

    return news_payload


def download_images(returned_news:list[News]) -> None:
    """Downloads the image of each found news.

    Args:
        returned_news (list): News returned after search.
    """
    http = HTTP()
    for news in returned_news:
        if not news.has_img:
            continue
        img_path = news.create_image_name('output')
        http.download(url=news.img_url, target_file = img_path, overwrite=True)
        logging.info(f"Image saved at path: {img_path}")


def write_output_excel(returned_news:list[News], search_phrase:str, file_name:str) -> None:
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
                "Image name": os.path.basename(news.img_local_path) if news.img_local_path else news.img_url,
                "Search frase count": news.count_search_phrase(search_phrase),
                "Is money metioned?": news.is_money_mentioned()
            }
        )
    df = pd.DataFrame(new_list)
    df.to_excel(f'output/{file_name}', index=False)
    logging.info(f'Excel file created at path: output/{file_name}')


if __name__ == "__main__":
    scrap_news_data()