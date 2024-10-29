#!/usr/bin/env python
###########################################
#                                         #
# Line speed, length, downtime, uptime,   #
# etc.. meter and logger.                 #
# Kristof Berta - Technology Department   #
# Vicente Torns Slovakia, 2024            #
#                                         #
###########################################

import os
import time
import sqlite3
from statistics import mean
from collections import deque
from platform import system as sys

## GPIO PINS TO USE FOR RELAYS AND SENSOR
RELAY_CH1 = 26
RELAY_CH2 = 20
RELAY_CH3 = 21
SENSOR_PIN1 = 4
SENSOR_PIN2 = 27
SENSOR_PIN3 = 21
SENSOR_PIN4 = 13

lengthSavePeriod = 5    ## period in seconds in which the current length is saved for backup in case of power outage, crash, etc..
maxPulseInterval1 = 3    ## max time in seconds between impulses for sensor
maxPulseInterval2 = 3    ## max time in seconds between impulses for sensor
maxPulseInterval3 = 3    ## max time in seconds between impulses for sensor
maxPulseInterval4 = 3    ## max time in seconds between impulses for sensor
wheelCircumference1 = 0.1 ## length per impulse in meters
wheelCircumference2 = 0.1 ## length per impulse in meters
wheelCircumference3 = 0.1 ## length per impulse in meters
wheelCircumference4 = 0.1 ## length per impulse in meters

## INITIALIZE VARIABLES ||DON'T EDIT||
pulseCount = 0
pulseCount21 = 0
pulseCount22 = 0
pulseCount23 = 0
pulseCount24 = 0

samplePeriod = 0.1 #seconds
savePeriod = 300 #seconds
time2 = time.time()-5
time3 = time2
time4 = time3

lastPulse1 = 0
lastPulse2 = 0
lastPulse3 = 0
lastPulse4 = 0

speed1 = 0
speed2 = 0
speed3 = 0
speed4 = 0

machineState1 = 0
machineState2 = 0
machineState3 = 0
machineState4 = 0

OS = sys()


if OS == 'Windows':
   print('Windows detected, no GPIO Functionality')
   databaseName = './Database.db'
   logoPath = './logo.png'
   saveFilePath1 = './lengthBackup1.txt'
   saveFilePath2 = './lengthBackup2.txt'
   saveFilePath3 = './lengthBackup3.txt'
   saveFilePath4 = './lengthBackup4.txt'
else:
   databaseName = '/home/pi/Database.db'
   logoPath = '/home/pi/ConformSpeedometer/logo.png'
   saveFilePath1 = '/home/pi/lengthBackup1.txt'
   saveFilePath2 = '/home/pi/lengthBackup2.txt'
   saveFilePath3 = '/home/pi/lengthBackup3.txt'
   saveFilePath4 = '/home/pi/lengthBackup4.txt'

   import gpiozero as GPIO

   relay1 = GPIO.LED(RELAY_CH1, active_high=False)
   relay2 = GPIO.LED(RELAY_CH2, active_high=False) 
   sensor1 = GPIO.Button(SENSOR_PIN1, pull_up = False, bounce_time = 0.001)
   sensor2 = GPIO.Button(SENSOR_PIN2, pull_up = False, bounce_time = 0.001)
   sensor3 = GPIO.Button(SENSOR_PIN3, pull_up = False, bounce_time = 0.001)
   sensor4 = GPIO.Button(SENSOR_PIN4, pull_up = False, bounce_time = 0.001)


