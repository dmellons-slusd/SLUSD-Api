import tempfile
import shutil
import os
from typing import List
from slusdlib import aeries, core
from config import get_settings
from iep_at_a_glance import split_iep_pdf_from_upload, upload_iep_docs_to_aeries_from_list
from models.sped import IEPDocumentInfo, IEPUploadResponse

class SPEDService:
    def __init__(self, db_connection=None):
        self.cnxn = db_connection or aeries.get_aeries_cnxn()
        self.settings = get_settings()
    
    def process_iep_upload(self, file_content: bytes, filename: str, test_run: bool = False) -> IEPUploadResponse:
        """
        Process uploaded IEP documents
        """
        # Validate file type
        if not filename.lower().endswith('.pdf'):
            return IEPUploadResponse(
                status="ERROR",
                message="Only PDF files are supported",
                total_documents=0,
                extracted_docs=[],
                uploaded_to_aeries=False
            )
        
        temp_dir = None
        try:
            # Create temporary directory for processing
            temp_dir = tempfile.mkdtemp(prefix="iep_upload_")
            
            core.log(f"Processing uploaded PDF: {filename} ({len(file_content)} bytes)")
            
            # Split the PDF into individual IEP documents
            extracted_docs = split_iep_pdf_from_upload(file_content, temp_dir)
            
            if not extracted_docs:
                return IEPUploadResponse(
                    status="WARNING", 
                    message="No IEP documents found in the uploaded PDF. Please ensure the PDF contains valid IEP 'At a Glance' documents with the expected header format.",
                    total_documents=0,
                    extracted_docs=[],
                    uploaded_to_aeries=False
                )
            
            # Get database connection
            cnxn = self._get_connection(test_run)
            
            # Upload to Aeries (unless it's a test run)
            upload_success = True
            try:
                if not test_run:
                    upload_iep_docs_to_aeries_from_list(cnxn, extracted_docs, test_run)
                else:
                    core.log("Test run - documents processed and uploaded to test database.")
            except Exception as e:
                core.log(f"Error uploading to Aeries: {e}")
                upload_success = False
            
            # Format response
            formatted_docs = [
                IEPDocumentInfo(
                    file=os.path.basename(doc["file"]),
                    stu_id=doc["stu_id"],
                    iep_date=doc["iep_date"],
                    pages=doc["pages"]
                )
                for doc in extracted_docs
            ]
            
            status_message = f"Successfully processed {len(extracted_docs)} IEP document(s)"
            if test_run:
                status_message += " (TEST RUN - not uploaded to database)"
            elif not upload_success:
                status_message += " but encountered errors during database upload"
            
            return IEPUploadResponse(
                status="SUCCESS" if upload_success else "PARTIAL_SUCCESS",
                message=status_message,
                total_documents=len(extracted_docs),
                extracted_docs=formatted_docs,
                uploaded_to_aeries=upload_success and not test_run
            )
            
        except Exception as e:
            core.log(f"Error processing IEP upload: {e}")
            return IEPUploadResponse(
                status="ERROR",
                message=f"Error processing IEP documents: {str(e)}",
                total_documents=0,
                extracted_docs=[],
                uploaded_to_aeries=False
            )
        
        finally:
            # Clean up temporary files
            if temp_dir and os.path.exists(temp_dir):
                try:
                    shutil.rmtree(temp_dir)
                    core.log(f"Cleaned up temporary directory: {temp_dir}")
                    core.log('~' * 80)
                except Exception as e:
                    core.log(f"Warning: Could not clean up temporary directory {temp_dir}: {e}")
    
    def _get_connection(self, test_run: bool):
        """Get appropriate database connection based on test_run flag"""
        if test_run:
            return aeries.get_aeries_cnxn(
                database=self.settings.TEST_DATABASE, 
                access_level='w'
            )
        else:
            return aeries.get_aeries_cnxn(access_level='w', database=self.settings.TEST_DATABASE)