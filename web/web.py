#!/usr/bin/env python
# -*- coding: utf-8 -*-

from datetime import datetime, timedelta
from platform import system as sys
from flask import Flask, render_template, send_from_directory, request

import threading
import pandas
import dateutil.relativedelta
import sqlite3


app = Flask(__name__)


if sys() == 'Windows':
    conn=sqlite3.connect('./Database.db', check_same_thread=False)
    databaseName = './Database.db'
else:
    conn=sqlite3.connect('/home/pi/Database.db', check_same_thread=False)
    databaseName = '/home/pi/Database.db'
curs=conn.cursor()

lock = threading.Lock()

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
    numSamples2 = numSamples1 + timedelta(days=1, hours=6)

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
    
def getHistData (numSamples2, lineNum):
   conn=sqlite3.connect(databaseName)
   curs=conn.cursor()
   curs.execute("SELECT * FROM data"+ str(lineNum) +" WHERE timestamp >= '" + str(numSamples2 - timedelta(days=1)) + "' AND timestamp <= '" + str(numSamples2) + "' ORDER BY timestamp DESC")
   data = curs.fetchall()
   dates = []
   speed = []
   length = []
   alarm = []
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
		curs.execute("SELECT SUM(speed) FROM data"+ str(lineNum) +" WHERE timestamp >= '" + str(entry1) + "' AND timestamp <= '" + str(entry2) + "'")
		dataSum = curs.fetchall()
		datesSum.append(str(entry2))
		lengthSum.append(dataSum[0][0])
	lengthSum = [0 if v is None else v*5 for v in lengthSum]

	return datesSum, lengthSum


def getProductivityToday(numSamples2, lineNum):

    curs.execute("SELECT * FROM stops"+ str(lineNum) +" WHERE timestamp >= '" + str(numSamples2 - timedelta(days=1)) + "' AND timestamp <= '"+ str(numSamples2) +"';")
    data = curs.fetchall()
    
    StoppedDates = []
    StoppedIntervals = []

    if len(data) != 0:
        oldDate = datetime(*datetime.strptime(data[0][0], "%Y-%m-%d %H:%M:%S").timetuple()[:6])
        oldState = data[0][1]
        for i in data:

            Date = datetime(*datetime.strptime(i[0], "%Y-%m-%d %H:%M:%S").timetuple()[:6])

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

        return totalStoppedTime, timesStopped, StoppedDates
    
    else:
        return timedelta(seconds=0), 0, StoppedDates

def getProductivityMonth(numSamples2, lineNum):

    curs.execute("SELECT * FROM stops"+ str(lineNum) +" WHERE timestamp >= '" + str(numSamples2 - timedelta(days=30)) + "' AND timestamp <= '"+ str(numSamples2) +"';")
    data = curs.fetchall()
    
    StoppedDates = []
    StoppedIntervals = []

    if len(data) != 0:
        oldDate = datetime(*datetime.strptime(data[0][0], "%Y-%m-%d %H:%M:%S").timetuple()[:6])
        oldState = data[0][1]
        for i in data:

            Date = datetime(*datetime.strptime(i[0], "%Y-%m-%d %H:%M:%S").timetuple()[:6])

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

        return totalStoppedTime, timesStopped, StoppedDates
    
    else:
        return timedelta(seconds=0), 0, StoppedDates

def getProductivityAlltime(lineNum):
    curs.execute("SELECT * FROM stops"+ str(lineNum) +";")
    data = curs.fetchall()
    
    StoppedDates = []
    StoppedIntervals = []

    if len(data) != 0:
        oldDate = datetime(*datetime.strptime(data[0][0], "%Y-%m-%d %H:%M:%S").timetuple()[:6])
        oldState = data[0][1]
        for i in data:

            Date = datetime(*datetime.strptime(i[0], "%Y-%m-%d %H:%M:%S").timetuple()[:6])

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

        return totalStoppedTime, timesStopped, StoppedDates
    
    else:
        return timedelta(seconds=0), 0, StoppedDates

def getAvgSpeed(numSamples2, lineNum):
    curs.execute("SELECT AVG(speed) FROM data"+ str(lineNum) +" WHERE timestamp >= '" + str(numSamples2 - timedelta(days=1)) + "' AND timestamp <= '"+ str(numSamples2) +"';")
    dataSum = curs.fetchall()
    avgSpeed = round(dataSum[0][0], 1)

    return avgSpeed






