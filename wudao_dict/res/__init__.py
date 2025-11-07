from os.path import abspath, dirname


RESOURCE_DIR = abspath(dirname(__file__))
DICT_DB_ZST = f"{RESOURCE_DIR}/dict.db.zst"


__all__ = ["DICT_DB_ZST"]
