#!/usr/bin/python
import sys
import os
import re
import argparse

"""
Arguments to program
"""

parser = argparse.ArgumentParser()
parser.add_argument("path")
args = parser.parse_args()

increment = 0
tests = dict()

def timestamp_to_ms(stamp):
    stamp = re.sub('[+() \n]', '', stamp)
    time = 0
    integers = re.split('[h,m,s,ms\n,ms]', stamp)
    units = re.split('[\d]+', stamp)
    integers = [x for x in integers if x]
    units = [x for x in units if x]

    print(integers)
    print(units)
    if (len(integers) != len(units)):
        raise ValueError('# integers does not match # units')
    index = 0
    for integer in integers:
        if units[index] == 'ms':
            time += int(integer)
        elif units[index] == 's':
            time += int(integer) * 1000
        elif units[index] == 'm':
            time += int(integer) * 1000 * 1000
    return time

def search_filepath(root_path, match):
    """
    Open all files which have a given name within root_path.
    Searches subdirectories.

    ----------
    @param root_path : str          - not case sensitive
    @param match : str              - name of files to match 
    """
    for root, dirs, files in os.walk(root_path):
        for filename in files:
            print(filename)
            if filename.lower() == match:
                global increment
                tests[increment] = parse_file(os.path.join(root, filename))
                increment += 1
    return 



def parse_file(filepath):
    """
    Parse file at filepath

    ----------
    @param filepath : str  
    ----------
    returns device dictionary
    """
    device = dict()
    print('Search in ', filepath)
    # Python uses a lookahead buffer internally thus faster reading line by line 
    
    # do stuff here
    with open(filepath, 'r') as file:

        lines = file.readlines()

        # Iterate each line
        for line in lines:
            # Regex applied to each line 
            
            """
                Android specific 
            """
            ## Displayed
            if re.search("ActivityManager(.*)Displayed(.*).MainActivity", line):
                if "(total" not in line:
                    device['displayed'] = timestamp_to_ms(line.split(".MainActivity: +")[1])
                else:
                    device['displayed'] = timestamp_to_ms(line.split(".MainActivity: +")[1].split("(total")[0])
                    device['displayed_plus_total'] = timestamp_to_ms(line.split(".MainActivity:")[1].split("(total")[1])    
                device['app_name']  = line.split("Displayed ")[1].split("/.MainActivity")[0]

            # Displayed BackdropActivity /!\ Must be else if of previous case 
            elif re.search("ActivityManager(.*)Displayed", line):
                activity = line.split("/.")[1].split(":")[0]
                if "(total" not in line:
                    device[activity] = timestamp_to_ms(line.split("/.")[1].split(":")[1])
                else:
                    device[activity] = timestamp_to_ms(line.split("/.")[1].split(":")[1].split("(total")[0])
                    device[activity+'_plus_total'] = timestamp_to_ms(line.split("/.")[1].split(":")[1].split("(total")[1])
            
            # Fully Drawn 
            if re.search("Fully drawn", line):          
                device['fully_drawn'] = timestamp_to_ms(line.split("Fully drawn")[1].split(":")[1])               

            """
                Cordova specific 
            """
            # CordovaWebView Started (A)
            if re.search("Apache Cordova native platform", line):
                device['cordova_start_tmp'] = float(line.split(":")[2])             

            # CordovaWebView Loaded (B): Calculate diff from started untill loaded == B - A 
            if re.search("CordovaWebView is running on device made by", line):
                device['cordova_loadtime'] = float(line.split(":")[2]) - int(device['cordova_start_tmp'])    
                    
            # Ionic Native: deviceready
            if re.search("Ionic Native: deviceready", line):
                device['deviceready'] = int(line.split("deviceready event fired after")[1].split("ms")[0])       
                
            # Ionic Loaded 
            if re.search("ionic loaded:", line):
                device['timer_ionic'] = int(line.split(":")[1].split("ms")[0])              
                
            # Cordova device 
            if re.search("device: Device", line):
                attributes = line.split('{')[1].split(',')
                # Add from current format=device: Device {cordova:7.0.0,manufacturer:Google,model:Android SDK built for x86,platform:Android,serial:EMULATOR28X0X23X0,version:8.1.0
                for item in attributes:
                    device[item.split(':')[0]] = item.split(':')[1]

            """
                Specific to Boende Appen 
            """
            # checkBackendVersionIsActive
            if re.search("checkBackendVersionIsActive", line):
                device['timer_backend'] = int(line.split(":")[1].split("ms")[0])  

            # storage.get('loginToken')
            if re.search("get('loginToken')", line):
                device['timer_storage'] = int(line.split(":")[1].split("ms")[0])  

            # loginService.login()->browser.on('loadstop')
            if re.search("loginService.login()->browser.on('loadstop'):", line):
                device['timer_loginservice'] = int(line.split(":")[1].split("ms")[0])  


    print(device)
    return device


if __name__ == "__main__":
    increment = 0
    search_filepath(args.path, 'logcat')