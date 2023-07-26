set default=main2
set /p version=Run test or production? \n  1=test \n  2=production:


set server_file=%default%

if "%version%"=="2" (
    set server_file=main
)

uvicorn %server_file%:app --reload