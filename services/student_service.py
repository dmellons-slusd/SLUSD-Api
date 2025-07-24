from typing import List, Dict, Optional
import pandas as pd
from sqlalchemy import text
from slusdlib import aeries, core
from utils.student_lookup import StudentLookup, StudentMatch
from models.student import StudentSearchRequest, StudentMatchResponse, StudentLookupResponse

class StudentService:
    def __init__(self, db_connection=None):
        self.engine = db_connection or aeries.get_aeries_cnxn()
        self.sql_obj = core.build_sql_object()
        self.lookup = StudentLookup(self.engine)
    
    def get_student_by_id(self, student_id: int) -> Dict:
        """Get a single student's information"""
        sql = self.sql_obj.student_test.format(id=student_id)
        data = pd.read_sql(sql, self.engine)   
        return data.to_dict("records")[0] if not data.empty else {}
    
    def search_students(self, search_request: StudentSearchRequest) -> StudentLookupResponse:
        """
        Search for students using progressive matching with confidence scoring
        """
        try:
            # Perform the search using StudentLookup
            matches = self.lookup.find_students(
                first_name=search_request.first_name,
                last_name=search_request.last_name,
                birthdate=search_request.birthdate,
                address=search_request.address,
                max_results=search_request.max_results
            )
            
            # Convert matches to response format
            match_responses = []
            for match in matches:
                match_responses.append(StudentMatchResponse(
                    student_id=match.student_id,
                    first_name=match.first_name,
                    last_name=match.last_name,
                    birthdate=match.birthdate.strftime('%Y-%m-%d') if match.birthdate else None,
                    address=match.address,
                    confidence=match.confidence,
                    match_reasons=match.match_reasons,
                    tier=match.tier
                ))
            
            # Build response
            if matches:
                return StudentLookupResponse(
                    status="SUCCESS",
                    message=f"Found {len(matches)} potential matches for {search_request.first_name} {search_request.last_name}",
                    total_matches=len(matches),
                    matches=match_responses
                )
            else:
                return StudentLookupResponse(
                    status="SUCCESS", 
                    message=f"No matches found for {search_request.first_name} {search_request.last_name}",
                    total_matches=0,
                    matches=[]
                )
        except Exception as e:
            return StudentLookupResponse(
                status="ERROR",
                message=f"Error during student lookup: {str(e)}",
                total_matches=0,
                matches=[]
            )
    
    def get_student_details(self, student_id: int) -> Optional[Dict]:
        """Get detailed information for a specific student by ID"""
        try:
            student_details = self.lookup.get_student_details(student_id)
            
            if student_details and student_details.get('birthdate'):
                student_details['birthdate'] = student_details['birthdate'].strftime('%Y-%m-%d')
            
            return student_details
        except Exception as e:
            raise Exception(f"Error retrieving student details: {str(e)}")