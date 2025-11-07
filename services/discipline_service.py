from sqlalchemy import text
from typing import Tuple
import pandas as pd
from slusdlib import aeries, core
from models.discipline import ADS_POST_Body, DSP_POST_Body, Discipline_POST_Body

class DisciplineService:
    def __init__(self, db_connection=None):
        self.cnxn = db_connection or aeries.get_aeries_cnxn()
        self.sql_obj = core.build_sql_object()
    
    def get_next_ads_iid(self) -> int:
        """Get the next IID for the ADS table"""
        sql = self.sql_obj.get_next_ADS_IID
        response = pd.read_sql(text(sql), self.cnxn)
        return response.to_dict('records')[0]["IID"] + 1
    
    def clean_params(self, params: dict) -> dict:
        """Convert numpy types to native Python types for SQLAlchemy compatibility"""
        cleaned_params = {}
        for key, value in params.items():
            if hasattr(value, 'item'):
                cleaned_params[key] = value.item()
            else:
                cleaned_params[key] = value
        return cleaned_params
    
    def create_ads_record(self, data: ADS_POST_Body) -> Tuple[str, str, str]:
        """
        Create a new ADS record
        Returns: (ID, SQ, IID)
        """
        cnxn = aeries.get_aeries_cnxn(access_level='w')
        sq = self._get_next_ads_sq(data.PID, cnxn)
        next_iid = self.get_next_ads_iid()
        
        # Use parameterized query instead of string formatting to prevent SQL injection
        sql = self.sql_obj.insert_into_ADS_table
        
        params = {
            'PID': data.PID,
            'GR': data.GR,
            'SCL': data.SCL,
            'SQ': sq,
            'CD': data.CD,
            'CO': data.CO,
            'DT': str(data.DT) if hasattr(data.DT, 'strftime') else data.DT,
            'LCN': data.LCN,
            'RF': data.RF,
            'SRF': data.SRF,
            'IID': str(next_iid)
        }
        cleaned_params = self.clean_params(params)
        with cnxn.connect() as conn:
            conn.execute(text(sql), cleaned_params)
            conn.commit()
        
        return str(data.PID), str(sq), str(next_iid)
    def create_dsp_record(self, data: DSP_POST_Body) -> int:
        """
        Create a new DSP record
        Returns: SQ1 (sequence number)
        """
        cnxn = aeries.get_aeries_cnxn(access_level='w')
        sq1 = self._get_next_dsp_sq(data.PID, data.SQ, cnxn)
        
        # Use parameterized query instead of string formatting
        sql = """
        INSERT INTO DSP (PID, SQ, SQ1, DS)
        VALUES (:PID, :SQ, :SQ1, :DS)
        """
        
        params = {
            'PID': data.PID,
            'SQ': data.SQ,
            'SQ1': sq1,
            'DS': data.DS
        }
        cleaned_params = self.clean_params(params)
        with cnxn.connect() as conn:
            conn.execute(text(sql), cleaned_params)
            conn.commit()
        
        return sq1
    
    def create_discipline_record(self, data: Discipline_POST_Body):
        """
        Create both ADS and DSP records (composite operation)
        This is a work-in-progress method
        """
        # Convert to ADS format
        ads_data = ADS_POST_Body(
            PID=data.PID,
            SCL=data.SCL,
            CD=data.CD,
            GR=data.GR,
            CO=data.CO
        )
        
        # Create ADS record
        pid, sq, iid = self.create_ads_record(ads_data)
        
        # Create DSP record
        dsp_data = DSP_POST_Body(
            PID=data.PID,
            SQ=int(sq),
            DS=data.DS
        )
        
        sq1 = self.create_dsp_record(dsp_data)
        
        return {
            "ADS": {"ID": pid, "SQ": sq, "IID": iid},
            "DSP": {"SQ1": sq1}
        }
    
    def _get_next_ads_sq(self, id: int, cnxn) -> int:
        """Find the next sequence number in the ADS table for a given student id"""
        sql = self.sql_obj.ADS_table_sequence.format(id=id)
        data = pd.read_sql(sql, cnxn)
        if data.empty: 
            return 1
        return data.sq.values[0] + 1
    
    def _get_next_dsp_sq(self, id: int, sq: int, cnxn) -> int:
        """Find the next sequence number in the DSP table for a given student id and sequence"""
        sql = self.sql_obj.DSP_table_sequence.format(id=id, sq=sq)
        data = pd.read_sql(sql, cnxn)
        if data.empty: 
            return 1 
        return data.sq1.values[0] + 1
