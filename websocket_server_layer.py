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

app = Flask(__name__)
socketio = SocketIO(app, heartbeat_interval=30, heartbeat_timeout=5)

def getserial():
    # Extract serial from cpuinfo file
    cpuserial = "0000000000000000"
    try:
        f = open('/proc/cpuinfo','r')
        for line in f:
            if line[0:6]=='Serial':
                cpuserial = line[10:26]
        f.close()
    except:
        cpuserial = "ERROR00000000000"
    return cpuserial

@socketio.on('value changed')
def value_changed(message):
    values[message['who']] = message['data']
    emit('update value', message, broadcast=True)

def on_mqtt_connect(client, userdata, flags, rc):
    print("Connected")

    data = {}
    data['client-id'] = getserial()

    client.loop_start()

    client.subscribe("/dps/client/" + data['client-id'] + "/#")
    client.subscribe("/dps/clients/#")

    client.publish("/dps/clients/connected", json.dumps(data))

def on_mqtt_mesage(client, userdata, msg):
    payload = msg.payload.decode("utf-8")
    print("mqtt_message: " + msg.topic + " " + payload)
    if msg.topic == '/dps/client/' + getserial() + '/message':
        try:
            socketio.emit('message', {'data': payload, 'time': str(datetime.datetime.utcnow())}, namespace='/test')
        except:
            print("Error: " + sys.exc_info()[0])
    
    elif msg.topic == '/dps/clients/restart' and payload == 'true':
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

    x = getserial()

    s.sendto(bytearray.fromhex(x), ("<broadcast>", 30303))
    try:
        answer, server_addr = s.recvfrom(1024)
        print("UDP Server " + server_addr[0])
        try:
            settings['dps_server'] = json.loads(answer)['mqtt']
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
    data['client-id'] = getserial()
    c.will_set("/dps/clients/disconnected", json.dumps(data), retain=False)
    print("mqtt connect_async " + settings['dps_server'])
    c.connect_async(settings['dps_server'], keepalive=10)
    c.loop_start()


if __name__ == "__main__":
    findDpsServer()

    mqttClient()
    socketio.run(app)
