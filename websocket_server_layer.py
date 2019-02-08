#!/usr/bin/env python
# -*- coding: utf-8 -*-

from flask import Flask
from flask_socketio import SocketIO, emit
import paho.mqtt.client as mqtt
import json, datetime

app = Flask(__name__)
socketio = SocketIO(app)

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

    client.subscribe("/dps/clients/#")

    client.publish("/dps/clients/connected", json.dumps(data))

def on_mqtt_mesage(client, userdata, msg):
    print("mqtt_message: " + msg.topic + " " + str(msg.payload))
    if msg.topic == '/dps/clients/message':
        print(msg.topic + " " + str(msg.payload))
        try:
            socketio.emit('message', {'data': str(msg.payload), 'time': str(datetime.datetime.utcnow())}, namespace='/test')
        except:
            print("Error: " + sys.exc_info()[0])

@socketio.on('my event', namespace='/test')
def my_event(msg):
    print("my event: " + msg['data'])

@socketio.on('connect', namespace='/test')
def test_connect():
    print("client connected")
    emit('message xy', {'data': 'Connected ' + str(datetime.datetime.utcnow()), 'count': 0, 'time': str(datetime.datetime.utcnow())}, namesace='/test', broadcast=True)

@socketio.on('disconnect', namespace='/test')
def test_disconnect():
    print('Client disconnected')

c = mqtt.Client(protocol=mqtt.MQTTv31)

def mqttClient():
    c.on_connect = on_mqtt_connect
    c.on_message = on_mqtt_mesage

    data = {}
    data['client-id'] = getserial()
    c.will_set("/dps/clients/disconnected", json.dumps(data), retain=False)
    print("mqtt connect_async")
    c.connect_async("192.168.1.10", keepalive=10)
    c.loop_start()

if __name__ == "__main__":
    mqttClient()
    socketio.run(app)