######################################################################
###############################        ###############################
############################### LINE 1 ###############################
###############################        ###############################
######################################################################
@app.route("/")
def index():
    global  numSamples1, numSamples2
    setGlobalVars()


    numSamples2_1 = numSamples2 + timedelta(days=1, hours = 6)
    
    numSamples1_disp = str(numSamples1)[:10]
    numSamples2_disp = str(numSamples2_1)[:10]
    
    lastDate, power, length = getLastData(1)
    firstDate = getFirstData(1)
    power = round(power, 2)
    length = round(length, 2)

    Dates, Speeds, Lengths = getHistData(numSamples2, 1)
    DatesSum1, LengthsSum1 = getHistDataLengthMonthly(numSamples2, 1)
    avgSpeed = getAvgSpeed(numSamples2, 1)

    totalStoppedTime24h, timesStopped24h, StoppedDates24h = getProductivityToday(numSamples2, 1)
    totalStoppedTime30d, timesStopped30d, StoppedDates30d = getProductivityMonth(numSamples2, 1)
    #totalStoppedTimeAll, timesStoppedAll, StoppedDatesAll = getProductivityAlltime(1)

    for i in range(len(Dates)):
      Dates[i] = Dates[i][5:16]

    for i in range(len(DatesSum1)):
        DatesSum1[i] = DatesSum1[i][:7]

    productivity24h = round(totalStoppedTime24h / timedelta(hours = 24) * 100, 1)
    productivity30d = round(totalStoppedTime30d / timedelta(days = 30) * 100, 1)

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
        'downTime24h'               : totalStoppedTime24h,
        'timesStopped24h'           : timesStopped24h,
        'productivity24h'           : productivity24h,
        'downTime30d'               : totalStoppedTime30d,
        'timesStopped30d'           : timesStopped30d,
        'productivity30d'           : productivity30d,
        'avgSpeed'                  : avgSpeed
    }

    return render_template('line1.html', **templateData)

@app.route('/', methods=['POST'])
def my_form_post():
    global  numSamples1, numSamples2
    numSamples2 = request.form['numSamples2']
    numSamples2 = datetime.strptime(numSamples2, "%Y-%m-%d")

    numSamples1_disp = str(numSamples1)[:10]
    numSamples2_disp = str(numSamples2)[:10]
    numSamples2 = numSamples2 + timedelta(days=1, hours=6)
    lastDate, power, length = getLastData(1)
    firstDate = getFirstData(1)
    power = round(power, 2)
    length = round(length, 2)

    Dates, Speeds, Lengths = getHistData(numSamples2, 1)
    DatesSum1, LengthsSum1 = getHistDataLengthMonthly(numSamples2, 1)
    avgSpeed = getAvgSpeed(numSamples2, 1)

    totalStoppedTime24h, timesStopped24h, StoppedDates24h = getProductivityToday(numSamples2, 1)
    totalStoppedTime30d, timesStopped30d, StoppedDates30d = getProductivityMonth(numSamples2, 1)
    #totalStoppedTimeAll, timesStoppedAll, StoppedDatesAll = getProductivityAlltime(1)

    for i in range(len(Dates)):
      Dates[i] = Dates[i][5:16]

    for i in range(len(DatesSum1)):
        DatesSum1[i] = DatesSum1[i][:7]

    productivity24h = round(totalStoppedTime24h / timedelta(hours = 24) * 100, 1)
    productivity30d = round(totalStoppedTime30d / timedelta(days = 30) * 100, 1)

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
        'downTime24h'               : totalStoppedTime24h,
        'timesStopped24h'           : timesStopped24h,
        'productivity24h'           : productivity24h,
        'downTime30d'               : totalStoppedTime30d,
        'timesStopped30d'           : timesStopped30d,
        'productivity30d'           : productivity30d,
        'avgSpeed'                  : avgSpeed
    }

    return render_template('line1.html', **templateData)


