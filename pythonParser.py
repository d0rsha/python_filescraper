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
global fail_count_fatal_error
fail_count_fatal_error = {}
global fail_count_deviceready
fail_count_deviceready = {}
global fail_count_plugin
fail_count_plugin = {}


def clean(dirty_string):
    """
        Clean string from wierd signs & chars given by regEx
    """
    return re.sub('[+()\n\" ]', '', dirty_string)



def timestamp_to_ms(stamp):
    """
    Helper function
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

    return time



def parse_timestamp(searchName, attribute, regPattern, line, dev):
    """
        Helper function
    """
    if re.search(regPattern, line):
        if "(total" not in line:
            dev[attribute] = timestamp_to_ms(line.split("MainActivity: +")[1])
        else:
            dev[attribute] = timestamp_to_ms(line.split("MainActivity: +")[1].split("total")[0])
            dev[attribute + '_plus_total'] = timestamp_to_ms(line.split(".MainActivity:")[1].split("total")[1])    
        dev['app_name']  = line.split(searchName)[1].split("/.MainActivity")[0]



def clean_str(dirty_string):
    """
        Helper function
        Clean string from wierd signs & chars given by regEx
    """
    return re.sub('[+()\n\" ]', '', dirty_string)



def inc_error_count(dict_obj, data_row):
    """
        Help function for recording errors
        @ dict_object Error counting object 
    """
    if 'app_name' in data_row:
        if data_row['app_name'].ljust(20) in dict_obj:
            dict_obj[data_row['app_name'].ljust(20)] += 1
        else:  
            dict_obj[data_row['app_name'].ljust(20)] = 1
    else:
        if ''.ljust(20) in dict_obj:
            dict_obj[''.ljust(20)] += 1
        else:
            dict_obj[''.ljust(20)] = 1
    return



def count_errors(data_row):
    """
        Helper function
        Count different type of errors 
    """
    inc_error_count(fail_count, data_row)
    if "fatal_exception" in data_row:
        inc_error_count(fail_count_fatal_error, data_row)
    elif not "plugin_loaded" in data_row:
        inc_error_count(fail_count_plugin, data_row)
    elif "deviceready_error" in data_row:
        inc_error_count(fail_count_deviceready, data_row)

    return



def search_filepath(root_path, match):
    """
    Open all files which have a given name within root_path.
    Searches subdirectories.

    ----------
    @param root_path : str          - not case sensitive
    @param match : str              - name of files to match 
    """
    filenumber = 0
    for root, dirs, files in os.walk(root_path):
        for filename in files:
            # print(filename)
            if filename.lower() == match:
                #global tests
                dic = parse_file(os.path.join(root, filename))
                tests.insert(1, dic)

                filenumber += 1
                print ("File: " + str(filenumber).ljust(3) + " " + root + "/" + filename)
    return 



def parse_line(line, device):
    """
        Android specific 
    """
    #
    # Displayed, Fully drawn && app_name
    #
    if "ActivityManager" in line:
        if "Displayed" in line:
            parse_timestamp('Displayed ', 'displayed', "ActivityManager(.*)Displayed(.*)\.MainActivity", line, device)
        elif "Fully drawn":
            parse_timestamp('Fully drawn ', 'fully_drawn', "ActivityManager(.*)Fully drawn(.*)\.MainActivity", line, device)

    #
    #    Device 
    #
    elif "device: Device" in line:
        if not "evaluateJavascript" in line:
            if re.search("device: Device", line):
                device['plugin_loaded'] = True
                attributes = line.split('{')[1].split(',')
                # Add from current format=device: Device {cordova:7.0.0,manufacturer:Google,model:Android SDK built for x86,platform:Android,serial:EMULATOR28X0X23X0,version:8.1.0
                for item in attributes:
                    if clean_str(item) and item.split(':'):
                        device[ clean_str(item.split(':')[0]) ] = item.split(':')[1]
   
    elif "Cordova" in line:
        """
            Cordova specific 
        """
        # CordovaWebView Started (A)
        if re.search("Apache Cordova native platform", line):
            # device['cordova_start'] = float(line.split(":")[2])    
            device['cordova_version'] = clean_str( line.split('platform version')[1].split('is')[0] )
            
    #
    #   Deviceready event
    #
    elif "deviceready" in line:
        # Ionic Native: deviceready
        if re.search("Ionic Native: deviceready event fired after", line):
            device['deviceready'] = line.split("deviceready event fired after")[1].split("ms")[0]       
        
        # Ionic Native: Problem 
        elif re.search("Ionic Native: deviceready did not fire within", line):
            device['deviceready_error'] = "true"         
        # Ionic Native: Problem 
        elif re.search("deviceready has not fired after 5 seconds", line):
            device['deviceready_error'] = "true"  
            
    
    #
    #    Specific Chrome console output !WARNING! ( NOT ALWAYS IN LOG OUTPUT )
    #
    elif "INFO:" in line:
        # Cordova device Memory
        if re.search("device: MemoryUsage", line):
            attributes = line.split('{')[1].split(',')
            # Add from current format=device: MemoryUsage {cordova:7.0.0,manufacturer:Google,model:Android SDK built for x86,platform:Android,serial:EMULATOR28X0X23X0,version:8.1.0
            for item in attributes:
                device[ clean_str( item.split(':')[0] ) ] = clean_str( item.split(':')[1].split(".")[0] )
        
        # Cordova device Memory
        elif re.search("device: BrowserTiming", line):
            attributes = line.split('{')[1].split(',')
            # Add from current format=device: MemoryUsage {cordova:7.0.0,manufacturer:Google,model:Android SDK built for x86,platform:Android,serial:EMULATOR28X0X23X0,version:8.1.0
            for item in attributes:
                device[ clean_str( item.split(':')[0] ) ] = clean_str( item.split(':')[1].split(".")[0] )
       
    elif "FATAL EXCEPTION" in line:
        device['fatal_exception'] = True

    elif "UPDATE_DEVICE_STATS" in line and 'fatal_exception' in device:
        device['API19'] = True
    
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
                        print('_________/!\\ Probbly error Parsing line /!\\_________')
                        print(e)
                        traceback.print_exc()

            if filepath[-1] == '/':
                device['filepath'] = filepath # args.path
            else: 
                device['filepath'] = filepath + '/'
                
            if not 'app_name' in device:
                artifact_path = args.path + device['filepath'].split('logcat')[0] + 'artifacts/accessibility1.meta'
                with open(artifact_path, 'rb') as file: 
                    lines = file.read().decode(errors='replace')
                    
                    lines = lines.split('\n')
                    for line in lines:
                        try:
                            #process_print(line)
                            if 'android.blankapp' in line:
                                device['app_name'] = 'android.blankapp'
                                break
                            elif 'com.avrethem.plugins' in line:
                                device['app_name'] = 'com-avrethem.plugins'
                                break
                            elif 'minimal' in line:
                                device['app_name'] = 'minimal'
                                break
                            elif 'plugins.xwalk' in line:
                                device['app_name'] = 'plugins.xwalk'
                                break
                            elif 'appen2.xwalk' in line:
                                device['app_name'] = 'appen2.xwalk'
                                break
                            elif 'boende.xwalk' in line:
                                device['app_name'] = 'boende.xwalk'
                                break

                        except Exception as e:
                            print('_________/!\\ Probbly error Parsing line /!\\_________')
                            print(e)
                            traceback.print_exc()

    except Exception as e:
        print('_________/!\\ Probbly error Opening file /!\\_________')
        print(e)
        traceback.print_exc()
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
    csv_columns = [
                    'unique','isVirtual', 'approach','app_name', 'serial','uuid', 
                    'model',   'manufacturer', 'platform',
                    'version', 'sdk-version',  'cordova', 
                    'displayed' , 'deviceready', 'fully_drawn', 'install_time',
                    '1displayed','2deviceready','3fully_drawn', 'total_time',
                    # 'backdrop_displayed', 'deviceready_error',
                    # Specific to BoendeAppen
                    # 'timer_backend','timer_backend_count','timer_storage','timer_storage_count',
                    # 'timer_loginservice','timer_loginservice_count',
                    '3fully_splitted', '4login_time', '5backend_time', 'error'
                  ] 
    print_columns = [ 'app_name','displayed','2deviceready','fully_drawn', 'model', 'manufacturer', 'sdk-version']

    
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
        fail_count_fatal_error[''.ljust(20)] = 0
        
         #
        # Create a new Dict with the columns from csv_columns and create csv file from new Dict
        #
        csv_dict = {}


        for data_row in dict_data:
            try:

                 #    Rename / Give app nickname
                data_row['app_name'] = re.sub('exjobb.', '', data_row['app_name'])
                data_row['app_name'] = re.sub('exjob.', '', data_row['app_name'])
                data_row['app_name'] = re.sub('.blankapp', '', data_row['app_name'])
                data_row['app_name'] = re.sub('com.example.androidblank', 'android', data_row['app_name'])

                data_row['app_name'] = re.sub('com.avrethem.', '', data_row['app_name'])
                data_row['app_name'] = re.sub('com.ionicframework.', '', data_row['app_name'])
                data_row['app_name'] = re.sub('se.solutionxperts.', '', data_row['app_name'])
                data_row['app_name'] = re.sub('.stangastaden', '', data_row['app_name'])
                #data_row['app_name'] = re.sub('xom.xwalk.browser', 'plugins.xwalk', data_row['app_name'])
                # Skip old tests
                if 'minimal' in data_row['app_name'] or 'xom.xwalk.browser'in data_row['app_name'] or 'boendeapp' in data_row['app_name'] or 'appen2' in data_row['app_name'] or 'conferenc' in data_row['app_name'] or 'dialer' in data_row['app_name']:
                   continue

                if 'API19' in data_row:
                    continue


                #
                #    Fix 'deltider' : 1displayed, 2deviceready, 3fully_drawn, 4login_time, 5backend_time  
                #
                data_row['1displayed'] = data_row['displayed']
                if 'deviceready' in data_row:
                    data_row['2deviceready'] = data_row['deviceready']
                    data_row['deviceready'] = int(data_row['displayed']) + int(data_row['deviceready'])

                if "android" not in data_row["app_name"]:
                    data_row['3fully_drawn'] = data_row['fully_drawn'] - data_row['deviceready']
                
                    if '4login_time' in data_row:
                        ## 3fully splitted before 
                        data_row['3fully_splitted'] = int(data_row['3fully_drawn']) - int(data_row['4login_time'])
                        if '5backend_time' in data_row:
                            ## 4login-time
                            data_row['4login_time'] = int(data_row['4login_time']) - int(data_row['5backend_time'])
                            ## 5backend-time
                            data_row['5backend_time'] = int(data_row['5backend_time'])
                        else:
                            data_row['5backend_time'] = 0
                    else:
                        data_row['3fully_splitted'] = int(data_row['3fully_drawn'])
                        data_row['4login_time'] = 0 
                        data_row['5backend_time'] = 0

                #
                #    Interpolate app_name; sdk-version; approach
                #
                if 'cordova_version' in data_row:
                    data_row['cordova'] = data_row['cordova_version']

                #    Add API-level for Android-rows that are mssing sdk-version
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
                
                #   Remove tests with API 18 && 19 
                if '18' in data_row['sdk-version'] or '19' in data_row['sdk-version']:
                    raise KeyError('API 18/19')

                #   Add approach to old result that are missing those outputs to log
                if not 'approach' in data_row:
                    if 'cordova' in data_row:
                        data_row['approach'] = 'hybrid'
                    else:
                        data_row['approach'] = 'native'

                #   Add 'fatal_exception' flag to failed tests 
                if "fatal_exception" in data_row:
                    raise KeyError('fatal')
                #   Add plugin check 
                elif not "plugin_loaded" in data_row:
                    raise KeyError('plugin')
                    #   Add 'fatal_exception' flag to failed tests 
                elif "deviceready_error" in data_row:
                    raise KeyError('devRdy_err')

               

                total_time = 0
                for field_name in csv_columns:
                    try:
                        field_value = clean_str( str(data_row[field_name]) )
                        if '1displayed' == field_name or '2deviceready' == field_name or '3fully_drawn' == field_name:
                            total_time += int(data_row[field_name])
                    except KeyError: # KeyError when field_name does not exists 
                        field_value = ''

                    csv_dict[field_name] = field_value

                csv_dict['total_time'] = total_time


                #
                # Check if counted correctly in csv_dict
                #
                check_columns = ['1displayed', '2deviceready', '3fully_splitted', '4login_time', '5backend_time']
                for field_name in check_columns:
                    if csv_dict[field_name] == '':
                        csv_dict[field_name] = 0
                sum = (int(csv_dict['1displayed']) + int(csv_dict['2deviceready']) + int(csv_dict['3fully_splitted']) + int(csv_dict['4login_time']) + int(csv_dict['5backend_time']))
                if (int(csv_dict['total_time']) != sum ):
                    print('Failed sum for ', csv_dict['app_name'], '|   tot=', csv_dict['total_time'],'    sum=', sum)

                csv_dict['unique'] = unique_key
                unique_key += 1
                writer.writerow(csv_dict)

                #   Count 
                if data_row['app_name'].ljust(20) in count:
                    count[data_row['app_name'].ljust(20)] += 1
                else:  
                    count[data_row['app_name'].ljust(20)] = 1

            except KeyError as exception:
                t1 = 'KeyError: ' + str(exception).ljust(13) 
                tmp = str(unique_key + row_errors).rjust(3) + ": "
                for field_name in print_columns:
                    try:
                        COL_SIZE = int(len(field_name))
                        if field_name == 'app_name' or field_name == 'model' or field_name == 'manufacturer':
                            tmp += str(clean_str( str(data_row[field_name][-COL_SIZE:]) )).ljust(COL_SIZE) + ", "
                        else:
                            tmp += str(clean_str( str(data_row[field_name]) )).ljust(COL_SIZE) + ", "                            
                    except (KeyError, IndexError, TypeError) as e: # KeyError when field_name does not exists 
                        tmp += "''".ljust(COL_SIZE) + ", "

                tmp += t1
                error = ''
                if "fatal_exception" in data_row:
                    error += " FATAL EXCEPT"
                elif not "plugin_loaded" in data_row:
                    error += " PLUGIN ERROR"
                elif "deviceready_error" in data_row:
                    error += " CORDOV ERROR"
                else:
                    error += "             "
                data_row['error'] = error
                tmp += error
                tmp += ' ' + data_row['filepath']
                print(tmp)

                count_errors(data_row)
                row_errors += 1

                total_time = 0
                for field_name in csv_columns:
                    try:
                        field_value = clean_str( str(data_row[field_name]) )
                        if '1displayed' == field_name or '2deviceready' == field_name or '3fully_drawn' == field_name:
                            total_time += int(data_row[field_name])
                    except KeyError: # KeyError when field_name does not exists 
                        field_value = ''

                    csv_dict[field_name] = field_value

                csv_dict['unique'] = unique_key
                unique_key += 1
                writer.writerow(csv_dict)

            except Exception as e:
                print(e)
                traceback.print_exc()

#
# Display result
#
    print(str(row_errors) + " rows removed of " + str(unique_key + row_errors) + " in total" )
    print('____________________________')
    print('__# accepted rows per app___')
    print('____________________________')
    pprint.pprint(count)
    print('              of total : ' + str(unique_key))
    print('----------------------------')

    print('____________________________|')
    print('___# erased rows per app____|')
    print('____________________________|')
    pprint.pprint(fail_count)
    print('           of total : ', row_errors,'|')
    print('                            |')
    print(' of which is FATAL ERRORS   |')
    pprint.pprint(fail_count_fatal_error)
    print('                            |')
    print(' of which is PLUGIN ERR     |')
    pprint.pprint(fail_count_plugin)
    print('                            |')
    print(' of which is CORDOVA ERR    |')
    pprint.pprint(fail_count_deviceready)
    print('----------------------------|')
    print('----------------------------|')