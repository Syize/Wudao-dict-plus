from typing import TypedDict, Literal, Union


class ENPronounce(TypedDict):
    usa: str
    uk: str
    other: str


class SentenceUnit(TypedDict):
    en: str
    zh: str


class CollinsSentenceUnit(TypedDict):
    mean: str
    category: str
    sentences: "list[SentenceUnit]"


class ENSentence(TypedDict):
    is_collins: bool
    sentences: list


class ENWord(TypedDict):
    word: str
    pronunciation: ENPronounce
    paraphrase: "dict[str, list[str]]"
    rank: str
    pattern: str
    sentence: ENSentence


class ZHDesc(TypedDict):
    desc: str
    desc_sentences: "list[SentenceUnit]"


class ZHWord(TypedDict):
    word: str
    pronunciation: str
    paraphrase: "dict[str, list[str]]"
    desc: "list[ZHDesc]"
    sentence: "list[SentenceUnit]"
    
    
class QuitMessage(TypedDict):
    cmd: Literal["quit"]
    

class QueryMessage(TypedDict):
    cmd: Literal["query"]
    word: str
    online: bool
    update_db: bool
    
    
Message = Union[QuitMessage, QueryMessage]
    
    
class OnlineAPIBase:
    def __init__(self, token: str) -> None:
        self.token = token
        
    def query_api(self, word: str, lang: str) -> "dict":
        """
        Query word information from API.

        :param word: Word or paraphase.
        :type word: str
        :param lang: Language type.
        :type lang: str
        :return: Response results.
        :rtype: dict
        """
        raise NotImplementedError("You have to implement this method.")
    
    def parse_response_en(self, response: "dict") -> ENWord:
        """
        Parse the response from the API.

        :param response: Response results.
        :type response: dict
        :param lang: Language type.
        :type lang: str
        :return: Word information.
        :rtype: ENWord
        """
        raise NotImplementedError("You have to implement this method.")
        
    def get_en_word(self, word: str) -> "ENWord":
        """
        Get Englist word information from online API.

        :param word: English word or paraphase.
        :type word: str
        :return: Word information.
        :rtype: ENWord
        """
        # check the word
        response = self.query_api(word, "en")
        return self.parse_response_en(response)


__all__ = ["ENPronounce", "SentenceUnit", "CollinsSentenceUnit", "ENSentence", "ENWord", "ZHWord", "OnlineAPIBase",
           "Message", "QuitMessage", "QueryMessage"]