######################################################################
###############################        ###############################
############################### LINE 2 ###############################
###############################        ###############################
######################################################################
@app.route("/line2")
def index2():
    global  numSamples1, numSamples2
    setGlobalVars()


    numSamples2_1 = numSamples2 + timedelta(days=1, hours = 6)
    
    numSamples1_disp = str(numSamples1)[:10]
    numSamples2_disp = str(numSamples2_1)[:10]
    
    lastDate, power, length = getLastData(2)
    firstDate = getFirstData(2)
    power = round(power, 2)
    length = round(length, 2)

    Dates, Speeds, Lengths = getHistData(numSamples2, 2)
    DatesSum1, LengthsSum1 = getHistDataLengthMonthly(numSamples2, 2)
    avgSpeed = getAvgSpeed(numSamples2, 2)

    totalStoppedTime24h, timesStopped24h, StoppedDates24h = getProductivityToday(numSamples2, 2)
    totalStoppedTime30d, timesStopped30d, StoppedDates30d = getProductivityMonth(numSamples2, 2)
    #totalStoppedTimeAll, timesStoppedAll, StoppedDatesAll = getProductivityAlltime(2)

    for i in range(len(Dates)):
      Dates[i] = Dates[i][5:16]

    for i in range(len(DatesSum1)):
        DatesSum1[i] = DatesSum1[i][:7]

    productivity24h = round(totalStoppedTime24h / timedelta(hours = 24) * 100, 1)
    productivity30d = round(totalStoppedTime30d / timedelta(days = 30) * 100, 1)

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
        'downTime24h'               : totalStoppedTime24h,
        'timesStopped24h'           : timesStopped24h,
        'productivity24h'           : productivity24h,
        'downTime30d'               : totalStoppedTime30d,
        'timesStopped30d'           : timesStopped30d,
        'productivity30d'           : productivity30d,
        'avgSpeed'                  : avgSpeed
    }

    return render_template('line2.html', **templateData)

@app.route('/line2', methods=['POST'])
def my_form_post2():
    global  numSamples1, numSamples2
    numSamples2 = request.form['numSamples2']
    numSamples2 = datetime.strptime(numSamples2, "%Y-%m-%d")

    numSamples1_disp = str(numSamples1)[:10]
    numSamples2_disp = str(numSamples2)[:10]
    numSamples2 = numSamples2 + timedelta(days=1, hours=6)
    lastDate, power, length = getLastData(2)
    firstDate = getFirstData(2)
    power = round(power, 2)
    length = round(length, 2)

    Dates, Speeds, Lengths = getHistData(numSamples2, 2)
    DatesSum1, LengthsSum1 = getHistDataLengthMonthly(numSamples2, 2)
    avgSpeed = getAvgSpeed(numSamples2, 1)

    totalStoppedTime24h, timesStopped24h, StoppedDates24h = getProductivityToday(numSamples2, 2)
    totalStoppedTime30d, timesStopped30d, StoppedDates30d = getProductivityMonth(numSamples2, 2)
    #totalStoppedTimeAll, timesStoppedAll, StoppedDatesAll = getProductivityAlltime(2)

    for i in range(len(Dates)):
      Dates[i] = Dates[i][5:16]

    for i in range(len(DatesSum1)):
        DatesSum1[i] = DatesSum1[i][:7]

    productivity24h = round(totalStoppedTime24h / timedelta(hours = 24) * 100, 1)
    productivity30d = round(totalStoppedTime30d / timedelta(days = 30) * 100, 1)

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
        'downTime24h'               : totalStoppedTime24h,
        'timesStopped24h'           : timesStopped24h,
        'productivity24h'           : productivity24h,
        'downTime30d'               : totalStoppedTime30d,
        'timesStopped30d'           : timesStopped30d,
        'productivity30d'           : productivity30d,
        'avgSpeed'                  : avgSpeed
    }

    return render_template('line2.html', **templateData)


######################################################################
###############################        ###############################
############################### LINE 3 ###############################
###############################        ###############################
######################################################################
@app.route("/line3")
def index3():
    global  numSamples1, numSamples2
    setGlobalVars()


    numSamples2_1 = numSamples2 + timedelta(days=1, hours = 6)
    
    numSamples1_disp = str(numSamples1)[:10]
    numSamples2_disp = str(numSamples2_1)[:10]
    
    lastDate, power, length = getLastData(3)
    firstDate = getFirstData(3)
    power = round(power, 2)
    length = round(length, 2)

    Dates, Speeds, Lengths = getHistData(numSamples2, 3)
    DatesSum1, LengthsSum1 = getHistDataLengthMonthly(numSamples2, 3)
    avgSpeed = getAvgSpeed(numSamples2, 3)

    totalStoppedTime24h, timesStopped24h, StoppedDates24h = getProductivityToday(numSamples2, 3)
    totalStoppedTime30d, timesStopped30d, StoppedDates30d = getProductivityMonth(numSamples2, 3)
    #totalStoppedTimeAll, timesStoppedAll, StoppedDatesAll = getProductivityAlltime(3)

    for i in range(len(Dates)):
      Dates[i] = Dates[i][5:16]

    for i in range(len(DatesSum1)):
        DatesSum1[i] = DatesSum1[i][:7]

    productivity24h = round(totalStoppedTime24h / timedelta(hours = 24) * 100, 1)
    productivity30d = round(totalStoppedTime30d / timedelta(days = 30) * 100, 1)

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
        'downTime24h'               : totalStoppedTime24h,
        'timesStopped24h'           : timesStopped24h,
        'productivity24h'           : productivity24h,
        'downTime30d'               : totalStoppedTime30d,
        'timesStopped30d'           : timesStopped30d,
        'productivity30d'           : productivity30d,
        'avgSpeed'                  : avgSpeed
    }

    return render_template('line3.html', **templateData)

