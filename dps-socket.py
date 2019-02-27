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
import time
from settings import settings, get_mqtt_namespace
from lib import utils
from threading import Thread

app = Flask(__name__)
socketio = SocketIO(app, heartbeat_interval=30, heartbeat_timeout=15)
last_mqtt_payload = None

def on_mqtt_connect(client, userdata, flags, rc):
    print("Connected")
    socketio.emit('message', {'data': None, "message" : "DPS-Server connected", 'time': str(datetime.datetime.utcnow())}, namespace=get_mqtt_namespace())

    data = {}
    data['client-id'] = utils.get_serial()

    client.subscribe([("/dps/client/" + data['client-id'] + "/#", 0), ("/dps/clients/commands/#", 0)])
    client.publish("/dps/clients/connected", json.dumps(data))

def on_mqtt_mesage(client, userdata, msg):
    global last_mqtt_payload
    try:
        payload = msg.payload.decode("utf-8")
        print("mqtt_message: {} {}".format(msg.topic, msg.payload))
    except Exception as ex:
        print(ex)

    if msg.topic == '/dps/client/' + utils.get_serial() + '/message':
        try:
            socketio.emit('message', {'data': payload, 'time': str(datetime.datetime.utcnow())}, namespace=get_mqtt_namespace())
            last_mqtt_payload = payload
        except:
            print("Error: " + sys.exc_info()[0])
    
    elif (msg.topic == '/dps/clients/commands/restart' or msg.topic == '/dps/client/' + utils.get_serial() + '/restart') and payload == 'true':
        restart()

    elif (msg.topic == '/dps/clients/commands/reboot' or msg.topic == '/dps/client/' + utils.get_serial() + '/reboot') and payload == 'true':
        reboot()

def reboot():
    subprocess.call('/usr/bin/sudo /sbin/reboot now', shell=True)

def restart():
    subprocess.call('/usr/bin/sudo /usr/sbin/service screenly-web restart', shell=True)
    subprocess.call('/usr/bin/sudo /usr/sbin/service screenly-viewer restart', shell=True)
    subprocess.call('/usr/bin/sudo /usr/sbin/service screenly-websocket_server_layer restart', shell=True)

@socketio.on('connect', namespace=get_mqtt_namespace())
def socketio_connect():
    global last_mqtt_payload
    print("SocketIO Client connected")

    mqtt_server = settings['dps_server']

    if mqtt_server == None:
        socketio.emit('message', {'data': None, "message" : "DPS-Server not found", 'time': str(datetime.datetime.utcnow())}, namespace=get_mqtt_namespace())
    elif last_mqtt_payload != None:
        socketio.emit('message', {'data': last_mqtt_payload, 'time': str(datetime.datetime.utcnow())}, namespace=get_mqtt_namespace())
    
@socketio.on('disconnect', namespace=get_mqtt_namespace())
def socketio_disconnect():
    print('SocketIO Client disconnected')

c = mqtt.Client(protocol=mqtt.MQTTv31)

class MqttFinderThread(Thread):
    def __init__(self):
        Thread.__init__(self)

    def run(self):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
        s.settimeout(5)

        x = utils.get_serial()

        settings['dps_server'] = None
        socketio.emit('message', {'message': 'Searching for MQTT Server', 'data': None, 'time': str(datetime.datetime.utcnow())}, namespace=get_mqtt_namespace())
        while settings['dps_server'] is None:
            s.sendto(bytearray.fromhex(x), ("<broadcast>", 30303))
            try:
                answer, server_addr = s.recvfrom(1024)
                print("UDP Server " + server_addr[0])
                try:
                    settings['dps_server'] = json.loads(answer.decode('utf-8'))['mqtt']
                except:
                    settings['dps_server'] = None
                
                print("Response: %s" % settings['dps_server'])
            except socket.timeout:
                settings['dps_server'] = None
                print("No MQTT Server found")

        s.close()

        mqttClient()

def findDpsServer():
    thread = MqttFinderThread()
    thread.daemon = True
    thread.start()

    time.sleep(5)


def mqttClient():
    c.on_connect = on_mqtt_connect
    c.on_message = on_mqtt_mesage

    data = {}
    data['client-id'] = utils.get_serial()
    c.will_set("/dps/clients/disconnected", json.dumps(data), retain=False)

    while settings['dps_server'] is None:
        time.sleep(5)

    print("mqtt connect_async " + settings['dps_server'])
    c.connect_async(settings['dps_server'], keepalive=10)
    c.loop_start()

if __name__ == "__main__":
    findDpsServer()

    socketio.run(app)
