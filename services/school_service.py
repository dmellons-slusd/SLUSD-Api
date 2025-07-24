from typing import List, Dict, Optional
import pandas as pd
from slusdlib import aeries, core

class SchoolService:
    def __init__(self, db_connection=None):
        self.cnxn = db_connection or aeries.get_aeries_cnxn()
        self.sql_obj = core.build_sql_object()
    
    def get_all_schools(self) -> List[Dict]:
        """Get a list of all schools"""
        sql = self.sql_obj.locations
        data = pd.read_sql(sql, self.cnxn)
        return data.to_dict(orient="records")
    
    def get_school_by_code(self, school_code: int) -> Optional[Dict]:
        """Get a single school's information by school code"""
        sql = self.sql_obj.locations + f' WHERE cd = {school_code}'
        data = pd.read_sql(sql, self.cnxn)
        
        if data.empty:
            return None
        
        return data.to_dict(orient="records")[0]