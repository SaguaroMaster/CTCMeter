#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import time
import sqlite3
from platform import system
from datetime import datetime, timedelta


loadTime = time.time()

if system() == 'Windows':
    conn=sqlite3.connect('./Database.db', check_same_thread=False)
    databaseName = './Database.db'
else:
    conn=sqlite3.connect('/home/pi/Database.db', check_same_thread=False)
    databaseName = '/home/pi/Database.db'
    logFilePath = '/home/pi/webServer.log'
    sys.stdout = open(logFilePath, 'a')

print(str(datetime.now()) + ": Initializing...")

from flask import Flask, render_template, send_from_directory, request, redirect, send_file

import threading
import pandas
import dateutil.relativedelta
import sqlite3
import platform
import os
import csv
from glob import glob
from io import BytesIO
from zipfile import ZipFile
from scipy.signal import find_peaks

app = Flask(__name__)
hostName = str(platform.node())

if hostName == 'ctcpi':
    lineType = 'CTC'
    lineType2 = 'Taping'
elif hostName == 'tapingpi':
    lineType = 'Taping'
    lineType2 = 'CTC'
else:
    lineType = '???'
    lineType2 = '???'

curs=conn.cursor()
lock = threading.Lock()
maxSampleCount = 2000

def logIp(page):
    ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr) 
    curs.execute("INSERT INTO log values(datetime('now', 'localtime'), (?), (?))", (ip, page))
    conn.commit()

def readLog():
    curs.execute("SELECT * FROM log;")
    data = curs.fetchall()
    return data

def getLastData(lineNum):
    for row in curs.execute("SELECT * FROM data"+ str(lineNum) +" ORDER BY timestamp DESC LIMIT 1"):
        time = row[0]
        speed = row[1]
        length = row[2]
    return time, speed, length

def getFirstData(lineNum):
    for row in curs.execute("SELECT * FROM data"+ str(lineNum) +" ORDER BY timestamp ASC LIMIT 1"):
        time = str(row[0])
    return time

def setGlobalVars():
    global numSamples1, numSamples2
    numSamples1, nada2, nada3 = getLastData(1)
    numSamples1 = datetime(*datetime.strptime(numSamples1, "%Y-%m-%d %H:%M:%S").timetuple()[:3])
    numSamples1 = numSamples1 + timedelta(hours=6)
    numSamples2 = numSamples1 + timedelta(days=1)

def saveSettings(samplingPeriod, language, theme):
    curs.execute("INSERT INTO settings values(datetime('now', 'localtime'), (?), (?), (?))", (samplingPeriod, language, theme))
    conn.commit()

def getSettings():
   for row in curs.execute("SELECT * FROM settings ORDER BY timestamp DESC LIMIT 1"):
      lastEdit = row[0]
      samplingPeriod = row[1]
      savingPeriod = row[2]
      Circumference = row[3]
      return lastEdit, samplingPeriod, savingPeriod, Circumference
   return None, None, None, None
    
def getHistData (numSamples1, numSamples2, lineNum):
   conn=sqlite3.connect(databaseName)
   curs=conn.cursor()
   #curs.execute("SELECT * FROM data"+ str(lineNum) +" WHERE timestamp >= '" + str(numSamples2 - timedelta(days=1)) + "' AND timestamp <= '" + str(numSamples2) + "' ORDER BY timestamp DESC")
   curs.execute("SELECT * FROM data"+ str(lineNum) +" WHERE timestamp >= '" + str(numSamples1) + "' AND timestamp <= '" + str(numSamples2) + "' ORDER BY timestamp DESC")

   data = curs.fetchall()
   dates = []
   speed = []
   length = []
   for row in reversed(data):
      dates.append(row[0])
      speed.append(row[1])
      length.append(row[2])
   return dates, speed, length


#initialize global variables
global numSamples1, numSamples2
setGlobalVars()

def getHistDataLengthMonthly (numSamples2, lineNum):
	datesSum = []
	lengthSum = []
	timeInterval = pandas.date_range(str(numSamples2 - timedelta(days=365))[:10],str(numSamples2)[:10],freq='M').tolist()
	for entry1 in timeInterval[:len(timeInterval)]:
		entry2 = entry1 + dateutil.relativedelta.relativedelta(months=1)
		curs.execute("SELECT SUM(speed) FROM data" + str(lineNum) + " WHERE timestamp >= '" + str(entry1) + "' AND timestamp <= '" + str(entry2) + "'")
		dataSum = curs.fetchall()
		datesSum.append(str(entry2))
		lengthSum.append(dataSum[0][0])
	lengthSum = [0 if v is None else v*1 for v in lengthSum] # *1 because of 60 second saving period

	return datesSum, lengthSum


