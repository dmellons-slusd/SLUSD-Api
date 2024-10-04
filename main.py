import json
from db_users import db
from decouple import config
import requests
from typing import List, Literal, Optional, Union
from fastapi import Depends, FastAPI, HTTPException, status, Request, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware
from slusd_api_types import Student, StudentTest , School
from sqlalchemy import text
from json import loads
from slusdlib import aeries, core
import pandas as pd

SECRET_KEY = config("SECRET_KEY")
ALGORITHM = config("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(config("ACCESS_TOKEN_EXPIRE_MINUTES"))

##
# Response Classes
##
# Moved to slusd_api_types.py

##
# Request Classes
##
class ADS_RESPONSE(BaseModel):
    status: str
    message: str
    ID: str
    SQ: str
    IID: str

class SUIA_Body(BaseModel):
    ID: int
    SD: str
    ADSQ: int
    INV: Literal['ACAD','RESO','TUPE']
    
class SUIAUpdade(BaseModel):
    ID: int
    SQ: int
    SD: Union[str,None] = None
    ADSQ: Union[int,None] = None
    INV: Union[Literal['ACAD','RESO','TUPE'],None] = None

class SUIADelete(BaseModel):
    ID: int
    SQ: int

class SUIA_Table(BaseModel):
    ID: int
    SD: str
    ADSQ: int
    SQ: int
    INV: Literal['ACAD','RESO','TUPE']
    DEL: bool
    DTS: datetime = datetime.now()
class ADS_POST_Body(BaseModel):
    PID: int = Field(..., description='Student ID')
    SCL: int = Field(..., description='School ID') # School ID
    CD: str = Field(..., description='Disposition Code') # Code
    GR: int = Field(..., description='Grade') # Grade
    CO: str = Field(default='', description='Comments')
    DT: str = Field(default=datetime.now(), description='Date of Disposition')
    LCN: int = Field(default=99, description='Location Code')
    SRF: int = Field(default=0, description='Staff Referrer ID')
    RF: str = Field(default='', description='Referrer Name')
class Discipline_POST_Body(BaseModel):
    PID: int = Field(..., description='Student ID')
    SCL: int = Field(..., description='School ID') # School ID
    CD: str = Field(..., description='Disposition Code') # Code
    GR: int = Field(..., description='Grade') # Grade
    DS: Optional[str] = Field(default='',  description='Disposition Code') # Disposition
    CO: Optional[str] = Field(default='', description='Comments')

class DSP_POST_Body(BaseModel):
    PID: int = Field(..., description='Student ID')
    SQ: int = Field(..., description='ADS Sequence') # Sequence
    DS: Optional[str] = Field(default='',  description='Disposition Code') # Disposition
    # SQ1: int = Field( default=1, description='Disposition Sequence (restarts every ADS entry)') # Sequence

##
# Internal auth classes
##
class Token(BaseModel):
    token: str
    token_type: str

class TokenData(BaseModel):
    username: str or None = None

class UserCredentials(BaseModel):
    username: str
    password: str

class User(BaseModel):
    username: str
    email: str or None = None
    full_name: str or None = None
    disabled: bool or None = None

class UserInDB(User):
    hashed_password: str

class BaseResponse(BaseModel):
    status: str
    message: str
##
# Server Context
##
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth_2_scheme = OAuth2PasswordBearer(tokenUrl="token")
sql_obj = core.build_sql_object()

app = FastAPI(
    title="SLUSD API",
    description="SLUSD Api Documentation"
)

origins = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://localhost:8000",
    "http://*.slusd.us",
    "https://*.slusd.us",
    "http://10.15.1.*" 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

##
# Helper functoins
##

def create_sql_update(body:dict, ignore_keys:List[str]=['ID', 'SQ', 'DEL', 'DTS']) -> str:
    """
    Create a SQL update statement from a dictionary of key-value pairs.

    Parameters
    ----------
    body : dict
        A dictionary of key-value pairs to update in the SQL table
    ignore_keys : List[str], optional
        A list of keys to ignore in the update statement, by default ['ID', 'SQ', 'DEL', 'DTS']

    Returns
    -------
    str
        The SQL update statement
    """
    statements = []
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    for key, value in body:
        if key in ignore_keys or value is None : continue
        statement = f"{key} = '{value}'"
        statements.append(statement)
    return f"SET {', '.join(statements)} , DTS ='{now}'"


def get_next_SQIA_sq(id:int, cnxn) -> int:
    """
    Find the next sequence number in the SUIA table for a given student id.

    Queries the SUIA table to find the highest sequence number for a given student id.
    If no records are found, returns 1.

    Parameters
    ----------
    id : int
        The student id to query
    cnxn : sqlalchemy.engine.Connection
        The db connection to use

    Returns
    -------
    int
        The next sequence number
    """
    sql = sql_obj.SUIA_table_sequence.format(id=id)
    data = pd.read_sql(sql, cnxn)
    if data.empty: return 1
    return data.sq.values[0]+1

def get_next_ADS_sq(id:int, cnxn) -> int:
    """
    Find the next sequence number in the ADS table for a given student id.

    Parameters
    ----------
    id : int
        The student id to find the next sequence for
    cnxn : sqlalchemy.engine.Connection
        The database connection object

    Returns
    -------
    int
        The next sequence number to use for an ADS insert
    """
    sql = sql_obj.ADS_table_sequence.format(id=id)
    data = pd.read_sql(sql, cnxn)
    if data.empty: return 1
    return data.sq.values[0]+1

def get_next_DSP_sq(id:int, sq:int, cnxn) -> int:
    """
    Find the next sequence number in the DSP table for a given student id and sequence.

    Queries the DSP table to find the highest sequence number for a given student id and sequence.
    If no records are found, returns 1.

    Parameters
    ----------
    id : int
        The student id to query
    sq : int
        The sequence to query
    cnxn : sqlalchemy.engine.Connection
        The db connection to use

    Returns
    -------
    int
        The next sequence number to use for a DSP insert
    """
    sql = sql_obj.DSP_table_sequence.format(id=id, sq=sq)
    data = pd.read_sql(sql, cnxn)

    if data.empty: return 1 
    return data.sq1.values[0]+1 

def verify_password(plain_password, hashed_password):
    """
    Verify a plaintext password against a hashed password

    Parameters
    ----------
    plain_password : str
        The plaintext password to verify
    hashed_password : str
        The hashed password to compare against

    Returns
    -------
    bool
        True if the password is valid, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """
    Return a hashed version of the given plaintext password

    Parameters
    ----------
    password : str
        The plaintext password to hash

    Returns
    -------
    str
        The hashed password
    """
    return pwd_context.hash(password)

def get_user(db, username: str):
    """
    Find a user in the given database by username

    Parameters
    ----------
    db : dict
        The database to search in
    username : str
        The username to search for

    Returns
    -------
    UserInDB or None
        The user if found, None otherwise
    """
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    
def authenticate_user(db, username: str, password: str):
    
    """
    Authenticate a user against the given database

    Parameters
    ----------
    db : dict
        The database to search in
    username : str
        The username to search for
    password : str
        The password to verify against

    Returns
    -------
    UserInDB or False
        The user if authenticated, False otherwise
    """
    user = get_user(db, username)
    if not user: return False
    if not verify_password(password, user.hashed_password): return False
    return user

def create_access_token(data: dict, expires_delta: timedelta or None = None):
    """
    Create a JWT token from the given data with an optional expiration time.

    Parameters
    ----------
    data : dict
        The data to encode in the JWT token
    expires_delta : timedelta or None, optional
        The time until the token expires, by default None (set to 15 minutes)

    Returns
    -------
    str
        The encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta: 
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_auth(token: str = Depends(oauth_2_scheme)):
    """
    Validate a JWT token and return the associated user

    Parameters
    ----------
    token : str
        The JWT token to validate

    Returns
    -------
    UserInDB
        The associated user if the token is valid, raises an HTTPException otherwise
    """
    credential_exception = HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Could not validate credentials", headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")

        if username is None:
            raise credential_exception
        token_data = TokenData(username=username)
    except JWTError:
        raise credential_exception
    user = get_user(db, username=token_data.username)

    if user is None:
        raise credential_exception
    return user

