#!/usr/bin/python
import sys
import os
import re
import argparse
import logging
import traceback
import csv
import pprint

### 
### MULTITHREADING
###
import threading
import time

# Threads per process!!
THREADS = 2
globalLock = threading.Lock()
threads = []
filenumber = 0

###
### MULTIPROCESSING
###
import time
from multiprocessing import Pool
from multiprocessing import current_process

PROFFESORS = 20

#
#   Arguments and global variable 
#
parser = argparse.ArgumentParser()
parser.add_argument("path")
args = parser.parse_args()

global tests 
tests= []
global result
result = []
global count 
count = {}
global fail_count
fail_count = {}

"""
    Print <PID> (message)
"""
def process_print(*argv):  
    try:
        if not 'MainProcess' in str(current_process()):
            pid = str(str(current_process()).split("-")[1].split(',')[0])
        else:
            pid = "Main"
        print_me = ''
        for arg in argv:  
            print_me += str(arg)
        print('<', pid.ljust(4), '> ', print_me)
    except Exception as e:
        print(e)
        traceback.print_exc()
        print('<', str(current_process()), '> ', argv)

    
"""
    Creates #THREADS new threads, 
        Threads need synchonization for global variable
"""
def multi_threading_compute(a_list):
    poolsize = int(len(a_list) / THREADS)
    process_print ("||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
    process_print ("|||||||||||||| EACH THREAD SHOULD RUN " + str(poolsize).ljust(3) + " TIMES ||||||||||||||||||||||||||||||||||||||||||||||||||")
    process_print ("|||||||||||||| OF ", str(len(a_list)).ljust(5), " IN TOTAL |||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
    # Create new threads
    # Balance workload
    # Lock in threads 

    for pid in range(THREADS):
        start = pid * poolsize
        end = start + poolsize
        process_print(pid,"[", start, ":",end)
        thread = myThread(pid, "Thread-" + str(pid), a_list[start:end])
        thread.start()
        threads.append(thread)

    # Wait for all threads to complete
    for t in threads:
        t.join()

    return tests
 
"""
    Spawns #PROFFESSOR new processes 
        Finished processes wake up every 0.5 second to recheck 
        Does not need Synchronization: Handled by framework 
            Variables not in same namespace 
"""
def multi_processing_compute(a_list):
    chunks = [a_list[i::PROFFESORS] for i in range(PROFFESORS)] 
    pool = Pool(processes=PROFFESORS)

    # launching multiple evaluations asynchronously *may* use more processes
    multiple_results = [pool.apply_async(multi_threading_compute, [chunks[i]]) for i in range(PROFFESORS)]
    # print ([res.get(timeout=180) for res in multiple_results])
    return [res.get(timeout=720) for res in multiple_results]
    

class myThread (threading.Thread):
    def __init__(self, tid, name, workload):
        threading.Thread.__init__(self)
        self.tid = tid
        self.name = name
        self.workload = workload
        self.local_tests = []
        self.counter = 0

    def run(self):
            process_print ("Starting " + self.name)

            for entry in self.workload:
                dic = parse_file(entry)
                # Get lock to synchronize threads
                self.local_tests.insert(1, dic)
                self.counter += 1
                process_print ("[",str(self.tid).rjust(4),"] File:",str(self.counter).rjust(4),"/",str(len(self.workload)).rjust(4), " -> ", entry)
                # Free lock to release next thread
            
            globalLock.acquire()
            tests.extend(self.local_tests)
            globalLock.release()
#
# END MULTI stuff
#

def findFilesInFolder(path, pathList, extension, subFolders = True):
    """  Recursive function to find all files of an extension type in a folder (and optionally in all subfolders too)

    path:        Base directory to find files
    pathList:    A list that stores all paths
    extension:   File extension to find
    subFolders:  Bool.  If True, find files in all subfolders under path. If False, only searches files in the specified folder
    """

    try:   # Trapping a OSError:  File permissions problem I believe
        for entry in os.scandir(path):
            if entry.is_file() and entry.path.endswith(extension):
                pathList.append(entry.path)
            elif entry.is_dir() and subFolders:   # if its a directory, then repeat process as a nested function
                pathList = findFilesInFolder(entry.path, pathList, extension, subFolders)
    except OSError:
        process_print('Cannot access ' + path +'. Probably a permissions error')

    return pathList


def print_shit(e):
    process_print("\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\//////////////////////////////////////")
    process_print("   \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\///////////////////////////////////   ")
    process_print("       \\\\\\\\\\\\\\\\\\\\\\\\\\\//////////////////////////////        ")
    process_print("               \\\\\\\\\\\\\\\\\\\\//////////////////////               ")
    process_print("                       \\\\\\\\\\\\/////////////                        ")
    process_print("                              \\\\///////                               ")
    process_print("                            login_time Error                            ")
    process_print(e)
    process_print("||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||||")
    traceback.print_exc()
    process_print("                              \\\\///////                               ")
    process_print("                       \\\\\\\\\\\\/////////////                        ")
    process_print("               \\\\\\\\\\\\\\\\\\\\//////////////////////               ")
    process_print("       \\\\\\\\\\\\\\\\\\\\\\\\\\\//////////////////////////////        ")
    process_print("   \\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\///////////////////////////////////   ")
    process_print("\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\\//////////////////////////////////////")

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
    # process_print('[INFO:CONSOLE] line=', 'integers', integers)
    # process_print('[INFO:CONSOLE] line=', 'units   ', units)

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

    # process_print('[INFO:CONSOLE] line=', 'time==', time)
    return time

def search_filepath(root_path, match):
    """
    Open all files which have a given name within root_path.
    Searches subdirectories.

    ----------
    @param root_path : str          - not case sensitive
    @param match : str              - name of files to match 
    """
    pathList = []
    pathList = findFilesInFolder(root_path, pathList, 'logcat', True)

    result = multi_processing_compute(pathList)
    return result

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
                        process_print("_________/!\\ Line Error /!\\_________")
                        process_print(line)
                        process_print(e)
                        traceback.print_exc()

                
    except Exception as e:
        process_print('_________/!\\ Probbly error Opening file /!\\_________')
        process_print(e)
        traceback.print_exc()
    #process_print(device)
    return device

def parse_line(line, device):
    
    """
        Android specific 
    """
    if "vityMana" in line:
        if "Displayed" in line:
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
        elif re.search("Fully drawn", line):
            if "(total" not in line:          
                device['fully_drawn'] = timestamp_to_ms(line.split("Fully drawn")[1].split(":")[1])
            else:
                device['fully_drawn'] = timestamp_to_ms(line.split("MainActivity: +")[1].split("total")[0])
                device['fully_drawn_plus_total'] = timestamp_to_ms(line.split(".MainActivity:")[1].split("total")[1])
                

    #
    #    Device 
    #
    elif "device:" in line:
        if not "evaluateJavascript" in line:
            if re.search("device: Device", line):
                attributes = line.split('{')[1].split(',')
                # Add from current format=device: Device {cordova:7.0.0,manufacturer:Google,model:Android SDK built for x86,platform:Android,serial:EMULATOR28X0X23X0,version:8.1.0
                for item in attributes:
                    if clean(item) and item.split(':'):
                        device[ clean(item.split(':')[0]) ] = item.split(':')[1]

    
    # Package installed 
    #if "Package" in line:
     #   if re.search("I\/Pm\([0-9]+\)(.*)Package(.*)installed", line) and "android" not in line:          
      #      device['install_time'] = timestamp_to_ms(line.split("installed in")[1]) 
            
    elif "Cordova" in line:
        """
            Cordova specific 
        """
        # CordovaWebView Started (A)
        if re.search("Apache Cordova native platform", line):
            # device['cordova_start'] = float(line.split(":")[2])    
            device['cordova_version'] = clean( line.split('platform version')[1].split('is')[0] )
            
        # CordovaWebView Loaded (B): Calculate diff from started untill loaded == B - A 
        #elif re.search("CordovaWebView is running on device made by", line):
         #   device['cordova_loaded'] = float(line.split(":")[2])    
          #  device['my_deviceready_timing'] =  int( 1000*(device['cordova_loaded'] - device['cordova_start']) )
           # del device['cordova_loaded']
            #del device['cordova_start']

    #
    #    Specific Chrome console output 
    #
    elif "INFO:" in line:
        # Ionic Native: deviceready
        if re.search("Ionic Native: deviceready event fired after", line):
            device['deviceready'] = line.split("deviceready event fired after")[1].split("ms")[0]       
        
        # Ionic Native: Problem 
        elif re.search("Ionic Native: deviceready did not fire within", line):
            device['deviceready_error'] = "true"       

        # Ionic Loaded 
        elif re.search("ionic loaded:", line):
            device['timer_ionic'] = line.split(":")[1].split("ms")[0].split('.')[0]     

        # Cordova device Memory
        elif re.search("device: MemoryUsage", line):
            attributes = line.split('{')[1].split(',')
            # Add from current format=device: MemoryUsage {cordova:7.0.0,manufacturer:Google,model:Android SDK built for x86,platform:Android,serial:EMULATOR28X0X23X0,version:8.1.0
            for item in attributes:
                device[ clean( item.split(':')[0] ) ] = clean( item.split(':')[1].split(".")[0] )
        
        # Cordova device Memory
        elif re.search("device: BrowserTiming", line):
            attributes = line.split('{')[1].split(',')
            # Add from current format=device: MemoryUsage {cordova:7.0.0,manufacturer:Google,model:Android SDK built for x86,platform:Android,serial:EMULATOR28X0X23X0,version:8.1.0
            for item in attributes:
                device[ clean( item.split(':')[0] ) ] = clean( item.split(':')[1].split(".")[0] )

        #  login_time
        elif re.search("login_time", line):
            if not "4login_time" in device:
                try:
                    item = line.split("\"")[1]
                    device[ '4login_time' ] = clean( item.split(':')[1].split("ms")[0].split(".")[0] )
                except Exception as e:
                    print_shit(e)
        
        elif re.search("backend_time", line):
            if not "5backend_time" in device:
                try:
                    item = line.split("\"")[1]
                    device[ '5backend_time' ] = clean( item.split(':')[1].split("ms")[0].split(".")[0] )
                except Exception as e:
                    print_shit(e)

    elif "FATAL EXCEPTION" in line:
        device['fatal_error'] = True

    return device


"""
    Main program

    calls search_filepath, result added to global variable 'result'
    creates csv file with headers according to csv_columns 
"""
if __name__ == "__main__":
    dict_data = []
    ave_dict = {}

    res = search_filepath(args.path, 'logcat')
    for bin in res:
        dict_data.extend(bin)


    # pprint.pprint(result)
    print("---------------")
    # print(dict_data)
    print("Length of result == ", len(dict_data))
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
                    '3fully_splitted', '4login_time', '5backend_time'
                  ] 
    # All exisisting keys in dict =
    # ['app_name', 'serial', 'manufacturer', 'platform', 'version', 'cordova_version', ' source', 'model','deviceready','displayed','displayed_plus_total','fully_drawn','install_time','cordova_start','cordova_loaded','timer_backend','timer_backend_count','timer_storage','timer_storage_count','timer_loginservice','timer_loginservice_count','cordova_timing']
    
    print_columns = [ 'app_name','1displayed','2deviceready','3fully_drawn', 'model',   'manufacturer']

    tmp = "Parse error, removing row: "
    for field_name in print_columns:
        COL_SIZE = int(len(field_name))
        tmp += str(clean( str(field_name[-COL_SIZE:]) )).ljust(COL_SIZE) + ", "
    print(tmp)

    
    with open('test.csv', 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
        writer.writeheader()

        unique_key = 0
        row_errors = 0
        fail_count[''.ljust(20)] = 0
        for data_row in dict_data:

            try:
                #
                #    Remove broken result
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
                        raise KeyError('Fully drawn not among input')
                        # Skip if app is not android and do not contain fully_drawn

                #
                #    Rename / Give app nickname
                #
                data_row['app_name'] = re.sub('com.avrethem.', '', data_row['app_name'])
                data_row['app_name'] = re.sub('com.ionicframework.', '', data_row['app_name'])
                # data_row['app_name'] = re.sub('android.', 'droid', data_row['app_name'])
                # data_row['app_name'] = re.sub('app', '', data_row['app_name'])
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
                #    Interpolate with 80 % confidence: Add API-level for Android-rows that are mssing sdk-version
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

                if '18' in data_row['sdk-version'] or '19' in data_row['sdk-version']:
                    break

                #
                #    Interpolate with 100% confidence: Add approach to old result that are missing those outputs to log
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
                tmp = "Parse error, removing row" + str(unique_key + row_errors).rjust(3) + ": "
                for field_name in print_columns:
                    try:
                        COL_SIZE = int(len(field_name))
                        tmp += str(clean( str(data_row[field_name][-COL_SIZE:]) )).ljust(COL_SIZE) + ", "
                    except (KeyError, IndexError, TypeError) as e: # KeyError when field_name does not exists 
                        tmp += "''".ljust(COL_SIZE) + ", "
                print(tmp)
                print(e)
                
                row_errors += 1

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
                    if '1displayed' == field_name or '2deviceready' == field_name or '3fully_drawn' == field_name:
                        total_time += int(data_row[field_name])

                except KeyError: # KeyError when field_name does not exists 
                    field_value = ''

                # If all ok: Add to dict 
                csv_dict[field_name] = field_value

            """ >>>> TMP >>>> <<<<< TMP <<<<< """
            csv_dict['total_time'] = total_time

            if (csv_dict['1displayed'] == ''):
                csv_dict['1displayed'] = 0
            if (csv_dict['2deviceready'] == ''):
                csv_dict['2deviceready'] = 0
            if (csv_dict['3fully_splitted'] == ''):
                csv_dict['3fully_splitted'] = 0
            if (csv_dict['4login_time'] == ''): 
                csv_dict['4login_time'] = 0
            if (csv_dict['5backend_time'] == ''):
                csv_dict['5backend_time'] = 0
            sum = (int(csv_dict['1displayed']) + int(csv_dict['2deviceready']) + int(csv_dict['3fully_splitted']) + int(csv_dict['4login_time']) + int(csv_dict['5backend_time']))
            if (int(csv_dict['total_time']) != sum ):
                print('Failed sum for ', csv_dict['app_name'], '|   tot=', csv_dict['total_time'],'    sum=', sum)

            if csv_dict['app_name'] not in ave_dict:
                ave_dict[csv_dict['app_name']] = total_time
            else:
                ave_dict[csv_dict['app_name']] += total_time

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
    print('             of total : ', row_errors)
    print('----------------------------')


    print('Average appen2.css '.ljust(25),      ave_dict['appen2.css']   /  count['appen2.css          '])
    print('Average appen2'.ljust(25),           ave_dict['appen2']       /  count['appen2              '])
    print('Average appen2.xwalk '.ljust(25),    ave_dict['appen2.xwalk'] /  count['appen2.xwalk        '])


