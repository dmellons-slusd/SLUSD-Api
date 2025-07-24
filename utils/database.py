from sqlalchemy import text
from typing import List
from datetime import datetime
import pandas as pd

def create_sql_update(body: dict, ignore_keys: List[str] = ['ID', 'SQ', 'DEL', 'DTS']) -> str:
    """
    Create a SQL update statement from a dictionary of key-value pairs.

    Parameters
    ----------
    body : dict
        A dictionary of key-value pairs to update in the SQL table
    ignore_keys : List[str], optional
        A list of keys to ignore in the update statement

    Returns
    -------
    str
        The SQL update statement
    """
    statements = []
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    for key, value in body.items():
        if key in ignore_keys or value is None:
            continue
        statement = f"{key} = '{value}'"
        statements.append(statement)
    
    return f"SET {', '.join(statements)} , DTS ='{now}'"

def execute_query(connection, query: str, params: dict = None):
    """
    Execute a SQL query with optional parameters
    
    Parameters
    ----------
    connection : sqlalchemy.engine.Connection
        Database connection
    query : str
        SQL query to execute
    params : dict, optional
        Query parameters
        
    Returns
    -------
    pandas.DataFrame
        Query results as DataFrame
    """
    if params:
        return pd.read_sql(text(query), connection, params=params)
    else:
        return pd.read_sql(query, connection)

def execute_non_query(connection, query: str, params: dict = None):
    """
    Execute a non-query SQL statement (INSERT, UPDATE, DELETE)
    
    Parameters
    ----------
    connection : sqlalchemy.engine.Connection
        Database connection
    query : str
        SQL statement to execute
    params : dict, optional
        Query parameters
    """
    with connection.connect() as conn:
        if params:
            conn.execute(text(query), params)
        else:
            conn.execute(text(query))