if not os.path.isfile(databaseName):
   conn = sqlite3.connect(databaseName)
   curs=conn.cursor()
   curs.execute("CREATE TABLE data1(timestamp DATETIME, speed REAL, length REAL);")
   conn.commit()
   curs.execute("CREATE TABLE data2(timestamp DATETIME, speed REAL, length REAL);")
   conn.commit()
   curs.execute("CREATE TABLE data3(timestamp DATETIME, speed REAL, length REAL);")
   conn.commit()
   curs.execute("CREATE TABLE data4(timestamp DATETIME, speed REAL, length REAL);")
   conn.commit()
   curs.execute("CREATE TABLE stops1(timestamp DATETIME, start BOOL, stop BOOL);")
   conn.commit()
   curs.execute("CREATE TABLE stops2(timestamp DATETIME, start BOOL, stop BOOL);")
   conn.commit()
   curs.execute("CREATE TABLE stops3(timestamp DATETIME, start BOOL, stop BOOL);")
   conn.commit()
   curs.execute("CREATE TABLE stops4(timestamp DATETIME, start BOOL, stop BOOL);")
   conn.commit()
   curs.execute("CREATE TABLE settings(timestamp DATETIME, sampling_period REAL, saving_period NUMERIC, circumference1 NUMERIC, circumference2 NUMERIC, circumference3 NUMERIC, circumference4 NUMERIC);")
   conn.commit()
   curs.execute("INSERT INTO settings values(datetime('now', 'localtime'), 0.1, 300, (?), (?), (?), (?));", (wheelCircumference1, wheelCircumference2, wheelCircumference3, wheelCircumference4))
   conn.commit()
   curs.execute("INSERT INTO stops1 values(datetime('now', 'localtime'), False, False);")
   conn.commit()
   curs.execute("INSERT INTO stops2 values(datetime('now', 'localtime'), False, False);")
   conn.commit()
   curs.execute("INSERT INTO stops3 values(datetime('now', 'localtime'), False, False);")
   conn.commit()
   curs.execute("INSERT INTO stops4 values(datetime('now', 'localtime'), False, False);")
   conn.commit()
   curs.execute("INSERT INTO data1 values(datetime('now', 'localtime'), 0, 0);")
   conn.commit()
   curs.execute("INSERT INTO data2 values(datetime('now', 'localtime'), 0, 0);")
   conn.commit()
   curs.execute("INSERT INTO data3 values(datetime('now', 'localtime'), 0, 0);")
   conn.commit()
   curs.execute("INSERT INTO data4 values(datetime('now', 'localtime'), 0, 0);")
   conn.commit()
   conn.close()

def logData(speed, length, lineNum):
   conn=sqlite3.connect(databaseName)
   curs=conn.cursor()

   if lineNum == 1:
      query = "INSERT INTO data1 values(datetime('now', 'localtime'), (?), (?))"
   elif lineNum == 2:
      query = "INSERT INTO data2 values(datetime('now', 'localtime'), (?), (?))"
   elif lineNum == 3:
      query = "INSERT INTO data3 values(datetime('now', 'localtime'), (?), (?))"
   else:
      query = "INSERT INTO data4 values(datetime('now', 'localtime'), (?), (?))"

   curs.execute(query, (speed, length))
   conn.commit()
   conn.close()

def logStops(state, lineNum):

   startState = 0
   stopState = 0

   if state == 0:
      startState = 0
      stopState = 1
   elif state == 1:
      startState = 1
      stopState = 0
   conn=sqlite3.connect(databaseName)
   curs=conn.cursor()

   if lineNum == 1:
      query = "INSERT INTO stops1 values(datetime('now', 'localtime'), (?), (?))"
   elif lineNum == 2:
      query = "INSERT INTO stops2 values(datetime('now', 'localtime'), (?), (?))"
   elif lineNum == 3:
      query = "INSERT INTO stops3 values(datetime('now', 'localtime'), (?), (?))"
   else:
      query = "INSERT INTO stops4 values(datetime('now', 'localtime'), (?), (?))"
   
   curs.execute(query, (startState, stopState))
   conn.commit()
   conn.close()

def getSettings():
   conn=sqlite3.connect(databaseName)
   curs=conn.cursor()
   for row in curs.execute("SELECT * FROM settings ORDER BY timestamp DESC LIMIT 1"):
      lastEdit = row[0]
      samplingPeriod = row[1]
      savingPeriod = row[2]
      Circumference1 = row[3]
      Circumference2 = row[4]
      Circumference3 = row[5]
      Circumference4 = row[6]
      return lastEdit, samplingPeriod, savingPeriod, Circumference1, Circumference2, Circumference3, Circumference4
   return None, None, None, None, None, None, None

def getLastData(lineNum):
   conn=sqlite3.connect(databaseName)
   curs=conn.cursor()

   if lineNum == 1:
      query = "SELECT * FROM data1 ORDER BY timestamp DESC LIMIT 1"
   elif lineNum == 2:
      query = "SELECT * FROM data2 ORDER BY timestamp DESC LIMIT 1"
   elif lineNum == 3:
      query = "SELECT * FROM data3 ORDER BY timestamp DESC LIMIT 1"
   else:
      query = "SELECT * FROM data4 ORDER BY timestamp DESC LIMIT 1"

   for row in curs.execute(query):
      time = row[0]
   return time

