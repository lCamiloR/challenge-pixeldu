from extended_selenium import ExtendedSelenium
from robocorp import workitems
from robocorp.tasks import task
import urllib
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='[%(levelname)s] %(asctime)s - %(message)s')

RESULT_FILE_NAME = "search_result.xlsx"

@task
def scrap_news_data():
    
    for item in workitems.inputs:
        try:
            item_payload = item.payload
            logging.info(f'item_payload: {item_payload}')

            if not item_payload['search_phrase']:
                raise ValueError('The "search_phrase" is not valid.')
            search_phrase = str(item_payload['search_phrase'])

            # Calc search time range
            # ============================================
            browser = ExtendedSelenium()
            max_date_str, min_date_str = browser.calc_search_time_range(item_payload['number_of_months'])
            logging.info(f'max_date_str: {max_date_str} - min_date_str: {min_date_str}')

            # Search 'The New York Times'
            # ============================================
            browser = ExtendedSelenium()
            new_url = f'https://www.nytimes.com/search?query={urllib.parse.quote_plus(search_phrase)}'
            browser.execute_search(new_url, item_payload['category'], max_date_str,
                                   min_date_str)
            
            # Get search result in excel
            # ============================================
            total_news = browser.get_number_total_news()
            if total_news == 0:
                browser.close_all_browsers()
                logging.warning(f'No results found for this search.')
            else:
                news_list = browser.get_all_returned_news(total_news)
                browser.close_all_browsers()
                browser.download_images(news_list)
                browser.write_output_excel(news_list, search_phrase, RESULT_FILE_NAME)
            item.done()
        
        except Exception as err:
            item.fail(
                exception_type='APPLICATION',
                code='UNCAUGHT_ERROR',
                message=str(err)
            )


if __name__ == "__main__":
    scrap_news_data()