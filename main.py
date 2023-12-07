from db_users import db
from decouple import config
from typing import List, Literal, Union
from fastapi import Depends, FastAPI, HTTPException, status, Request
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
    SD: Union[str, datetime]
    ADSQ: int
    INV: Literal['ACAD','RESO','TUPE']

class SUIA_Table(BaseModel):
    ID: int
    SD: Union[str,datetime]
    ADSQ: int #= Field("Assertive Discipline Sequence refrence")
    SQ: Union[int,None] = None
    INV: Literal['ACAD','RESO','TUPE']
    DEL: bool = 0
    DTS: datetime = datetime.now().strftime('YYYY-mm-ddTHH:MM:SS')    


##
# Internal auth classes
##
class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: str or None = None

class User(BaseModel):
    username: str
    email: str or None = None
    full_name: str or None = None
    disabled: bool or None = None

class UserInDB(User):
    hashed_password: str

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
@app.post("/token/", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
            )
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(data={"sub": user.username}, expires_delta=access_token_expires)
    return {"access_token": access_token, "token_type": "bearer"}

# @app.exception_handler(Exception)
# async def exception_handler(request: Request, exc: Exception):
#     error_message = f"Unexpected error occured: {exc}"
#     return JSONResponse(status_code=500, content={"detail": error_message})

@app.get("/users/me/", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@app.get("/test/{id}/")
async def test(id: int):
    return {"message": "Hello World", "id": id}

@app.post("/aeries/SUIA", response_model=None)
async def insert_SUIA_row(data:SUIA_Body, auth = Depends(get_auth)):
    cnxn = aeries.get_aeries_cnxn(access_level='w')
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    if 'T' not in data.SD: data.SD = data.SD+'T00:00:00'
    if data.SQ is None : data.SQ = get_next_SQIA_sq(data.ID, cnxn)
    post_data:SUIA_Table = SUIA_Table(
        ID=data.ID,
        SQ=data.SQ,
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
            "message": f"Inserted new row into SUIA for student ID#{data.ID} @ SQ {data.SQ}"
        }
        return JSONResponse(content=content, status_code=200)
     
    except Exception as e:
        print(e)
        content = {
            "error": f"{e}"
        }
        return JSONResponse(content=content, status_code=500)


@app.get("/aeries/student/{id}/", response_model=Student)
async def get_student(id: int, auth = Depends(get_auth)):
    cnxn = aeries.get_aeries_cnxn()
    sql = sql_obj.student_test.format(id=id)
    data = pd.read_sql(sql, cnxn)   
    ret = loads(data.to_json(orient="records"))[0]
    return ret

@app.get("/test/student/{id}/", response_model=StudentTest)
async def get_student_test(id: int, auth = Depends(get_auth)):
    """!! Not yet working !!
    """
    cnxn = aeries.get_aeries_cnxn()
    sql = sql_obj.student.format(id=id)
    data = pd.read_sql(sql, cnxn)   
    ret:Student = loads(data.to_json(orient="records"))[0]
    return ret

@app.get("/schools/", response_model=List[School])
async def get_all_schools_info():
    """List of basic school data for all schools"""
    cnxn = aeries.get_aeries_cnxn()
    sql = sql_obj.locations
    data = pd.read_sql(sql, cnxn)
    ret = loads(data.to_json(orient="records"))
    return ret

@app.get("/schools/{sc}", response_model=School)
async def get_single_school_info(sc:int):
    cnxn = aeries.get_aeries_cnxn()
    sql = sql_obj.locations
    sql = sql + f' where cd = {sc}'
    data = pd.read_sql(sql, cnxn)
    ret:School = loads(data.to_json(orient="records"))[0]
    return ret