def getLastStopState(lineNum):
   conn=sqlite3.connect(databaseName)
   curs=conn.cursor()
   if lineNum == 1:
      query = "SELECT * FROM stops1 ORDER BY timestamp DESC LIMIT 1"
   elif lineNum == 2:
      query = "SELECT * FROM stops2 ORDER BY timestamp DESC LIMIT 1"
   elif lineNum == 3:
      query = "SELECT * FROM stops3 ORDER BY timestamp DESC LIMIT 1"
   else:
      query = "SELECT * FROM stops4 ORDER BY timestamp DESC LIMIT 1"

   for row in curs.execute(query):
      time = row[0]
      startState = row[1]
      stopState = row[2]

   if startState == 1 and stopState == 0:
      machineState1 = 1
   elif startState == 0 and stopState == 1:
      machineState1 = 0
   else:
      machineState1 = 0
      
   return time, machineState1


lastEdit, samplePeriod, savePeriod, wheelCircumference1, wheelCircumference2, wheelCircumference3, wheelCircumference4 = getSettings()

runningAvgLong1 = deque(maxlen = int(savePeriod / samplePeriod))
runningAvgShort1 = deque(maxlen = 4)
maxLength1 = deque(maxlen = int(savePeriod / samplePeriod) + 1)

runningAvgLong2 = deque(maxlen = int(savePeriod / samplePeriod))
runningAvgShort2 = deque(maxlen = 4)
maxLength2 = deque(maxlen = int(savePeriod / samplePeriod) + 1)

runningAvgLong3 = deque(maxlen = int(savePeriod / samplePeriod))
runningAvgShort3 = deque(maxlen = 4)
maxLength3 = deque(maxlen = int(savePeriod / samplePeriod) + 1)

runningAvgLong4 = deque(maxlen = int(savePeriod / samplePeriod))
runningAvgShort4 = deque(maxlen = 4)
maxLength4 = deque(maxlen = int(savePeriod / samplePeriod) + 1)


def pulseCallback1(self):
   global pulseCount21, speed1, maxPulseInterval1, wheelCircumference1, lastPulse1
   print("Pulse S1")
   pulseCount21 = pulseCount21 + 1
   timeDiff1 = time.time() - lastPulse1
   if timeDiff1 > 0.005 and timeDiff1 < maxPulseInterval1:
      speed1 = 60 / timeDiff1 * wheelCircumference1

   lastPulse1 = time.time()

def pulseCallback2(self):
   global pulseCount22, speed2, maxPulseInterval2, wheelCircumference2, lastPulse2
   print("Pulse S2")
   pulseCount22 = pulseCount22 + 1
   timeDiff2 = time.time() - lastPulse2
   if timeDiff2 > 0.005 and timeDiff2 < maxPulseInterval2:
      speed2 = 60 / timeDiff2 * wheelCircumference2

   lastPulse2 = time.time()

def pulseCallback3(self):
   global pulseCount23, speed3, maxPulseInterval3, wheelCircumference3, lastPulse3
   print("Pulse S3")
   pulseCount23 = pulseCount23 + 1
   timeDiff3 = time.time() - lastPulse3
   if timeDiff3 > 0.005 and timeDiff3 < maxPulseInterval3:
      speed3 = 60 / timeDiff3 * wheelCircumference3

   lastPulse3 = time.time()

def pulseCallback4(self):
   global pulseCount24, speed4, maxPulseInterval4, wheelCircumference4, lastPulse4
   print("Pulse S4")
   pulseCount24 = pulseCount24 + 1
   timeDiff4 = time.time() - lastPulse4
   if timeDiff4 > 0.005 and timeDiff4 < maxPulseInterval4:
      speed4 = 60 / timeDiff4 * wheelCircumference4

   lastPulse4 = time.time()

if OS != 'Windows': 
   sensor1.when_released = pulseCallback1
   sensor2.when_released = pulseCallback2
   sensor3.when_released = pulseCallback3
   sensor4.when_released = pulseCallback4


date1, machineState1 = getLastStopState(1)
date2, machineState2 = getLastStopState(2)
date3, machineState3 = getLastStopState(3)
date4, machineState4 = getLastStopState(4)

