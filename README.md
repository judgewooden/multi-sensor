# pi Sensor Monitor

I used this project to learn more about python, flask and asynchronous messaging. I am new to python and would not mind any suggestions advice from experts that come to this repo.

## Synopsis

The purpose of the project is to automate the control of Raspberry Pi sensors on the network. All the components communicate using a Multicast Messaging layer.

![Multicast Network](https://github.com/judgewooden/multi-sensor/raw/master/static/network.png)

## 
Program | Purpose
------- | -------------
jph.py | Library of routines to manage the Multicast messaging
sensor.py          | Routines to read sensors 
router.py          | Route message between multiple networks
redis.py           | Store last state multicast messages 
control.py         | Command line interface for viewing/managing jph library
sql.py             | Store messages in SQL
flask.py           | WebServices interface
generateSQL.py     | Generate SQL to create database from config
static/config.json | Config file, ready by jph.py and used by all components
static/(www)       | Files for the web interface
templates/(www)    | Files for the web interface  



Sensor.py   | 
Content Cell  | Content Cell

Components are:

    Sensors   