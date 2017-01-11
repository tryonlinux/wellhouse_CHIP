#!/usr/bin/python3

import time
import os
import CHIP_IO.GPIO as GPIO
import glob
import sys
import ftplib
from urllib.request import urlopen
import json

#global vars for Inside Temp Reading
base_dir = '/sys/bus/w1/devices/'
device_folder = glob.glob(base_dir + '28*')[0]
device_file = device_folder + '/w1_slave'

#set up CSIDO pin at output (we won't be reading any data from it)
GPIO.setup("U14_31",GPIO.OUT)

#Removes existing JPEG and Text Files in the wellhouse folder to prepare for new data
def deleteOld():
  filelist = glob.glob("*.jpeg")
  for f in filelist:
    os.remove(f)
  filelist = glob.glob("*.txt")
  for f in filelist:
    os.remove(f) 

#Takes Picture and saves to YYYYMMDD--HH Format"
def takePic():
  from subprocess import call
  call(["streamer", "-f","jpeg","-o",time.strftime("%Y%m%d--%H") + ".jpeg"])

  return

#Switches the Relay on CSID0 to On
def switchOn():
  GPIO.output("U14_31",GPIO.HIGH)
  time.sleep(1)

#Switches the Relay on CSID0 to Off
def switchOff():
  GPIO.output("U14_31",GPIO.LOW)

#Check the state of the CSIDO Pin
def checkState():
  return GPIO.input("U14_31")
#Reads private data from private.txt in ../private
#Pass in which row you want, and it will return it as a string
def readPrivate(intWhichLine):
  path = sys.path[0].replace("wellhouse","private") + "/private.txt"
  pathFile = open(path,'r')
  return pathFile.readlines()[intWhichLine].strip()

#Gets the raw temp data from DS18B20
def read_temp_raw():
  f = open(device_file, 'r')
  lines = f.readlines()
  f.close()
  return lines

#Gets the current Inside Temp in F from the One-Wire DS18B20 
#Code from: https://learn.adafruit.com/adafruits-raspberry-pi-lesson-11-ds18b20-temperature-sensing/overview 
def tempInside():
  lines = read_temp_raw()
  while lines[0].strip()[-3:] != 'YES':
    time.sleep(0.2)
    lines = read_temp_raw()
  equals_pos = lines[1].find('t=')
  if equals_pos != -1:
    temp_string = lines[1][equals_pos+2:]
#    If we wanted Celsius uncomment and replace temp_f in return
    temp_c = float(temp_string) / 1000.0
    temp_f = temp_c * 9.0 / 5.0 + 32.0
    return temp_f

#Get Outside Temp from Weather Underground, note API Key is stored in text file private.txt, see sample.txt for sample formating
#City and Sate are also stored here
#This file is stored up one directory from current running directory in a folder called private
def tempOutside():
  # Get the data from Weather Underground
  url = "http://api.wunderground.com/api/" + readPrivate(0) + "/geolookup/conditions/q/" + readPrivate(1) +"/" + readPrivate(2) +".json"
  response = urlopen(url)
  # Convert bytes to string type and string type to dict
  string = response.read().decode('utf-8')
  json_obj = json.loads(string)
  location = json_obj['location']['city']
  temp_f = json_obj['current_observation']['temp_f']
  return temp_f 

#Writes temps to file
def writeData():
  f = open("data.txt","w")
  f.write(str(tempInside()) + "\n")
  f.write(str(tempOutside()) + "\n")
  f.close()

#Uploads File to FTP for website, private data is stored in private.txt as well
def uploadFTP():
  ftp = ftplib.FTP(readPrivate(3),readPrivate(4),readPrivate(5))
  ftp.cwd("/wellhouse/") #changing to 
  ftp.storbinary("STOR data.txt", open("data.txt", "rb"))
  ftp.cwd("/wellhouse/Pictures") #changing to 
  command = "STOR " + time.strftime("%Y%m%d--%H") + ".jpeg"
  ftp.storbinary(command , open(time.strftime("%Y%m%d--%H") + ".jpeg","rb" ))

#Run PHP Cron Job
def runCron():
  from subprocess import call
  call(["wget", "-q","--spider",readPrivate(6)])
def doIStayOn():
  if (tempInside() > 40):
    switchOff()  

#Start of Program we will Delete Old Data > Check Previous Stat >  Store Previous State >
#Make sure light is on for pic > Take Pic > Collect Data > 
#Check if light should remain on > Turn Light off if temp is below threshold >
#FTP data to Server > Call Cron Job > Save Electricty and look cool doing it
deleteOld()
previousState = checkState()
if not (previousState):
  switchOn()

#sleep for 5 seconds to make sure light is on and warmed up
time.sleep(5)
takePic()
writeData()
doIStayOn()
uploadFTP()
runCron()


  

















