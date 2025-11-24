#!/bin/bash
mosquitto_pub -h 192.168.178.23 -t heatp/pump -m reset -n && echo "Reset sent"
