import tempfile
import shutil
import PyPDF2
import re
import os
from typing import List, Dict
import dateparser
from pandas import read_sql_query
from datetime import datetime
from sqlalchemy.sql import text
from slusdlib import aeries, core
from config import get_settings
from models.sped import IEPDocumentInfo, IEPUploadResponse
from utils.helpers import remove_all_files

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
                extracted_docs=[]
            )
        
        temp_dir = None
        try:
            # Create temporary directory for processing
            temp_dir = tempfile.mkdtemp(prefix="iep_upload_")
            
            core.log(f"Processing uploaded PDF: {filename} ({len(file_content)} bytes)")
            
            # Split the PDF into individual IEP documents
            extracted_docs = self._split_iep_pdf_from_upload(file_content, temp_dir)
            
            if not extracted_docs:
                return IEPUploadResponse(
                    status="WARNING", 
                    message="No IEP documents found in the uploaded PDF. Please ensure the PDF contains valid IEP 'At a Glance' documents with the expected header format.",
                    total_documents=0,
                    extracted_docs=[]
                )
            
            # Get database connection
            cnxn = self._get_connection(test_run)
            
            # Upload to Aeries (unless it's a test run)
            upload_success = True
            try:
                if not test_run:
                    self._upload_iep_docs_to_aeries(cnxn, extracted_docs, test_run)
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
                extracted_docs=formatted_docs
            )
            
        except Exception as e:
            core.log(f"Error processing IEP upload: {e}")
            return IEPUploadResponse(
                status="ERROR",
                message=f"Error processing IEP documents: {str(e)}",
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

    def process_iep_from_file(self, input_pdf_path: str) -> List[Dict]:
        """
        Process IEP documents from a file path (for batch processing)
        """
        if not os.path.exists(input_pdf_path):
            core.log(f"Error: File '{input_pdf_path}' not found.")
            return []
        
        core.log(f"Processing PDF: {input_pdf_path}")
        extracted_docs = self._split_iep_pdf(input_pdf_path)
        
        if not extracted_docs:
            core.log("No IEP documents found in the PDF.")
            return []
        
        # Get database connection
        cnxn = self._get_connection(self.settings.TEST_RUN)
        
        # Upload to Aeries
        self._upload_iep_docs_to_aeries(cnxn, extracted_docs, self.settings.TEST_RUN)
        
        # Log summary
        core.log("-" * 80)
        core.log(f"{'Student ID':<15} {'IEP Date':<15} {'Output File':<40} {'Pages':<10}")
        core.log("-" * 80)
        for doc in extracted_docs:
            core.log(f"{doc['stu_id']:<15} {doc['iep_date']:<15} {os.path.basename(doc['file']):<40} {doc['pages']:<10}")
        core.log("-" * 80)
        core.log(f"Total: {len(extracted_docs)} IEP documents")
        
        # Clean up split files
        remove_all_files(self.settings.SPLIT_IEP_FOLDER)
        
        return extracted_docs

    def process_iep_from_input_folder(self) -> List[Dict]:
        """
        Process IEP documents from the configured input folder
        """
        input_folder = self.settings.INPUT_DIRECTORY_PATH
        input_pdf = core.find_file_in_dir(input_folder, extension=".pdf")
        
        if not input_pdf:
            core.log(f"No PDF files found in {input_folder}")
            return []
        
        return self.process_iep_from_file(input_pdf)

    def _split_iep_pdf_from_upload(self, pdf_file_content: bytes, output_dir: str) -> List[Dict]:
        """
        Split an IEP PDF from uploaded content into multiple PDFs by detecting the header pattern.
        Extract District ID from each document.
        """
        # Create a temporary file for the uploaded PDF
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            temp_file.write(pdf_file_content)
            temp_pdf_path = temp_file.name
        
        try:
            return self._split_iep_pdf(temp_pdf_path, output_dir)
        finally:
            # Clean up the temporary PDF file
            os.unlink(temp_pdf_path)

    def _split_iep_pdf(self, input_pdf_path: str, output_dir: str = None) -> List[Dict]:
        """
        Split an IEP PDF into multiple PDFs by detecting the header pattern.
        Extract District ID from each document.
        """
        if output_dir is None:
            output_dir = self.settings.SPLIT_IEP_FOLDER
            
        os.makedirs(output_dir, exist_ok=True)
        
        with open(input_pdf_path, "rb") as file:
            reader = PyPDF2.PdfReader(file)
            total_pages = len(reader.pages)
            
            header_pattern = r"MID ALAMEDA COUNTY SELPA\s+IEP AT A GLANCE"
            district_id_pattern = r"District ID:\s*(\d+)"
            iep_date_pattern = r"IEP Date:\s*(\d{1,2}/\d{1,2}/\d{4})"
            
            doc_boundaries = []
            
            core.log(f"Scanning {total_pages} pages for IEP documents...")
            for page_num in range(total_pages):
                text = reader.pages[page_num].extract_text()
                
                if re.search(header_pattern, text[:500]):
                    district_id_match = re.search(district_id_pattern, text)
                    stu_id = district_id_match.group(1) if district_id_match else f"unknown_{page_num}"
                    
                    iep_date_match = re.search(iep_date_pattern, text)
                    iep_date = iep_date_match.group(1) if iep_date_match else "unknown_date"
                    
                    if iep_date != "unknown_date":
                        try:
                            month, day, year = iep_date.split('/')
                            month = month.zfill(2)
                            day = day.zfill(2)
                            iep_date_formatted = f"{year}-{month}-{day}"
                        except:
                            iep_date_formatted = iep_date.replace('/', '-')
                    else:
                        iep_date_formatted = iep_date
                    
                    core.log(f"Found IEP document on page {page_num+1} with District ID: {stu_id}, IEP Date: {iep_date}")
                    doc_boundaries.append({
                        "start_page": page_num, 
                        "stu_id": stu_id,
                        "iep_date": iep_date,
                        "iep_date_formatted": iep_date_formatted
                    })
            
            extracted_docs = []
            for i, doc in enumerate(doc_boundaries):
                writer = PyPDF2.PdfWriter()
                
                end_page = doc_boundaries[i+1]["start_page"] if i < len(doc_boundaries) - 1 else total_pages
                
                for page_num in range(doc["start_page"], end_page):
                    writer.add_page(reader.pages[page_num])
                
                output_filename = os.path.join(output_dir, f"IEP_at_a_Glance_for_{doc['stu_id']}_{doc['iep_date_formatted']}.pdf")
                with open(output_filename, "wb") as output_file:
                    writer.write(output_file)
                
                core.log(f"Created {output_filename}")
                extracted_docs.append({
                    "file": output_filename,
                    "stu_id": doc["stu_id"],
                    "iep_date": doc["iep_date"],
                    "pages": end_page - doc["start_page"]
                })
            
            return extracted_docs

    def _upload_iep_docs_to_aeries(self, cnxn, extracted_docs: List[Dict], test_run: bool = False, lock_table: str = 'CSE') -> None:
        """
        Upload IEP documents to Aeries from a list of extracted document info.
        """
        category_code = self.settings.IEP_AT_A_GLANCE_DOCUMENT_CODE
        today = datetime.now().strftime("%Y-%m-%d")
        
        for doc in extracted_docs:
            core.log(f"Uploading {doc['file']} to AERIES...")
            with open(doc['file'], "rb") as file:
                pdf_data = file.read()
            
            # Use the helper methods
            next_sq = self._get_next_sq(int(doc['stu_id']), 'DOC', cnxn)
            stu_gr = self._get_student_grade(cnxn, int(doc['stu_id']))
            
            if stu_gr == "" or stu_gr is None:
                core.log(f"Student {doc['stu_id']} not found in the database.")
                continue
                
            # Delete old IEP docs
            self._delete_old_iep_docs(cnxn, int(doc['stu_id']))
            
            # Prepare SQL insert
            sql = text('''INSERT INTO DOC (
                ID, SQ, DT, GR, CT, NM, XT, RB, SZ, LK, SRC, SCT, TY, UN, IDT
                ) VALUES (
                :id, :sq, :dt, :gr, :ct, :nm, :xt, :rb, :sz, :lk, :src, :sct, :ty, :un, :idt
                )''')
                
            params = {
                'id': str(doc['stu_id']),
                'sq': int(next_sq),
                'dt': str(doc['iep_date']),
                'gr': int(stu_gr) if isinstance(stu_gr, (int, float)) else str(stu_gr),
                'ct': str(category_code),
                'nm': f'IEP At A Glance {dateparser.parse(doc["iep_date"]).strftime("%m/%d/%Y")} #{str(doc["stu_id"])}',
                'xt': 'pdf',
                'rb': pdf_data,
                'sz': int(len(pdf_data)),
                'lk': 1,
                'src': '',
                'sct': '',
                'ty': str(lock_table),
                'un': 'Automation',
                'idt': today
            }
            
            if not test_run:
                with cnxn.connect() as conn:
                    conn.execute(sql, params)
                    conn.commit()
        
        core.log("Upload complete.")

    def _get_next_sq(self, id: int, table_name: str, cnxn, pid_for_id: bool = False) -> int:
        """
        Find the next sequence number in the DOC table for a given student id.
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

    def _delete_old_iep_docs(self, cnxn, stu_id: int) -> None:
        """
        Delete old IEP documents from the DOC table for a given student id.
        """
        doc_type_code = self.settings.IEP_AT_A_GLANCE_DOCUMENT_CODE
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
            return aeries.get_aeries_cnxn(access_level='w', database=self.settings.TEST_DATABASE)