#!/bin/sh

export JPH_DEBUG=1
python mSensor.py -c A1 &
python mSensor.py -c F1 &
python mSensor.py -c F6 &
python mSensor.py -c C1 &

echo pkill -f mSensor