def getProductivity(numSamples1, numSamples2, lineNum): #not actually for 24h but any selected period between numSamples1 and 2

    curs.execute("SELECT * FROM stops"+ str(lineNum) +" WHERE timestamp >= '" + str(numSamples1) + "' AND timestamp <= '"+ str(numSamples2) +"';")
    data = curs.fetchall()

    curs.execute("SELECT * FROM data"+ str(lineNum) + " WHERE timestamp >= '" + str(numSamples1) + "' AND timestamp <= '"+ str(numSamples2) +"' ORDER BY timestamp DESC LIMIT 1")
    data2 = curs.fetchall()

    curs.execute("SELECT * FROM data"+ str(lineNum) + " WHERE timestamp >= '" + str(numSamples1) + "' AND timestamp <= '"+ str(numSamples2) +"' ORDER BY timestamp ASC LIMIT 1")
    data3 = curs.fetchall()

    curs.execute("SELECT speed FROM data"+ str(lineNum) +" WHERE timestamp >= '" + str(numSamples1) + "' AND timestamp <= '"+ str(numSamples2) +"';")
    data4 = curs.fetchall()

    speedSum = 0
    for i in data4:
        speedSum += sum(list(i))

    FirstDate = datetime(*datetime.strptime(data3[0][0], "%Y-%m-%d %H:%M:%S").timetuple()[:6])
    LastDate = datetime(*datetime.strptime(data2[0][0], "%Y-%m-%d %H:%M:%S").timetuple()[:6])
    
    StoppedDates = []
    StoppedIntervals = []

    if len(data) != 0:
        oldDate = datetime(*datetime.strptime(data[0][0], "%Y-%m-%d %H:%M:%S").timetuple()[:6])
        oldState = data[0][1]
        for i in data:

            Date = datetime(*datetime.strptime(i[0], "%Y-%m-%d %H:%M:%S").timetuple()[:6])

            if i[0] == data[0][0] and i[1] == 1 and i[2] == 0: 
                # if its the first iteration of for

                ShiftChangeTime = Date.replace(hour = 6, minute = 0, second = 0)
                timeDelta = Date - ShiftChangeTime
                StoppedDates.append([ShiftChangeTime, Date])

            elif i[0] == data[len(data)-1][0] and i[1] == 0 and i[2] == 1:

                timeDelta = Date - LastDate
                StoppedDates.append([Date, LastDate])

            if i[1] == 1 and i[2] == 0 and oldState !=1:
                # its a start 
                timeDelta = Date - oldDate
                if timeDelta > timedelta(seconds = 20):
                    StoppedDates.append([oldDate, Date])

            oldDate = Date
            oldState = i[1]
        
        for i in StoppedDates:
            timeDelta = i[1] - i[0]
            if timeDelta > timedelta(seconds = 20):
                StoppedIntervals.append(timeDelta)
        
        timesStopped = len(StoppedIntervals)
        totalStoppedTime = sum(StoppedIntervals, timedelta())

        try:
            productivity = round(totalStoppedTime / (LastDate - FirstDate) * 100, 1)
        except:
            productivity = 0

        return totalStoppedTime, timesStopped, StoppedDates, productivity


    elif speedSum == 0:

        StoppedDates = [[FirstDate, LastDate]]
        for i in StoppedDates:
            timeDelta = i[1] - i[0]
            if timeDelta > timedelta(seconds = 20):
                StoppedIntervals.append(timeDelta)
        timesStopped = len(StoppedIntervals)
        totalStoppedTime = sum(StoppedIntervals, timedelta())

        productivity = round(totalStoppedTime / (LastDate - FirstDate) * 100, 1)

        return totalStoppedTime, timesStopped, StoppedDates, productivity
    
    else:
        return timedelta(seconds=0), 0, StoppedDates, 0


def getAvgSpeed(numSamples1, numSamples2, lineNum):
    curs.execute("SELECT AVG(speed) FROM data"+ str(lineNum) +" WHERE timestamp >= '" + str(numSamples1) + "' AND timestamp <= '"+ str(numSamples2) +"';")
    dataSum = curs.fetchall()
    avgSpeed = round(dataSum[0][0], 1)

    return avgSpeed

def saveToExcel(csvName):
    curs.execute("SELECT * FROM data1;")
    data1 = curs.fetchall()
    curs.execute("SELECT * FROM data2;")
    data2 = curs.fetchall()
    curs.execute("SELECT * FROM data3;")
    data3 = curs.fetchall()
    curs.execute("SELECT * FROM data4;")
    data4 = curs.fetchall()
    if os.path.isfile(csvName + '_line1.csv'):
        os.remove(csvName)
    if os.path.isfile(csvName + '_line2.csv'):
        os.remove(csvName) 
    if os.path.isfile(csvName + '_line3.csv'):
        os.remove(csvName) 
    if os.path.isfile(csvName + '_line4.csv'):
        os.remove(csvName) 

    with open(csvName + '_line1.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Date and Time', 'Speed [m/min]', 'Length [m]', 'Alarm Setting [m]'])
        writer.writerows(data1)
    
    with open(csvName + '_line2.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Date and Time', 'Speed [m/min]', 'Length [m]', 'Alarm Setting [m]'])
        writer.writerows(data2)
    
    with open(csvName + '_line3.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Date and Time', 'Speed [m/min]', 'Length [m]', 'Alarm Setting [m]'])
        writer.writerows(data3)
    
    with open(csvName + '_line4.csv', 'w', newline='') as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(['Date and Time', 'Speed [m/min]', 'Length [m]', 'Alarm Setting [m]'])
        writer.writerows(data4)



