from fastapi import APIRouter, Depends, UploadFile, File, Form
from fastapi.responses import JSONResponse
from typing import Optional
from models.doc import DocumentUploadResponse, GeneralDocumentUpload
from services.doc_service import DocService
from dependencies import get_auth
from slusdlib import core

router = APIRouter()

def get_doc_service():
    return DocService()

@router.post("/uploadReclassification/", response_model=DocumentUploadResponse)
async def upload_reclassification_documents(
    file: UploadFile = File(..., description="PDF file containing reclassification documents"),
    test_run: bool = Form(False, description="Whether this is a test run"),
    auth=Depends(get_auth),
    service: DocService = Depends(get_doc_service)
):
    """
    Upload and process reclassification paperwork documents.
    
    This endpoint:
    1. Accepts a multi-page PDF containing multiple student reclassification documents
    2. Splits the PDF by detecting student IDs and document types
    3. Uploads each combined student document to the Aeries DOC table
    4. Returns information about processed documents
    
    Expected document types:
    - Notification of English Language Program Exit
    - Reclassification Meeting with Parent/Guardian  
    - Teacher Evaluation for Reclassification
    """
    try:
        # Read uploaded file content
        file_content = await file.read()
        core.log('~' * 80)
        core.log(f"Received reclassification file: {file.filename} ({len(file_content)} bytes)")
        
        # Process the upload
        response = service.process_reclassification_upload(file_content, file.filename, test_run)
        
        # Return appropriate HTTP status code based on response status
        status_code = 200
        if response.status == "ERROR":
            status_code = 500 if "Error processing" in response.message else 400
        elif response.status == "PARTIAL_SUCCESS":
            status_code = 207  # Multi-status for partial success
        
        return JSONResponse(
            content=response.dict(),
            status_code=status_code
        )
        
    except Exception as e:
        core.log(f"Unexpected error in reclassification upload: {str(e)}")
        return JSONResponse(
            content={
                "status": "ERROR",
                "message": f"Unexpected error: {str(e)}",
                "total_documents": 0,
                "extracted_docs": [],
                "errors": []
            },
            status_code=500
        )

@router.post("/uploadGeneral/", response_model=DocumentUploadResponse)
async def upload_general_document(
    file: UploadFile = File(..., description="Document file to upload"),
    student_id: int = Form(..., description="Student ID"),
    document_name: str = Form(..., description="Name for the document"),
    document_type: str = Form("GENERAL", description="Document type category"),
    test_run: bool = Form(False, description="Whether this is a test run"),
    auth=Depends(get_auth),
    service: DocService = Depends(get_doc_service)
):
    """
    Upload a general document for a specific student.
    
    This endpoint:
    1. Accepts a single document file (PDF, DOC, DOCX, JPG, PNG)
    2. Associates it with the specified student ID
    3. Uploads it to the Aeries DOC table with the given name
    4. Returns information about the upload
    
    Supported file types: PDF, DOC, DOCX, JPG, JPEG, PNG
    """
    try:
        # Read uploaded file content
        file_content = await file.read()
        core.log('~' * 80)
        core.log(f"Received general document: {file.filename} ({len(file_content)} bytes) for student {student_id}")
        
        # Process the upload
        response = service.upload_general_document(
            file_content=file_content,
            filename=file.filename,
            student_id=student_id,
            document_name=document_name,
            document_type=document_type,
            test_run=test_run
        )
        
        # Return appropriate HTTP status code based on response status
        status_code = 200
        if response.status == "ERROR":
            status_code = 500 if "Error uploading" in response.message else 400
        
        return JSONResponse(
            content=response.dict(),
            status_code=status_code
        )
        
    except Exception as e:
        core.log(f"Unexpected error in general document upload: {str(e)}")
        return JSONResponse(
            content={
                "status": "ERROR",
                "message": f"Unexpected error: {str(e)}",
                "total_documents": 0,
                "extracted_docs": [],
                "errors": []
            },
            status_code=500
        )

@router.get("/categories/")
async def get_document_categories(
    auth=Depends(get_auth)
):
    """
    Get available document categories and their codes.
    
    Returns the available document categories that can be used
    when uploading documents to the Aeries system.
    """
    try:
        categories = {
            "RECLASS": {
                "code": "12",
                "name": "Reclassification Documents",
                "description": "Documents related to English Language Learner reclassification"
            },
            "IEP": {
                "code": "11", 
                "name": "IEP Documents",
                "description": "Individualized Education Program documents"
            },
            "GENERAL": {
                "code": "99",
                "name": "General Documents", 
                "description": "General student documents"
            }
        }
        
        return JSONResponse(
            content={
                "status": "SUCCESS",
                "message": "Available document categories",
                "categories": categories
            },
            status_code=200
        )
        
    except Exception as e:
        return JSONResponse(
            content={
                "status": "ERROR",
                "message": f"Error retrieving categories: {str(e)}"
            },
            status_code=500
        )

@router.get("/student/{student_id}/documents/")
async def get_student_documents(
    student_id: int,
    document_type: Optional[str] = None,
    auth=Depends(get_auth),
    service: DocService = Depends(get_doc_service)
):
    """
    Get a list of documents for a specific student.
    
    This endpoint returns metadata about documents stored in Aeries
    for the specified student. Optionally filter by document type.
    
    Note: This returns document metadata only, not the actual file content.
    """
    try:
        # This would require implementing a method to query existing documents
        # For now, return a placeholder response
        return JSONResponse(
            content={
                "status": "SUCCESS",
                "message": f"Document listing for student {student_id}",
                "student_id": student_id,
                "documents": [],
                "note": "Document listing functionality not yet implemented"
            },
            status_code=200
        )
        
    except Exception as e:
        return JSONResponse(
            content={
                "status": "ERROR", 
                "message": f"Error retrieving documents for student {student_id}: {str(e)}"
            },
            status_code=500
        )