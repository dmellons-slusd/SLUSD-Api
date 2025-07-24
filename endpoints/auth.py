from fastapi import APIRouter, Depends, HTTPException, Request, status, Body
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import ValidationError
from datetime import timedelta
from models.auth import Token, UserCredentials, User
from dependencies import authenticate_user, create_access_token, get_current_active_user
from config import get_settings
from db_users import db

router = APIRouter()
settings = get_settings()

@router.post("/token/", response_model=Token)
async def login_for_access_token_json(request: Request):
    """
    Return an access token for the given username and password.
    Accepts both OAuth2 form data and JSON body.
    """
    username = None
    password = None
    
    content_type = request.headers.get("content-type", "").lower()
    
    try:
        if "application/json" in content_type:
            # Parse JSON manually and validate
            body = await request.json()
            try:
                credentials = UserCredentials(**body)
                username = credentials.username
                password = credentials.password
            except ValidationError as e:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=e.errors()
                )
                
        elif "application/x-www-form-urlencoded" in content_type:
            # Parse form data manually
            form = await request.form()
            username = form.get("username")
            password = form.get("password")
            
            if not username or not password:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Username and password are required in form data"
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Content-Type must be 'application/json' or 'application/x-www-form-urlencoded'"
            )
            
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid JSON format"
        )
    
    # Authenticate user
    user = authenticate_user(db, username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, 
        expires_delta=access_token_expires
    )
    
    return {
        "token": access_token,
        "access_token": access_token,
        "token_type": "bearer"
    }

@router.get("/users/me/", response_model=User)
async def read_users_me(current_user: User = Depends(get_current_active_user)):
    """Get the current user"""
    return current_user