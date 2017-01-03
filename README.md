# pi Sensor Monitor

I used this project to learn more about python, flask and asynchronous messaging. I am new to python and would not mind any suggestions advice from experts that come to this repo.

## Synopsis

The purpose of the project is to automate the control of Raspberry Pi sensors on the network. All the components communicate using a Multicast Messaging layer.

![Multicast Network](https://github.com/judgewooden/multi-sensor/raw/master/static/network.png)

## Overview of the programs

Program | Purpose
------- | -------
jph.py  | Library of routines to manage the Multicast messaging
sensor.py  | Routines to read sensors
router.py  | Route message between multiple networks
redis.py   | Store last state of all multicast messages 
control.py | Command line interface for viewing/managing jph library
sql.py     | Store messages in SQL
flask.py   | WebServices interface
generateSQL.py     | Generate SQL to create database from config
static/config.json | Config file, ready by jph.py and used by all components
static/(www)       | Files for the web interface
templates/(www)    | Files for the web interface  

## Sensor

Sensors are very easy to add in python. The jph library will callback your sensors reading routine and sending data to the network is done with sendData() message. 

### Sensor supported are

Interface | Example
--------- | -------
Pipe | Return a value from a UNIX pipe
JSON | Do a http request to read JSON
ADC pi + | Analogue-to-Digital board output ![ADC Pi Plus](https://www.abelectronics.co.uk/p/56/ADC-Pi-Plus-Raspberry-Pi-Analogue-to-Digital-converter)
ADAfruit | The Temperature & Humidity sensors ![AM2302](https://www.adafruit.com/products/393)

## Overview of Multicast bus

Each component on te nework is identifed by a two characters, called *Codifiers*. There are two networks:

1. Control bus - All components talk to each other on this bus, sending keep-alive messages and commands
2. Data bus - Only collector components listen to this bus and sensors send data on this bus.

For both busses each message carries a millisecond timevalue, sequence number and a to/from Codifier. The following message types are supported:


Flag | Purpose
---- | -------
n / N | New sequence start message
I | Keep-Alive message
C | Request to re-read the config and restart
P | Ping message to a component 
T | Time value response to a {P} message, responding with payload
S | Start the Data channel callbacks
H | Halt the Data channel callbacks

## Installation

TBC
