from pydantic import BaseModel, Field
from typing import List, Optional

class Student(BaseModel):
    id: int 
    sc: int
    fn: str 
    ln: str 
    gr: int

class StudentLookup(BaseModel):
    stu_id: int
    first_name: str
    last_name: str
    grade: str
    email: str
    birthdate: str
    activation_code: str

class StudentSearchRequest(BaseModel):
    first_name: str = Field(..., description="Student's first name")
    last_name: str = Field(..., description="Student's last name") 
    birthdate: Optional[str] = Field(None, description="Student's birthdate (YYYY-MM-DD or MM/DD/YYYY format)")
    address: Optional[str] = Field(None, description="Student's address")
    max_results: Optional[int] = Field(10, description="Maximum number of results to return")

class StudentMatchResponse(BaseModel):
    student_id: int
    first_name: str
    last_name: str
    birthdate: Optional[str]
    address: Optional[str]
    confidence: float
    match_reasons: List[str]
    tier: int

class StudentLookupResponse(BaseModel):
    status: str
    message: str
    total_matches: int
    matches: List[StudentMatchResponse]

class StudentMatchDetails(BaseModel):
    student_id: int
    first_name: str
    last_name: str
    birthdate: Optional[str]
    address: Optional[str]
    grade: Optional[int]
    school: Optional[int]

class StudentSearchCriteria(BaseModel):
    first_name: str
    last_name: str
    birthdate: Optional[str] = None
    address: Optional[str] = None
    max_results: Optional[int] = 10