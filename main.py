from db_users import db
from decouple import config
from typing import List, Literal, Union
from fastapi import Depends, FastAPI, HTTPException, status, Request, Body
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.responses import Response, JSONResponse
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

class SUIA_Body(BaseModel):
    ID: int
    SD: str
    ADSQ: int
    INV: Literal['ACAD','RESO','TUPE']

class DeleteSUIA(BaseModel):
    ID: int
    SQ: int

class SUIA_Table(BaseModel):
    ID: int
    SD: str
    ADSQ: int
    SQ: int
    INV: Literal['ACAD','RESO','TUPE']
    DEL: bool
    DTS: datetime


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

def get_next_SQIA_sq(id:int, cnxn) -> int:
    sql = sql_obj.SUIA_table_sequence.format(id=id)
    data = pd.read_sql(sql, cnxn)
    if data.empty: return 1
    return data.sq.values[0]+1


def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def get_user(db, username: str):
    if username in db:
        user_dict = db[username]
        return UserInDB(**user_dict)
    
def authenticate_user(db, username: str, password: str):
    user = get_user(db, username)
    if not user: return False
    if not verify_password(password, user.hashed_password): return False
    return user

def create_access_token(data: dict, expires_delta: timedelta or None = None):
    to_encode = data.copy()
    if expires_delta: 
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_auth(token: str = Depends(oauth_2_scheme)):
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

# @app.exception_handler(Exception)
# async def exception_handler(request: Request, exc: Exception):
#     error_message = f"Unexpected error occured: {exc}"
#     return JSONResponse(status_code=500, content={"detail": error_message})

@app.post("/token/", response_model=Token, tags=["Auth"])
async def login_for_access_token(form_data: UserCredentials):
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

@app.get("/aeries/SUIA/",  tags=["SUIA Endpoints"])
async def get_all_suia_records(auth = Depends(get_auth)):
    cnxn = aeries.get_aeries_cnxn()
    sql = sql_obj.get_all_suia_records
    ret = pd.read_sql(sql, cnxn).to_dict(orient='records')
    return ret

@app.get("/aeries/SUIA/{id}",  tags=["SUIA Endpoints"])
async def get_student_suia_records(id:int,auth = Depends(get_auth)):
    cnxn = aeries.get_aeries_cnxn()
    sql = sql_obj.get_student_suia_records.format(id=id)
    ret = pd.read_sql(sql, cnxn).to_dict(orient='records')
    return ret

@app.post("/aeries/SUIA/", response_model=BaseResponse, tags=["SUIA Endpoints"])
async def insert_SUIA_row(data:SUIA_Body, auth = Depends(get_auth)):
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

@app.delete("/aeries/SUIA", response_model=BaseResponse, tags=["SUIA Endpoints"])
async def delete_SUIA_row(body:DeleteSUIA, auth = Depends(get_auth)):
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
    

@app.get("/aeries/student/{id}/", response_model=Student, tags=["Student Endoints"])
async def get_student(id: int, auth = Depends(get_auth)):
    cnxn = aeries.get_aeries_cnxn()
    sql = sql_obj.student_test.format(id=id)
    data = pd.read_sql(sql, cnxn)   
    ret = loads(data.to_json(orient="records"))[0]
    return ret

@app.get("/schools/", response_model=List[School], tags=["School Endpoints"])
async def get_all_schools_info():
    """List of basic school data for all schools"""
    cnxn = aeries.get_aeries_cnxn()
    sql = sql_obj.locations
    data = pd.read_sql(sql, cnxn)
    ret = loads(data.to_json(orient="records"))
    return ret

@app.get("/schools/{sc}", response_model=School, tags=["School Endpoints"])
async def get_single_school_info(sc:int):
    cnxn = aeries.get_aeries_cnxn()
    sql = sql_obj.locations
    sql = sql + f' where cd = {sc}'
    data = pd.read_sql(sql, cnxn)
    ret:School = loads(data.to_json(orient="records"))[0]
    return ret

@app.get("/users/me/", response_model=User, tags=["Testing"])
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user