async def get_current_active_user(current_user: User = Depends(get_auth)):
    if current_user.disabled:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


##
# API Endpoints / Routes
##

@app.post("/token/", response_model=Token, tags=["Auth"])
async def login_for_access_token(form_data:UserCredentials):
    """
    Return an access token for the given username and password

    Parameters
    ----------
    form_data : UserCredentials
        The username and password to authenticate

    Returns
    -------
    Token
        The access token and its type

    Raises
    ------
    HTTPException
        If the username or password are invalid
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
            )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"token": access_token, "token_type": "bearer"}

@app.get("/aeries/SUIA/",  tags=["SUIA Endpoints", "Aeries"])
async def get_all_suia_records(auth = Depends(get_auth)):
    """
    Returns a list of all SUIA records in Aeries

    Returns
    -------
    JSONResponse
        A JSON response containing the list of all SUIA records in Aeries
    """
    cnxn = aeries.get_aeries_cnxn()
    sql = sql_obj.get_all_suia_records
    ret = pd.read_sql(sql, cnxn).to_dict(orient='records')
    return JSONResponse(content=ret, status_code=200)

@app.get("/aeries/SUIA/{id}/",  tags=["SUIA Endpoints", "Aeries"])
async def get_single_student_suia_records(id:int, auth = Depends(get_auth)):
    """
    Returns a list of all SUIA records for a given student ID

    Parameters
    ----------
    id : int
        The student ID

    Returns
    -------
    JSONResponse
        A JSON response containing the list of all SUIA records for the given student ID
    """
    cnxn = aeries.get_aeries_cnxn()
    sql = sql_obj.get_student_suia_records.format(id=id)
    try:
        ret = pd.read_sql(sql, cnxn)
        if ret.empty : 
            content = {
            "status":"SUCCESS",
            "message":f"No rows found for ID# {id}"
            }
            return JSONResponse(content=content, status_code=200)
        ret['SD'] = ret['SD'].dt.strftime('%Y-%m-%d')
        ret['DTS'] = ret['DTS'].dt.strftime('%Y-%m-%d %H:%M:%S')

    except Exception as e:
        content = {
            "status":"Error",
            "message":f"Error:{e}"
            }
        return JSONResponse(content=content, status_code=500)

    return JSONResponse(content=ret.to_dict('records'), status_code=200)

@app.post("/aeries/SUIA/", response_model=BaseResponse, tags=["SUIA Endpoints", "Aeries"])
async def insert_SUIA_row(data:SUIA_Body, auth = Depends(get_auth)):
    """
    Inserts a new row into the SUIA table

    Parameters
    ----------
    data : SUIA_Body
        The data to be inserted into the SUIA table

    Returns
    -------
    JSONResponse
        A JSON response containing the status and message of the operation
    """
    cnxn = aeries.get_aeries_cnxn(access_level='w')
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if 'T' not in data.SD: data.SD = data.SD+'T00:00:00'
    sq = get_next_SQIA_sq(data.ID, cnxn)
    post_data:SUIA_Table = SUIA_Table(
        ID=data.ID,
        SQ=sq,
        ADSQ=data.ADSQ,
        INV=data.INV,
        SD=data.SD,
        DEL=0,
        DTS=now
    )
    sql = sql_obj.insert_into_SUIA_table.format(
        ID=post_data.ID,
        SQ=post_data.SQ,
        ADSQ=post_data.ADSQ,
        INV=post_data.INV,
        SD=post_data.SD,
        DEL=0,
        DTS=post_data.DTS
    )
    try: 
        with cnxn.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        content = {
            "status":"SUCCESS",
            "message": f"Inserted new row into SUIA for student ID#{data.ID} @ SQ {post_data.SQ}"
        }
        return JSONResponse(content=content, status_code=200)
     
    except Exception as e:
        print(e)
        content = {
            "error": f"{e}"
        }
        return JSONResponse(content=content, status_code=500)
    
@app.put("/aeries/SUIA/", response_model=BaseResponse, tags=["SUIA Endpoints", "Aeries"])
async def update_SUIA_row(body:SUIAUpdade, auth=Depends(get_auth)):
    """
    Updates a row in the SUIA table

    Parameters
    ----------
    body : SUIAUpdade
        The data to be updated in the SUIA table

    Returns
    -------
    JSONResponse
        A JSON response containing the status and message of the operation
    """
    try:
        cnxn = aeries.get_aeries_cnxn(access_level='w')
        sql_row = sql_obj.find_SUIA_row.format(id=body.ID, sq=body.SQ)
        old_row = pd.read_sql(sql_row, cnxn)
        if old_row.empty:
            content={
                "status": "FAIL",
                "message": f"No SQ# {body.SQ} for ID# {body.ID}"
            }
            return JSONResponse(content, status_code=200)
        old_row['SD'] = old_row['SD'].dt.strftime('%Y-%m-%d')
        old_row['DTS'] = old_row['DTS'].dt.strftime('%Y-%m-%d %H:%M:%S')
        old_row = old_row.to_dict('records')[0]
        new_row = old_row
        for key, value in body:
            if value: new_row[key] = value
        updates = create_sql_update(body, ignore_keys=['ID', 'SQ', 'DEL', 'DTS'])
        sq = body.SQ
        id = body.ID
        update_sql = sql_obj.update_SUIA.format(updates=updates, sq=sq, id=id)
        # print('sql', update_sql)
        with cnxn.connect() as conn:
            conn.execute(text(update_sql))
            conn.commit()


        content = {
            'status':'SUCCESS',
            'message': f'Updated row ID={id} SQ={sq} with values {updates}'
        }
        return JSONResponse(content=content, status_code=200)
    except Exception as e:
        content = {
            'status': 'FAIL',
            'message': f'ERROR: {e}'
        }
        return JSONResponse(content=content, status_code=500)

@app.delete("/aeries/SUIA/", response_model=BaseResponse, tags=["SUIA Endpoints", "Aeries"])
async def delete_SUIA_row(body:SUIADelete, auth = Depends(get_auth)):
    """
    Deletes a single row from the SUIA table in Aeries

    Parameters
    ----------
    body : SUIADelete
        The ID and SQ of the row to be deleted

    Returns
    -------
    JSONResponse
        A JSON response with the status and message of the operation
    """
    cnxn = aeries.get_aeries_cnxn(access_level='w')
    delete_sql = sql_obj.delete_from_SUIA_table.format(id=body.ID, sq=body.SQ)
    find_sql = sql_obj.find_SUIA_row.format(id=body.ID, sq=body.SQ)
    try:
        if pd.read_sql(find_sql, cnxn).empty:
            content = {
                "status":"Row Not Found",
                "message": f"No SUIA row found with ID#{body.ID} and SQ {body.SQ}"
            }
            return JSONResponse(content=content, status_code=404)
        with cnxn.connect() as conn:
            conn.execute(text(delete_sql))
            conn.commit()
        content = {
            "status":"SUCCESS",
            "message": f"Deleted row from SUIA for student ID#{body.ID} @ SQ {body.SQ}"
        }
        return JSONResponse(content=content, status_code=200)
    except Exception as e:
        print(e)
        content = {
            "error": f"{e}"
        }
        return JSONResponse(content=content, status_code=500)


@app.get('/aeries/ADS_next_IID/', tags=["Discipline Endpoints", "Aeries"])
async def get_next_ADS_IID():
    """
    CURRENTLY WRITING TO DST24000SLUSD_DAILY
    ----------------------------------------
    Returns the next IID for the ADS table in Aeries Between 500000 AND 968159
    """
    try:
        cnxn = aeries.get_aeries_cnxn(database='DST24000SLUSD_DAILY')
        sql = sql_obj.get_next_ADS_IID
        # core.log(sql)
        response = pd.read_sql(text(sql), cnxn)
        ret = response.to_dict('records')[0]["IID"] + 1
        return ret
    except Exception as e:
        print(e)
        return JSONResponse(content={"error": f"{e}"}, status_code=500)

def get_next_ADS_IID_internal(cnxn):
    sql = sql_obj.get_next_ADS_IID
    # core.log(sql)
    response = pd.read_sql(text(sql), cnxn)
    ret = response.to_dict('records')[0]["IID"] + 1
    return ret

@app.post('/aeries/DSP/', response_model=BaseResponse, tags=["Discipline Endpoints", "Aeries"])
async def insert_DSP_row(data:DSP_POST_Body, auth = Depends(get_auth)):
    """
    CURRENTLY WRITING TO DST24000SLUSD_DAILY
    ----------------------------------------
    Inserts a new row into the DSP table in Aeries

    Parameters
    ----------
    data : DSP_POST_Body
        The data to be inserted into the DSP table

    Returns
    -------
    JSONResponse
        A JSON response containing the next SQ number for the given PID and SQ
    """
    cnxn = aeries.get_aeries_cnxn(database='DST24000SLUSD_DAILY', access_level='w')
    sq1 = get_next_DSP_sq(data.PID, data.SQ, cnxn)
    sql = sql_obj.insert_into_DSP_table.format(
        PID=data.PID,
        SQ=data.SQ,
        SQ1=sq1,
        DS=data.DS,
    ) 

    try: 
        with cnxn.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        content = {
            "status":"SUCCESS",
            "message": f"Inserted new row into DSP for student ID#{data.PID} @ SQ {data.SQ} - SQ1 {sq1}"
        }
        return JSONResponse(content=content, status_code=200)
     
    except Exception as e:
        print(e)
        content = {
            "error": f"{e}"
        }
        return JSONResponse(content=content, status_code=500)



@app.post("/aeries/ADS/", response_model=ADS_RESPONSE, tags=["Discipline Endpoints", "Aeries"])
async def insert_ADS_row(data:ADS_POST_Body, auth = Depends(get_auth)):
    """
    WARN: CURRENTLY WRITING TO DST24000SLUSD_DAILY
    ----------------------------------------
    Inserts a new row into the ADS table in Aeries

    Parameters
    ----------
    data : ADS_POST_Body 
        The data to be inserted into the ADS table

    Returns
    -------
    JSONResponse
        A JSON response containing the status and message of the operation
    """ 
    
    cnxn = aeries.get_aeries_cnxn(database='DST24000SLUSD_DAILY', access_level='w')
    sq = get_next_ADS_sq(data.PID, cnxn)
    next_iid = get_next_ADS_IID_internal(cnxn) 
    sql = sql_obj.insert_into_ADS_table.format(
        PID=data.PID,
        GR=data.GR,
        SCL=data.SCL,
        SQ=sq,
        CD=data.CD,
        CO=data.CO,
             
        DT=data.DT, 
        LCN=data.LCN,
        RF=data.RF,         
        SRF=data.SRF,
        IID=str(next_iid)
    )

    try:
        with cnxn.connect() as conn:
            conn.execute(text(sql))
            conn.commit()
        content = {
            "status":"SUCCESS",
            "message": f"Inserted new row into ADS for student ID#{data.PID} @ SQ {sq}",
            "ID": f"{data.PID}",
            "SQ": f"{sq}",
            "IID": f"{next_iid}"
        } 
        return JSONResponse(content=content, status_code=200)
     
    except Exception as e:
        print(e)
        content = {
            "error": f"{e}"
        }
        return JSONResponse(content=content, status_code=500)
      
@app.post('/aeries/discipline/', response_model=BaseResponse, tags=["Discipline Endpoints", "Aeries"])
async def insert_discipline_record(data:Discipline_POST_Body, auth = Depends(get_auth)):
    """
    !!! CURRENTLY A WORK IN PROGRESS !!!
    ---------------------
    USE /aeries/ADS/ AND /aeries/DSP/ INSTEAD
    ----------------------
    """
    id = data.PID
    ds = data.DS
    ads_response = await insert_ADS_row(data, auth=auth)

    ads_record_decode =  ads_response.body.decode()
    ads_record = loads(ads_record_decode)
    sq = ads_record['SQ']

    print(f'{data = }')
    dsp_body = {
        "PID": id,
        "SQ": sq,
        "DS": ds
    }
    dsp_response = await insert_DSP_row(dsp_body, auth=auth)

    dsp_record_decode =  dsp_response.body.decode()
    dsp_record = loads(dsp_record_decode)
    print(f'{dsp_record = }')

    ret = {
        "message": f"Inserted new row into ADS for student ID#{data.PID} ",
        "ADS": ads_record,
        

    } 
    return JSONResponse(content=ret, status_code=200)

@app.get("/aeries/student/{id}/", response_model=Student, tags=["Student Endoints"])
async def get_student(id: int, auth = Depends(get_auth)):
    """
    Get a single student's information from Aeries

    Parameters
    ----------
    id : int
        The student ID to query

    Returns
    -------
    Student
        A Student object containing the student's information
    """
    cnxn = aeries.get_aeries_cnxn()
    sql = sql_obj.student_test.format(id=id)
    data = pd.read_sql(sql, cnxn)   
    ret = loads(data.to_json(orient="records"))[0]
    return ret

@app.get("/schools/", response_model=List[School], tags=["School Endpoints"])
async def get_all_schools_info():

    """
    Get a list of all schools in Aeries

    Returns
    -------
    List[School]
        A list of School objects containing the school's information
    """
    cnxn = aeries.get_aeries_cnxn()
    sql = sql_obj.locations
    data = pd.read_sql(sql, cnxn)
    ret = loads(data.to_json(orient="records"))
    return ret

@app.get("/schools/{sc}/", response_model=School, tags=["School Endpoints"])
async def get_single_school_info(sc:int):
    """
    Get a single school's information from Aeries

    Parameters
    ----------
    sc : int
        The school code to query

    Returns
    -------
    School
        A School object containing the school's information
    """
    cnxn = aeries.get_aeries_cnxn()
    sql = sql_obj.locations
    sql = sql + f' where cd = {sc}'
    data = pd.read_sql(sql, cnxn)
    ret:School = loads(data.to_json(orient="records"))[0]
    return ret

@app.get("/users/me/", response_model=User, tags=["Testing"])
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """
    Get the current user

    Returns
    -------
    User
        The current user
    """
    return current_user


