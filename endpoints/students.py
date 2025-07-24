from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from models.student import Student, StudentSearchRequest, StudentLookupResponse
from services.student_service import StudentService
from dependencies import get_auth

router = APIRouter()

def get_student_service():
    return StudentService()

@router.get("/{id}/", response_model=Student)
async def get_student(
    id: int,
    auth=Depends(get_auth),
    service: StudentService = Depends(get_student_service)
):
    """
    Get a single student's information from Aeries
    """
    try:
        student = service.get_student_by_id(id)
        if not student:
            return JSONResponse(
                content={"error": f"Student with ID {id} not found"},
                status_code=404
            )
        return student
    except Exception as e:
        return JSONResponse(
            content={"error": f"Error retrieving student: {e}"},
            status_code=500
        )

@router.post("/lookup/", response_model=StudentLookupResponse)
async def search_students(
    search_request: StudentSearchRequest,
    auth=Depends(get_auth),
    service: StudentService = Depends(get_student_service)
):
    """
    Search for students using progressive matching with confidence scoring
    
    This endpoint uses a tiered approach to find student matches:
    - Tier 1: Exact match on all provided fields (95% confidence)
    - Tier 2: Exact name + birthdate (85% confidence) 
    - Tier 3: Exact name + address (80% confidence)
    - Tier 4: Exact name only (70% confidence)
    - Tier 5: Fuzzy matching with phonetic and partial matches (50-75% confidence)
    """
    try:
        response = service.search_students(search_request)
        return JSONResponse(content=response.dict(), status_code=200)
        
    except Exception as e:
        error_response = StudentLookupResponse(
            status="ERROR",
            message=f"Error during student lookup: {str(e)}",
            total_matches=0,
            matches=[]
        )
        return JSONResponse(content=error_response.dict(), status_code=500)

@router.get("/{student_id}/details/")
async def get_student_details(
    student_id: int,
    auth=Depends(get_auth),
    service: StudentService = Depends(get_student_service)
):
    """
    Get detailed information for a specific student by ID
    """
    try:
        student_details = service.get_student_details(student_id)
        
        if student_details:
            return JSONResponse(content={
                "status": "SUCCESS",
                "message": f"Found details for student ID {student_id}",
                "student": student_details
            }, status_code=200)
        else:
            return JSONResponse(content={
                "status": "NOT_FOUND", 
                "message": f"No student found with ID {student_id}",
                "student": None
            }, status_code=404)
            
    except Exception as e:
        return JSONResponse(content={
            "status": "ERROR",
            "message": f"Error retrieving student details: {str(e)}",
            "student": None
        }, status_code=500)