#!/usr/bin/env python3
import sched, time
import socket
import platform
from datetime import datetime
import os

SERVER = "0.0.0.0"
PORT = 1234
CHECKIN_INTERVAL = 30

print("starting")

def ping(checkin_scheduler):
    # Set up next scheduled ping
    checkin_scheduler.enter(CHECKIN_INTERVAL, 1, ping, (checkin_scheduler,))
    print("send req to ping server")

def setup_connection():
    print("setup connection to server")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #sock.connect((SERVER, PORT))

        sys_info = get_system_info()
        send(sys_info)

    except Exception as e:
        print("error connecting")

def get_system_info():
    info = {
            "session_id": 1234,
            "hostname": socket.gethostname(),
            "os": platform.system(),
            "username": os.getenv("USER") or os.getenv("USERNAME"),
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ip_address": socket.gethostbyname(socket.gethostname()),
            "platform": platform.platform(),
        }
        
    # OS-specific info
    if platform.system() == "Windows":
        try:
            print("windows stuff here")
        except Exception as e:
            pass
    else:  # Linux/Unix
        try:
            info["privileges"] = "root" if os.geteuid() == 0 else "user"
            info["shell"] = os.getenv("SHELL")
        except Exception as e:
            pass
                
    return info

def send(data):
    print("sending data")
    print(data)

def recieve():
    print("recieving data")



setup_connection()

# creates scheduler to ping server
checkin_scheduler = sched.scheduler(time.time, time.sleep)
checkin_scheduler.enter(CHECKIN_INTERVAL, 1, ping, (checkin_scheduler,))
checkin_scheduler.run()