@app.route('/line3', methods=['POST'])
def my_form_post3():
    global  numSamples1, numSamples2
    numSamples2 = request.form['numSamples2']
    numSamples2 = datetime.strptime(numSamples2, "%Y-%m-%d")

    numSamples1_disp = str(numSamples1)[:10]
    numSamples2_disp = str(numSamples2)[:10]
    numSamples2 = numSamples2 + timedelta(days=1, hours=6)
    lastDate, power, length = getLastData(3)
    firstDate = getFirstData(3)
    power = round(power, 2)
    length = round(length, 2)

    Dates, Speeds, Lengths = getHistData(numSamples2, 3)
    DatesSum1, LengthsSum1 = getHistDataLengthMonthly(numSamples2, 3)
    avgSpeed = getAvgSpeed(numSamples2, 3)

    totalStoppedTime24h, timesStopped24h, StoppedDates24h = getProductivityToday(numSamples2, 3)
    totalStoppedTime30d, timesStopped30d, StoppedDates30d = getProductivityMonth(numSamples2, 3)
    #totalStoppedTimeAll, timesStoppedAll, StoppedDatesAll = getProductivityAlltime(3)

    for i in range(len(Dates)):
      Dates[i] = Dates[i][5:16]

    for i in range(len(DatesSum1)):
        DatesSum1[i] = DatesSum1[i][:7]

    productivity24h = round(totalStoppedTime24h / timedelta(hours = 24) * 100, 1)
    productivity30d = round(totalStoppedTime30d / timedelta(days = 30) * 100, 1)

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
        'downTime24h'               : totalStoppedTime24h,
        'timesStopped24h'           : timesStopped24h,
        'productivity24h'           : productivity24h,
        'downTime30d'               : totalStoppedTime30d,
        'timesStopped30d'           : timesStopped30d,
        'productivity30d'           : productivity30d,
        'avgSpeed'                  : avgSpeed
    }

    return render_template('line3.html', **templateData)


######################################################################
###############################        ###############################
############################### LINE 4 ###############################
###############################        ###############################
######################################################################
@app.route("/line4")
def index4():
    global  numSamples1, numSamples2
    setGlobalVars()


    numSamples2_1 = numSamples2 + timedelta(days=1, hours = 6)
    
    numSamples1_disp = str(numSamples1)[:10]
    numSamples2_disp = str(numSamples2_1)[:10]
    
    lastDate, power, length = getLastData(4)
    firstDate = getFirstData(4)
    power = round(power, 2)
    length = round(length, 2)

    Dates, Speeds, Lengths = getHistData(numSamples2, 4)
    DatesSum1, LengthsSum1 = getHistDataLengthMonthly(numSamples2, 4)
    avgSpeed = getAvgSpeed(numSamples2, 4)

    totalStoppedTime24h, timesStopped24h, StoppedDates24h = getProductivityToday(numSamples2, 4)
    totalStoppedTime30d, timesStopped30d, StoppedDates30d = getProductivityMonth(numSamples2, 4)
    #totalStoppedTimeAll, timesStoppedAll, StoppedDatesAll = getProductivityAlltime(4)

    for i in range(len(Dates)):
      Dates[i] = Dates[i][5:16]

    for i in range(len(DatesSum1)):
        DatesSum1[i] = DatesSum1[i][:7]

    productivity24h = round(totalStoppedTime24h / timedelta(hours = 24) * 100, 1)
    productivity30d = round(totalStoppedTime30d / timedelta(days = 30) * 100, 1)

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
        'downTime24h'               : totalStoppedTime24h,
        'timesStopped24h'           : timesStopped24h,
        'productivity24h'           : productivity24h,
        'downTime30d'               : totalStoppedTime30d,
        'timesStopped30d'           : timesStopped30d,
        'productivity30d'           : productivity30d,
        'avgSpeed'                  : avgSpeed
    }

    return render_template('line4.html', **templateData)

