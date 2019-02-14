#!/usr/bin/env python
# -*- coding: utf-8 -*-

import paho.mqtt.client as mqtt
import json

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

def on_mqtt_connect(client, userdata, flags, rc):
    print("Connected")
    #print("Connected with result code " + str(rc))

    data = {}
    data['client-id'] = getserial()

    #client.loop_start()

    client.subscribe("/dps/clients/#")

    client.publish("/dps/clients/connected", json.dumps(data))

def on_mqtt_mesage(client, userdata, msg):
    print(msg.topic + " " + str(msg.payload))
    if msg.topic == '/dps/clients/message':
        try:
            #socketio.emit('message', {'data': str(msg.payload), 'time': str(datetime.datetime.utcnow())}, namespace='/test')
            #socketio.emit('message', 'hallo')
            return
        except:
            print("Error: " + sys.exc_info()[0])


def mqttClient():
    c = mqtt.Client(protocol=mqtt.MQTTv31, clean_session=True)
    c.on_connect = on_mqtt_connect
    c.on_message = on_mqtt_mesage

    data = {}
    data['client-id'] = getserial()
    c.will_set("/dps/clients/disconnected", json.dumps(data), retain=False)
    #print("mqtt connect_async")
    c.connect("192.168.1.10", 1883, 30)

    c.loop_forever()
    

def testX():
    # The callback for when the client receives a CONNACK response from the server.
    def on_connect(client, userdata, flags, rc):
        print("Connected with result code "+str(rc))

        # Subscribing in on_connect() means that if we lose the connection and
        # reconnect then subscriptions will be renewed.
        client.subscribe("$SYS/broker/clients/#")

    # The callback for when a PUBLISH message is received from the server.
    def on_message(client, userdata, msg):
        print(msg.topic+" "+str(msg.payload))

    client = mqtt.Client(protocol=mqtt.MQTTv31)
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect_async("192.168.1.10", 1883, 60)

    # Blocking call that processes network traffic, dispatches callbacks and
    # handles reconnecting.
    # Other loop*() functions are available that give a threaded interface and a
    # manual interface.
    client.loop_forever()

if __name__ == '__main__':
    mqttClient()