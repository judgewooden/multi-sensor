export FLASK_APP=jphFlask.py
export FLASK_DEBUG=1
export TEMPLATES_AUTO_RELOAD=True
export JPH_DEBUG=1
export JPH_SENSOR=CF
export JPH_CONFIG="file:static/config.json"

flask run --host=0.0.0.0

#redis-cli flushall
#sudo -u postgres psql