try:
   if os.path.isfile(saveFilePath1) and os.path.isfile(saveFilePath2) and os.path.isfile(saveFilePath3):
      f1 = open(saveFilePath1, "r")
      length1 = float(f1.read())
      f1.close()
      pulseCount21 = length1 / wheelCircumference1
      f2 = open(saveFilePath2, "r")
      length2 = float(f2.read())
      f2.close()
      pulseCount22 = length2 / wheelCircumference2
      f3 = open(saveFilePath3, "r")
      length3 = float(f3.read())
      pulseCount23 = length3 / wheelCircumference3
      f3.close()
      f4 = open(saveFilePath4, "r")
      length4 = float(f4.read())
      pulseCount23 = length4 / wheelCircumference4
      f4.close()
   else:
      length1 = 0
      length2 = 0
      length3 = 0
      length4 = 0
      pulseCount21 = 0
      pulseCount22 = 0
      pulseCount23 = 0
      pulseCount24 = 0
      f1 = open(saveFilePath1, "w")
      f1.write(str(length1))
      f1.close()
      f2 = open(saveFilePath2, "w")
      f2.write(str(length2))
      f2.close()
      f3 = open(saveFilePath3, "w")
      f3.write(str(length3))
      f3.close()
      f4 = open(saveFilePath4, "w")
      f4.write(str(length4))
      f4.close()
      
except:
   length1 = 0
   pulseCount21 = 0
   length2 = 0
   pulseCount22 = 0
   length3 = 0
   pulseCount23 = 0
   length4 = 0
   pulseCount24 = 0


while True:

   length1 = round(pulseCount21 * wheelCircumference1, 1)
   length2 = round(pulseCount22 * wheelCircumference2, 1)
   length3 = round(pulseCount23 * wheelCircumference3, 1)
   length4 = round(pulseCount24 * wheelCircumference4, 1)

   if time.time() > time2 + samplePeriod:
      time2 = time.time()

      if time2 > lastPulse1 + maxPulseInterval1:
         speed1 = 0
      if time2 > lastPulse2 + maxPulseInterval2:
         speed2 = 0
      if time2 > lastPulse3 + maxPulseInterval3:
         speed3 = 0
      if time2 > lastPulse4 + maxPulseInterval4:
         speed4 = 0
      
      maxLength1.append(length1)
      runningAvgLong1.append(speed1)
      runningAvgShort1.append(speed1)

      maxLength2.append(length2)
      runningAvgLong2.append(speed2)
      runningAvgShort2.append(speed2)

      maxLength3.append(length3)
      runningAvgLong3.append(speed3)
      runningAvgShort3.append(speed3)

      maxLength4.append(length4)
      runningAvgLong4.append(speed4)
      runningAvgShort4.append(speed4)

   if time.time() > time3 + savePeriod:
      time3 = time.time()
      logData(round(mean(runningAvgLong1), 2), max(maxLength1), 1)
      logData(round(mean(runningAvgLong2), 2), max(maxLength2), 2)
      logData(round(mean(runningAvgLong3), 2), max(maxLength3), 3)
      logData(round(mean(runningAvgLong4), 2), max(maxLength4), 4)
   
   if time.time() > time4 + lengthSavePeriod:
      
      f1 = open(saveFilePath1, "w")
      f1.write(str(length1))
      f1.close()
      f2 = open(saveFilePath2, "w")
      f2.write(str(length2))
      f2.close()
      f3 = open(saveFilePath3, "w")
      f3.write(str(length3))
      f3.close()
      f4 = open(saveFilePath4, "w")
      f4.write(str(length4))
      f4.close()
      time4 = time.time()

      print(f'''
         Line 1 Speed: {speed1} m/min
         Line 1 Length: {length1} m
         Line 2 Speed: {speed1} m/min
         Line 2 Length: {length1} m
         Line 3 Speed: {speed1} m/min
         Line 3 Length: {length1} m
         Line 4 Speed: {speed1} m/min
         Line 4 Length: {length1} m
      ''')

   if speed1 == 0 and machineState1 == 1:
      machineState1 = 0
      logStops(machineState1, 1)
   elif speed1 != 0 and machineState1 == 0:
      machineState1 = 1
      logStops(machineState1, 1)

   if speed2 == 0 and machineState2 == 1:
      machineState2 = 0
      logStops(machineState2, 2)
   elif speed2 != 0 and machineState2 == 0:
      machineState2 = 1
      logStops(machineState2, 2)

   if speed1 == 0 and machineState3 == 1:
      machineState3 = 0
      logStops(machineState3, 3)
   elif speed3 != 0 and machineState3 == 0:
      machineState3 = 1
      logStops(machineState3, 3)

   if speed4 == 0 and machineState4 == 1:
      machineState4 = 0
      logStops(machineState4, 4)
   elif speed4 != 0 and machineState4 == 0:
      machineState4 = 1
      logStops(machineState4, 4)

   time.sleep(0.01)
