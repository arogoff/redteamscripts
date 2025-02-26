#!/usr/bin/env python3
import sched, time

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

# creates scheduler to ping server
checkin_scheduler = sched.scheduler(time.time, time.sleep)
checkin_scheduler.enter(CHECKIN_INTERVAL, 1, ping, (checkin_scheduler,))
checkin_scheduler.run()