@app.route('/line4', methods=['POST'])
def my_form_post4():
    global  numSamples1, numSamples2
    numSamples2 = request.form['numSamples2']
    numSamples2 = datetime.strptime(numSamples2, "%Y-%m-%d")

    numSamples1_disp = str(numSamples1)[:10]
    numSamples2_disp = str(numSamples2)[:10]
    numSamples2 = numSamples2 + timedelta(days=1, hours=6)
    lastDate, power, length = getLastData(4)
    firstDate = getFirstData(4)
    power = round(power, 2)
    length = round(length, 2)

    Dates, Speeds, Lengths = getHistData(numSamples2, 4)
    DatesSum1, LengthsSum1 = getHistDataLengthMonthly(numSamples2, 4)
    avgSpeed = getAvgSpeed(numSamples2, 4)

    totalStoppedTime24h, timesStopped24h, StoppedDates24h = getProductivityToday(numSamples2, 4)
    totalStoppedTime30d, timesStopped30d, StoppedDates30d = getProductivityMonth(numSamples2, 4)
    #totalStoppedTimeAll, timesStoppedAll, StoppedDatesAll = getProductivityAlltime(4)

    for i in range(len(Dates)):
      Dates[i] = Dates[i][5:16]

    for i in range(len(DatesSum1)):
        DatesSum1[i] = DatesSum1[i][:7]

    productivity24h = round(totalStoppedTime24h / timedelta(hours = 24) * 100, 1)
    productivity30d = round(totalStoppedTime30d / timedelta(days = 30) * 100, 1)

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
        'downTime24h'               : totalStoppedTime24h,
        'timesStopped24h'           : timesStopped24h,
        'productivity24h'           : productivity24h,
        'downTime30d'               : totalStoppedTime30d,
        'timesStopped30d'           : timesStopped30d,
        'productivity30d'           : productivity30d,
        'avgSpeed'                  : avgSpeed
    }

    return render_template('line4.html', **templateData)

@app.route('/download', methods=['GET', 'POST'])
def download():

    return send_from_directory("/home/pi", "Database.db")


@app.route("/downtime24hl1")
def downtime24hl1():
    global numSamples2
    
    totalStoppedTime24h, timesStopped24h, StoppedDates24h = getProductivityToday(numSamples2, 1)

    formattedString = []

    for i in StoppedDates24h:
        formattedString.append([str(i[0]), str(i[1])])

    return formattedString

@app.route("/downtime24hl2")
def downtime24hl2():
    global numSamples2
    
    totalStoppedTime24h, timesStopped24h, StoppedDates24h = getProductivityToday(numSamples2, 2)

    formattedString = []

    for i in StoppedDates24h:
        formattedString.append([str(i[0]), str(i[1])])

    return formattedString

@app.route("/downtime24hl3")
def downtime24hl3():
    global numSamples2
    
    totalStoppedTime24h, timesStopped24h, StoppedDates24h = getProductivityToday(numSamples2, 3)

    formattedString = []

    for i in StoppedDates24h:
        formattedString.append([str(i[0]), str(i[1])])

    return formattedString

@app.route("/downtime24hl4")
def downtime24hl4():
    global numSamples2
    
    totalStoppedTime24h, timesStopped24h, StoppedDates24h = getProductivityToday(numSamples2, 4)

    formattedString = []

    for i in StoppedDates24h:
        formattedString.append([str(i[0]), str(i[1])])

    return formattedString

@app.route("/downtime30dl1")
def downtime30dl1():
    global numSamples2   
    
    totalStoppedTime24h, timesStopped24h, StoppedDates24h = getProductivityMonth(numSamples2, 1)

    formattedString = []

    for i in StoppedDates24h:
        formattedString.append([str(i[0]), str(i[1])])

    return formattedString

@app.route("/downtime30dl2")
def downtime30dl2():
    global numSamples2   
    
    totalStoppedTime24h, timesStopped24h, StoppedDates24h = getProductivityMonth(numSamples2, 2)

    formattedString = []

    for i in StoppedDates24h:
        formattedString.append([str(i[0]), str(i[1])])

    return formattedString

@app.route("/downtime30dl3")
def downtime30dl3():
    global numSamples2   
    
    totalStoppedTime24h, timesStopped24h, StoppedDates24h = getProductivityMonth(numSamples2, 3)

    formattedString = []

    for i in StoppedDates24h:
        formattedString.append([str(i[0]), str(i[1])])

    return formattedString

@app.route("/downtime30dl4")
def downtime30dl4():
    global numSamples2   
    
    totalStoppedTime24h, timesStopped24h, StoppedDates24h = getProductivityMonth(numSamples2, 4)

    formattedString = []

    for i in StoppedDates24h:
        formattedString.append([str(i[0]), str(i[1])])

    return formattedString

@app.route("/help")
def help():
    global  numSamples1, numSamples2
    
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


if __name__ == "__main__":
   app.run(host='0.0.0.0', port=8000, debug=False)
