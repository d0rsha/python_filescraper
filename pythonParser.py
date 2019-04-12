#!/usr/bin/python
import sys
import os
import re
import argparse
import logging
import traceback
import csv

"""
Arguments to program
"""

parser = argparse.ArgumentParser()
parser.add_argument("path")
args = parser.parse_args()

global tests 
tests= []

def timestamp_to_ms(stamp):
    """
    Convert a timestamp on the following format: XXhXXmXXsXXXms to ms 

    ----------
    @param stamp : str              - Timestamp on format [XX]h[XX]m[XX]s[XXX]ms
    """
    stamp = re.sub('[+()\n total]', '', stamp)
    time = 0
    integers = re.split('[h,m,s,ms\n,ms,]', stamp)
    units = re.split('[\d]+', stamp)
    integers = [x for x in integers if x and not x == ' ']
    units = [x for x in units if x and not x == ' ']
    # print('[INFO:CONSOLE] line=', 'integers', integers)
    # print('[INFO:CONSOLE] line=', 'units   ', units)

    if (len(integers) != len(units)):
        raise ValueError('# integers does not match # units')
    index = 0
    for integer in integers:
        if units[index] == 'ms':
            time += int(integer)
        elif units[index] == 's':
            time += (int(integer) * 1000) 
        elif units[index] == 'm':
            time += (int(integer) * 1000 * 60)
        index += 1

    # print('[INFO:CONSOLE] line=', 'time==', time)
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
            # print(filename)
            if filename.lower() == match:
                #global tests
                dic = parse_file(os.path.join(root, filename))
                tests.insert(1, dic)
    return 

def parse_line(line, device):
    # Regex applied to each line 
    
    if "ActivityManager" in line:
        """
            Android specific 
        """
        ## Displayed
        if re.search("ActivityManager(.*)Displayed(.*)\.MainActivity", line):
            if "(total" not in line:
                device['displayed'] = timestamp_to_ms(line.split("MainActivity: +")[1])
                device['displayed2'] = (line.split("MainActivity: +")[1])
            else:
                device['displayed'] = timestamp_to_ms(line.split("MainActivity: +")[1].split("total")[0])
                device['displayed2'] = (line.split("MainActivity: +")[1].split("(total")[0])
                device['displayed_plus_total'] = timestamp_to_ms(line.split(".MainActivity:")[1].split("total")[1])    
            device['app_name']  = line.split("Displayed ")[1].split("/.MainActivity")[0]
        # Displayed BackdropActivity /!\ Must be else if of previous case 
        """ elif re.search("ActivityManager(.*)Displayed", line):
            activity = line.split(".")[-1].split(":")[0]
            if "(total" not in line:
                device[activity] = timestamp_to_ms(line.split(".")[-1].split(":")[1])
            else:
                device[activity] = timestamp_to_ms(line.split(".")[-1].split(":")[1].split("total")[0])
                device[activity+'_plus_total'] = timestamp_to_ms(line.split(".")[-1].split(":")[1].split("total")[1])
         """
        # Fully Drawn 
        if re.search("Fully drawn", line):          
            device['fully_drawn'] = timestamp_to_ms(line.split("Fully drawn")[1].split(":")[1])
            print(device['fully_drawn'])

    # Package installed 
    if re.search("I\/Pm\([0-9]+\)(.*)Package(.*)installed", line) and "android" not in line:          
        device['install_time'] = timestamp_to_ms(line.split("installed in")[1]) 
            
    if "Cordova" in line:
        """
            Cordova specific 
        """
        # CordovaWebView Started (A)
        if re.search("Apache Cordova native platform", line):
            device['cordova_start'] = float(line.split(":")[2])             
            
        # CordovaWebView Loaded (B): Calculate diff from started untill loaded == B - A 
        if re.search("CordovaWebView is running on device made by", line):
            device['cordova_loaded'] = float(line.split(":")[2])    
            device['my_deviceready_timing'] =  1000*(device['cordova_loaded'] - device['cordova_start'])

    if "INFO:CONSOLE" in line:
        # Ionic Native: deviceready
        if re.search("Ionic Native: deviceready", line):
            device['deviceready'] = line.split("deviceready event fired after")[1].split("ms")[0]       
            
        # Ionic Loaded 
        if re.search("ionic loaded:", line):
            device['timer_ionic'] = line.split(":")[1].split("ms")[0].split('.')[0]     
            
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
            if not 'timer_backend' in device:
                device['timer_backend'] = int(line.split("checkBackendVersionIsActive:")[1].split("ms")[0].split(".")[0])
                device['timer_backend_count'] = 1
            else:
                device['timer_backend_count'] += 1
        # storage.get('loginToken')
        if re.search("get\('loginToken'\)", line):
            if not 'timer_storage' in device:
                device['timer_storage'] = int(line.split("storage.get('loginToken'):")[1].split("ms")[0].split(".")[0])
                device['timer_storage_count'] = 1
            else:
                device['timer_storage_count'] += 1
        # loginService.login()->browser.on('loadstop')
        if re.search("loginService.login", line):
            if not 'timer_loginservice' in device:
                device['timer_loginservice'] = int(line.split("->browser.on('loadstop'):")[1].split("ms")[0].split(".")[0])
                device['timer_loginservice_count'] = 1
            else:
                device['timer_loginservice_count'] += 1
    return device

def parse_file(filepath):
    """
    Parse file at filepath

    ----------
    @param filepath : str  
    ----------
    returns device dictionary
    """
    linenumber = 0
    device = dict()
    #print('Search in ', filepath)
    # Python uses a lookahead buffer internally thus faster reading line by line 
    
    # do stuff here
    try:

        bufsize = 65536
        with open(filepath, 'r') as file: 
            while True:
                lines = file.readlines(bufsize)
                if not lines:
                    break
                for line in lines:
                    device = parse_line(line, device)
                    linenumber += 1

    except Exception as e:
        print(line)
        print(e)
        traceback.print_exc()
    
    #print(device)
    return device


if __name__ == "__main__":
    search_filepath(args.path, 'logcat')
    #global tests
    print(tests)
    """ with open('test.csv', 'w') as f:
        for key in tests.keys():
            f.write("%s,%s\n"%(key,tests[key])) """



     # All exisisting keys in dict
    csv_columns = ['unique','app_name', 'serial', 'manufacturer', 'platform', 'version', 'cordova',              'model','deviceready', 'my_deviceready_timing','timer_ionic','displayed','displayed2',          'fully_drawn','install_time',                                'timer_backend',                        'timer_storage',                    'timer_loginservice']
    #csv_columns = ['app_name', 'serial', 'manufacturer', 'platform', 'version', 'cordova', ' source', 'model','deviceready','timer_ionic','displayed','displayed_plus_total','fully_drawn','install_time','cordova_start','cordova_loaded','timer_backend','timer_backend_count','timer_storage','timer_storage_count','timer_loginservice','timer_loginservice_count','cordova_timing']
    
    dict_data = tests

    with open('test.csv', 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
        writer.writeheader()

        unique_key = 0
        for data_row in dict_data:

            # The names of the fields you want to check
            fields = csv_columns
            # Create a new dict to remove unecciscary fields from data_row
            insert = {}

            # Check the values, within this row, for each of the fields listed 
            for field_name in fields:
                try:
                    field_value = str(data_row[field_name]).strip()
                except KeyError: # Catch KeyError exception, thus field_value never undefined 
                    field_value = ''
                insert[field_name] = field_value

            insert['unique'] = unique_key
            unique_key += 1
            writer.writerow(insert)
