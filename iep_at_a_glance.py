import shutil
import PyPDF2
import re
import os
import tempfile
from typing import List
from pandas import read_sql_query
from decouple import config
from datetime import datetime
from sqlalchemy.sql import text
from slusdlib import core, aeries


def split_iep_pdf(input_pdf_path, output_dir=config("SPLIT_IEP_FOLDER", default="split_pdfs")):
    """
    Split an IEP PDF into multiple PDFs by detecting the header pattern.
    Extract District ID from each document.
    
    Args:
        input_pdf_path (str): Path to the input PDF file
        output_dir (str): Directory to save the split PDFs
    
    Returns:
        list: Information about each extracted document
    """
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

def split_iep_pdf_from_upload(pdf_file_content: bytes, output_dir: str = None) -> List[dict]:
    """
    Split an IEP PDF from uploaded content into multiple PDFs by detecting the header pattern.
    Extract District ID from each document.
    
    Args:
        pdf_file_content (bytes): PDF file content as bytes
        output_dir (str): Directory to save the split PDFs
    
    Returns:
        list: Information about each extracted document
    """
    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="split_ieps_")
    
    # Create a temporary file for the uploaded PDF
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
        temp_file.write(pdf_file_content)
        temp_pdf_path = temp_file.name
    
    try:
        with open(temp_pdf_path, "rb") as file:
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
    
    finally:
        # Clean up the temporary PDF file
        os.unlink(temp_pdf_path)

def get_next_sq(id:int, table_name:str, cnxn, pid_for_id: bool=False,) -> int:
    """
    Find the next sequence number in the DOC table for a given student id.

    Parameters
    ----------
    id : int
        The student id to find the next sequence for
    table_name : str
        The name of the table to query
    pid_for_id : bool, optional
        If True, use the PID column instead of ID column, by default False
    cnxn : sqlalchemy.engine.Connection
        The database connection object

    Returns
    -------
    int
        The next sequence number to use for an ADS insert
    """
    if pid_for_id:
        sql = f'''select top 1 sq
                from {table_name}
                where PID = {id}
                order by sq desc'''.format(table_name=table_name, id=id)
    else:
        sql = f'''select top 1 sq
                from {table_name}
                where ID = {id}
                order by sq desc'''.format(table_name=table_name, id=id)

    data = read_sql_query(text(sql), cnxn)
    if data.empty: return 1
    return data.sq.values[0]+1

def get_student_grade(cnxn, stu_id:int) -> str:
    """
    Get the grade of a student from the database.

    Parameters
    ----------
    cnxn : sqlalchemy.engine.Connection
        The database connection object
    stu_id : int
        The student id to find the grade for

    Returns
    -------
    str
        The grade of the student
    """
    sql = f"""SELECT GR FROM STU WHERE ID = {stu_id} AND tg = '' and del = 0"""
    data = read_sql_query(text(sql), cnxn)
    if data.empty: return ""
    return data.GR.values[0]

def delete_old_iep_docs(cnxn, stu_id:int) -> None:
    """
    Delete old IEP documents from the DOC table for a given student id.

    Parameters
    ----------
    cnxn : sqlalchemy.engine.Connection
        The database connection object
    stu_id : int
        The student id to delete old documents for
    """
    doc_type_code = config("IEP_AT_A_GLANCE_DOCUMENT_CODE", default="11", cast=str)
    sql = f"""UPDATE DOC SET DEL = 1 WHERE ID = '{stu_id}' AND CT = '{doc_type_code}' AND DEL = 0"""
    with cnxn.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
    
def upload_iep_docs_to_aeries( cnxn, extracted_docs_folder:str=config("SPLIT_IEP_FOLDER", default="split_pdfs"), test_run:bool=False) -> None:
    extracted_docs = []
    today = datetime.now().strftime("%Y-%m-%d")
    for file in os.listdir(extracted_docs_folder):
        if file.endswith(".pdf"):
            file_path = os.path.join(extracted_docs_folder, file)
            stu_id = re.search(r"_(\d+)_", file).group(1) if "_" in file else "unknown"
            iep_date = re.search(r"_(\d{4}-\d{2}-\d{2})", file) 
            if iep_date:
                iep_date = iep_date.group(1)
            else:
                iep_date = datetime.now().strftime("%Y-%m-%d")
            
            extracted_docs.append({
                "file": file_path,
                "stu_id": stu_id,
                "iep_date": iep_date
            })
    category_code = config("IEP_AT_A_GLANCE_DOCUMENT_CODE", default="11", cast=str)
    
    for doc in extracted_docs:
        core.log(f"Uploading {doc['file']} to AERIES...")
        with open(doc['file'], "rb") as file:
            pdf_data = file.read()
        next_sq = get_next_sq(doc['stu_id'], 'DOC', cnxn)
        stu_gr = get_student_grade(cnxn, doc['stu_id'])
        file_name = os.path.basename(doc['file'])[-4:]
        
        if stu_gr == "" or stu_gr is None:
            core.log(f"Student {doc['stu_id']} not found in the database.")
            continue
        delete_old_iep_docs(cnxn, doc['stu_id'])
        sql = text('''INSERT INTO DOC (
            ID
            , SQ
            , DT
            , GR
            , CT
            , NM
            , XT
            , RB
            , SZ
            , LK
            , SRC
            , SCT
            , TY
            , UN
            , IDT
            ) VALUES (
            :id
            , :sq
            , :dt
            , :gr
            , :ct
            , :nm
            , :xt
            , :rb
            , :sz
            , :lk
            , :src
            , :sct
            , :ty
            , :un
            , :idt
            )''')
            
        params = {
            'id': str(doc['stu_id']),
            'sq': int(next_sq),
            'dt': str(doc['iep_date']),
            'gr': int(stu_gr) if isinstance(stu_gr, (int, float)) else str(stu_gr),
            'ct': str(category_code),
            'nm': f'IEP At A Glance {datetime.strptime(doc["iep_date"], "%Y-%m-%d").strftime("%m/%d/%Y")} #{str(doc["stu_id"])}',
            'xt': os.path.basename(doc['file'])[-3:],
            'rb': pdf_data,
            'sz': int(len(pdf_data)),
            'lk': 1,
            'src': '',
            'sct': '',
            'ty': 'CSE',
            'un': 'Automation',
            'idt': today
        }
        with cnxn.connect() as conn:
            conn.execute(sql, params)
            conn.commit()
    core.log("Upload complete.")

