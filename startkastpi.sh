#!/bin/sh

# pkill -f mSensor

python mSensor.py -c A1 &
python mSensor.py -c F1 &
python mSensor.py -c F6 &
python mSensor.py -c C1 &

