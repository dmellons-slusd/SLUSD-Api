from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from typing import List
from models.suia import SUIA_Body, SUIAUpdate, SUIADelete
from models.auth import BaseResponse
from services.suia_service import SUIAService
from dependencies import get_auth

router = APIRouter()

def get_suia_service():
    return SUIAService()

@router.get("/")
async def get_all_suia_records(
    auth=Depends(get_auth),
    service: SUIAService = Depends(get_suia_service)
):
    """
    Returns a list of all SUIA records in Aeries
    """
    try:
        records = service.get_all_records()
        return JSONResponse(content=records, status_code=200)
    except Exception as e:
        return JSONResponse(
            content={"status": "ERROR", "message": f"Error: {e}"}, 
            status_code=500
        )

@router.get("/{id}/")
async def get_single_student_suia_records(
    id: int,
    auth=Depends(get_auth),
    service: SUIAService = Depends(get_suia_service)
):
    """
    Returns a list of all SUIA records for a given student ID
    """
    try:
        records, is_empty = service.get_student_records(id)
        
        if is_empty:
            content = {
                "status": "SUCCESS",
                "message": f"No rows found for ID# {id}"
            }
            return JSONResponse(content=content, status_code=200)
        
        return JSONResponse(content=records, status_code=200)
        
    except Exception as e:
        content = {
            "status": "Error",
            "message": f"Error:{e}"
        }
        return JSONResponse(content=content, status_code=500)

@router.post("/", response_model=BaseResponse)
async def insert_SUIA_row(
    data: SUIA_Body,
    auth=Depends(get_auth),
    service: SUIAService = Depends(get_suia_service)
):
    """
    Inserts a new row into the SUIA table
    """
    try:
        post_data = service.create_record(data)
        content = {
            "status": "SUCCESS",
            "message": f"Inserted new row into SUIA for student ID#{data.ID} @ SQ {post_data.SQ}"
        }
        return JSONResponse(content=content, status_code=200)
    except Exception as e:
        content = {"error": f"{e}"}
        return JSONResponse(content=content, status_code=500)

@router.put("/", response_model=BaseResponse)
async def update_SUIA_row(
    body: SUIAUpdate,
    auth=Depends(get_auth),
    service: SUIAService = Depends(get_suia_service)
):
    """
    Updates a row in the SUIA table
    """
    try:
        success, message, old_row = service.update_record(body)
        
        if not success:
            content = {
                "status": "FAIL",
                "message": message
            }
            return JSONResponse(content, status_code=200)
        
        content = {
            'status': 'SUCCESS',
            'message': message
        }
        return JSONResponse(content=content, status_code=200)
        
    except Exception as e:
        content = {
            'status': 'FAIL',
            'message': f'ERROR: {e}'
        }
        return JSONResponse(content=content, status_code=500)

@router.delete("/", response_model=BaseResponse)
async def delete_SUIA_row(
    body: SUIADelete,
    auth=Depends(get_auth),
    service: SUIAService = Depends(get_suia_service)
):
    """
    Deletes a single row from the SUIA table in Aeries
    """
    try:
        success, message = service.delete_record(body)
        
        if not success:
            content = {
                "status": "Row Not Found",
                "message": message
            }
            return JSONResponse(content=content, status_code=404)
        
        content = {
            "status": "SUCCESS",
            "message": message
        }
        return JSONResponse(content=content, status_code=200)
        
    except Exception as e:
        content = {"error": f"{e}"}
        return JSONResponse(content=content, status_code=500)