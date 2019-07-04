#!/usr/bin/python
import sys
import os
import logging
import traceback
import re

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

global tests 
tests= []
global progress
progress = 0


def process_print(*argv):  
    """
    Print <PID> (message)
    """
    try:
        if not 'MainProcess' in str(current_process()):
            pid = str(str(current_process()).split("-")[1].split(',')[0])
        else:
            pid = "Main"
        print_me = ''
        for arg in argv:  
            print_me += str(arg)
        print('<PID:', pid.ljust(2), '> ', print_me)
    except Exception as e:
        print(e)
        traceback.print_exc()
        print('<PID:', str(current_process()), '> ', argv)

    

def multi_threading_compute(a_list):
    """
    Creates #THREADS new threads, 
        Threads need synchonization for global variable
    """
    poolsize = int(len(a_list) / THREADS)
    process_print ("|||| THIS THREAD SHOULD RUN " + str(poolsize).ljust(3) + " TIMES; OF ", str(len(a_list)).ljust(5), " IN TOTAL FOR PROCESS ||||||||")
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
 

def multi_processing_compute(a_list):
    """
    Spawns #PROFFESSOR new processes 
        Finished processes wake up every 0.5 second to recheck 
        Does not need Synchronization: Handled by framework 
            Variables not in same namespace 
    """
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
                
                if self.counter % (len(self.workload) / 4) == 0:
                    
                    # process_print ("[",str(self.tid).rjust(4),"] File:",str(self.counter).rjust(4),"/",str(len(self.workload)).rjust(4), " -> ", entry)
                    globalLock.acquire()
                    global progress
                    progress += (len(self.workload) / 4)
                    prog_bar = progress
                    globalLock.release()

                    prog_bar = prog_bar / (len(self.workload) * THREADS)
                    prog_bar = int(prog_bar * 100.0)
                    process_print ("Progress:", '#'.ljust( prog_bar, '#'),'>',prog_bar,' %')
            
            # Free lock to release next thread
            globalLock.acquire()
            tests.extend(self.local_tests)
            #global progress
            #progress += self.counter
            #prog_bar = progress
            globalLock.release()

            #prog_bar = prog_bar / len(self.workload) * THREADS
            #process_print ("[",str(self.tid).rjust(4),"] Progress:", '#'.ljust( int(prog_bar * 50.0), '#'),'>')
            
            #process_print ("[",str(self.tid).rjust(4)," Finished ]") 
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


def clean_str(dirty_string):
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
                        # TODO: Felsök parse_line ...
                        device = parse_line(line, device)
                        linenumber += 1
                    except Exception as e:
                        process_print("_________/!\\ Line Error /!\\_________")
                        process_print(line)
                        process_print(e)
                        traceback.print_exc()

            remove_start = filepath.split('/')[1::1]
            device['filepath'] = '/'.join(remove_start)

    except Exception as e:
        process_print('_________/!\\ Probbly error Opening file /!\\_________')
        process_print(e)
        traceback.print_exc()
    #process_print(device)
    return device

def parse_timestamp(searchName, attribute, regPattern, line, dev):
    if re.search(regPattern, line):
        if "(total" not in line:
            dev[attribute] = timestamp_to_ms(line.split("MainActivity: +")[1])
        else:
            dev[attribute] = timestamp_to_ms(line.split("MainActivity: +")[1].split("total")[0])
            dev[attribute + '_plus_total'] = timestamp_to_ms(line.split(".MainActivity:")[1].split("total")[1])    
        dev['app_name']  = line.split(searchName)[1].split("/.MainActivity")[0]


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
    elif "device:" in line:
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
    
    return device