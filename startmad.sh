#!/bin/sh

export JPH_DEBUG=0

python mSensor.py -c C3 &
python mSensor.py -c X1 &
python mSensor.py -c Y1 &

echo pkill -f mSensor
