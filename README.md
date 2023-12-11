# SLUSD API

FastAPI REST api for SLUSD data requests

## API Documentation

FastAPI automatically documents API endpoints. Docs can be found here -> [SLUSD API Docs](http://10.100.4.98:8000/docs)

## TODO
- [X] Install as Service
    - [X] Install in `systemd/system`
    - [X] Setup Logging
    -    [X] `journalctl -f -u fastapi.service`
- [X] Setup Security
- [X] Setup CORS policy as needed
- [X] Branch API endpoints per application (Aeries, Escape, etc)
