from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from models.discipline import ADS_POST_Body, DSP_POST_Body, Discipline_POST_Body, ADS_RESPONSE
from models.auth import BaseResponse
from services.discipline_service import DisciplineService
from dependencies import get_auth

router = APIRouter()

def get_discipline_service():
    return DisciplineService()

@router.get('/ADS_next_IID/')
async def get_next_ADS_IID(
    service: DisciplineService = Depends(get_discipline_service)
):
    """
    Returns the next IID for the ADS table in Aeries Between 500000 AND 968159
    """
    try:
        next_iid = service.get_next_ads_iid()
        return next_iid
    except Exception as e:
        return JSONResponse(content={"error": f"{e}"}, status_code=500)

@router.post("/ADS/", response_model=ADS_RESPONSE)
async def insert_ADS_row(
    data: ADS_POST_Body,
    auth=Depends(get_auth),
    service: DisciplineService = Depends(get_discipline_service)
):
    """
    Inserts a new row into the ADS table in Aeries
    """ 
    try:
        pid, sq, iid = service.create_ads_record(data)
        
        content = {
            "status": "SUCCESS",
            "message": f"Inserted new row into ADS for student ID#{data.PID} @ SQ {sq}",
            "ID": pid,
            "SQ": sq,
            "IID": iid
        } 
        return JSONResponse(content=content, status_code=200)
     
    except Exception as e:
        content = {"error": f"{e}"}
        return JSONResponse(content=content, status_code=500)

@router.post('/DSP/', response_model=BaseResponse)
async def insert_DSP_row(
    data: DSP_POST_Body,
    auth=Depends(get_auth),
    service: DisciplineService = Depends(get_discipline_service)
):
    """
    Inserts a new row into the DSP table in Aeries
    """
    try:
        sq1 = service.create_dsp_record(data)
        
        content = {
            "status": "SUCCESS",
            "message": f"Inserted new row into DSP for student ID#{data.PID} @ SQ {data.SQ} - SQ1 {sq1}"
        }
        return JSONResponse(content=content, status_code=200)
     
    except Exception as e:
        content = {"error": f"{e}"}
        return JSONResponse(content=content, status_code=500)

@router.post('/discipline/', response_model=BaseResponse)
async def insert_discipline_record(
    data: Discipline_POST_Body,
    auth=Depends(get_auth),
    service: DisciplineService = Depends(get_discipline_service)
):
    """
    !!! CURRENTLY A WORK IN PROGRESS !!!
    ---------------------
    USE /aeries/ADS/ AND /aeries/DSP/ INSTEAD
    ----------------------
    """
    try:
        result = service.create_discipline_record(data)
        
        content = {
            "status": "SUCCESS",
            "message": f"Inserted discipline record for student ID#{data.PID}",
            "result": result
        } 
        return JSONResponse(content=content, status_code=200)
    
    except Exception as e:
        content = {"error": f"{e}"}
        return JSONResponse(content=content, status_code=500)