# Functions to download yesterday's races and associated raceforms from host

import configparser
import requests
import re
import sys
import time
from datetime import datetime, timedelta

from hracing.db import parse_racesheet
from hracing.db import mongo_insert_race


def download_list_of_races(oriheader,pastdays=3,datestr=None):
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
    baseurl = 'https://' + oriheader['host']
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
        raceid_urls.append(
            re.findall(
                    '\<li\sclass\=\"raceli\s*status_.*\s*clearfix\"\s*data-url\=\"'
                    '(\/race\?id\=\d*\&country\=.+\&track\=.*\&date=\d\d\d\d-\d\d-\d\d)\"',
                    temp_race.text))
        raceids.append(
            re.findall(
                    '\<li\sclass\=\"raceli\s*status_.*\s*clearfix\"\s*data-url\=\"'
                    '\/race\?id\=(\d*)\&country\=.+\&track\=.*\&date=\d\d\d\d-\d\d-\d\d\"',
                    temp_race.text))
    print("Finished importing raceIDs: " + d.strftime(('%Y-%m-%d-%H-%M')))
    return raceids, raceid_urls


def scrape_races(raceids,raceid_urls,oriheader,payload):
    """ Fetch a list of all races from host for a given day.
    Date is selected either as:
    a) pastdays (e.g. pastdays=1 means yesterday).
    OR  
    b) by specifying a datestr of the format YYYY-MM-DD.
    Default is to download races from TWO DAYS AGO, which is useful for
    data-base building since this avoids US/CAN races are not finished
    Return a list of raceids and raceid_urls, which are clustered according to race-location"""

    baseurl='https://'+oriheader['host']
    racemindur=25 # minimum time per/download in seconds to avoid getting kicked
    d=datetime.today()
    a=time.monotonic()
    #formen=[]
    tries=1
    #For each race location...
    for (i, raceid_url) in enumerate(raceid_urls):
        try: 
            #Open new session...
            with requests.Session() as s:              
                p = s.post(baseurl+'/auth/validatepostajax',
                           headers = oriheader,
                           data=payload)
                # Check if login was successful
                if not re.search('"login":true',p.text):
                    sys.exit("LOGIN FAILED")
                #For each single race at each race location...
                for (j, r_url) in enumerate(raceid_url):
                    print("Start downloading race_ID: "+raceids[i][j])
                    #Check current time
                    rstarttime=time.monotonic()
                    #Get current racesheet
                    racesheet=s.get(baseurl+r_url,
                                            headers = oriheader,
                                            cookies=s.cookies)
                    #Get horseformen urls for that race
                    # — Formen associated with horses are currently mostly empty...
                    #include again when host updates site
                    
                    #horseform_urls=(re.findall("window.open\(\'(.+?)', \'Formguide\'",
                    #                           racesheet.text))
                    #curr_formen=[]
                    #Get horseformen-sheets for that race
                    #for (k, horseform_url) in enumerate(horseform_urls):
                    #    curr_formen.append(s.get(baseurl+horseform_url,
                    #                             headers = oriheader,
                    #                             cookies=s.cookies))
                    #formen.append(curr_formen)
                    
                    # Try parsing current race and add to mogodb. If something fails
                    # Save race as .txt in folder for troubleshooting.
                    #try:
                    race=parse_racesheet(racesheet)
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
                    
                    #Wait a little if faster than racemindur to avoid scraping too fast
                    rtotaltime=time.monotonic()-rstarttime
                    rwaittime=racemindur-rtotaltime
                    if rwaittime>0:
                        time.sleep(rwaittime)
                   # Print current runtime, current race, and number of formen extracted  
                    print("Finished: "
                          +str(time.monotonic()-a))
                         # +"   n Formen: "+str(len(curr_formen)))
                 
        #Exception of Request
        except requests.exceptions.RequestException as e:
            print(e)
            tries=tries+1
            time.sleep(600) # wait ten minutes before next try
            print("Download exception, trying to continue in 10 mins"
                +d.strftime('%Y-%m-%d-%H-%M'))
            if tries > 4:
                print(str(tries) + "Download exceptions, exiting loop")
                break
    print("Finished: Download race xmls: "
            + d.strftime('%Y-%m-%d-%H-%M'))
    racesheet
    #return racesheet #,formen


def main():
# get scraping target and login info from config file
    configFile='../hracing_private/scraping_payload.ini'
    pageConfig = configparser.ConfigParser()
    pageConfig.read(configFile)
    oriheader=dict(pageConfig['oriheader'])
    payload=dict(pageConfig['payload'])

    raceids, raceid_urls=download_list_of_races(oriheader)
    scrape_races(raceids, raceid_urls, oriheader, payload)


if __name__ == "__main__":
    main()
