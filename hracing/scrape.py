# Functions to download yesterday's races and associated raceforms from host

import configparser
import requests
import re
import sys
import time
import pymongo
import random
from datetime import datetime, timedelta

from hracing.db import parse_racesheet
from hracing.db import mongo_insert_race
from hracing.tools import delay_scraping
from hracing.tools import shuffle_ids

def download_list_of_races(header,pastdays=3,datestr=None):
    """ Fetch a list of all raceIDs and raceURLs listed on host for a given day.
    Date is selected either as:
    a) pastdays (e.g. pastdays=1 means yesterday).
    OR  
    b) by specifying a datestr of the format YYYY-MM-DD.
    Default is to download races from THREE DAYS AGO, which is useful for
    data-base building since this avoids unfinished US/CAN races
    Returns a lists of raceids and a lists of raceid_urls,
    nested in a list of race-locations"""
    
    # Compose URL
    if datestr == None:
        d = datetime.today()-timedelta(days=int(pastdays))
        datestr = d.strftime('%Y-%m-%d')
    yesterdayurl = '/races?date=' + datestr
    baseurl = 'https://' + header['host']
    url = baseurl + yesterdayurl 
    # Actual download
    tpage=requests.get(url) 
    #Console feedback
    print("Time: " + d.strftime(('%Y-%m-%d-%H-%M')))
    print("Import race IDs for " + datestr)
    print("From " + url)
    #Get list of race-locations (TR)
    tr_urls_raw=re.split('\<div class\=\"dayHeader\"\>',tpage.text)
    tr_urls=re.findall(
            '\<div class\=\"meetingRaces\" '
            'data-url\=\"(/meetings/meeting\?id\=\d+)\">',
            tr_urls_raw[1])
    # Loop through race-locations, get raceIDs and urls
    raceid_urls=[]
    raceids=[]
    for tr_url in tr_urls:
        url=baseurl+tr_url
        temp_race=requests.get(url)
        raceid_urls.extend(
            re.findall(
                    '\<li\sclass\=\"raceli\s*status_.*\s*clearfix\"\s*data-url\=\"'
                    '(\/race\?id\=\d*\&country\=.+\&track\=.*\&date=\d\d\d\d-\d\d-\d\d)\"',
                    temp_race.text))
        raceids.extend(
            re.findall(
                    '\<li\sclass\=\"raceli\s*status_.*\s*clearfix\"\s*data-url\=\"'
                    '\/race\?id\=(\d*)\&country\=.+\&track\=.*\&date=\d\d\d\d-\d\d-\d\d\"',
                    temp_race.text))
    print("Finished importing raceIDs: " + d.strftime(('%Y-%m-%d-%H-%M')))
    return raceids, raceid_urls


def scrape_races(raceids,raceid_urls,header,payload):
    """ Fetch a list of all races from host for a given day.
    Date is selected either as:
    a) pastdays (e.g. pastdays=1 means yesterday).
    OR  
    b) by specifying a datestr of the format YYYY-MM-DD.
    Default is to download races from TWO DAYS AGO, which is useful for
    data-base building since this avoids US/CAN races are not finished
    Return a list of raceids and raceid_urls, which are clustered according to race-location"""

    baseurl='https://'+header['host']
    race_dur_sd=30 # minimum time(s)/race download to avoid getting kicked
    form_dur_sd=8 # minimum time(s)/form download to avoid getting kicked
    reconnect_dur=60 # minimum time ind s to wait before reconnecting after losing connection
    max_tries=50
    d=datetime.today()
    a=time.monotonic()
    tries=1
    
    #Shuffle order of races
    raceids,raceid_urls=shuffle_ids(raceids,raceid_urls)   
    #Open new session...
    with requests.Session() as s:              
        p = s.post(baseurl+'/auth/validatepostajax',
        headers = header,
        data=payload)
 
    #For each race location...
    for (i, raceid_url) in enumerate(raceid_urls):
        if not re.search('"login":true',p.text):
            with requests.Session() as s:              
                p = s.post(baseurl+'/auth/validatepostajax',
                headers = header,
                data=payload)
        try: 
            #For each single race...
            print("Start downloading race_ID: "+raceids[i]+
                " ("+str(i+1) +"/"+str(len(raceid_urls))+")")
            #Check current time
            start_time=time.monotonic()
            #Get current racesheet
            racesheet=s.get(baseurl+raceid_url,
                                    headers = header,
                                    cookies=s.cookies)
            #Get horseforms urls for that race                    
            horseform_urls=(re.findall("window.open\(\'(.+?)', \'Formguide\'",
                                       racesheet.text))
            forms=[]
            #Get horseforms-sheets for that race
            for (k, horseform_url) in enumerate(horseform_urls):
                start_time_2=time.monotonic()
                forms.append(s.get(baseurl+horseform_url,
                                         headers = header,
                                         cookies=s.cookies))
                delay_scraping(start_time_2,form_dur_sd)
            # Try parsing current race and add to mogodb. If something fails
            # Save race as .txt in folder for troubleshooting.
            
            # UNCOMMENT TRY/EXCEPT WHEN UP AND RUNNING
            #try: 
            race=parse_racesheet(racesheet,forms)
            mongo_insert_race(race)
#                    except Exception as e:
#                        #Save raw html text to file for debugging purposes, overwrite every time
#                        errordump='../hracing_private/failed_parsing/'
#                        rawtextFilename=errordump+str(raceids[i][j])+'.txt'
#                        print('Error when parsing race_ID: '+str(raceids[i][j])+'. Page saved in '+errordump)
#                        print('Error msg for '+str(raceids[i][j])+': \n'+str(e))
#
#                        with open(rawtextFilename, 'wb') as text_file:
#                            text_file.write(racesheet.content)
                
            delay_scraping(start_time,race_dur_sd)# Slow scraping to avoid getting kicked from server.

            # Print current runtime, current race, and number of forms extracted  
            print("Finished: " +str(time.monotonic()-a))
                     # +"   n forms: "+str(len(curr_forms)))
                 
        #Exception of Request
        except requests.exceptions.RequestException as e:
            print(e)
            tries=tries+1
            time.sleep(reconnect_dur) # wait ten minutes before next try
            print("Download exception, trying to continue in "+str(reconnect_dur)+" seconds "
                +d.strftime('%Y-%m-%d-%H-%M'))
            if tries > max_tries:
                print(str(tries) + "Download exceptions, exiting loop")
                break
    print("Finished: Download race xmls: "
            + d.strftime('%Y-%m-%d-%H-%M'))


def get_races_IDs_not_in_db(raceids, raceid_urls):
    client = pymongo.MongoClient()
    db = client.races
    race_IDs_db=[]
    for race in db.races.find({},{'race_ID':1, '_id': 0}):
        race_IDs_db.append(race['race_ID'])
    race_zip=zip(raceids,raceid_urls)
    filtered_race_zip = filter(lambda x: int(x[0]) not in race_IDs_db,race_zip)
    novel_raceids,novel_raceid_urls =zip(*filtered_race_zip)
    return list(novel_raceids), list(novel_raceid_urls)


def main():
# get scraping target and login info from config file
    configFile='../hracing_private/scraping_payload.ini'
    pageConfig = configparser.ConfigParser()
    pageConfig.read(configFile)
    header=dict(pageConfig['header'])
    payload=dict(pageConfig['payload'])

    raceids, raceid_urls = download_list_of_races(header)
    filtered_raceids, filtered_raceid_urls = get_races_IDs_not_in_db(raceids,raceid_urls)
    scrape_races(filtered_raceids, filtered_raceid_urls, header, payload)


if __name__ == "__main__":
    main()
