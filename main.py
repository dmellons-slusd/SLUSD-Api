import logging
from time import perf_counter
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.config.fileConfig('logging.conf', disable_existing_loggers=False)

log = logging.getLogger(__name__)

app = FastAPI()

origins = [
    "http://localhost:3000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/log")
async def log_test():
    start = perf_counter()
    end = perf_counter()
    log.info(f'')
    return {"message": f"Log test"}:
