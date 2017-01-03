#!/bin/sh

export JPH_DEBUG=0
python sensor.py -c C3 &
python sensor.py -c X1 &
python sensor.py -c Y1 &

echo pkill -f sensor
