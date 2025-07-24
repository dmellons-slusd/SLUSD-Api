from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

class ADS_RESPONSE(BaseModel):
    status: str
    message: str
    ID: str
    SQ: str
    IID: str

class ADS_POST_Body(BaseModel):
    PID: int = Field(..., description='Student ID')
    SCL: int = Field(..., description='School ID')
    CD: str = Field(..., description='Disposition Code')
    GR: int = Field(..., description='Grade')
    CO: str = Field(default='', description='Comments')
    DT: str = Field(default=datetime.now(), description='Date of Disposition')
    LCN: int = Field(default=99, description='Location Code')
    SRF: int = Field(default=0, description='Staff Referrer ID')
    RF: str = Field(default='', description='Referrer Name')

class Discipline_POST_Body(BaseModel):
    PID: int = Field(..., description='Student ID')
    SCL: int = Field(..., description='School ID')
    CD: str = Field(..., description='Disposition Code')
    GR: int = Field(..., description='Grade')
    DS: Optional[str] = Field(default='', description='Disposition Code')
    CO: Optional[str] = Field(default='', description='Comments')

class DSP_POST_Body(BaseModel):
    PID: int = Field(..., description='Student ID')
    SQ: int = Field(..., description='ADS Sequence')
    DS: Optional[str] = Field(default='', description='Disposition Code')