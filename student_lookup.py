from typing import List, Dict, Optional, Tuple, Union
from dataclasses import dataclass
from datetime import datetime, date
from slusdlib import aeries
from sqlalchemy import text
from dateparser import parse

@dataclass
class StudentMatch:
    student_id: int
    first_name: str
    last_name: str
    birthdate: Optional[date]
    address: Optional[str]
    confidence: float
    match_reasons: List[str]
    tier: int

class StudentLookup:
    def __init__(self, db_connection):
        self.engine = db_connection  # This is now a SQLAlchemy engine
        
    def _execute_query(self, query: str, params: dict):
        """Execute query using SQLAlchemy engine"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(query), params)
                return result.fetchall()
        except Exception as e:
            print(f"Database query error: {e}")
            print(f"Query: {query}")
            print(f"Params: {params}")
            return []
    
    def _parse_date(self, date_input: Union[str, date, None]) -> Optional[date]:
        """Convert string dates to date objects"""
        if date_input is None:
            return None
        if isinstance(date_input, date):
            return date_input
        if isinstance(date_input, str):
            parsed_date = parse(date_input, settings={'RETURN_AS_TIMEZONE_AWARE': False})
            if parsed_date:
                print(f"Parsed date: {parsed_date}")
                return parsed_date.date()
            else:
                print(f"Invalid date format: {date_input}")
                return None
        return date_input  # fallback for other types
    
    def find_students(self, first_name: str, last_name: str, 
                     birthdate: Optional[Union[str, date]] = None, 
                     address: Optional[str] = None,
                     max_results: int = 10) -> List[StudentMatch]:
        """
        Progressive student lookup with confidence scoring
        """
        all_matches = []
        birthdate = self._parse_date(birthdate)
        
        
        
        # Tier 1: Exact match on all provided fields (highest confidence)
        if birthdate and address:
            matches = self._tier1_exact_all(first_name, last_name, birthdate, address)
            all_matches.extend(matches)
            
        # Tier 2: Exact name + birthdate
        if birthdate and len(all_matches) < max_results:
            matches = self._tier2_name_birthdate(first_name, last_name, birthdate)
            all_matches.extend(self._filter_duplicates(matches, all_matches))
            
        # Tier 3: Exact name + address
        if address and len(all_matches) < max_results:
            matches = self._tier3_name_address(first_name, last_name, address)
            all_matches.extend(self._filter_duplicates(matches, all_matches))
            
        # Tier 4: Exact name only
        if len(all_matches) < max_results:
            matches = self._tier4_exact_name(first_name, last_name)
            all_matches.extend(self._filter_duplicates(matches, all_matches))
            
        # Tier 5: Fuzzy name matching with available criteria
        if len(all_matches) < max_results:
            matches = self._tier5_fuzzy_matching(first_name, last_name, birthdate, address)
            all_matches.extend(self._filter_duplicates(matches, all_matches))
            
        # Sort by confidence and return top results
        all_matches.sort(key=lambda x: x.confidence, reverse=True)
        return all_matches[:max_results]
    
    def _tier1_exact_all(self, first_name: str, last_name: str, 
                        birthdate: date, address: str) -> List[StudentMatch]:
        """Tier 1: Exact match on name, birthdate, and address"""
        query = """
        SELECT ID, FN, LN, BD, AD
        FROM STU 
        WHERE LOWER(FN) = LOWER(:first_name) 
          AND LOWER(LN) = LOWER(:last_name)
          AND BD = :birthdate
          AND LOWER(AD) = LOWER(:address)
        """
        
        params = {
            'first_name': first_name,
            'last_name': last_name,
            'birthdate': birthdate,
            'address': address
        }
        
        results = self._execute_query(query, params)
        matches = []
        
        for row in results:
            matches.append(StudentMatch(
                student_id=row[0],
                first_name=row[1],
                last_name=row[2],
                birthdate=row[3],
                address=row[4],
                confidence=0.95,
                match_reasons=["Exact name match", "Exact birthdate match", "Exact address match"],
                tier=1
            ))
        
        return matches
    
    def _tier2_name_birthdate(self, first_name: str, last_name: str, 
                             birthdate: date) -> List[StudentMatch]:
        """Tier 2: Exact name + birthdate match"""
        query = """
        SELECT ID, FN, LN, BD, AD
        FROM STU 
        WHERE LOWER(FN) = LOWER(:first_name) 
          AND LOWER(LN) = LOWER(:last_name)
          AND BD = :birthdate
        """
        
        params = {
            'first_name': first_name,
            'last_name': last_name,
            'birthdate': birthdate
        }
        
        results = self._execute_query(query, params)
        matches = []
        
        for row in results:
            matches.append(StudentMatch(
                student_id=row[0],
                first_name=row[1],
                last_name=row[2],
                birthdate=row[3],
                address=row[4],
                confidence=0.85,
                match_reasons=["Exact name match", "Exact birthdate match"],
                tier=2
            ))
        
        return matches
    
    def _tier3_name_address(self, first_name: str, last_name: str, 
                           address: str) -> List[StudentMatch]:
        """Tier 3: Exact name + address match"""
        query = """
        SELECT ID, FN, LN, BD, AD
        FROM STU 
        WHERE LOWER(FN) = LOWER(:first_name) 
          AND LOWER(LN) = LOWER(:last_name)
          AND LOWER(AD) = LOWER(:address)
        """
        
        params = {
            'first_name': first_name,
            'last_name': last_name,
            'address': address
        }
        
        results = self._execute_query(query, params)
        matches = []
        
        for row in results:
            matches.append(StudentMatch(
                student_id=row[0],
                first_name=row[1],
                last_name=row[2],
                birthdate=row[3],
                address=row[4],
                confidence=0.80,
                match_reasons=["Exact name match", "Exact address match"],
                tier=3
            ))
        
        return matches
    
    def _tier4_exact_name(self, first_name: str, last_name: str) -> List[StudentMatch]:
        """Tier 4: Exact name match only"""
        query = """
        SELECT ID, FN, LN, BD, AD
        FROM STU 
        WHERE LOWER(FN) = LOWER(:first_name) 
          AND LOWER(LN) = LOWER(:last_name)
        """
        
        params = {
            'first_name': first_name,
            'last_name': last_name
        }
        
        results = self._execute_query(query, params)
        matches = []
        
        for row in results:
            matches.append(StudentMatch(
                student_id=row[0],
                first_name=row[1],
                last_name=row[2],
                birthdate=row[3],
                address=row[4],
                confidence=0.70,
                match_reasons=["Exact name match"],
                tier=4
            ))
        
        return matches
    
    def _tier5_fuzzy_matching(self, first_name: str, last_name: str,
                             birthdate: Optional[date] = None,
                             address: Optional[str] = None) -> List[StudentMatch]:
        """Tier 5: Fuzzy matching with phonetic and partial matches"""
        matches = []
        
        # Phonetic matching (SOUNDEX-like)
        phonetic_matches = self._phonetic_name_search(first_name, last_name, birthdate, address)
        matches.extend(phonetic_matches)
        
        # Partial string matching
        partial_matches = self._partial_name_search(first_name, last_name, birthdate, address)
        matches.extend(partial_matches)
        
        return matches
    
    def _phonetic_name_search(self, first_name: str, last_name: str,
                             birthdate: Optional[date] = None,
                             address: Optional[str] = None) -> List[StudentMatch]:
        """Phonetic name matching using SOUNDEX"""
        base_query = """
        SELECT ID, FN, LN, BD, AD
        FROM STU 
        WHERE (SOUNDEX(FN) = SOUNDEX(:first_name) AND SOUNDEX(LN) = SOUNDEX(:last_name))
        """
        
        params = {
            'first_name': first_name,
            'last_name': last_name
        }
        confidence = 0.65
        reasons = ["Phonetic name match"]
        
        # Add optional criteria
        if birthdate:
            base_query += " AND BD = :birthdate"
            params['birthdate'] = birthdate
            confidence += 0.10
            reasons.append("Exact birthdate match")
            
        if address:
            base_query += " AND LOWER(AD) = LOWER(:address)"
            params['address'] = address
            confidence += 0.08
            reasons.append("Exact address match")
        
        results = self._execute_query(base_query, params)
        matches = []
        
        for row in results:
            matches.append(StudentMatch(
                student_id=row[0],
                first_name=row[1],
                last_name=row[2],
                birthdate=row[3],
                address=row[4],
                confidence=min(confidence, 0.85),  # Cap at 0.85 for fuzzy matches
                match_reasons=reasons.copy(),
                tier=5
            ))
        
        return matches
    
    def _partial_name_search(self, first_name: str, last_name: str,
                       birthdate: Optional[date] = None,
                       address: Optional[str] = None) -> List[StudentMatch]:
        """Partial string matching with wildcards"""
        base_query = """
        SELECT ID, FN, LN, BD, AD
        FROM STU 
        WHERE (FN LIKE :first_pattern AND LN LIKE :last_pattern)
        OR (FN LIKE :first_pattern2 AND LOWER(LN) = LOWER(:last_name))
        OR (LOWER(FN) = LOWER(:first_name) AND LN LIKE :last_pattern2)
        """
        
        first_pattern = f"%{first_name}%"
        last_pattern = f"%{last_name}%"
        
        params = {
            'first_pattern': first_pattern,
            'last_pattern': last_pattern,
            'first_pattern2': first_pattern,
            'last_name': last_name,
            'first_name': first_name,
            'last_pattern2': last_pattern
        }
        
        base_confidence = 0.50
        base_reasons = ["Partial name match"]
        
        # Add optional criteria for higher confidence
        if birthdate:
            base_query += " AND BD = :birthdate"
            params['birthdate'] = birthdate
            base_confidence += 0.15
            # Don't add "Exact birthdate match" here - check it per result
            
        if address:
            base_query += " AND LOWER(AD) LIKE LOWER(:address_pattern)"
            params['address_pattern'] = f"%{address}%"
            base_confidence += 0.10
            # Don't add "Partial address match" here - check it per result
        
        results = self._execute_query(base_query, params)
        matches = []
        
        for row in results:
            # Build match reasons based on actual matches
            reasons = base_reasons.copy()
            actual_confidence = base_confidence
            
            # Check if birthdate actually matches
            if birthdate and row[3] and row[3].date() == birthdate:
                reasons.append("Exact birthdate match")
            
            # Check if address actually matches (partial)
            if address and row[4] and address.lower() in row[4].lower():
                reasons.append("Partial address match")
            
            # Calculate dynamic confidence based on name similarity
            name_similarity = self._calculate_name_similarity(
                first_name, last_name, row[1], row[2]
            )
            
            final_confidence = min(actual_confidence + (name_similarity * 0.15), 0.75)
            
            matches.append(StudentMatch(
                student_id=row[0],
                first_name=row[1],
                last_name=row[2],
                birthdate=row[3],
                address=row[4],
                confidence=final_confidence,
                match_reasons=reasons,
                tier=5
            ))
        
        return matches
    
    def _calculate_name_similarity(self, search_first: str, search_last: str,
                                  found_first: str, found_last: str) -> float:
        """Calculate similarity score between 0 and 1"""
        first_ratio = self._string_similarity(search_first.lower(), found_first.lower())
        last_ratio = self._string_similarity(search_last.lower(), found_last.lower())
        return (first_ratio + last_ratio) / 2
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """Simple string similarity using character overlap"""
        if not s1 or not s2:
            return 0.0
        
        # Simple implementation - in production, consider using libraries like difflib
        longer = s1 if len(s1) > len(s2) else s2
        shorter = s2 if len(s1) > len(s2) else s1
        
        if len(longer) == 0:
            return 1.0
        
        matches = sum(1 for c in shorter if c in longer)
        return matches / len(longer)
    
    def get_student_details(self, student_id: int) -> Optional[Dict]:
        """Get detailed information for a specific student"""
        query = """
        SELECT ID, FN, LN, BD, AD, GR, SC
        FROM STU 
        WHERE ID = :student_id
        """
        
        params = {'student_id': student_id}
        results = self._execute_query(query, params)
        
        if results:
            row = results[0]
            return {
                'student_id': row[0],
                'first_name': row[1],
                'last_name': row[2],
                'birthdate': row[3],
                'address': row[4],
                'grade': row[5] if len(row) > 5 else None,
                'school': row[6] if len(row) > 6 else None,
            }
        return None

    def _filter_duplicates(self, new_matches: List[StudentMatch], 
                          existing_matches: List[StudentMatch]) -> List[StudentMatch]:
        """Remove duplicates based on student_id"""
        existing_ids = {match.student_id for match in existing_matches}
        return [match for match in new_matches if match.student_id not in existing_ids]

# Example usage
def example_usage():
    # Get SQLAlchemy engine from aeries
    engine = aeries.get_aeries_cnxn(database="DST24000SLUSD")
    
    # Create the lookup instance
    lookup = StudentLookup(engine)
    
    # Example searches
    print("Searching for: Zaid Abushi")
    print("=" * 50)
    
    results = lookup.find_students(
        first_name="Za",
        last_name="Abushi",
        max_results=1,
        birthdate='5/15/2000',  # date(2000, 5, 15),
        address="123 Main St"
    )
    
    if results:
        print(f"Found {len(results)} potential matches:\n")
        
        # Display results
        for i, match in enumerate(results, 1):
            print(f"{i}. Tier {match.tier} - Confidence: {match.confidence:.2f}")
            print(f"   Student ID: {match.student_id}")
            print(f"   Name: {match.first_name} {match.last_name}")
            if match.birthdate:
                print(f"   Birthdate: {match.birthdate}")
            if match.address:
                print(f"   Address: {match.address}")
            print(f"   Match Reasons: {', '.join(match.match_reasons)}")
            print()
    else:
        print("No matches found.")
    
    # Example with additional criteria
    print("\n" + "=" * 50)
    print("Searching with birthdate example:")
    # Uncomment and modify as needed
    # results2 = lookup.find_students(
    #     first_name="John",
    #     last_name="Smith",
    #     birthdate=date(2005, 3, 15)
    # )
    # print(f"Found {len(results2)} matches with birthdate criteria")

if __name__ == "__main__":
    example_usage()