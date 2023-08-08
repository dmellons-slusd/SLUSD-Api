#!/bin/bash

default="main"
reload=""
read -p "Run test or production? (1=production, 2=test): " version
read -p "Run with reload flag? (y=reload, n=no): " q_reload
server_file="$default"

if [ "$version" == "2" ]; then
    server_file="main_test"
fi

if [ "$q_reload" == "y" ]; then
    reload="--reload"
fi




uvicorn "$server_file:app" --host 0.0.0.0 $reload