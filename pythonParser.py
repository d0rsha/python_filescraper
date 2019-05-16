#!/usr/bin/python
import sys
import os
import re
import argparse
import logging
import traceback
import csv

#
#   Arguments and global variable 
#
parser = argparse.ArgumentParser()
parser.add_argument("path")
args = parser.parse_args()

global tests 
tests= []
global count 
count = {}
global fail_count
fail_count = {}

def clean(dirty_string):
    """
        Clean string from wierd signs & chars given by regEx
    """
    return re.sub('[+()\n\" ]', '', dirty_string)

def timestamp_to_ms(stamp):
    """
    Convert a timestamp on the following format: XXhXXmXXsXXXms to ms 

    ----------
    @param stamp : str              - Timestamp on format [XX]h[XX]m[XX]s[XXX]ms
    ----------
    returns 
        time in milliseconds (ms)
    """
    stamp = re.sub('[+()\n\" total]', '', stamp)
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
    
    """
        Android specific 
    """
    if "vityMana" in line:
        ## Displayed
        if re.search("ActivityManager(.*)Displayed(.*)\.MainActivity", line):
            if "(total" not in line:
                device['displayed'] = timestamp_to_ms(line.split("MainActivity: +")[1])
            else:
                device['displayed'] = timestamp_to_ms(line.split("MainActivity: +")[1].split("total")[0])
                device['displayed_plus_total'] = timestamp_to_ms(line.split(".MainActivity:")[1].split("total")[1])    
            device['app_name']  = line.split("Displayed ")[1].split("/.MainActivity")[0]
        # Displayed BackdropActivity /!\ Must be else if of previous case 
        elif re.search("ActivityManager(.*)Displayed(.*)\.BackdropActivity", line):
            #activity = line.split(".")[-1].split(":")[0]
            if 'app_name' in device:
                if device['app_name'] in line:
                    if "(total" not in line:
                        device['backdrop_displayed'] = timestamp_to_ms(line.split("BackdropActivity: +")[1])
                    else:
                        device['backdrop_displayed'] = timestamp_to_ms(line.split("BackdropActivity: +")[1].split("total")[0])
        
        # Fully Drawn 
        if re.search("Fully drawn", line):          
            device['fully_drawn'] = timestamp_to_ms(line.split("Fully drawn")[1].split(":")[1])

    """
        Device 
    """
    if "device:" in line:
        if re.search("device: Device", line):
            attributes = line.split('{')[1].split(',')
            # Add from current format=device: Device {cordova:7.0.0,manufacturer:Google,model:Android SDK built for x86,platform:Android,serial:EMULATOR28X0X23X0,version:8.1.0
            for item in attributes:
                if clean(item) and item.split(':'):
                    device[ clean(item.split(':')[0]) ] = item.split(':')[1]

    
    # Package installed 
    if "Package" in line:
        if re.search("I\/Pm\([0-9]+\)(.*)Package(.*)installed", line) and "android" not in line:          
            device['install_time'] = timestamp_to_ms(line.split("installed in")[1]) 
            
    if "Cordova" in line:
        """
            Cordova specific 
        """
        # CordovaWebView Started (A)
        if re.search("Apache Cordova native platform", line):
            device['cordova_start'] = float(line.split(":")[2])    
            device['cordova_version'] = clean( line.split('platform version')[1].split('is')[0] )
            
        # CordovaWebView Loaded (B): Calculate diff from started untill loaded == B - A 
        if re.search("CordovaWebView is running on device made by", line):
            device['cordova_loaded'] = float(line.split(":")[2])    
            device['my_deviceready_timing'] =  int( 1000*(device['cordova_loaded'] - device['cordova_start']) )
            del device['cordova_loaded']
            del device['cordova_start']

    """
        Specific Chrome console output 
    """
    if "INFO:" in line:
        # Ionic Native: deviceready
        if re.search("Ionic Native: deviceready event fired after", line):
            device['deviceready'] = line.split("deviceready event fired after")[1].split("ms")[0]       
        
        # Ionic Native: Problem 
        if re.search("Ionic Native: deviceready did not fire within", line):
            device['deviceready_error'] = "true"       

        # Ionic Loaded 
        if re.search("ionic loaded:", line):
            device['timer_ionic'] = line.split(":")[1].split("ms")[0].split('.')[0]     

        # Cordova device Memory
        if re.search("device: MemoryUsage", line):
            attributes = line.split('{')[1].split(',')
            # Add from current format=device: MemoryUsage {cordova:7.0.0,manufacturer:Google,model:Android SDK built for x86,platform:Android,serial:EMULATOR28X0X23X0,version:8.1.0
            for item in attributes:
                device[ clean( item.split(':')[0] ) ] = clean( item.split(':')[1].split(".")[0] )
        
        # Cordova device Memory
        if re.search("device: BrowserTiming", line):
            attributes = line.split('{')[1].split(',')
            # Add from current format=device: MemoryUsage {cordova:7.0.0,manufacturer:Google,model:Android SDK built for x86,platform:Android,serial:EMULATOR28X0X23X0,version:8.1.0
            for item in attributes:
                device[ clean( item.split(':')[0] ) ] = clean( item.split(':')[1].split(".")[0] )


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
    Parse file at filepath, line by line 

    ----------
    @param filepath : str  
    ----------
    returns device dictionary
    """
    linenumber = 0
    device = dict()
    
    bufsize = 65536
    try:
        with open(filepath, 'r') as file: 
            while True:
                    lines = file.readlines(bufsize)
                    if not lines:
                        break
                    for line in lines:
                        try:
                            device = parse_line(line, device)
                            linenumber += 1
                        except Exception as e:
                            print("_________/!\\ Line Error /!\\_________")
                            print(line)
                            print(e)
                            traceback.print_exc()
    except Exception as e:
        print('_________/!\\ Probbly error Opening file /!\\_________')
        print(e)
        traceback.print_exc()
    #print(device)
    return device

"""
    Main program

    calls search_filepath, result added to global variable 'tests'
    creates csv file with headers according to csv_columns 
