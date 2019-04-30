#!/usr/bin/env python
# -*- coding: utf-8 -*-

import eventlet
eventlet.monkey_patch()

from flask import Flask
from flask_socketio import SocketIO, emit
import paho.mqtt.client as mqtt
import json, datetime
import subprocess
import socket
import time, os, pytz
from settings import settings, get_mqtt_namespace
from lib import utils
from threading import Thread

app = Flask(__name__)
socketio = SocketIO(app, heartbeat_interval=30, heartbeat_timeout=15)
last_mqtt_payload = None

local_tz = pytz.timezone('Europe/Zurich')

def on_mqtt_connect(client, userdata, flags, rc):
    print("MQTT connected")
    messageToViewer("MQTT: DPS-Server [{}] connected".format(settings['dps_server']))

    data = get_default_data()
    client.publish("/dps/clients/connected", json.dumps(data))

    client.subscribe([("/dps/client/" + data['client-id'] + "/#", 0), ("/dps/clients/commands/#", 0)])

def on_mqtt_disconnect(client, userdata, rc):
    print("MQTT disconnected")
    messageToViewer('MQTT: DPS-Server disconnected ' + str(rc))

def on_mqtt_mesage(client, userdata, msg):
    global last_mqtt_payload
    try:
        payload = msg.payload.decode("utf-8")
        print("mqtt_message: {} {}".format(msg.topic, msg.payload))
    except Exception as ex:
        print(ex)

    if msg.topic == '/dps/client/' + utils.get_serial() + '/message':
        try:
            socketio.emit('message', {'data': payload, 'time': str(localNow())}, namespace=get_mqtt_namespace())
            last_mqtt_payload = payload
        except:
            print("Error: " + sys.exc_info()[0])
    
    elif (msg.topic == '/dps/clients/commands/restart' or msg.topic == '/dps/client/' + utils.get_serial() + '/restart') and payload == 'true':
        restart()

    elif (msg.topic == '/dps/clients/commands/reboot' or msg.topic == '/dps/client/' + utils.get_serial() + '/reboot') and payload == 'true':
        reboot()
    else:
       socketio.emit('message', {'data': None, "message" : "unhandled topic {}".format(msg.topic), 'time': str(localNow())}, namespace=get_mqtt_namespace()) 

def reboot():
    subprocess.call('/usr/bin/sudo /sbin/reboot now', shell=True)

def restart():
    subprocess.call('/usr/bin/sudo /usr/sbin/service screenly-web restart', shell=True)
    subprocess.call('/usr/bin/sudo /usr/sbin/service screenly-viewer restart', shell=True)
    subprocess.call('/usr/bin/sudo /usr/sbin/service screenly-websocket_server_layer restart', shell=True)

@socketio.on('my_event', namespace=get_mqtt_namespace())
def socketio_my_event(msg):
    print("my_event {}".format(msg))

@socketio.on('connect', namespace=get_mqtt_namespace())
def socketio_connect():
    global last_mqtt_payload

    mqtt_server = settings['dps_server']

    print("SocketIO Client connected")
    send_browser_status('connected')

    if mqtt_server == None:
        messageToViewer("DPS-Server not found")
    elif last_mqtt_payload != None:
        socketio.emit('message', {'data': last_mqtt_payload, 'time': str(localNow())}, namespace=get_mqtt_namespace())
    else:
        messageToViewer('MQTT: connected [{}] but no data available'.format(settings['dps_server']))

@socketio.on('disconnect', namespace=get_mqtt_namespace())
def socketio_disconnect():
    print('SocketIO Client disconnected')
    send_browser_status('disconnected')

def get_default_data():
    data = {}
    data['client-id'] = utils.get_serial()
    data['ip'] = utils.get_node_ip()
    return data

def send_browser_status(status):
    data = get_default_data()
    data['status'] = status
    c.publish("/dps/clients/status", json.dumps(data))

c = mqtt.Client(client_id="dps-{}".format(utils.get_serial()), protocol=mqtt.MQTTv31)
c.enable_logger(None)

class MqttFinderThread(Thread):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        settings['dps_server'] = None

        x = utils.get_serial()
        mqtt_json_file = 'mqtt.json'

        messageToViewer('Searching for MQTT Server')
        while settings['dps_server'] is None:
            try:
                messageToViewer("Search for file {}".format(mqtt_json_file))
                if os.path.isfile(mqtt_json_file) and os.access(mqtt_json_file, os.R_OK):
                    messageToViewer("File found {}".format(mqtt_json_file))
                    with open(mqtt_json_file) as json_file:
                        data = json.load(json_file)

                    try:
                        settings['dps_server'] = data['server']
                    except Exception as ex:
                        messageToViewer("Exception {}".format(ex))
                        settings['dps_server'] = None
            except Exception as ex:
                messageToViewer("Exception {}".format(ex))
                settings['dps_server'] = None

            if settings['dps_server'] == None:
                messageToViewer("no DPS-Server found in configuration")

            time.sleep(5)

        messageToViewer("DPS-Server [{}] found, now connecting...".format(settings['dps_server']))

        mqttClient()

def messageToViewer(msg):
    now = localNow()
    socketio.emit('message', {'data': None, "message" : now.strftime('%H:%M:%S - ') + msg, 'time': str(now)}, namespace=get_mqtt_namespace())

def localNow():
    utcNow = datetime.datetime.utcnow()
    return utc_to_local(utcNow)


def utc_to_local(utc_dt):
    local_dt = utc_dt.replace(tzinfo=pytz.utc).astimezone(local_tz)
    return local_tz.normalize(local_dt) # .normalize might be unnecessary

def findDpsServer():
    thread = MqttFinderThread()
    thread.daemon = True
    thread.start()


def mqttClient():
    c.on_connect = on_mqtt_connect
    c.on_disconnect = on_mqtt_disconnect
    c.on_message = on_mqtt_mesage

    data = get_default_data()
    c.will_set("/dps/clients/disconnected", json.dumps(data), retain=False)

    while settings['dps_server'] is None:
        time.sleep(5)

    print("mqtt connect_async " + settings['dps_server'])
    c.connect_async(settings['dps_server'], keepalive=10)
    c.loop_start()

if __name__ == "__main__":
    findDpsServer()

    socketio.run(app)
