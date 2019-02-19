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
from settings import settings
from lib import utils

app = Flask(__name__)
socketio = SocketIO(app, heartbeat_interval=30, heartbeat_timeout=5)

@socketio.on('value changed')
def value_changed(message):
    values[message['who']] = message['data']
    emit('update value', message, broadcast=True)

def on_mqtt_connect(client, userdata, flags, rc):
    print("Connected")

    data = {}
    data['client-id'] = utils.get_serial()

    client.subscribe([("/dps/client/" + data['client-id'] + "/#", 0), ("/dps/clients/commands/#", 0)])
    client.publish("/dps/clients/connected", json.dumps(data))

def on_mqtt_mesage(client, userdata, msg):
    try:
        payload = msg.payload.decode("utf-8")
        print("mqtt_message: {} {}".format(msg.topic, msg.payload))
    except Exception as ex:
        print(ex)

    if msg.topic == '/dps/client/' + utils.get_serial() + '/message':
        try:
            socketio.emit('message', {'data': payload, 'time': str(datetime.datetime.utcnow())}, namespace='/test')
        except:
            print("Error: " + sys.exc_info()[0])
    
    elif msg.topic == '/dps/clients/commands/restart' and payload == 'true':
        subprocess.call('/usr/bin/sudo /usr/sbin/service screenly-viewer restart', shell=True)

    elif msg.topic == '/dps/clients/reboot' and payload == 'true':
        subprocess.call('/usr/bin/sudo /sbin/reboot now', shell=True)

@socketio.on('my event', namespace='/test')
def my_event(msg):
    print("my event: " + msg['data'])

@socketio.on('connect', namespace='/test')
def test_connect():
    print("SocketIO Client connected")
    emit('message', {'data': '{"values":["","","",""]}', 'time': str(datetime.datetime.utcnow())}, namesace='/test', broadcast=True)

@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected')

c = mqtt.Client(protocol=mqtt.MQTTv31)

def findDpsServer():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, True)
    s.settimeout(5)

    x = utils.get_serial()

    s.sendto(bytearray.fromhex(x), ("<broadcast>", 30303))
    try:
        answer, server_addr = s.recvfrom(1024)
        print("UDP Server " + server_addr[0])
        try:
            settings['dps_server'] = json.loads(answer.decode('utf-8'))['mqtt']
        except:
            settings['dps_server'] = 'None'
        
        print("Response: %s" % settings['dps_server'])
    except socket.timeout:
        settings['dps_server'] = 'None'
        print("No server found")

    s.close()

def mqttClient():
    c.on_connect = on_mqtt_connect
    c.on_message = on_mqtt_mesage

    data = {}
    data['client-id'] = utils.get_serial()
    c.will_set("/dps/clients/disconnected", json.dumps(data), retain=False)
    print("mqtt connect_async " + settings['dps_server'])
    c.connect_async(settings['dps_server'], keepalive=10)
    c.loop_start()

if __name__ == "__main__":
    findDpsServer()

    mqttClient()
    socketio.run(app)
