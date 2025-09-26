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
    
    def process_reclassification_upload(self, file_content: bytes, filename: str, test_run: bool = False) -> DocumentUploadResponse:
        """
        Process uploaded reclassification paperwork
        """
        # Validate file type
        if not filename.lower().endswith('.pdf'):
            return DocumentUploadResponse(
                status="ERROR",
                message="Only PDF files are supported",
                total_documents=0,
                extracted_docs=[]
            )
        
        temp_dir = None
        try:
            # Create temporary directory for processing
            temp_dir = tempfile.mkdtemp(prefix="reclass_upload_")
            
            core.log(f"Processing uploaded reclassification PDF: {filename} ({len(file_content)} bytes)")
            
            # Split the PDF into individual student documents
            extracted_docs = self._split_reclassification_pdf_from_upload(file_content, temp_dir, filename)
            
            if not extracted_docs:
                return DocumentUploadResponse(
                    status="WARNING", 
                    message="No reclassification documents found in the uploaded PDF. Please ensure the PDF contains valid reclassification documents with student IDs.",
                    total_documents=0,
                    extracted_docs=[]
                )
            
            # Get database connection
            cnxn = self._get_connection(test_run)
            
            # Upload to Aeries (unless it's a test run)
            upload_success = True
            errors = []
            
            if not test_run:
                errors = self._upload_docs_to_aeries(cnxn, extracted_docs, document_type="RECLASS", test_run=test_run)
            else:
                core.log("Test run - documents processed and uploaded to test database.")
                errors = self._upload_docs_to_aeries(cnxn, extracted_docs, document_type="RECLASS", test_run=test_run)
            
            # Format response
            formatted_docs = [
                DocumentInfo(
                    file=os.path.basename(doc["file"]),
                    stu_id=doc["stu_id"],
                    student_name=doc.get("student_name", "Unknown"),
                    document_type=doc.get("document_type", "Reclassification"),
                    pages=doc["pages"],
                    upload_date=datetime.now().strftime('%Y-%m-%d')
                )
                for doc in extracted_docs
            ]
            
            status_message = f"Successfully processed {len(extracted_docs)} reclassification document(s)"
            if len(errors) > 0:
                status_message += f" with {len(errors)} errors"
            if test_run:
                status_message += " (TEST RUN)"
            elif not upload_success:
                status_message += " but encountered errors during database upload"
                upload_success = False
            
            return DocumentUploadResponse(
                status="SUCCESS" if upload_success and len(errors) == 0 else "PARTIAL_SUCCESS",
                message=status_message,
                total_documents=len(extracted_docs),
                extracted_docs=formatted_docs,
                errors=errors
            )
            
        except Exception as e:
            core.log(f"Error processing reclassification upload: {e}")
            return DocumentUploadResponse(
                status="ERROR",
                message=f"Error processing reclassification documents: {str(e)}",
                total_documents=0,
                extracted_docs=[]
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

    def _split_reclassification_pdf_from_upload(self, pdf_file_content: bytes, output_dir: str, original_filename: str = None) -> List[Dict]:
        """
        Split a reclassification PDF from uploaded content into multiple PDFs by detecting student documents.
        """
        # Create a temporary file for the uploaded PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(pdf_file_content)
            temp_pdf_path = temp_file.name
        
        try:
            return self._split_reclassification_pdf(temp_pdf_path, output_dir, original_filename)
        finally:
            # Clean up the temporary PDF file
            os.unlink(temp_pdf_path)

    def _split_reclassification_pdf(self, input_pdf_path: str, output_dir: str, original_filename: str = None) -> List[Dict]:
        """
        Split a reclassification PDF into individual student documents.
        """
        os.makedirs(output_dir, exist_ok=True)
        
        with open(input_pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            total_pages = len(reader.pages)
            
            # Document type patterns for reclassification paperwork
            doc_patterns = {
                'notification': r'Notification of English Language Program Exit',
                'meeting': r'Reclassification Meeting w/ Parent/Guardian|Alternate Reclassification IEP Meeting',
                'teacher_eval': r'Teacher Evaluation for Reclassification|Criteria 2: Teacher Evaluation'
            }
            
            # Student ID patterns
            student_id_patterns = [
                r'Student ID#?\s*:?\s*(\d{6})',
                r'Student ID#?\s*:?\s*(\d{5})',
                r'Student ID[#:\s]*(\d{6})',
                r'Student ID[#:\s]*(\d{5})'
            ]
            
            # Name patterns - more targeted to avoid capturing surrounding text
            name_patterns = [
                # Most specific patterns first - looking for exact formats from your PDFs
                r'Student:\s*([A-Za-z]+(?:\s+[A-Za-z]+)+)\s*\n',  # "Student: Borui Hu" followed by newline
                r'Student\s+([A-Za-z]+(?:\s+[A-Za-z]+)+)\s+Grade Level',  # Table format: "Student Borui Hu Grade Level"
                r'Name:\s*([A-Za-z]+(?:\s+[A-Za-z]+)+)\s*\n',     # "Name: Angel Ramirez Hermosillo" followed by newline
                
                # Backup patterns
                r'Student:\s*([A-Za-z]+(?:\s+[A-Za-z]+)+)\s+Student ID',
                r'Name:\s*([A-Za-z]+(?:\s+[A-Za-z]+)+)\s+Student ID',
                
                # Last resort - capture name between specific markers
                r'(?:Student:|Name:)\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\s*(?:Grade|Student ID|School)',
            ]
            
            student_documents = {}
            
            core.log(f"Scanning {total_pages} pages for reclassification documents...")
            
            for page_num in range(total_pages):
                text = reader.pages[page_num].extract_text()
                text = self._normalize_ligatures(text)
                
                # Find student ID
                student_id = None
                for pattern in student_id_patterns:
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        student_id = match.group(1)
                        break
                
                if not student_id:
                    continue
                
                # Find student name with improved extraction
                student_name = "Unknown"
                for i, pattern in enumerate(name_patterns):
                    match = re.search(pattern, text, re.IGNORECASE)
                    if match:
                        name = match.group(1).strip()
                        # Clean up the name - be more strict about what we accept
                        name = re.sub(r'\s+', ' ', name)  # Normalize whitespace
                        name = re.sub(r'[,\n\r\t]+', '', name)  # Remove commas, newlines, tabs
                        
                        # Validate the name - must be reasonable length and format
                        if (2 < len(name) <= 50 and 
                            not any(char.isdigit() for char in name) and
                            len(name.split()) >= 2 and  # At least first and last name
                            all(word.isalpha() for word in name.split())):  # All words are alphabetic
                            
                            student_name = name
                            core.log(f"Extracted student name '{student_name}' using pattern {i+1}")
                            break
                
                if student_name == "Unknown":
                    # Try to extract from the original filename as fallback
                    if original_filename:
                        filename_match = re.search(r'\d{5,6}_([A-Za-z_]+)', original_filename)
                        if filename_match:
                            filename_name = filename_match.group(1).replace('_', ' ')
                            if len(filename_name.split()) >= 2:
                                student_name = filename_name
                                core.log(f"Extracted student name '{student_name}' from original filename")
                    
                if student_name == "Unknown":
                    core.log(f"Could not extract student name from page {page_num+1}. Text preview: {text[:300]}...")
                
                # Determine document type
                doc_type = "Reclassification"
                for doc_key, doc_pattern in doc_patterns.items():
                    if re.search(doc_pattern, text, re.IGNORECASE):
                        # Use the actual pattern match, not just the key
                        if doc_key == 'notification':
                            doc_type = "Notification of English Language Program Exit"
                        elif doc_key == 'meeting':
                            doc_type = "Reclassification Meeting"
                        elif doc_key == 'teacher_eval':
                            doc_type = "Teacher Evaluation for Reclassification"
                        else:
                            doc_type = doc_key.title().replace('_', ' ')
                        break
                
                core.log(f"Found {doc_type} document on page {page_num+1} for Student ID: {student_id} ({student_name})")
                
                # Group pages by student
                if student_id not in student_documents:
                    student_documents[student_id] = {
                        'student_name': student_name,
                        'pages': [],
                        'doc_types': set()
                    }
                
                student_documents[student_id]['pages'].append(page_num)
                student_documents[student_id]['doc_types'].add(doc_type)
            
            # Create combined PDFs for each student
            extracted_docs = []
            for student_id, doc_info in student_documents.items():
                if not doc_info['pages']:
                    continue
                
                writer = PyPDF2.PdfWriter()
                
                # Sort pages and add to writer
                sorted_pages = sorted(doc_info['pages'])
                for page_num in sorted_pages:
                    writer.add_page(reader.pages[page_num])
                
                # Use original filename if provided, otherwise generate new name
                if original_filename and len(student_documents) == 1:
                    # Single student document - use original filename
                    output_filename = os.path.join(output_dir, original_filename)
                else:
                    # Multiple students or no original filename - generate descriptive names
                    safe_name = doc_info['student_name'].replace(' ', '_').replace(',', '')
                    if len(doc_info['doc_types']) == 1:
                        # Single document type
                        doc_types_str = list(doc_info['doc_types'])[0].replace(' ', '_')
                    else:
                        # Multiple document types - create a combined name
                        doc_types_sorted = sorted(doc_info['doc_types'])
                        doc_types_str = "Complete_Reclassification_Package"
                    
                    output_filename = os.path.join(
                        output_dir, 
                        f"{student_id}_{safe_name}_{doc_types_str}.pdf"
                    )
                
                with open(output_filename, "wb") as output_file:
                    writer.write(output_file)
                
                core.log(f"Created {output_filename}")
                
                # Determine the document type name for the response
                if len(doc_info['doc_types']) == 1:
                    response_doc_type = list(doc_info['doc_types'])[0]
                else:
                    response_doc_type = "Complete Reclassification Package"
                
                extracted_docs.append({
                    "file": output_filename,
                    "stu_id": student_id,
                    "student_name": doc_info['student_name'],
                    "document_type": response_doc_type,
                    "pages": len(sorted_pages),
                    "doc_types": list(doc_info['doc_types'])
                })
            
            return extracted_docs

    def _normalize_ligatures(self, text: str) -> str:
        """Normalize ligatures and special characters to standard ASCII"""
        replacements = {
            'ﬁ': 'fi',  # fi ligature
            'ﬂ': 'fl',  # fl ligature
            'ﬀ': 'ff',  # ff ligature
            'ﬃ': 'ffi', # ffi ligature
            'ﬄ': 'ffl', # ffl ligature
        }
        for ligature, replacement in replacements.items():
            text = text.replace(ligature, replacement)
        return text

    def _upload_docs_to_aeries(self, cnxn, extracted_docs: List[Dict], document_type: str = "RECLASS", test_run: bool = False, ty_value: str = None) -> List[Dict]:
        """
        Upload documents to Aeries DOC table
        """
        # Document category codes - you may need to adjust these based on your Aeries setup
        category_codes = {
            "RECLASS": "06",  # Reclassification documents
            "IEP": "11",      # IEP documents (from sped_service)
            "GENERAL": "99"   # General documents
        }
        
        category_code = category_codes.get(document_type, "99")
        today = datetime.now().strftime("%Y-%m-%d")
        errors = []        
        
        for doc in extracted_docs:
            # Skip documents with invalid student IDs
            if doc['stu_id'].startswith("unknown_"):
                errors.append({
                    "message": f"Invalid student ID format: {doc['stu_id']}",
                    "stu_id": doc['stu_id'],
                    "student_name": doc.get('student_name', 'Unknown')
                })
                core.log(f"Skipping document with invalid student ID: {doc['stu_id']}")
                continue
            
            # Validate student ID is numeric
            try:
                student_id = int(doc['stu_id'])
            except ValueError:
                errors.append({
                    "message": f"Invalid student ID format: {doc['stu_id']}",
                    "stu_id": doc['stu_id'],
                    "student_name": doc.get('student_name', 'Unknown')
                })
                core.log(f"Skipping document with invalid student ID: {doc['stu_id']}")
                continue
            
            core.log(f"Uploading {doc['file']} to AERIES...")
            
            try:
                with open(doc['file'], "rb") as file:
                    pdf_data = file.read()
                
                # Use the helper methods
                next_sq = self._get_next_sq(int(doc['stu_id']), 'DOC', cnxn)
                stu_gr = self._get_student_grade(cnxn, int(doc['stu_id']))
                
                if stu_gr == "" or stu_gr is None:
                    errors.append({
                        "message": f"Student {doc['stu_id']} not found in the database, or student is inactive.",
                        "stu_id": doc['stu_id'],
                        "student_name": doc.get('student_name', 'Unknown')
                    })
                    core.log(f"Student {doc['stu_id']} not found in the database, or student is inactive.")
                    continue
                
                # Delete old documents of the same type if needed
                self._delete_old_docs(cnxn, int(doc['stu_id']), category_code)
                
                # Prepare document name - use original filename instead of generating new one
                original_filename = os.path.basename(doc['file'])
                # Remove the path and extension, keep the original name
                doc_name = os.path.splitext(original_filename)[0]
                
                # Prepare SQL insert
                sql = text('''INSERT INTO DOC (
                    ID, SQ, DT, GR, CT, NM, XT, RB, SZ, LK, SRC, SCT, TY, UN, IDT
                    ) VALUES (
                    :id, :sq, :dt, :gr, :ct, :nm, :xt, :rb, :sz, :lk, :src, :sct, :ty, :un, :idt
                    )''')
                    
                params = {
                    'id': str(doc['stu_id']),
                    'sq': int(next_sq),
                    'dt': today,  # Use today's date for reclassification docs
                    'gr': int(stu_gr) if isinstance(stu_gr, (int, float)) else str(stu_gr),
                    'ct': str(category_code),
                    'nm': doc_name[:100],  # Limit name length
                    'xt': 'pdf',
                    'rb': pdf_data,
                    'sz': int(len(pdf_data)),
                    'lk': 1,
                    'src': '',
                    'sct': '',
                    'ty': ty_value if ty_value else '',  # Use shorter value instead of 'RECLASS'
                    'un': 'Automation',
                    'idt': today
                }
                
                with cnxn.connect() as conn:
                    conn.execute(sql, params)
                    conn.commit()
                
                core.log(f"Successfully uploaded document for student {doc['stu_id']}")
                
            except Exception as e:
                errors.append({
                    "message": f"Error uploading document for student {doc['stu_id']}: {str(e)}",
                    "stu_id": doc['stu_id'],
                    "student_name": doc.get('student_name', 'Unknown')
                })
                core.log(f"Error uploading document for student {doc['stu_id']}: {e}")
                continue
        
        core.log("Upload complete.")
        return errors

    def _get_next_sq(self, id: int, table_name: str, cnxn, pid_for_id: bool = False) -> int:
        """
        Find the next sequence number in the specified table for a given student id.
        """
        if pid_for_id:
            sql = f'''select top 1 sq
                    from {table_name}
                    where PID = {id}
                    order by sq desc'''
        else:
            sql = f'''select top 1 sq
                    from {table_name}
                    where ID = {id}
                    order by sq desc'''

        data = read_sql_query(text(sql), cnxn)
        if data.empty: 
            return 1
        return data.sq.values[0] + 1

    def _get_student_grade(self, cnxn, stu_id: int) -> str:
        """
        Get the grade of a student from the database.
        """
        sql = f"""SELECT GR FROM STU WHERE ID = {stu_id} AND tg = '' and del = 0"""
        data = read_sql_query(text(sql), cnxn)
        if data.empty: 
            return ""
        return data.GR.values[0]

    def _delete_old_docs(self, cnxn, stu_id: int, doc_type_code: str) -> None:
        """
        Delete old documents from the DOC table for a given student id and document type.
        """
        sql = f"""UPDATE DOC SET DEL = 1 WHERE ID = '{stu_id}' AND CT = '{doc_type_code}' AND DEL = 0"""
        with cnxn.connect() as conn:
            conn.execute(text(sql))
            conn.commit()

    def _get_connection(self, test_run: bool):
        """Get appropriate database connection based on test_run flag"""
        if test_run:
            return aeries.get_aeries_cnxn(
                database=self.settings.TEST_DATABASE, 
                access_level='w'
            )
        else:
            return aeries.get_aeries_cnxn(access_level='w')

    def upload_general_document(self, file_content: bytes, filename: str, student_id: int, 
                              document_name: str, document_type: str = "GENERAL", 
                              test_run: bool = False) -> DocumentUploadResponse:
        """
        Upload a general document for a specific student
        """
        try:
            # Validate file type
            if not filename.lower().endswith(('.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png')):
                return DocumentUploadResponse(
                    status="ERROR",
                    message="Unsupported file type. Supported types: PDF, DOC, DOCX, JPG, JPEG, PNG",
                    total_documents=0,
                    extracted_docs=[]
                )
            
            # Get database connection
            cnxn = self._get_connection(test_run)
            
            # Create document info
            doc_info = {
                'stu_id': str(student_id),
                'student_name': self._get_student_name(cnxn, student_id),
                'document_type': document_name,
                'file_content': file_content,
                'file_extension': os.path.splitext(filename)[1].lower().replace('.', '')
            }
            
            # Upload to Aeries
            errors = self._upload_single_doc_to_aeries(cnxn, doc_info, document_type, test_run)
            
            formatted_doc = DocumentInfo(
                file=filename,
                stu_id=str(student_id),
                student_name=doc_info['student_name'],
                document_type=document_name,
                pages=1,
                upload_date=datetime.now().strftime('%Y-%m-%d')
            )
            
            if not errors:
                return DocumentUploadResponse(
                    status="SUCCESS",
                    message=f"Successfully uploaded {document_name} for student {student_id}",
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
            return DocumentUploadResponse(
                status="ERROR",
                message=f"Error uploading document: {str(e)}",
                total_documents=0,
                extracted_docs=[],
                errors=[]
            )

    def _upload_single_doc_to_aeries(self, cnxn, doc_info: Dict, document_type: str, test_run: bool, ty_value: str = '') -> List[Dict]:
        """Upload a single document to Aeries"""
        category_codes = {
            "RECLASS": "06",
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
                'ty': ty_value if ty_value else '',
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