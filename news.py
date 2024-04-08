import re
import os
import time

MONEY_RGX_PATTERNS = (
    r"\$\s*\d+[\.|,]?\d+\.{0,1}\d*",
    r"\d+\s(dollars|USD)"
)

class News():

    img_local_path = None

    def __init__(self, title:str, date:str, description:str = None, img_url:str = None) -> None:
        self.title = title
        self.date = date
        self.description = description
        self.img_url = img_url

    def create_image_name(self, base_path:str) -> str:
        """Creates the image local file name.

        Args:
            base_path (str): Base system path.

        Returns:
            str: Image local file name.
        """
        if self.img_local_path:
            return self.img_local_path
        
        img_name = self.img_url.rsplit("?", 1)
        img_name = img_name[0].rsplit("/", 1)[-1]
        full_file_path = f'{base_path}/{img_name}'

        if os.path.isfile(full_file_path):
            timestamp = str(time.time()).replace(".","")
            full_file_path = f'{base_path}/{timestamp}_{img_name}'
        
        self.img_local_path = full_file_path

        return full_file_path
    
    def count_search_phrase(self, search_phrase:str) -> int:
        """Counts how many times the search phrase can be found in the title and description.

        Args:
            search_phrase (str): Search phrase to be matched.

        Returns:
            int: Number of occurrences
        """
        search_phrase = search_phrase.strip()
        description_count = self.description.count(search_phrase) if self.description else 0
        return self.title.count(search_phrase) + description_count
    
    def is_money_mentioned(self) -> bool:
        """Checks if money is mentioned in the title or description.

        Returns:
            bool: True if money is mentioned, False if not.
        """
        for rgx_pattern in MONEY_RGX_PATTERNS:

            match_on_description = re.search(rgx_pattern, self.description) if self.description else None
            if re.search(rgx_pattern, self.title) or match_on_description:
                return True
        return False