from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from endpoints import auth, suia, discipline, students, schools, sped
from config import get_settings

settings = get_settings()

app = FastAPI(
    title="SLUSD API",
    description="SLUSD Api Documentation"
)

# CORS Middleware
origins = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://localhost:8000",
    "http://*.slusd.us",
    "https://*.slusd.us",
    "http://10.15.1.*",
    "https://data.slusd.us" 
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router, tags=["Authentication"])
app.include_router(suia.router, prefix="/aeries/SUIA", tags=["SUIA Endpoints", "Aeries"])
app.include_router(discipline.router, prefix="/aeries", tags=["Discipline Endpoints", "Aeries"])
app.include_router(students.router, prefix="/aeries/student", tags=["Student Endpoints", "Aeries"])
app.include_router(schools.router, prefix="/schools", tags=["School Endpoints"])
app.include_router(sped.router, prefix="/sped", tags=["SPED Endpoints", "Aeries"])

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)