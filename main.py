from db_users import db
from decouple import config
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi.middleware.cors import CORSMiddleware
# from slusd_api_types import Student
from json import loads
from slusdlib import aeries, core
import pandas as pd

SECRET_KEY = config("SECRET_KEY")
ALGORITHM = config("ALGORITHM")
ACCESS_TOKEN_EXPIRE_MINUTES = int(config("ACCESS_TOKEN_EXPIRE_MINUTES"))

##
# Response Classes
##
class Student(BaseModel):
    SC: int
    SN: int
    LN: str
    FN: str
    MN: str
    ID: int
    SX: str
    GR: int
    BD: int
    PG: str
    AD: str
    CY: str
    ST: str
    ZC: str
    ZX: str
    TL: str
    FW: str
    FX: str
    MW: str
    MX: str
    T1: str
    T2: str
    T3: str
    T4: str
    T5: str
    U1: str
    U2: str
    U3: str
    U4: str
    U5: str
    U6: str
    U7: str
    U8: str
    ED: int
    LD: int
    GC: str
    MC: str
    EN: str
    EC: str
    SP: str
    LS: int
    GP: float
    CR: int
    CS: int
    TP: float
    CP: float
    UR: int
    CA: float
    CC: float
    LCA: float
    LCC: float
    CU: int
    ON: int
    QT: str
    TT: str
    PT: str
    LK: str
    LT: int
    RE: str
    PC: str
    TR: str
    LO: int
    HI: int
    TG: str
    LG: int
    LA: int
    MR: int
    LR: str
    FK: int
    GG: float
    GT: float
    GK: int
    GS: int
    BM: str
    CO: str
    HT: int
    WT: int
    EY: str
    HC: str
    L2: int
    GA: float
    GD: float
    SD: int
    DG: int
    GPN: float
    TPN: float
    CPN: float
    GGN: float
    GTN: float
    PTS: float
    PUC: float
    PCS: float
    QUC: str
    QCS: str
    LF: str
    HL: str
    SQ: int
    NS: int
    HP: str
    DE: int
    DP: int
    DA: int
    CCG: float
    GCG: float
    NG: int
    RAD: str
    RCY: str
    RST: str
    RZC: str
    RZX: str
    NT: int
    CRL: str
    SM: int
    DM: int
    CID: str
    SS: str
    PED: str
    SF: str
    LNA: str
    FNA: str
    MNA: str
    SFA: str
    VDT: int
    VBD: str
    VBO: str
    BCY: str
    BST: str
    BCU: str
    CL: str
    HLO: str
    DO: str
    HSG: str
    IT: str
    ITD: str
    GRT: str
    EC2: str
    EC3: str
    EC4: str
    EC5: str
    EC6: str
    GPA: float
    TPA: float
    CPA: float
    GGA: float
    GTA: float
    OCR: int
    OGR: int
    HS: int
    NTR: str
    CIC: str
    AP1: str
    AP2: str
    SEM: str
    PEM: str
    U9: str
    U10: str
    DD: int
    DNR: str
    CUC: str
    CCS: str
    SES: str
    SG: str
    RN: int
    VPC: str
    EGD: int
    CCO: str
    BPS: str
    SWR: str
    EOY: str
    CO2: str
    RS: int
    MPH: str
    CO3: str
    OID: int
    NID: str
    AV: bool
    ETH: str
    RC1: str
    RC2: str
    RC3: str
    RC4: str
    RC5: str
    U11: str
    U12: str
    U13: str
    INE: str
    TRU: str
    OSI: str
    RDT: int
    ITE: int
    ENS: int
    SNS: int
    SLD: int
    NIT: str
    NTD: str
    NRS: int
    RSY: str
    RP: float
    RC: str
    NSP: str
    NP1: str
    NP2: str
    NGC: str
    NP: str
    CGG: float
    DSL: bool
    AVI: str
    AVD: int
    MBS: str
    GN: str
    IGR: str
    IGG: str
    LVR: str
    CHT: str
    CNS: int
    SPE: str
    IBC: str
    RG: bool
    SCT: bool
    CT: str
    RCT: str
    CN: str
    RCN: str
    SCB: str
    EOO: bool
    OS: str
    OSS: str
    GSG: float
    LO1: int
    HI1: int
    LO2: int
    HI2: int
    CDT: int
    WD: int
    WS: str
    WA: str
    DEL: bool
    DTS: int
    
class StudentTest(BaseModel):
    id: int 
    sc: int
    fn: str 
    ln: str 
    gr: int

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

app = FastAPI()

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


@app.get("/users/me/", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    return current_user

@app.get("/test/{id}/")
async def test(id: int):
    return {"message": "Hello World", "id": id}


@app.get("/aeries/student/{id}/", response_model=Student)
async def get_student(id: int, auth = Depends(get_auth)):
    cnxn = aeries.get_aeries_cnxn()
    sql = sql_obj.student.format(id=id)
    data = pd.read_sql(sql, cnxn)   
    ret = loads(data.to_json(orient="records"))[0]
    return ret

@app.get("/test/student/{id}/", response_model=StudentTest)
async def get_student_test(id: int, auth = Depends(get_auth)):
    cnxn = aeries.get_aeries_cnxn()
    sql = sql_obj.student_test.format(id=id)
    data = pd.read_sql(sql, cnxn)   
    ret = loads(data.to_json(orient="records"))[0]
    return ret


