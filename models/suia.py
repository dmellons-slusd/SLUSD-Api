from pydantic import BaseModel
from typing import Union, Literal
from datetime import datetime

class SUIA_Body(BaseModel):
    ID: int
    SD: str
    ADSQ: int
    INV: Literal['ACAD','RESO','TUPE']
    
class SUIAUpdate(BaseModel):
    ID: int
    SQ: int
    SD: Union[str, None] = None
    ADSQ: Union[int, None] = None
    INV: Union[Literal['ACAD','RESO','TUPE'], None] = None

class SUIADelete(BaseModel):
    ID: int
    SQ: int

class SUIA_Table(BaseModel):
    ID: int
    SD: str
    ADSQ: int
    SQ: int
    INV: Literal['ACAD','RESO','TUPE']
    DEL: bool
    DTS: datetime = datetime.now()