from fastapi import APIRouter, Depends, UploadFile, File
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
                "extracted_docs": []
            },
            status_code=500
        )

@router.post("/processIepFromFolder/")
async def process_iep_from_folder(
    auth=Depends(get_auth),
    service: SPEDService = Depends(get_sped_service)
):
    """
    WARN: THIS IS NOT YET IMPLEMENTED
    ---
    Process IEP documents from the configured input folder.
    This is useful for batch processing of IEP documents.
    """
    try:
        core.log('~' * 80)
        extracted_docs = service.process_iep_from_input_folder()
        
        if not extracted_docs:
            return JSONResponse(
                content={
                    "status": "WARNING",
                    "message": "No IEP documents found in the input folder",
                    "total_documents": 0,
                    "extracted_docs": []
                },
                status_code=200
            )
        
        return JSONResponse(
            content={
                "status": "SUCCESS",
                "message": f"Successfully processed {len(extracted_docs)} IEP document(s)",
                "total_documents": len(extracted_docs),
                "extracted_docs": [
                    {
                        "file": doc["stu_id"],
                        "stu_id": doc["stu_id"],
                        "iep_date": doc["iep_date"],
                        "pages": doc["pages"]
                    }
                    for doc in extracted_docs
                ]
            },
            status_code=200
        )
        
    except Exception as e:
        return JSONResponse(
            content={
                "status": "ERROR",
                "message": f"Error processing IEP documents: {str(e)}",
                "total_documents": 0,
                "extracted_docs": []
            },
            status_code=500
        )