######################################################################
###############################        ###############################
############################### LINE 1 ###############################
###############################        ###############################
######################################################################
@app.route("/")
def index():
    global  numSamples1, numSamples2, lineType, lineType2, maxSampleCount
    setGlobalVars()
    logIp("index_line1")

    
    numSamples1_disp = str(numSamples1)[:10]
    numSamples2_disp = str(numSamples2 - timedelta(days = 1))[:10]
    
    lastDate, power, length = getLastData(1)
    firstDate = getFirstData(1)
    power = round(power, 2)
    length = round(length, 2)

    Dates, Speeds, Lengths = getHistData(numSamples1, numSamples2, 1)
    DatesSum1, LengthsSum1 = getHistDataLengthMonthly(numSamples2, 1)
    avgSpeed = getAvgSpeed(numSamples1, numSamples2, 1)

    totalStoppedTime, timesStopped, StoppedDates, productivity = getProductivity(numSamples1, numSamples2, 1)

    for i in range(len(Dates)):
      Dates[i] = Dates[i][5:16]

    for i in range(len(DatesSum1)):
        DatesSum1[i] = DatesSum1[i][:7]

    if len(Speeds) > maxSampleCount:
        Factor = round(len(Speeds)/maxSampleCount)
        Speeds = Speeds[1::Factor]
        Lengths = Lengths[1::Factor]
        Dates = Dates[1::Factor]
    
    else:
        Factor = 1

    ShiftChangeFlag = 0
    LineSampleNums = []
    for i in Dates:
        if int(i[6:8]) == 18 and ShiftChangeFlag == 0:
            LineSampleNums.append(Dates.index(i))
            ShiftChangeFlag = 1
        elif int(i[6:8]) == 19 and ShiftChangeFlag == 1:
            ShiftChangeFlag = 0

        elif int(i[6:8]) == 6 and ShiftChangeFlag == 0:
            LineSampleNums.append(Dates.index(i))
            ShiftChangeFlag = 1
        elif int(i[6:8]) == 7 and ShiftChangeFlag == 1:
            ShiftChangeFlag = 0

    OldLineSampleNum = 0
    LengthPerShift = []
    LineSampleNums.append(len(Lengths)-1)

    for i in LineSampleNums:
        LengthsLocal = Lengths[OldLineSampleNum:i]
        peaks, _ = find_peaks(LengthsLocal)
        peak_values = [LengthsLocal[j] for j in peaks]  
        OldLineSampleNum = i
        diff_list = []
        for k in range(1, len(LengthsLocal)):
            diff_list.append(round(LengthsLocal[k] - LengthsLocal[k-1]))

        try:
            print(abs(min(diff_list)))
            if len(peaks) > 0 or (LengthsLocal[-1] > LengthsLocal[0] ):
                LengthPerShift.append(round(sum(peak_values) + LengthsLocal[-1] - LengthsLocal[0]))
            elif len(peaks) == 0 and abs(min(diff_list)) > 100:
                LengthPerShift.append(round(LengthsLocal[-1]))
            else:
                LengthPerShift.append(0)
        except:
            pass

    if len(LineSampleNums) > 0:
        LineSampleNums.pop(0)
        LineSampleNums = LineSampleNums[:-1]


    templateData = {
        'speed'						: power,
        'length'    				: length,
        'minDateSel'				: numSamples1_disp,
        'maxDateSel'				: numSamples2_disp,
        'minDate'					: firstDate[:10],
        'maxDate'					: lastDate[:10],
        'maxDateFull'				: lastDate[11:],
        'speedX'					: Dates,
        'speedY'					: Speeds,
        'lengthsDailyX'			    : DatesSum1,
        'lengthsDailyY'		    	: LengthsSum1,
        'lengthX'	        		: Dates,
        'lengthY'		        	: Lengths,
        'downTime'                  : totalStoppedTime,
        'timesStopped'              : timesStopped,
        'productivity'              : productivity,
        'avgSpeed'                  : avgSpeed,
        'lineType'                  : lineType,
        'lineType2'                 : lineType2,
        'timeNow'                   : str(datetime.now())[:19],
        'lineSampleNums'            : LineSampleNums,
        'lengthPerShift'            : LengthPerShift
    }

    '''ip = request.environ.get('HTTP_X_REAL_IP', request.remote_addr) 
    if ip == '192.168.8.6':
        return redirect("https://www.youtube.com/watch?v=dQw4w9WgXcQ")'''

    return render_template('line1.html', **templateData)

@app.route('/', methods=['POST'])
def my_form_post():
    global  numSamples1, numSamples2, lineType, lineType2, maxSampleCount

    numSamples1 = request.form['numSamples1']
    numSamples1 = datetime.strptime(numSamples1, "%Y-%m-%d")

    numSamples2 = request.form['numSamples2']
    numSamples2 = datetime.strptime(numSamples2, "%Y-%m-%d")

    logIp("index_line1_getDate " + str(numSamples1)[:10] + " - " + str(numSamples2)[:10])

    numSamples1_disp = str(numSamples1)[:10]
    numSamples2_disp = str(numSamples2)[:10]


    numSamples2 = numSamples2 + timedelta(days=1, hours=6)
    numSamples1 = numSamples1 + timedelta(hours = 6)

    lastDate, power, length = getLastData(1)
    firstDate = getFirstData(1)
    power = round(power, 2)
    length = round(length, 2)

    Dates, Speeds, Lengths = getHistData(numSamples1, numSamples2, 1)
    DatesSum1, LengthsSum1 = getHistDataLengthMonthly(numSamples2, 1)
    avgSpeed = getAvgSpeed(numSamples1, numSamples2, 1)

    totalStoppedTime, timesStopped, StoppedDates, productivity = getProductivity(numSamples1, numSamples2, 1)

    for i in range(len(Dates)):
      Dates[i] = Dates[i][5:16]

    for i in range(len(DatesSum1)):
        DatesSum1[i] = DatesSum1[i][:7]

    if len(Speeds) > maxSampleCount:
        Factor = round(len(Speeds)/maxSampleCount)
        Speeds = Speeds[1::Factor]
        Lengths = Lengths[1::Factor]
        Dates = Dates[1::Factor]
    
    else:
        Factor = 1

    ShiftChangeFlag = 0
    LineSampleNums = []
    for i in Dates:
        if int(i[6:8]) == 18 and ShiftChangeFlag == 0:
            LineSampleNums.append(Dates.index(i))
            ShiftChangeFlag = 1
        elif int(i[6:8]) == 19 and ShiftChangeFlag == 1:
            ShiftChangeFlag = 0

        elif int(i[6:8]) == 6 and ShiftChangeFlag == 0:
            LineSampleNums.append(Dates.index(i))
            ShiftChangeFlag = 1
        elif int(i[6:8]) == 7 and ShiftChangeFlag == 1:
            ShiftChangeFlag = 0


    OldLineSampleNum = 0
    LengthPerShift = []
    LineSampleNums.append(len(Lengths)-1)

    for i in LineSampleNums:
        LengthsLocal = Lengths[OldLineSampleNum:i]
        peaks, _ = find_peaks(LengthsLocal)
        peak_values = [LengthsLocal[j] for j in peaks]  
        OldLineSampleNum = i
        diff_list = []
        for k in range(1, len(LengthsLocal)):
            diff_list.append(round(LengthsLocal[k] - LengthsLocal[k-1]))

        try:
            print(abs(min(diff_list)))
            if len(peaks) > 0 or (LengthsLocal[-1] > LengthsLocal[0] ):
                LengthPerShift.append(round(sum(peak_values) + LengthsLocal[-1] - LengthsLocal[0]))
            elif len(peaks) == 0 and abs(min(diff_list)) > 100:
                LengthPerShift.append(round(LengthsLocal[-1]))
            else:
                LengthPerShift.append(0)
        except:
            pass

    if len(LineSampleNums) > 0:
        LineSampleNums.pop(0)
        LineSampleNums = LineSampleNums[:-1]

    templateData = {
        'speed'						: power,
        'length'    				: length,
        'minDateSel'				: numSamples1_disp,
        'maxDateSel'				: numSamples2_disp,
        'minDate'					: firstDate[:10],
        'maxDate'					: lastDate[:10],
        'maxDateFull'				: lastDate[11:],
        'speedX'					: Dates,
        'speedY'					: Speeds,
        'lengthsDailyX'			    : DatesSum1,
        'lengthsDailyY'		    	: LengthsSum1,
        'lengthX'	        		: Dates,
        'lengthY'		        	: Lengths,
        'downTime'                  : totalStoppedTime,
        'timesStopped'              : timesStopped,
        'productivity'              : productivity,
        'avgSpeed'                  : avgSpeed,
        'lineType'                  : lineType,
        'lineType2'                 : lineType2,
        'timeNow'                   : str(datetime.now())[:19],
        'lineSampleNums'            : LineSampleNums,
        'lengthPerShift'            : LengthPerShift
    }

    return render_template('line1.html', **templateData)