def upload_iep_docs_to_aeries_from_list(cnxn, extracted_docs: List[dict], test_run: bool = False) -> None:
    """
    Upload IEP documents to Aeries from a list of extracted document info.
    
    Args:
        cnxn: Database connection
        extracted_docs: List of document information dictionaries
        test_run: Whether this is a test run
    """
    category_code = config("IEP_AT_A_GLANCE_DOCUMENT_CODE", default="11", cast=str)
    today = datetime.now().strftime("%Y-%m-%d")
    
    for doc in extracted_docs:
        core.log(f"Uploading {doc['file']} to AERIES...")
        with open(doc['file'], "rb") as file:
            pdf_data = file.read()
        
        # Use the helper functions from this module
        next_sq = get_next_sq(int(doc['stu_id']), 'DOC', cnxn)
        stu_gr = get_student_grade(cnxn, int(doc['stu_id']))
        
        if stu_gr == "" or stu_gr is None:
            core.log(f"Student {doc['stu_id']} not found in the database.")
            continue
            
        # Delete old IEP docs
        delete_old_iep_docs(cnxn, int(doc['stu_id']))
        
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
            'nm': f'IEP At A Glance {datetime.strptime(doc["iep_date"], "%Y-%m-%d").strftime("%m/%d/%Y")} #{str(doc["stu_id"])}',
            'xt': 'pdf',
            'rb': pdf_data,
            'sz': int(len(pdf_data)),
            'lk': 1,
            'src': '',
            'sct': '',
            'ty': 'CSE',
            'un': 'Automation',
            'idt': today
        }
        
        if not test_run:
            with cnxn.connect() as conn:
                conn.execute(sql, params)
                conn.commit()
    
    core.log("Upload complete.")

def remove_all_files(directory):
    """Removes all files and subdirectories within a directory.

    Args:
        directory: The path to the directory.
    """
    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            print(f"Failed to delete {file_path}. Reason: {e}")

def main(cnxn):
    input_folder = config("INPUT_DIRECTORY_PATH", default="input_pdfs", cast=str)
    input_pdf = core.find_file_in_dir(input_folder, extension=".pdf")
    
    if not os.path.exists(input_pdf):
        core.log(f"Error: File '{input_pdf}' not found.")
        return
    
    core.log(f"Processing PDF: {input_pdf}")
    extracted_docs = split_iep_pdf(input_pdf)
    upload_iep_docs_to_aeries(cnxn, extracted_docs_folder=config("SPLIT_IEP_FOLDER", default="split_pdfs"), test_run=config("TEST_RUN", default=False, cast=bool))
    
    # core.log("Extracted IEP documents:")
    core.log("-" * 80)
    core.log(f"{'Student ID':<15} {'IEP Date':<15} {'Output File':<40} {'Pages':<10}")
    core.log("-" * 80)
    for doc in extracted_docs:
        
        core.log(f"{doc['stu_id']:<15} {doc['iep_date']:<15} {os.path.basename(doc['file']):<40} {doc['pages']:<10}")
    core.log("-" * 80)
    core.log(f"Total: {len(extracted_docs)} IEP documents")
    remove_all_files(config("SPLIT_IEP_FOLDER", default="split_pdfs"))

def test(cnxn):
    sq = get_next_sq(77118, 'DOC', cnxn)
    upload_iep_docs_to_aeries(cnxn, test_run=config("TEST_RUN", default=False, cast=bool))
    core.log(sq)
    
    pass

if __name__ == "__main__":
    test_run = config("TEST_RUN", default=False, cast=bool)
    core.log("~" * 80)
    if test_run:
        core.log("Running in test mode. No changes will be made to the database.")
    cnxn = aeries.get_aeries_cnxn(access_level='w') if not test_run else aeries.get_aeries_cnxn(database=config("TEST_DATABASE", default='DST24000SLUSD_DAILY'), access_level='w')
    # test(cnxn=cnxn)
    main(cnxn=cnxn)
    core.log("~" * 80)