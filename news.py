import re

MONEY_RGX_PATTERNS = (
    r"\$\d+[\.|,]?\d+\.{0,1}\d*",
    r"\d+\s(dollars|USD)"
)

class News():
    def __init__(self, title:str, date:str, description:str = None, img_url:str = None) -> None:
        self.title = title
        self.date = date
        if description:
            self.has_description = True
            self.description = description
        else:
            self.has_description = False
            self.description = "** No description on Website **"
        if img_url:
            self.has_img = True
            self.img_url = img_url
        else:
            self.has_img = False
            self.img_url = "** No image on Website **"

    def get_image_name(self) -> str:
        """Returns the image base name on the URL.

        Returns:
            str: Image base name.
        """
        img_name = self.img_url.rsplit("?", 1)
        img_name = img_name[0].rsplit("/", 1)[-1]
        return img_name
    
    def count_key_words(self, key_word:str) -> int:
        """Counts how many times a key word can be found in the title and description.

        Args:
            key_word (str): key word to be searched.

        Returns:
            int: Number of occurrences
        """
        key_word = key_word.lower().strip()
        title_lower = self.title.lower()
        description_lower = self.description.lower()
        description_count = description_lower.count(key_word) if self.has_description else 0
        return title_lower.count(key_word) + description_count
    
    def is_money_mentioned(self) -> bool:
        """Checks if money is mentioned in the title or description.

        Returns:
            bool: True if money is mentioned, False if not.
        """
        for rgx_pattern in MONEY_RGX_PATTERNS:
            if re.search(rgx_pattern, self.title) or re.search(rgx_pattern, self.description):
                return True
        return False