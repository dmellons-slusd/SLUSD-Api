from sqlalchemy import text
from typing import List, Dict, Tuple
from datetime import datetime
import pandas as pd
from slusdlib import aeries, core
from models.suia import SUIA_Body, SUIAUpdate, SUIADelete, SUIA_Table

class SUIAService:
    def __init__(self, db_connection=None):
        self.cnxn = db_connection or aeries.get_aeries_cnxn()
        self.sql_obj = core.build_sql_object()
    
    def get_all_records(self) -> List[Dict]:
        """Get all SUIA records"""
        sql = self.sql_obj.get_all_suia_records
        return pd.read_sql(sql, self.cnxn).to_dict(orient='records')
    
    def get_student_records(self, student_id: int) -> Tuple[List[Dict], bool]:
        """
        Get SUIA records for a specific student
        Returns: (records, is_empty)
        """
        sql = self.sql_obj.get_student_suia_records.format(id=student_id)
        data = pd.read_sql(sql, self.cnxn)
        
        if data.empty:
            return [], True
        
        # Format dates
        data['SD'] = data['SD'].dt.strftime('%Y-%m-%d')
        data['DTS'] = data['DTS'].dt.strftime('%Y-%m-%d %H:%M:%S')
        
        return data.to_dict('records'), False
    
    def create_record(self, data: SUIA_Body) -> SUIA_Table:
        """Create a new SUIA record"""
        cnxn = aeries.get_aeries_cnxn(access_level='w')
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        if 'T' not in data.SD: 
            data.SD = data.SD + 'T00:00:00'
        
        sq = self._get_next_sq(data.ID, cnxn)
        
        post_data = SUIA_Table(
            ID=data.ID,
            SQ=sq,
            ADSQ=data.ADSQ,
            INV=data.INV,
            SD=data.SD,
            DEL=0,
            DTS=now
        )
        
        sql = self.sql_obj.insert_into_SUIA_table.format(
            ID=post_data.ID,
            SQ=post_data.SQ,
            ADSQ=post_data.ADSQ,
            INV=post_data.INV,
            SD=post_data.SD,
            DEL=0,
            DTS=post_data.DTS
        )
        
        with cnxn.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        
        return post_data
    
    def update_record(self, body: SUIAUpdate) -> Tuple[bool, str, Dict]:
        """
        Update a SUIA record
        Returns: (success, message, old_row_data)
        """
        cnxn = aeries.get_aeries_cnxn(access_level='w')
        
        # Check if record exists
        sql_row = self.sql_obj.find_SUIA_row.format(id=body.ID, sq=body.SQ)
        old_row = pd.read_sql(sql_row, cnxn)
        
        if old_row.empty:
            return False, f"No SQ# {body.SQ} for ID# {body.ID}", {}
        
        # Format dates for response
        old_row['SD'] = old_row['SD'].dt.strftime('%Y-%m-%d')
        old_row['DTS'] = old_row['DTS'].dt.strftime('%Y-%m-%d %H:%M:%S')
        old_row_dict = old_row.to_dict('records')[0]
        
        # Create update statement
        updates = self._create_sql_update(body, ignore_keys=['ID', 'SQ', 'DEL', 'DTS'])
        update_sql = self.sql_obj.update_SUIA.format(
            updates=updates, 
            sq=body.SQ, 
            id=body.ID
        )
        
        with cnxn.connect() as conn:
            conn.execute(text(update_sql))
            conn.commit()
        
        return True, f'Updated row ID={body.ID} SQ={body.SQ} with values {updates}', old_row_dict
    
    def delete_record(self, body: SUIADelete) -> Tuple[bool, str]:
        """
        Delete a SUIA record
        Returns: (success, message)
        """
        cnxn = aeries.get_aeries_cnxn(access_level='w')
        
        # Check if record exists
        find_sql = self.sql_obj.find_SUIA_row.format(id=body.ID, sq=body.SQ)
        if pd.read_sql(find_sql, cnxn).empty:
            return False, f"No SUIA row found with ID#{body.ID} and SQ {body.SQ}"
        
        # Delete record
        delete_sql = self.sql_obj.delete_from_SUIA_table.format(id=body.ID, sq=body.SQ)
        with cnxn.connect() as conn:
            conn.execute(text(delete_sql))
            conn.commit()
        
        return True, f"Deleted row from SUIA for student ID#{body.ID} @ SQ {body.SQ}"
    
    def _get_next_sq(self, id: int, cnxn) -> int:
        """Find the next sequence number in the SUIA table for a given student id"""
        sql = self.sql_obj.SUIA_table_sequence.format(id=id)
        data = pd.read_sql(sql, cnxn)
        if data.empty: 
            return 1
        return data.sq.values[0] + 1
    
    def _create_sql_update(self, body: SUIAUpdate, ignore_keys: List[str] = ['ID', 'SQ', 'DEL', 'DTS']) -> str:
        """Create a SQL update statement from a dictionary of key-value pairs"""
        statements = []
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        for key, value in body:
            if key in ignore_keys or value is None: 
                continue
            statement = f"{key} = '{value}'"
            statements.append(statement)
        
        return f"SET {', '.join(statements)} , DTS ='{now}'"