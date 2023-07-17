import logging
from time import perf_counter, sleep
from typing import Union
from requests import Request
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.config.fileConfig('logging.conf', disable_existing_loggers=False)

log = logging.getLogger(__name__)

app = FastAPI()

origins = [
    "http://localhost:3000",
    "http://localhost:8080",
    "http://localhost:8000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/log")
async def log_test(request = 'No request') -> str:
    start = perf_counter()
    sleep(2)
    end = perf_counter()
    log_str = f'Endpoint: {__name__} | Request: {request} | Time: {round(end - start, 2)}s'
    log.info(log_str)
    return {"message": f"{log_str}"}
