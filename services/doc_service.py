import tempfile
import shutil
import PyPDF2
import re
import os
from typing import List, Dict, Optional, Tuple
import dateparser
from pandas import read_sql_query
from datetime import datetime
from sqlalchemy.sql import text
from slusdlib import aeries, core
from config import get_settings
from models.doc import DocumentUploadResponse, DocumentInfo
from utils.helpers import remove_all_files

class DocService:
    """Service for uploading general documents to Aeries DOC table"""
    
    def __init__(self, db_connection=None):
        self.cnxn = db_connection or aeries.get_aeries_cnxn()
        self.settings = get_settings()
    
    def _get_connection(self, test_run: bool = False):
        return self.cnxn if not test_run else aeries.get_aeries_cnxn(
            database=self.settings.TEST_DATABASE if self.settings.TEST_RUN else None,
            access_level='w'
        )
    
    def process_reclassification_upload(self, file_content: bytes, filename: str, test_run: bool = False) -> DocumentUploadResponse:
        """
        Process uploaded reclassification paperwork - upload as-is without splitting
        """
        # Validate file type
        if not filename.lower().endswith('.pdf'):
            return DocumentUploadResponse(
                status="ERROR",
                message="Only PDF files are supported",
                total_documents=0,
                extracted_docs=[]
            )
        
        try:
            core.log(f"Processing uploaded reclassification PDF: {filename} ({len(file_content)} bytes)")
            
            # Extract student ID from filename if possible
            student_id = self._extract_student_id_from_filename(filename)
            if not student_id:
                return DocumentUploadResponse(
                    status="ERROR",
                    message="Could not extract student ID from filename. Expected format: 'XXXXXX_Name_Document.pdf'",
                    total_documents=0,
                    extracted_docs=[]
                )
            
            # Get database connection
            cnxn = self._get_connection(test_run)
            
            # Get student name from database
            student_name = self._get_student_name(cnxn, int(student_id))
            
            if student_name == "Unknown":
                return DocumentUploadResponse(
                    status="ERROR",
                    message=f"Student {student_id} not found in the database or is inactive",
                    total_documents=0,
                    extracted_docs=[]
                )
            
            # Create document info
            doc_info = {
                'stu_id': student_id,
                'student_name': student_name,
                'document_type': os.path.splitext(filename)[0],  # Use filename without extension
                'file_content': file_content,
                'file_extension': 'pdf'
            }
            
            # Upload to Aeries
            errors = []
            if not test_run:
                errors = self._upload_single_doc_to_aeries(cnxn, doc_info, "RECLASS", test_run)
            else:
                core.log("Test run - document would be uploaded to test database.")
            
            # Format response
            formatted_doc = DocumentInfo(
                file=filename,
                stu_id=student_id,
                student_name=student_name,
                document_type=os.path.splitext(filename)[0],
                pages=1,  # We don't know the actual page count, assume 1
                upload_date=datetime.now().strftime('%Y-%m-%d')
            )
            
            if not errors:
                status_message = f"Successfully uploaded {filename}"
                if test_run:
                    status_message += " (TEST RUN)"
                
                return DocumentUploadResponse(
                    status="SUCCESS",
                    message=status_message,
                    total_documents=1,
                    extracted_docs=[formatted_doc],
                    errors=[]
                )
            else:
                return DocumentUploadResponse(
                    status="ERROR",
                    message="Failed to upload document",
                    total_documents=0,
                    extracted_docs=[],
                    errors=errors
                )
            
        except Exception as e:
            core.log(f"Error processing reclassification upload: {e}")
            return DocumentUploadResponse(
                status="ERROR",
                message=f"Error processing reclassification document: {str(e)}",
                total_documents=0,
                extracted_docs=[]
            )

    def _extract_student_id_from_filename(self, filename: str) -> str:
        """Extract student ID from filename format: XXXXXX_Name_Document.pdf"""
        # Remove extension
        base_name = os.path.splitext(filename)[0]
        
        # Look for student ID at the beginning of filename
        match = re.search(r'^(\d{5,6})_', base_name)
        if match:
            return match.group(1)
        
        # Alternative: look for any 5-6 digit number
        match = re.search(r'(\d{5,6})', base_name)
        if match:
            return match.group(1)
        
        return None

    def _upload_single_doc_to_aeries(self, cnxn, doc_info: Dict, document_type: str, test_run: bool) -> List[Dict]:
        """Upload a single document to Aeries"""
        category_codes = {
            "RECLASS": "12",
            "IEP": "11",
            "GENERAL": "99"
        }
        
        category_code = category_codes.get(document_type, "99")
        today = datetime.now().strftime("%Y-%m-%d")
        errors = []
        
        try:
            student_id = int(doc_info['stu_id'])
            
            # Get student grade
            stu_gr = self._get_student_grade(cnxn, student_id)
            if not stu_gr:
                return [{
                    "message": f"Student {student_id} not found in the database, or student is inactive.",
                    "stu_id": doc_info['stu_id'],
                    "student_name": doc_info['student_name']
                }]
            
            # Get next sequence
            next_sq = self._get_next_sq(student_id, 'DOC', cnxn)
            
            # Delete old reclassification documents for this student
            if document_type == "RECLASS":
                self._delete_old_docs(cnxn, student_id, category_code)
            
            # Prepare SQL insert
            sql = text('''INSERT INTO DOC (
                ID, SQ, DT, GR, CT, NM, XT, RB, SZ, LK, SRC, SCT, TY, UN, IDT
                ) VALUES (
                :id, :sq, :dt, :gr, :ct, :nm, :xt, :rb, :sz, :lk, :src, :sct, :ty, :un, :idt
                )''')
                
            params = {
                'id': str(student_id),
                'sq': int(next_sq),
                'dt': today,
                'gr': int(stu_gr) if isinstance(stu_gr, (int, float)) else str(stu_gr),
                'ct': str(category_code),
                'nm': doc_info['document_type'][:100],
                'xt': doc_info['file_extension'],
                'rb': doc_info['file_content'],
                'sz': int(len(doc_info['file_content'])),
                'lk': 1,
                'src': '',
                'sct': '',
                'ty': 'DOC',
                'un': 'Automation',
                'idt': today
            }
            
            with cnxn.connect() as conn:
                conn.execute(sql, params)
                conn.commit()
                
            core.log(f"Successfully uploaded document '{doc_info['document_type']}' for student {student_id}")
                
        except Exception as e:
            errors.append({
                "message": f"Error uploading document: {str(e)}",
                "stu_id": doc_info['stu_id'],
                "student_name": doc_info['student_name']
            })
        
    def _upload_single_doc_to_aeries(self, cnxn, doc_info: Dict, document_type: str, test_run: bool) -> List[Dict]:
        """Upload a single document to Aeries"""
        category_codes = {
            "RECLASS": "12",
            "IEP": "11",
            "GENERAL": "99"
        }
        
        category_code = category_codes.get(document_type, "99")
        today = datetime.now().strftime("%Y-%m-%d")
        errors = []
        
        try:
            student_id = int(doc_info['stu_id'])
            
            # Get student grade
            stu_gr = self._get_student_grade(cnxn, student_id)
            if not stu_gr:
                return [{
                    "message": f"Student {student_id} not found in the database, or student is inactive.",
                    "stu_id": doc_info['stu_id'],
                    "student_name": doc_info['student_name']
                }]
            
            # Get next sequence
            next_sq = self._get_next_sq(student_id, 'DOC', cnxn)
            
            # Delete old reclassification documents for this student
            if document_type == "RECLASS":
                self._delete_old_docs(cnxn, student_id, category_code)
            
            # Prepare SQL insert
            sql = text('''INSERT INTO DOC (
                ID, SQ, DT, GR, CT, NM, XT, RB, SZ, LK, SRC, SCT, TY, UN, IDT
                ) VALUES (
                :id, :sq, :dt, :gr, :ct, :nm, :xt, :rb, :sz, :lk, :src, :sct, :ty, :un, :idt
                )''')
                
            params = {
                'id': str(student_id),
                'sq': int(next_sq),
                'dt': today,
                'gr': int(stu_gr) if isinstance(stu_gr, (int, float)) else str(stu_gr),
                'ct': str(category_code),
                'nm': doc_info['document_type'][:100],
                'xt': doc_info['file_extension'],
                'rb': doc_info['file_content'],
                'sz': int(len(doc_info['file_content'])),
                'lk': 1,
                'src': '',
                'sct': '',
                'ty': 'DOC',
                'un': 'Automation',
                'idt': today
            }
            
            with cnxn.connect() as conn:
                conn.execute(sql, params)
                conn.commit()
                
            core.log(f"Successfully uploaded document '{doc_info['document_type']}' for student {student_id}")
                
        except Exception as e:
            errors.append({
                "message": f"Error uploading document: {str(e)}",
                "stu_id": doc_info['stu_id'],
                "student_name": doc_info['student_name']
            })
        
        return errors
    def _upload_single_doc_to_aeries(self, cnxn, doc_info: Dict, document_type: str, test_run: bool) -> List[Dict]:
        """Upload a single document to Aeries"""
        category_codes = {
            "RECLASS": "12",
            "IEP": "11",
            "GENERAL": "99"
        }
        
        category_code = category_codes.get(document_type, "99")
        today = datetime.now().strftime("%Y-%m-%d")
        errors = []
        
        try:
            student_id = int(doc_info['stu_id'])
            
            # Get student grade
            stu_gr = self._get_student_grade(cnxn, student_id)
            if not stu_gr:
                return [{
                    "message": f"Student {student_id} not found in the database, or student is inactive.",
                    "stu_id": doc_info['stu_id'],
                    "student_name": doc_info['student_name']
                }]
            
            # Get next sequence
            next_sq = self._get_next_sq(student_id, 'DOC', cnxn)
            
            # Prepare SQL insert
            sql = text('''INSERT INTO DOC (
                ID, SQ, DT, GR, CT, NM, XT, RB, SZ, LK, SRC, SCT, TY, UN, IDT
                ) VALUES (
                :id, :sq, :dt, :gr, :ct, :nm, :xt, :rb, :sz, :lk, :src, :sct, :ty, :un, :idt
                )''')
                
            params = {
                'id': str(student_id),
                'sq': int(next_sq),
                'dt': today,
                'gr': int(stu_gr) if isinstance(stu_gr, (int, float)) else str(stu_gr),
                'ct': str(category_code),
                'nm': doc_info['document_type'][:100],
                'xt': doc_info['file_extension'],
                'rb': doc_info['file_content'],
                'sz': int(len(doc_info['file_content'])),
                'lk': 1,
                'src': '',
                'sct': '',
                'ty': 'DOC',
                'un': 'Automation',
                'idt': today
            }
            
            with cnxn.connect() as conn:
                conn.execute(sql, params)
                conn.commit()
                
        except Exception as e:
            errors.append({
                "message": f"Error uploading document: {str(e)}",
                "stu_id": doc_info['stu_id'],
                "student_name": doc_info['student_name']
            })
        
        return errors

    def _get_student_name(self, cnxn, stu_id: int) -> str:
        """Get student name from database"""
        try:
            sql = f"""SELECT FN + ' ' + LN as name FROM STU WHERE ID = {stu_id} AND tg = '' and del = 0"""
            data = read_sql_query(text(sql), cnxn)
            if not data.empty:
                return data.name.values[0]
        except:
            pass
        return "Unknown"