######################################################################
###############################        ###############################
############################### LINE 2 ###############################
###############################        ###############################
######################################################################
@app.route("/line2")
def index2():
    global  numSamples1, numSamples2, lineType, lineType2, maxSampleCount
    setGlobalVars()
    logIp("index_line2")

    
    numSamples1_disp = str(numSamples1)[:10]
    numSamples2_disp = str(numSamples2 - timedelta(days = 1))[:10]
    
    lastDate, power, length = getLastData(2)
    firstDate = getFirstData(2)
    power = round(power, 2)
    length = round(length, 2)

    Dates, Speeds, Lengths = getHistData(numSamples1,numSamples2, 2)
    DatesSum1, LengthsSum1 = getHistDataLengthMonthly(numSamples2, 2)
    avgSpeed = getAvgSpeed(numSamples1, numSamples2, 2)

    totalStoppedTime, timesStopped, StoppedDates, productivity = getProductivity(numSamples1, numSamples2, 2)

    for i in range(len(Dates)):
      Dates[i] = Dates[i][5:16]

    for i in range(len(DatesSum1)):
        DatesSum1[i] = DatesSum1[i][:7]

    if len(Speeds) > maxSampleCount:
        Factor = round(len(Speeds)/maxSampleCount)
        Speeds = Speeds[1::Factor]
        Lengths = Lengths[1::Factor]
        Dates = Dates[1::Factor]
    
    else:
        Factor = 1

    ShiftChangeFlag = 0
    LineSampleNums = []
    for i in Dates:
        if int(i[6:8]) == 18 and ShiftChangeFlag == 0:
            LineSampleNums.append(Dates.index(i))
            ShiftChangeFlag = 1
        elif int(i[6:8]) == 19 and ShiftChangeFlag == 1:
            ShiftChangeFlag = 0

        elif int(i[6:8]) == 6 and ShiftChangeFlag == 0:
            LineSampleNums.append(Dates.index(i))
            ShiftChangeFlag = 1
        elif int(i[6:8]) == 7 and ShiftChangeFlag == 1:
            ShiftChangeFlag = 0

    OldLineSampleNum = 0
    LengthPerShift = []
    LineSampleNums.append(len(Lengths)-1)

    for i in LineSampleNums:
        LengthsLocal = Lengths[OldLineSampleNum:i]
        peaks, _ = find_peaks(LengthsLocal)
        peak_values = [LengthsLocal[j] for j in peaks]  
        OldLineSampleNum = i
        diff_list = []
        for k in range(1, len(LengthsLocal)):
            diff_list.append(round(LengthsLocal[k] - LengthsLocal[k-1]))

        try:
            print(abs(min(diff_list)))
            if len(peaks) > 0 or (LengthsLocal[-1] > LengthsLocal[0] ):
                LengthPerShift.append(round(sum(peak_values) + LengthsLocal[-1] - LengthsLocal[0]))
            elif len(peaks) == 0 and abs(min(diff_list)) > 100:
                LengthPerShift.append(round(LengthsLocal[-1]))
            else:
                LengthPerShift.append(0)
        except:
            pass

    if len(LineSampleNums) > 0:
        LineSampleNums.pop(0)
        LineSampleNums = LineSampleNums[:-1]

    templateData = {
        'speed'						: power,
        'length'    				: length,
        'minDateSel'				: numSamples1_disp,
        'maxDateSel'				: numSamples2_disp,
        'minDate'					: firstDate[:10],
        'maxDate'					: lastDate[:10],
        'maxDateFull'				: lastDate[11:],
        'speedX'					: Dates,
        'speedY'					: Speeds,
        'lengthsDailyX'			    : DatesSum1,
        'lengthsDailyY'		    	: LengthsSum1,
        'lengthX'	        		: Dates,
        'lengthY'		        	: Lengths,
        'downTime'                  : totalStoppedTime,
        'timesStopped'              : timesStopped,
        'productivity'              : productivity,
        'avgSpeed'                  : avgSpeed,
        'lineType'                  : lineType,
        'lineType2'                 : lineType2,
        'timeNow'                   : str(datetime.now())[:19],
        'lineSampleNums'            : LineSampleNums,
        'lengthPerShift'            : LengthPerShift
    }

    return render_template('line2.html', **templateData)

