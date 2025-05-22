#!/bin/bash

./stop.sh
python3 app.py > server.log 2>&1 & disown

