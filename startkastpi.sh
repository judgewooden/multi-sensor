#!/bin/sh

export JPH_DEBUG=0
python sensor.py -c A1 &
python sensor.py -c F1 &
python sensor.py -c C1 &
python sensor.py -c F6 &

echo pkill -f sensor
