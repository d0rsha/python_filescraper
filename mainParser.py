#!/usr/bin/python
import sys
import os
import re
import argparse
import logging
import traceback
import csv
import pprint

from fileParseWorker import search_filepath, clean_str

#
#   Arguments and global variable 
#
parser = argparse.ArgumentParser()
parser.add_argument("path")
args = parser.parse_args()

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


def calculate_deltider(data_row):
    """
        Fix 'deltider' : 1displayed, 2deviceready, 3fully_drawn, 4login_time, 5backend_time  
    """
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
    return


def interpolate_row(data_row):
    """
        Interpolate app_name; sdk-version; approach
    """

    #    Rename / Give app nickname
    data_row['app_name'] = re.sub('com.avrethem.', '', data_row['app_name'])
    data_row['app_name'] = re.sub('com.ionicframework.', '', data_row['app_name'])
    # data_row['app_name'] = re.sub('android.', 'droid', data_row['app_name'])
    # data_row['app_name'] = re.sub('app', '', data_row['app_name'])
    data_row['app_name'] = re.sub('se.solutionxperts.', '', data_row['app_name'])
    data_row['app_name'] = re.sub('.stangastaden', '', data_row['app_name'])
    data_row['app_name'] = re.sub('xom.xwalk.browser', 'plugins.xwalk', data_row['app_name'])
    
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
    #   Add 'fatal_exception' flag to failed tests 
    if "deviceready_error" in data_row:
        raise KeyError('devRdy_err')
    #   Add plugin check 
    if not "plugin_loaded" in data_row:
        raise KeyError('plugin')

    return


def count_errors(data_row):
    #
    # Count different type of errors 
    inc_error_count(fail_count, data_row)
    if "deviceready_error" in data_row:
        inc_error_count(fail_count_deviceready, data_row)
    if "fatal_exception" in data_row:
        inc_error_count(fail_count_fatal_error, data_row)
    if not "plugin_loaded" in data_row:
        inc_error_count(fail_count_plugin, data_row)

    return

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


"""
    Main program

    calls search_filepath
    creates csv file with headers according to csv_columns 
"""
if __name__ == "__main__":
    dict_data = []

    res = search_filepath(args.path, 'logcat')
    for bin in res:
        dict_data.extend(bin)


    # pprint.pprint(result)
    print("---------------")
    pprint.pprint(dict_data)
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
    print_columns = [ 'app_name','displayed','2deviceready','fully_drawn', 'model', 'manufacturer', 'sdk-version']
    
    #
    # Print header
    print(">>>>>>>>>>>>>< Removing faulty rows <<<<<<<<<<<<<<<<")
    tmp = "row: "
    for field_name in print_columns:
        COL_SIZE = int(len(field_name))
        tmp += str(clean_str( str(field_name[-COL_SIZE:]) )).ljust(COL_SIZE) + ", "
    print(tmp)

    #
    #  Create CSV file
    #
    with open('test.csv', 'w') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=csv_columns)
        writer.writeheader()

        unique_key = 0
        row_errors = 0
        fail_count[''.ljust(20)] = 0
        fail_count_fatal_error[''.ljust(20)] = 0
        for data_row in dict_data:
            try:
                calculate_deltider(data_row)

                interpolate_row(data_row)

                #
                # Create a new Dict with the columns from csv_columns and create csv file from new Dict
                #
                csv_dict = {}

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
                if "fatal_exception" in data_row:
                    tmp += " FATAL EXCEPT"
                elif "plugin_loaded" in data_row:
                    tmp += " PLUGIN ERROR"
                elif "deviceready_error" in data_row:
                    tmp += " CORD ERROR  "
                else:
                    tmp += "             "
                tmp += ' ' + data_row['filepath']
                print(tmp)

                count_errors(data_row)
                row_errors += 1


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
    print(' and of which is deviceready|')
    pprint.pprint(fail_count_deviceready)
    print('                            |')
    print(' and of which is PLUGIN ERR |')
    pprint.pprint(fail_count_plugin)
    print('----------------------------|')
    print('----------------------------|')