"""
if __name__ == "__main__":
    search_filepath(args.path, 'logcat')

    import pprint
    # pprint.pprint(tests)
    print("---------------")

    # Headers to create in CSV file 
    csv_columns = ['unique','isVirtual', 'approach','app_name', 'serial','uuid', 
                    'model',   'manufacturer', 'platform',
                    'version', 'sdk-version',  'cordova', 
                    'displayed' , 'deviceready', 'fully_drawn', 
                    '1displayed','2deviceready','3fully_drawn',
                    'install_time', 'backdrop_displayed', 'deviceready_error',
                    'version', 'sdk-version', 'total_time',
                    
                    ] 
    # All exisisting keys in dict =
    # ['app_name', 'serial', 'manufacturer', 'platform', 'version', 'cordova_version', ' source', 'model','deviceready','displayed','displayed_plus_total','fully_drawn','install_time','cordova_start','cordova_loaded','timer_backend','timer_backend_count','timer_storage','timer_storage_count','timer_loginservice','timer_loginservice_count','cordova_timing']
    
    tmp = "Parse error, removing row: "
    for field_name in csv_columns:
        COL_SIZE = int(len(field_name))
        tmp += str(clean( str(field_name[-COL_SIZE:]) )).ljust(COL_SIZE) + ", "
    print(tmp)


    dict_data = tests

    with open('test.csv', 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
        writer.writeheader()

        unique_key = 0
        row_errors = 0
        fail_count[''.ljust(20)] = 0
        for data_row in dict_data:

            try:
                #
                #    Remove broken tests
                #
                if not clean( str(data_row['serial']) ) \
                or not clean( str(data_row['app_name']) )\
                or not clean( str(data_row['displayed']) ):
                    raise KeyError('undefined')

                #
                #   Remove test with missing 'Fully Drawn' attribute but not for android 
                #
                if "android" not in data_row["app_name"]:
                    if 'fully_drawn' not in data_row:
                        continue # Skip if app is not android and do not contain fully_drawn

                #
                #    Rename / Give app nickname
                #
                data_row['app_name'] = re.sub('com.avrethem.', '', data_row['app_name'])
                data_row['app_name'] = re.sub('com.ionicframework.', '', data_row['app_name'])
                data_row['app_name'] = re.sub('android.', 'droid', data_row['app_name'])
                data_row['app_name'] = re.sub('app', '', data_row['app_name'])
                data_row['app_name'] = re.sub('se.solutionxperts.', '', data_row['app_name'])
                data_row['app_name'] = re.sub('.stangastaden', '', data_row['app_name'])
                data_row['app_name'] = re.sub('xom.xwalk.browser', 'plugins.xwalk', data_row['app_name'])
                
                
                
                if 'cordova_version' in data_row:
                    data_row['cordova'] = data_row['cordova_version']

                
                # Sort Values by deltider 
                # deviceready is total time until device is ready from start 
                # 2deviceready is time it took for framework to load 
                if 'displayed' in data_row:
                    data_row['1displayed'] = data_row['displayed']
                    if 'deviceready' in data_row:
                        data_row['2deviceready'] = data_row['deviceready']
                        data_row['deviceready'] = int(data_row['displayed']) + int(data_row['deviceready'])
                if 'fully_drawn' in data_row:
                    data_row['3fully_drawn'] = data_row['fully_drawn'] - data_row['deviceready']
                
                #
                #    Interpolate with 99 % confidence: Add API-level for Android-rows that are mssing sdk-version
                #
                if not 'sdk-version' in data_row:
                    if '4.3' in data_row['version']:
                        data_row['sdk-version'] = '18'
                    elif '4.4' in data_row['version']:
                        data_row['sdk-version'] = '19'
                    elif '5.0' in data_row['version']:
                        data_row['sdk-version'] = '21'
                    elif '5.1' in data_row['version']:
                        data_row['sdk-version'] = '22'
                    elif '6.' in data_row['version']:
                        data_row['sdk-version'] = '23'
                    elif '7.1' in data_row['version']:
                        data_row['sdk-version'] = '25'
                    elif '7' in data_row['version']:
                        data_row['sdk-version'] = '24'
                    elif '8.1' in data_row['version']:
                        data_row['sdk-version'] = '27'
                    elif '8' in data_row['version']:
                        data_row['sdk-version'] = '26'
                    elif '9' in data_row['version']:
                        data_row['sdk-version'] = '28'
                    else:
                        data_row['sdk-version'] = 'null'

                #
                #    Interpolate with 100% confidence: Add approach to old tests that are missing those outputs to log
                #
                if not 'approach' in data_row:
                    if 'cordova' in data_row:
                        data_row['approach'] = 'hybrid'
                    else:
                        data_row['approach'] = 'native'

                # 
                #   Count 
                # 
                if data_row['app_name'].ljust(20) in count:
                    count[data_row['app_name'].ljust(20)] += 1
                else:  
                    count[data_row['app_name'].ljust(20)] = 1

            except (KeyError) as e:
                tmp = "Parse error, removing row" + str(row_errors).rjust(3) + ": "
                row_errors += 1
                for field_name in csv_columns:
                    try:
                        COL_SIZE = int(len(field_name))
                        tmp += str(clean( str(data_row[field_name][-COL_SIZE:]) )).ljust(COL_SIZE) + ", "
                    except (KeyError, IndexError, TypeError) as e: # KeyError when field_name does not exists 
                        tmp += "''".ljust(COL_SIZE) + ", "
                print(tmp)

                if 'app_name' in data_row:
                    if data_row['app_name'].ljust(20) in fail_count:
                        fail_count[data_row['app_name'].ljust(20)] += 1
                    else:  
                        fail_count[data_row['app_name'].ljust(20)] = 1
                else:
                    fail_count[''.ljust(20)] += 1
                continue
            

            #
            # Create a new Dict with the columns from csv_columns and create csv file from new Dict
            #
            csv_dict = {}

            total_time = 0
            for field_name in csv_columns:
                try:
                    field_value = clean( str(data_row[field_name]) )

                    """ 
                    >>>> TMP >>>>> 
                    """
                    if '1displayed' == field_name or '2deviceready' == field_name or '3fully_drawn' == field_name:
                        total_time += int(data_row[field_name])
                    """
                    <<<< TMP <<<<< 
                    """

                except KeyError: # KeyError when field_name does not exists 
                    field_value = ''
                csv_dict[field_name] = field_value

            """ >>>> TMP >>>> <<<<< TMP <<<<< """
            csv_dict['total_time'] = total_time
            """ >>>> TMP >>>> <<<<< TMP <<<<< """
            csv_dict['unique'] = unique_key
            unique_key += 1
            writer.writerow(csv_dict)

    print(str(row_errors) + " rows removed of " + str(unique_key + row_errors) + " in total" )
    print('____________________________')
    print('____COUNT___accepted________')
    print('__# accepted rows per app___')
    print('____________________________')
    pprint.pprint(count)
    print('              of total : ' + str(unique_key))
    print('----------------------------')

    print('____________________________')
    print('___COUNT___erased___________')
    print('__# accepted rows per app___')
    print('____________________________')
    pprint.pprint(fail_count)
    print('              of total : ', row_errors)
    print('----------------------------')
