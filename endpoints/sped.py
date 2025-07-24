from fastapi import APIRouter, Depends, UploadFile, File, Request
from fastapi.responses import JSONResponse
from models.sped import IEPUploadResponse
from services.sped_service import SPEDService
from dependencies import get_auth
from slusdlib import core

router = APIRouter()

def get_sped_service():
    return SPEDService()

@router.post("/uploadIepAtAGlance/", response_model=IEPUploadResponse)
async def upload_iep_documents(
    file: UploadFile = File(..., description="PDF file containing IEP documents"),
    test_run: bool = False,
    auth=Depends(get_auth),
    service: SPEDService = Depends(get_sped_service)
):
    """
    Upload and process IEP "At a Glance" documents.
    
    This endpoint:
    1. Accepts a multi-page PDF containing multiple IEP documents
    2. Splits the PDF by detecting IEP headers and extracting District IDs
    3. Uploads each individual IEP document to the Aeries DOC table
    4. Returns information about processed documents
    """
    try:
        # Read uploaded file content
        file_content = await file.read()
        core.log('~' * 80)
        core.log(f"Received file: {file.filename} ({len(file_content)} bytes)")
        # Process the upload
        response = service.process_iep_upload(file_content, file.filename, test_run)
        
        # Return appropriate HTTP status code based on response status
        status_code = 200
        if response.status == "ERROR":
            status_code = 500 if "Error processing" in response.message else 400
        
        return JSONResponse(
            content=response.dict(),
            status_code=status_code
        )
        
    except Exception as e:
        return JSONResponse(
            content={
                "status": "ERROR",
                "message": f"Unexpected error: {str(e)}",
                "total_documents": 0,
                "extracted_docs": [],
                "uploaded_to_aeries": False
            },
            status_code=500
        )
