from pydantic import BaseModel
from typing import List

class IEPDocumentInfo(BaseModel):
    file: str
    stu_id: str
    iep_date: str
    pages: int

class upload_error(BaseModel):
    message: str
    stu_id: str
    iep_date: str
    
class IEPUploadResponse(BaseModel):
    status: str
    message: str
    total_documents: int
    extracted_docs: List[IEPDocumentInfo]
    errors: List[upload_error] = []
    