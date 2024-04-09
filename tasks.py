from scrapper import Scrapper
from robocorp import workitems
from robocorp.tasks import task
import urllib
import logging

logging.basicConfig(level=logging.DEBUG,
                    format='[%(levelname)s] %(asctime)s - %(message)s')

RESULT_FILE_NAME = 'search_result.xlsx'
IMG_ZIP_FILE_NAME = 'downloaded_images.zip'

@task
def scrap_news_data():
    
    try:
        for item in workitems.inputs:
            item_payload = item.payload
            logging.info(f'item_payload: {item_payload}')

            if not item_payload['search_phrase']:
                raise ValueError('The "search_phrase" is not valid.')
            search_phrase = str(item_payload['search_phrase'])

            # Calc search time range
            # ============================================
            scrapper = Scrapper()
            max_date_str, min_date_str = scrapper.calc_search_time_range(item_payload['number_of_months'])
            logging.info(f'max_date_str: {max_date_str} - min_date_str: {min_date_str}')

            # Search 'The New York Times'
            # ============================================
            new_url = f'https://www.nytimes.com/search?query={urllib.parse.quote_plus(search_phrase)}'
            scrapper.execute_search(new_url, item_payload['category'], max_date_str,
                                    min_date_str)
            
            # Get search result in excel
            # ============================================
            total_news = scrapper.get_number_total_news()
            if total_news == 0:
                scrapper.browser.close_all_browsers()
                logging.warning(f'No results found for this search.')
            else:
                news_list = scrapper.get_all_returned_news(total_news)
                scrapper.browser.close_all_browsers()
                scrapper.download_images(news_list, IMG_ZIP_FILE_NAME)
                scrapper.write_output_excel(news_list, search_phrase, RESULT_FILE_NAME)
            item.done()
        
    except Exception as err:
        workitems.inputs.current.fail(
            exception_type='APPLICATION',
            code='UNCAUGHT_ERROR',
            message=str(err)
        )


if __name__ == "__main__":
    scrap_news_data()