@app.route('/line2', methods=['POST'])
def my_form_post2():
    global  numSamples1, numSamples2, lineType, lineType2, maxSampleCount

    numSamples1 = request.form['numSamples1']
    numSamples1 = datetime.strptime(numSamples1, "%Y-%m-%d")

    numSamples2 = request.form['numSamples2']
    numSamples2 = datetime.strptime(numSamples2, "%Y-%m-%d")

    logIp("index_line2_getDate " + str(numSamples1)[:10] + " - " + str(numSamples2)[:10])

    numSamples1_disp = str(numSamples1)[:10]
    numSamples2_disp = str(numSamples2)[:10]


    numSamples2 = numSamples2 + timedelta(days=1, hours=6)
    numSamples1 = numSamples1 + timedelta(hours = 6)


    lastDate, power, length = getLastData(2)
    firstDate = getFirstData(2)
    power = round(power, 2)
    length = round(length, 2)

    Dates, Speeds, Lengths = getHistData(numSamples1,numSamples2, 2)
    DatesSum1, LengthsSum1 = getHistDataLengthMonthly(numSamples2, 2)
    avgSpeed = getAvgSpeed(numSamples1, numSamples2, 2)

    totalStoppedTime, timesStopped, StoppedDates, productivity = getProductivity(numSamples1, numSamples2, 2)

    for i in range(len(Dates)):
      Dates[i] = Dates[i][5:16]

    for i in range(len(DatesSum1)):
        DatesSum1[i] = DatesSum1[i][:7]


    if len(Speeds) > maxSampleCount:
        Factor = round(len(Speeds)/maxSampleCount)
        Speeds = Speeds[1::Factor]
        Lengths = Lengths[1::Factor]
        Dates = Dates[1::Factor]
    
    else:
        Factor = 1

    ShiftChangeFlag = 0
    LineSampleNums = []
    for i in Dates:
        if int(i[6:8]) == 18 and ShiftChangeFlag == 0:
            LineSampleNums.append(Dates.index(i))
            ShiftChangeFlag = 1
        elif int(i[6:8]) == 19 and ShiftChangeFlag == 1:
            ShiftChangeFlag = 0

        elif int(i[6:8]) == 6 and ShiftChangeFlag == 0:
            LineSampleNums.append(Dates.index(i))
            ShiftChangeFlag = 1
        elif int(i[6:8]) == 7 and ShiftChangeFlag == 1:
            ShiftChangeFlag = 0

    OldLineSampleNum = 0
    LengthPerShift = []
    LineSampleNums.append(len(Lengths)-1)

    for i in LineSampleNums:
        LengthsLocal = Lengths[OldLineSampleNum:i]
        peaks, _ = find_peaks(LengthsLocal)
        peak_values = [LengthsLocal[j] for j in peaks]  
        OldLineSampleNum = i
        diff_list = []
        for k in range(1, len(LengthsLocal)):
            diff_list.append(round(LengthsLocal[k] - LengthsLocal[k-1]))

        try:
            print(abs(min(diff_list)))
            if len(peaks) > 0 or (LengthsLocal[-1] > LengthsLocal[0] ):
                LengthPerShift.append(round(sum(peak_values) + LengthsLocal[-1] - LengthsLocal[0]))
            elif len(peaks) == 0 and abs(min(diff_list)) > 100:
                LengthPerShift.append(round(LengthsLocal[-1]))
            else:
                LengthPerShift.append(0)
        except:
            pass

    if len(LineSampleNums) > 0:
        LineSampleNums.pop(0)
        LineSampleNums = LineSampleNums[:-1]
        

    templateData = {
        'speed'						: power,
        'length'    				: length,
        'minDateSel'				: numSamples1_disp,
        'maxDateSel'				: numSamples2_disp,
        'minDate'					: firstDate[:10],
        'maxDate'					: lastDate[:10],
        'maxDateFull'				: lastDate[11:],
        'speedX'					: Dates,
        'speedY'					: Speeds,
        'lengthsDailyX'			    : DatesSum1,
        'lengthsDailyY'		    	: LengthsSum1,
        'lengthX'	        		: Dates,
        'lengthY'		        	: Lengths,
        'downTime'                  : totalStoppedTime,
        'timesStopped'              : timesStopped,
        'productivity'              : productivity,
        'avgSpeed'                  : avgSpeed,
        'lineType'                  : lineType,
        'lineType2'                 : lineType2,
        'timeNow'                   : str(datetime.now())[:19],
        'lineSampleNums'            : LineSampleNums,
        'lengthPerShift'            : LengthPerShift
    }

    return render_template('line2.html', **templateData)


######################################################################
###############################        ###############################
############################### LINE 3 ###############################
###############################        ###############################
######################################################################
@app.route("/line3")
def index3():
    global  numSamples1, numSamples2, lineType, lineType2, maxSampleCount
    setGlobalVars()
    logIp("index_line3")
    
    numSamples1_disp = str(numSamples1)[:10]
    numSamples2_disp = str(numSamples2 - timedelta(days = 1))[:10]
    
    lastDate, power, length = getLastData(3)
    firstDate = getFirstData(3)
    power = round(power, 2)
    length = round(length, 2)

    Dates, Speeds, Lengths = getHistData(numSamples1,numSamples2, 3)
    DatesSum1, LengthsSum1 = getHistDataLengthMonthly(numSamples2, 3)
    avgSpeed = getAvgSpeed(numSamples1, numSamples2, 3)

    totalStoppedTime, timesStopped, StoppedDates, productivity = getProductivity(numSamples1, numSamples2, 3)
    for i in range(len(Dates)):
      Dates[i] = Dates[i][5:16]

    for i in range(len(DatesSum1)):
        DatesSum1[i] = DatesSum1[i][:7]

    if len(Speeds) > maxSampleCount:
        Factor = round(len(Speeds)/maxSampleCount)
        Speeds = Speeds[1::Factor]
        Lengths = Lengths[1::Factor]
        Dates = Dates[1::Factor]
    
    else:
        Factor = 1

    ShiftChangeFlag = 0
    LineSampleNums = []
    for i in Dates:
        if int(i[6:8]) == 18 and ShiftChangeFlag == 0:
            LineSampleNums.append(Dates.index(i))
            ShiftChangeFlag = 1
        elif int(i[6:8]) == 19 and ShiftChangeFlag == 1:
            ShiftChangeFlag = 0

        elif int(i[6:8]) == 6 and ShiftChangeFlag == 0:
            LineSampleNums.append(Dates.index(i))
            ShiftChangeFlag = 1
        elif int(i[6:8]) == 7 and ShiftChangeFlag == 1:
            ShiftChangeFlag = 0

    OldLineSampleNum = 0
    LengthPerShift = []
    LineSampleNums.append(len(Lengths)-1)

    for i in LineSampleNums:
        LengthsLocal = Lengths[OldLineSampleNum:i]
        peaks, _ = find_peaks(LengthsLocal)
        peak_values = [LengthsLocal[j] for j in peaks]  
        OldLineSampleNum = i
        diff_list = []
        for k in range(1, len(LengthsLocal)):
            diff_list.append(round(LengthsLocal[k] - LengthsLocal[k-1]))

        try:
            print(abs(min(diff_list)))
            if len(peaks) > 0 or (LengthsLocal[-1] > LengthsLocal[0] ):
                LengthPerShift.append(round(sum(peak_values) + LengthsLocal[-1] - LengthsLocal[0]))
            elif len(peaks) == 0 and abs(min(diff_list)) > 100:
                LengthPerShift.append(round(LengthsLocal[-1]))
            else:
                LengthPerShift.append(0)
        except:
            pass

    if len(LineSampleNums) > 0:
        LineSampleNums.pop(0)
        LineSampleNums = LineSampleNums[:-1]

    templateData = {
        'speed'						: power,
        'length'    				: length,
        'minDateSel'				: numSamples1_disp,
        'maxDateSel'				: numSamples2_disp,
        'minDate'					: firstDate[:10],
        'maxDate'					: lastDate[:10],
        'maxDateFull'				: lastDate[11:],
        'speedX'					: Dates,
        'speedY'					: Speeds,
        'lengthsDailyX'			    : DatesSum1,
        'lengthsDailyY'		    	: LengthsSum1,
        'lengthX'	        		: Dates,
        'lengthY'		        	: Lengths,
        'downTime'                  : totalStoppedTime,
        'timesStopped'              : timesStopped,
        'productivity'              : productivity,
        'avgSpeed'                  : avgSpeed,
        'lineType'                  : lineType,
        'lineType2'                 : lineType2,
        'timeNow'                   : str(datetime.now())[:19],
        'lineSampleNums'            : LineSampleNums,
        'lengthPerShift'            : LengthPerShift
    }

    return render_template('line3.html', **templateData)

