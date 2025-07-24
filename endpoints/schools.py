from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from typing import List
from models.school import School
from services.school_service import SchoolService

router = APIRouter()

def get_school_service():
    return SchoolService()

@router.get("/", response_model=List[School])
async def get_all_schools_info(
    service: SchoolService = Depends(get_school_service)
):
    """
    Get a list of all schools in Aeries
    """
    try:
        schools = service.get_all_schools()
        return schools
    except Exception as e:
        return JSONResponse(
            content={"error": f"Error retrieving schools: {e}"},
            status_code=500
        )

@router.get("/{sc}/", response_model=School)
async def get_single_school_info(
    sc: int,
    service: SchoolService = Depends(get_school_service)
):
    """
    Get a single school's information from Aeries
    """
    try:
        school = service.get_school_by_code(sc)
        if not school:
            return JSONResponse(
                content={"error": f"School with code {sc} not found"},
                status_code=404
            )
        return school
    except Exception as e:
        return JSONResponse(
            content={"error": f"Error retrieving school: {e}"},
            status_code=500
        )