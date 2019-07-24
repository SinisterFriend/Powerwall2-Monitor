#!/usr/bin/python3
# Monitor energy usage from Powerwall 2 (via Backup Gateway) - Firmware 1.34.3 4/26/2019
#
# Tested on Ubuntu 18.04.1
#
#
# Req:
#     apt-get install python3-tk
#     pip3 install objectpath
#     pip3 install matplotlib
#
# Usage:
#     python3 mon.py [-x] [-t solar|grid|battery|homeload (default: homeload)] [-i interval (default: 1)]
#
#

import os
import signal
import sys
import json
import ssl
import time
import objectpath
import urllib.request
import matplotlib.pyplot as plt
import numpy as np
import tkinter as tk
from argparse import ArgumentParser


#IP Address of Backup Gateway on LAN
POWERWALL_LOCAL_IP="192.168.1.156"

def live_plotter(x_vec,y1_data,line1,identifier,y_label,pause_time=.5):
    if line1==[]:
        plt.ion()
        fig = plt.figure(figsize=(13,6))
        ax = fig.add_subplot(111)
        line1, = ax.plot(x_vec,y1_data,'-o',alpha=0.8)
        plt.ylabel(y_label)
        plt.xlabel("Time (seconds)")
        plt.title('{}'.format(identifier))
        plt.show()

    line1.set_ydata(y1_data)
    if np.min(y1_data)<=line1.axes.get_ylim()[0] or np.max(y1_data)>=line1.axes.get_ylim()[1]:
        plt.ylim([np.min(y1_data)-np.std(y1_data),np.max(y1_data)+np.std(y1_data)])

    try:
        plt.pause(pause_time)
    except tk.TclError:
        sys.exit(0)

    return line1


def build_argparser():
    parser = ArgumentParser()
    parser.add_argument("-x", "--x11", help="Display graph", action="store_true",default=0)
    parser.add_argument("-i", "--interval", help="Update interval in seconds", type=int, default=1)
    parser.add_argument("-t", "--type", help="Type: solar, grid, battery, homeload", action="store", dest="type", type=str, default="homeload")

    return parser


def signal_handler(sig, frame):
    print('Exiting')
    sys.exit(0)


plt.style.use('ggplot')

size = 60
x_vec = np.linspace(1,60,size+1)[0:-1]
y_vec = np.random.randn(len(x_vec))
line1 = []

signal.signal(signal.SIGINT, signal_handler)

args = build_argparser().parse_args()

if not args.x11:
    os.system('clear')

while True:
    t = time.strftime('%H:%M:%S',time.localtime(time.time()))

    ssl._create_default_https_context = ssl._create_unverified_context
    aggregates = urllib.request.urlopen("https://" + POWERWALL_LOCAL_IP + "/api/meters/aggregates")

    with aggregates:
        v_aggregates = json.load(aggregates)

    homeload_tree = objectpath.Tree(v_aggregates['load'])
    homeload_val = tuple(homeload_tree.execute('$..instant_power'))

    battery_tree = objectpath.Tree(v_aggregates['battery'])
    battery_flow = tuple(battery_tree.execute('$..instant_power'))

    site_tree = objectpath.Tree(v_aggregates['site'])
    grid_val = tuple(site_tree.execute('$..instant_power'))

    solar_tree = objectpath.Tree(v_aggregates['solar'])
    solar_val = tuple(solar_tree.execute('$..instant_power'))

    if args.type == "homeload":
        monitor_val = homeload_val
        label = "Power Used (Wh)"
    elif args.type == "battery":
        monitor_val = battery_flow
        label = "Power Charging (Wh)"
    elif args.type == "grid":
        monitor_val = grid_val
        label = "Power Used (Wh)"
    elif args.type == "solar":
        monitor_val = solar_val
        label = "Power Generation (Wh)"
    else:
        print("Unknown type:", args.type)
        sys.exit(0)

    if args.x11:
        y_vec[-1] = monitor_val[0]
        line1 = live_plotter(x_vec,y_vec,line1,args.type,label)
        y_vec = np.append(y_vec[1:],0.0)
    else:
        print(args.type,t," ","%.2f" %monitor_val[0], end="\r")

    time.sleep(args.interval)