@app.route('/line3', methods=['POST'])
def my_form_post3():
    global  numSamples1, numSamples2, lineType, lineType2, maxSampleCount

    numSamples1 = request.form['numSamples1']
    numSamples1 = datetime.strptime(numSamples1, "%Y-%m-%d")

    numSamples2 = request.form['numSamples2']
    numSamples2 = datetime.strptime(numSamples2, "%Y-%m-%d")

    logIp("index_line3_getDate " + str(numSamples1)[:10] + " - " + str(numSamples2)[:10])

    numSamples1_disp = str(numSamples1)[:10]
    numSamples2_disp = str(numSamples2)[:10]


    numSamples2 = numSamples2 + timedelta(days=1, hours=6)
    numSamples1 = numSamples1 + timedelta(hours = 6)


    lastDate, power, length = getLastData(3)
    firstDate = getFirstData(3)
    power = round(power, 2)
    length = round(length, 2)

    Dates, Speeds, Lengths = getHistData(numSamples1,numSamples2, 3)
    DatesSum1, LengthsSum1 = getHistDataLengthMonthly(numSamples2, 3)
    avgSpeed = getAvgSpeed(numSamples1, numSamples2, 3)

    totalStoppedTime, timesStopped, StoppedDates, productivity = getProductivity(numSamples1, numSamples2, 3)

    for i in range(len(Dates)):
      Dates[i] = Dates[i][5:16]

    for i in range(len(DatesSum1)):
        DatesSum1[i] = DatesSum1[i][:7]

    if len(Speeds) > maxSampleCount:
        Factor = round(len(Speeds)/maxSampleCount)
        Speeds = Speeds[1::Factor]
        Lengths = Lengths[1::Factor]
        Dates = Dates[1::Factor]
    
    else:
        Factor = 1

    ShiftChangeFlag = 0
    LineSampleNums = []
    for i in Dates:
        if int(i[6:8]) == 18 and ShiftChangeFlag == 0:
            LineSampleNums.append(Dates.index(i))
            ShiftChangeFlag = 1
        elif int(i[6:8]) == 19 and ShiftChangeFlag == 1:
            ShiftChangeFlag = 0

        elif int(i[6:8]) == 6 and ShiftChangeFlag == 0:
            LineSampleNums.append(Dates.index(i))
            ShiftChangeFlag = 1
        elif int(i[6:8]) == 7 and ShiftChangeFlag == 1:
            ShiftChangeFlag = 0

    OldLineSampleNum = 0
    LengthPerShift = []
    LineSampleNums.append(len(Lengths)-1)

    for i in LineSampleNums:
        LengthsLocal = Lengths[OldLineSampleNum:i]
        peaks, _ = find_peaks(LengthsLocal)
        peak_values = [LengthsLocal[j] for j in peaks]  
        OldLineSampleNum = i

        diff_list = []
        for k in range(1, len(LengthsLocal)):
            diff_list.append(round(LengthsLocal[k] - LengthsLocal[k-1]))

        try:
            print(abs(min(diff_list)))
            if len(peaks) > 0 or (LengthsLocal[-1] > LengthsLocal[0] ):
                LengthPerShift.append(round(sum(peak_values) + LengthsLocal[-1] - LengthsLocal[0]))
            elif len(peaks) == 0 and abs(min(diff_list)) > 100:
                LengthPerShift.append(round(LengthsLocal[-1]))
            else:
                LengthPerShift.append(0)
        except:
            pass

    if len(LineSampleNums) > 0:
        LineSampleNums.pop(0)
        LineSampleNums = LineSampleNums[:-1]

    templateData = {
        'speed'						: power,
        'length'    				: length,
        'minDateSel'				: numSamples1_disp,
        'maxDateSel'				: numSamples2_disp,
        'minDate'					: firstDate[:10],
        'maxDate'					: lastDate[:10],
        'maxDateFull'				: lastDate[11:],
        'speedX'					: Dates,
        'speedY'					: Speeds,
        'lengthsDailyX'			    : DatesSum1,
        'lengthsDailyY'		    	: LengthsSum1,
        'lengthX'	        		: Dates,
        'lengthY'		        	: Lengths,
        'downTime'                  : totalStoppedTime,
        'timesStopped'              : timesStopped,
        'productivity'              : productivity,
        'avgSpeed'                  : avgSpeed,
        'lineType'                  : lineType,
        'lineType2'                 : lineType2,
        'timeNow'                   : str(datetime.now())[:19],
        'lineSampleNums'            : LineSampleNums,
        'lengthPerShift'            : LengthPerShift
    }

    return render_template('line3.html', **templateData)


