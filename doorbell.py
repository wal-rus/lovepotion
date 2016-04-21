#!/usr/bin/python

import RPi.GPIO as GPIO  
import time

import send_string

GPIO.setmode(GPIO.BOARD)
GPIO.setup(18, GPIO.IN, pull_up_down=GPIO.PUD_UP)

s = send_string.SendString('192.168.1.17', 4002)
while True:
  bell = GPIO.input(18)
  if not bell:
    s.Send('foo')
    time.sleep(1)
  else:
    time.sleep(0.2)

