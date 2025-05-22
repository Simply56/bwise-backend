#!/bin/bash

./stop.sh
waitress-serve app.py >server.log 2>&1 &
disown