######################################################################
###############################        ###############################
############################### LINE 4 ###############################
###############################        ###############################
######################################################################
@app.route("/line4")
def index4():
    global  numSamples1, numSamples2, lineType, lineType2, maxSampleCount
    setGlobalVars()
    logIp("index_line4")

    
    numSamples1_disp = str(numSamples1)[:10]
    numSamples2_disp = str(numSamples2 - timedelta(days = 1))[:10]
    
    lastDate, power, length = getLastData(4)
    firstDate = getFirstData(4)
    power = round(power, 2)
    length = round(length, 2)

    Dates, Speeds, Lengths = getHistData(numSamples1,numSamples2, 4)
    DatesSum1, LengthsSum1 = getHistDataLengthMonthly(numSamples2, 4)
    avgSpeed = getAvgSpeed(numSamples1, numSamples2, 4)

    totalStoppedTime, timesStopped, StoppedDates, productivity = getProductivity(numSamples1, numSamples2, 4)

    for i in range(len(Dates)):
      Dates[i] = Dates[i][5:16]

    for i in range(len(DatesSum1)):
        DatesSum1[i] = DatesSum1[i][:7]

    if len(Speeds) > maxSampleCount:
        Factor = round(len(Speeds)/maxSampleCount)
        Speeds = Speeds[1::Factor]
        Lengths = Lengths[1::Factor]
        Dates = Dates[1::Factor]
    
    else:
        Factor = 1

    ShiftChangeFlag = 0
    LineSampleNums = []
    for i in Dates:
        if int(i[6:8]) == 18 and ShiftChangeFlag == 0:
            LineSampleNums.append(Dates.index(i))
            ShiftChangeFlag = 1
        elif int(i[6:8]) == 19 and ShiftChangeFlag == 1:
            ShiftChangeFlag = 0

        elif int(i[6:8]) == 6 and ShiftChangeFlag == 0:
            LineSampleNums.append(Dates.index(i))
            ShiftChangeFlag = 1
        elif int(i[6:8]) == 7 and ShiftChangeFlag == 1:
            ShiftChangeFlag = 0

    OldLineSampleNum = 0
    LengthPerShift = []
    LineSampleNums.append(len(Lengths)-1)

    for i in LineSampleNums:
        LengthsLocal = Lengths[OldLineSampleNum:i]
        peaks, _ = find_peaks(LengthsLocal)
        peak_values = [LengthsLocal[j] for j in peaks]  
        OldLineSampleNum = i
        diff_list = []
        for k in range(1, len(LengthsLocal)):
            diff_list.append(round(LengthsLocal[k] - LengthsLocal[k-1]))

        try:
            print(abs(min(diff_list)))
            if len(peaks) > 0 or (LengthsLocal[-1] > LengthsLocal[0] ):
                LengthPerShift.append(round(sum(peak_values) + LengthsLocal[-1] - LengthsLocal[0]))
            elif len(peaks) == 0 and abs(min(diff_list)) > 100:
                LengthPerShift.append(round(LengthsLocal[-1]))
            else:
                LengthPerShift.append(0)
        except:
            pass

    if len(LineSampleNums) > 0:
        LineSampleNums.pop(0)
        LineSampleNums = LineSampleNums[:-1]

    templateData = {
        'speed'						: power,
        'length'    				: length,
        'minDateSel'				: numSamples1_disp,
        'maxDateSel'				: numSamples2_disp,
        'minDate'					: firstDate[:10],
        'maxDate'					: lastDate[:10],
        'maxDateFull'				: lastDate[11:],
        'speedX'					: Dates,
        'speedY'					: Speeds,
        'lengthsDailyX'			    : DatesSum1,
        'lengthsDailyY'		    	: LengthsSum1,
        'lengthX'	        		: Dates,
        'lengthY'		        	: Lengths,
        'downTime'                  : totalStoppedTime,
        'timesStopped'              : timesStopped,
        'productivity'              : productivity,
        'avgSpeed'                  : avgSpeed,
        'lineType'                  : lineType,
        'lineType2'                 : lineType2,
        'timeNow'                   : str(datetime.now())[:19],
        'lineSampleNums'            : LineSampleNums,
        'lengthPerShift'            : LengthPerShift
    }

    return render_template('line4.html', **templateData)

