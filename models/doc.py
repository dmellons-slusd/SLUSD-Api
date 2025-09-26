from pydantic import BaseModel, Field
from typing import List, Optional

class DocumentInfo(BaseModel):
    """Information about a processed document"""
    file: str = Field(..., description="Original filename")
    stu_id: str = Field(..., description="Student ID")
    student_name: str = Field(..., description="Student name")
    document_type: str = Field(..., description="Type of document")
    pages: int = Field(..., description="Number of pages")
    upload_date: str = Field(..., description="Date of upload (YYYY-MM-DD)")

class UploadError(BaseModel):
    """Error information for failed uploads"""
    message: str = Field(..., description="Error message")
    stu_id: str = Field(..., description="Student ID")
    student_name: str = Field(..., description="Student name")

class DocumentUploadResponse(BaseModel):
    """Response for document upload operations"""
    status: str = Field(..., description="Status: SUCCESS, PARTIAL_SUCCESS, WARNING, or ERROR")
    message: str = Field(..., description="Human-readable message")
    total_documents: int = Field(..., description="Total number of documents processed")
    extracted_docs: List[DocumentInfo] = Field(default=[], description="Successfully processed documents")
    errors: List[UploadError] = Field(default=[], description="Upload errors")

class GeneralDocumentUpload(BaseModel):
    """Request model for general document upload"""
    student_id: int = Field(..., description="Student ID")
    document_name: str = Field(..., description="Name for the document")
    document_type: Optional[str] = Field("GENERAL", description="Document type category")
    test_run: Optional[bool] = Field(False, description="Whether this is a test run")

class ReclassificationUpload(BaseModel):
    """Request model for reclassification document upload"""
    test_run: Optional[bool] = Field(False, description="Whether this is a test run")