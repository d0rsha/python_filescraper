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
            if re.search("Displayed", line):
                device['displayed'] = line.split(".MainActivity: +")[1].split("ms")[0]
                device['app_name']  = line.split("Displayed ")[1].split("/.MainActivity")[0]

            # Fully Drawn 
            if re.search("Fully drawn", line):
                device['fully_drawn'] = line.split(".MainActivity: +")[1].split("ms")[0]               


            """
                Cordova specific 
            """
            # CordovaWebView Started 
            if re.search("Apache Cordova native platform", line):
                device['cordova_started'] = line.split("\d\d-\d\d \d\d:\d\d:")[1].split(":")[0]               

            # CordovaWebView Loaded
            if re.search("CordovaWebView is running on device made by", line):
                device['Fully drawn'] = line.split("\d\d-\d\d \d\d:\d\d:")[1].split(":")[0]              
                    
            # Ionic Native: deviceready

            # Ionic Loaded 

            # Cordova device 
            if re.search("device: Device", line):
                tmp = line.split('{')[1].split(',')
                # Add from current format=device: Device {cordova:7.0.0,manufacturer:Google,model:Android SDK built for x86,platform:Android,serial:EMULATOR28X0X23X0,version:8.1.0
                for items in tmp:
                    device[item.split(':')[0]] = item.split(':')[1]

            """
                Specific to Boende Appen 
            """
            # checkBackendVersionIsActive

            # storage.get('loginToken')

            # loginService.login()->browser.on('loadstop')



    print(device)
    return device


if __name__ == "__main__":
    increment = 0
    search_filepath(args.path, 'logcat')