@app.route('/line4', methods=['POST'])
def my_form_post4():
    global  numSamples1, numSamples2, lineType, lineType2, maxSampleCount

    numSamples1 = request.form['numSamples1']
    numSamples1 = datetime.strptime(numSamples1, "%Y-%m-%d")

    numSamples2 = request.form['numSamples2']
    numSamples2 = datetime.strptime(numSamples2, "%Y-%m-%d")

    logIp("index_line4_getDate " + str(numSamples1)[:10] + " - " + str(numSamples2)[:10])

    numSamples1_disp = str(numSamples1)[:10]
    numSamples2_disp = str(numSamples2)[:10]

    numSamples2 = numSamples2 + timedelta(days=1, hours=6)
    numSamples1 = numSamples1 + timedelta(hours = 6)


    lastDate, power, length = getLastData(4)
    firstDate = getFirstData(4)
    power = round(power, 2)
    length = round(length, 2)

    Dates, Speeds, Lengths = getHistData(numSamples1,numSamples2, 4)
    DatesSum1, LengthsSum1 = getHistDataLengthMonthly(numSamples2, 4)
    avgSpeed = getAvgSpeed(numSamples1, numSamples2, 4)

    totalStoppedTime, timesStopped, StoppedDates, productivity = getProductivity(numSamples1, numSamples2, 4)

    for i in range(len(Dates)):
      Dates[i] = Dates[i][5:16]

    for i in range(len(DatesSum1)):
        DatesSum1[i] = DatesSum1[i][:7]

    if len(Speeds) > maxSampleCount:
        Factor = round(len(Speeds)/maxSampleCount)
        Speeds = Speeds[1::Factor]
        Lengths = Lengths[1::Factor]
        Dates = Dates[1::Factor]
    
    else:
        Factor = 1

    ShiftChangeFlag = 0
    LineSampleNums = []
    for i in Dates:
        if int(i[6:8]) == 18 and ShiftChangeFlag == 0:
            LineSampleNums.append(Dates.index(i))
            ShiftChangeFlag = 1
        elif int(i[6:8]) == 19 and ShiftChangeFlag == 1:
            ShiftChangeFlag = 0

        elif int(i[6:8]) == 6 and ShiftChangeFlag == 0:
            LineSampleNums.append(Dates.index(i))
            ShiftChangeFlag = 1
        elif int(i[6:8]) == 7 and ShiftChangeFlag == 1:
            ShiftChangeFlag = 0

    OldLineSampleNum = 0
    LengthPerShift = []
    LineSampleNums.append(len(Lengths)-1)

    for i in LineSampleNums:
        LengthsLocal = Lengths[OldLineSampleNum:i]
        peaks, _ = find_peaks(LengthsLocal)
        peak_values = [LengthsLocal[j] for j in peaks]  
        OldLineSampleNum = i
        diff_list = []
        for k in range(1, len(LengthsLocal)):
            diff_list.append(round(LengthsLocal[k] - LengthsLocal[k-1]))

        try:
            print(abs(min(diff_list)))
            if len(peaks) > 0 or (LengthsLocal[-1] > LengthsLocal[0] ):
                LengthPerShift.append(round(sum(peak_values) + LengthsLocal[-1] - LengthsLocal[0]))
            elif len(peaks) == 0 and abs(min(diff_list)) > 100:
                LengthPerShift.append(round(LengthsLocal[-1]))
            else:
                LengthPerShift.append(0)
        except:
            pass

    if len(LineSampleNums) > 0:
        LineSampleNums.pop(0)
        LineSampleNums = LineSampleNums[:-1]


    templateData = {
        'speed'						: power,
        'length'    				: length,
        'minDateSel'				: numSamples1_disp,
        'maxDateSel'				: numSamples2_disp,
        'minDate'					: firstDate[:10],
        'maxDate'					: lastDate[:10],
        'maxDateFull'				: lastDate[11:],
        'speedX'					: Dates,
        'speedY'					: Speeds,
        'lengthsDailyX'			    : DatesSum1,
        'lengthsDailyY'		    	: LengthsSum1,
        'lengthX'	        		: Dates,
        'lengthY'		        	: Lengths,
        'downTime'                  : totalStoppedTime,
        'timesStopped'              : timesStopped,
        'productivity'              : productivity,
        'avgSpeed'                  : avgSpeed,
        'lineType'                  : lineType,
        'timeNow'                   : str(datetime.now())[:19],
        'lineSampleNums'            : LineSampleNums,
        'lengthPerShift'            : LengthPerShift
    }

    return render_template('line4.html', **templateData)

@app.route('/download', methods=['GET', 'POST'])
def download():

    return send_from_directory("/home/pi", "Database.db")

@app.route('/downloadcsv', methods=['GET', 'POST'])
def downloadcsv():
    logIp("downloadCSV")

    csvName = 'ExportedData'
    saveToExcel(csvName)
    #return send_from_directory("/home/pi", csvName)


    target = '/home/pi'

    stream = BytesIO()
    with ZipFile(stream, 'w') as zf:
        for file in glob(os.path.join(target, '*.csv')):
            zf.write(file, os.path.basename(file))
    stream.seek(0)

    return send_file(
        stream,
        as_attachment=True,
        download_name='ExportedData.zip'
    )

@app.route("/downtimel1")
def downtimel1():
    global numSamples1, numSamples2, lineType, lineType2, maxSampleCount

    logIp("downtimel1 " + str(numSamples1) + " - " + str(numSamples2))
    
    totalStoppedTime24h, timesStopped24h, StoppedDates24h, x = getProductivity(numSamples1, numSamples2, 1)

    formattedString = []

    for i in StoppedDates24h:
        formattedString.append([str(i[0]), str(i[1])])

    return formattedString

@app.route("/downtimel2")
def downtimel2():
    global numSamples1, numSamples2, lineType, lineType2, maxSampleCount

    logIp("downtimel2 " + str(numSamples1) + " - " + str(numSamples2))
    
    totalStoppedTime24h, timesStopped24h, StoppedDates24h, x = getProductivity(numSamples1, numSamples2, 2)

    formattedString = []

    for i in StoppedDates24h:
        formattedString.append([str(i[0]), str(i[1])])

    return formattedString

@app.route("/downtimel3")
def downtimel3():
    global numSamples1, numSamples2, lineType, lineType2, maxSampleCount

    logIp("downtimel3 " + str(numSamples1) + " - " + str(numSamples2))
    
    totalStoppedTime24h, timesStopped24h, StoppedDates24h, x = getProductivity(numSamples1, numSamples2, 3)

    formattedString = []

    for i in StoppedDates24h:
        formattedString.append([str(i[0]), str(i[1])])

    return formattedString

@app.route("/downtimel4")
def downtimel4():
    global numSamples1, numSamples2, lineType, lineType2, maxSampleCount

    logIp("downtimel4 " + str(numSamples1) + " - " + str(numSamples2))
    
    totalStoppedTime24h, timesStopped24h, StoppedDates24h, x = getProductivity(numSamples1, numSamples2, 4)

    formattedString = []

    for i in StoppedDates24h:
        formattedString.append([str(i[0]), str(i[1])])

    return formattedString

@app.route("/help")
def help():
    global  numSamples1, numSamples2, lineType, lineType2, maxSampleCount

    logIp("help")
    
    lastDate, power, length, ads = getLastData(1)
    power = round(power, 2)
    length = round(length, 2)

    Dates, Speeds, Lengths, Alarms = getHistData(numSamples2)
    avgSpeed = getAvgSpeed(numSamples2)

    templateData = {
        'speed'						: power,
        'length'    				: length,
        'maxDate'					: lastDate[:10],
        'maxDateFull'				: lastDate[11:],
        'speedX'					: Dates,
        'speedY'					: Speeds,
        'lengthX'	        		: Dates,
        'lengthY'		        	: Lengths,
        'alarmX'		    		: Dates,
        'alarmY'		       		: Alarms,
        'avgSpeed'                  : avgSpeed
    }

    return render_template('help.html', **templateData)

@app.route("/log")
def log():
    logIp("log")
    logs = readLog()
    return logs

if __name__ == "__main__":
    from waitress import serve
    print(str(datetime.now()) + ": Server Ready, took " + str(round(float(time.time()-loadTime), 2)) + " seconds")
    serve(app, host="0.0.0.0", port=8000, threads = 6)
    #app.run(host='0.0.0.0', port=8000, debug=False)
