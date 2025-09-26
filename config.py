from functools import lru_cache
from decouple import config

class Settings:
    # Authentication settings
    SECRET_KEY: str = config("SECRET_KEY")
    ALGORITHM: str = config("ALGORITHM")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = config("ACCESS_TOKEN_EXPIRE_MINUTES", cast=int)
    
    # Database settings
    TEST_DATABASE: str = config("TEST_DATABASE", default='DST25000SLUSD_DAILY')
    
    # IEP settings
    SPLIT_IEP_FOLDER: str = config("SPLIT_IEP_FOLDER", default="split_pdfs")
    INPUT_DIRECTORY_PATH: str = config("INPUT_DIRECTORY_PATH", default="input_pdfs")
    IEP_AT_A_GLANCE_DOCUMENT_CODE: str = config("IEP_AT_A_GLANCE_DOCUMENT_CODE", default="11")
    
    # Document settings
    RECLASSIFICATION_DOCUMENT_CODE: str = config("RECLASSIFICATION_DOCUMENT_CODE", default="12")
    GENERAL_DOCUMENT_CODE: str = config("GENERAL_DOCUMENT_CODE", default="99")
    SPLIT_DOC_FOLDER: str = config("SPLIT_DOC_FOLDER", default="split_docs")
    MAX_DOCUMENT_SIZE_MB: int = config("MAX_DOCUMENT_SIZE_MB", default=10, cast=int)
    
    # Application settings
    TEST_RUN: bool = config("TEST_RUN", default=False, cast=bool)

@lru_cache()
def get_settings():
    return Settings()