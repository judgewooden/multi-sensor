# Raspberry Pi - Sensor Monitor (unix)

I used this project to learn more about python, javascript, css, flask and more. I am new to these and would not mind any suggestions/advice from people that come to this repo.

## Synopsis

The purpose of the project is to monitor & control Raspberry Pi based sensors on the network.

![Multicast Network](https://github.com/judgewooden/multi-sensor/raw/master/static/network.png)

## The programs

Program | Purpose
------- | -------
jph.py  | Library of routines to manage the Multicast messaging
jphRedis.py   | Cache last state of all messages in the network
jphFlask.py   | Web Servers Gateway Interface
jphPostgreSQL.py   | Store the data in a postgreSQL database
static/(www)       | Files for the Web interface
static/config.json | Config file used by all components
templates/(www)    | Files for the web interface  
sensor.py  | Routines that read the sensors 
control.py | Command line interface for viewing/managing network
generateSQL.py     | Generate SQL to create database from config 
router.py  | Route message between multiple networks (TBC)
requirements.txt | (TBC)

## The JPH library

Each component (e.g. server, sensor, data element) in the network is identified by a two character code called a **Codifier**. The JPH library will read the configuration and load the enviroment for a Codifier managing the control flow using three call backs:

Nr. | Call back type | Usage
--- | -------------- | ------
1   | a timer        | Called every 'SensorInterval' seconds. Is typically used to tell a sensor to perform a reading.
2 | Control | Called everytime there is a control message received from another component.
3 | Data | Called everytime there is a data message received from another component.

The library exposes the following functions:

| Function | Purpose 
| -------- | ------- 
| jph()    | Returns the channel for all communication with the JPH network
| timeNow() | Returns the current time in milliseconds
| getConfig() | Returns the entire configuration
| getAllSensors() | Returns the array of all Codifiers 
| getSensor() | Returns a specific Sensor's configuration
| getMySensor() | Returns my configuration
| getMySensorElement() | Returns an element in my configuration
| sendData() | Sends data on the Data Channel
| sendCtrl() | Sends a message on the Control Channel
| run() | Manage the state of the network and provide call back hooks

## The Sensor

The jph library will callback the sensors reading routine which can send data to the network using sendData(). 

### Current supported Sensors

Interface | Example
--------- | -------
Pipe | Return a value from a UNIX pipe
JSON | Do a http request to read JSON
ADC pi + | Analogue-to-Digital board output [ADC Pi Plus](https://www.abelectronics.co.uk/p/56/ADC-Pi-Plus-Raspberry-Pi-Analogue-to-Digital-converter)
ADAfruit | The Temperature & Humidity sensors [AM2302](https://www.adafruit.com/products/393)
Dwarfpool | Read the current state of the mining on Dwarfpool
Nest | Read the data from a nest device
Zwave | Read the data from a zwave enabled device
Python | Make customized calculations (using ninja2 style variable injection)

## The Multicast bus

There are two networks:

1. Control bus - All components talk to each other on this bus, sending keep-alive messages and commands.
2. Data bus - Collector components listens to this bus and sensors components send data on this bus. 

For both busses each message carries a millisecond time value, sequence number and a to/from Codifier. The following message types are supported:

Flag | Purpose
---- | -------
I | **I** am alive
C | Request to (re)read the **C**onfig and restart
P | **P**ing a component, requesting a {T} response message 
T | **T**ime value response to a {P} message, responding with payload from {P}
S | **S**tart the Data channel callbacks
H | **H**alt the Data channel callbacks
N/n | The sequence numbering from this point is **N**ew 

Message with Codifier destination '@@'' is a broadcast to all.

## Installation

####Note: to enable multicast in kvm 
sudo ip link set dev macvtap0 allmulticast on

-- Prepare the unix box

apt-get update
apt-get upgrade
apt-get install python-setuptools python-dev build-essential 
easy_install pip 
apt-get install git

-- For redis

apt-get install redis-server
pip install redis

-- For Flask

pip install Flask
pip install Flask_redis
pip install Flask_login
pip install Flask_sqlalchemy
pip install bcrypt

-- For postgreSQL

apt-get install postgresql
apt-get install libpq-dev
pip install psycopg2

cat "secretPassword" > ~/.sqlpassword
export JPH_DEBUG=0
python generatePostgreSQL -c q1 -d > /tmp/x
sudo -u postgres psql < /tmp/x

-- For logfiles

apt-get install syslog-ng
```
echo "destination d_jph { file(\"/var/log/jph.log\"); };" > /tmp/x
echo "filter f_jph { program(\"jph*\" type(glob)); };" >> /tmp/x
echo "log { source(s_src); filter(f_jph); destination(d_jph); };" >> /tmp/x
cp /tmp/x /etc/syslog-ng/conf.d/jph.conf
```

-- Add users

export JPH_DEBUG=0
python generatePostgreSQL -c q1 -p user_name:password > /tmp/x
sudo -u postgres psql < /tmp/x

-- Startup test instance



