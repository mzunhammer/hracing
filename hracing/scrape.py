#!/Users/matthiaszunhammer/anaconda/bin/python
# coding: utf-8
# Function to download yesterday's races and associated raceforms from germantote

# Header
import requests
import re
import sys
import time
import pickle
import configparser

from datetime import datetime, timedelta
#from RaceClass import Race


def download_list_of_races(oriheader,pastdays=3,datestr=None):
    """ Fetch a list of all raceIDs and raceURLs listed on host for a given day.
    Date is selected either as:
    a) pastdays (e.g. pastdays=1 means yesterday).
    OR  
    b) by specifying a datestr of the format YYYY-MM-DD.
    Default is to download races from THREE DAYS AGO, which is useful for
    data-base building since this avoids unfinished US/CAN races
    
    Return a list of raceids and raceid_urls, which are clustered according to race-location"""
    
    # Compose URL
    if datestr==None:
        d=datetime.today()-timedelta(days=int(pastdays))
        datestr=d.strftime('%Y-%m-%d')
        
    yesterdayurl='/races?date='+datestr
    baseurl='https://'+oriheader['host']
    url= baseurl+yesterdayurl
    
    # Download
    tpage=requests.get(url) 
    
    #Console feedback
    print("Time: " + d.strftime(('%Y-%m-%d-%H-%M')))
    print("Import race IDs for " + datestr)
    print("From " + url)

    #Get list of race-locations (TR)
    tr_urls_raw=re.split(
            '\<div class\=\"dayHeader\"\>',
            tpage.text)
    tr_urls=re.findall(
            '\<div class\=\"meetingRaces\" data-url\=\"(/meetings/meeting\?id\=\d+)\">',
            tr_urls_raw[1])
    
    # Loop through race-locations, get raceIDs and urls
    raceid_urls=[]
    raceids=[]
    for (i, tr_url) in enumerate(tr_urls):
        url=baseurl+tr_url
        temptrace=requests.get(url)
        raceid_urls.append(
            re.findall(
                    '\<li\sclass\=\"raceli\s*status_.*\s*clearfix\"\s*data-url\=\"(\/race\?id\=\d*\&country\=.+\&track\=.*\&date=\d\d\d\d-\d\d-\d\d)\"',
                    temptrace.text))
        raceids.append(
            re.findall(
                    '\<li\sclass\=\"raceli\s*status_.*\s*clearfix\"\s*data-url\=\"\/race\?id\=(\d*)\&country\=.+\&track\=.*\&date=\d\d\d\d-\d\d-\d\d\"',
                    temptrace.text))
    print("Finished importing raceIDs: " + d.strftime(('%Y-%m-%d-%H-%M')))
    return raceids, raceid_urls


def download_races(raceids,raceid_urls,oriheader,payload):
    """ Fetch a list of all races from host for a given day.
    Date is selected either as:
    a) pastdays (e.g. pastdays=1 means yesterday).
    OR  
    b) by specifying a datestr of the format YYYY-MM-DD.
    Default is to download races from TWO DAYS AGO, which is useful for
    data-base building since this avoids US/CAN races are not finished
    Return a list of raceids and raceid_urls, which are clustered according to race-location"""

    # header of post simulating browser
    baseurl='https://'+oriheader['host']
    racemindur=25 # minimum time per/downloaded race in seconds
    d=datetime.today()
    a=time.monotonic()
    racesheets=[]
    formen=[]
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
                    #print(p.text) #For debugging: Login-response received
                    sys.exit("LOGIN FAILED")
            #For each single race at each race location...
                for (j, r_url) in enumerate(raceid_url):
                    #Check current time
                    rstarttime=time.monotonic()
                    #Get current racesheet
                    racesheets.append(s.get(baseurl+r_url,
                                            headers = oriheader,
                                            cookies=s.cookies))
                    #Get horseformen urls for that race
                    horseform_urls=(re.findall("window.open\(\'(.+?)', \'Formguide\'",
                                               racesheets[-1].text))
                    curr_formen=[]
                    #Get horseformen-sheets for that race
                    for (k, horseform_url) in enumerate(horseform_urls):
                        curr_formen.append(s.get(baseurl+horseform_url,
                                                 headers = oriheader,
                                                 cookies=s.cookies))
                    formen.append(curr_formen)
                    #Wait a little if faster than racemindur to avoid scraping too fast
                    rtotaltime=time.monotonic()-rstarttime
                    rwaittime=racemindur-rtotaltime
                    if rwaittime>0:
                        time.sleep(rwaittime)
            #Print current runtime, current race, and number of formen extracted  
                    print("Time: "
                          +str(time.monotonic()-a)
                          +"    RaceID: "+raceids[i][j]
                          +"   n Formen: "+str(len(curr_formen)))
        #Exception of Request
        except requests.exceptions.RequestException as e:
            print(e)
            tries=tries+1
            time.sleep(600) # wait ten minutes before next try
            print("Download exception, trying to continue in 10 mins"
                +d.strftime('%Y-%m-%d-%H-%M'))
            if tries > 4:
                print(str(tries) + "Download exceptions, exiting loop")
                racesheets=racesheets[0:len(formen)]# Shorten racesheets to length of formen, in case downloading aborted during loading formen 
                break
        #except: 
        #    print(e)
        #    print("Download loop aborted by unknown exception. Trying to rescue " + d.strftime('%Y-%m-%d-%H-%M'))
        #    racesheets=racesheets[0:len(formen)]# Shorten racesheets to length of formen, in case downloading aborted during loading formen 
        #    break
    print(len(racesheets))
    print("Finished: Download race xmls: "
            + d.strftime('%Y-%m-%d-%H-%M'))
    return racesheets,formen


def extract_racedata(racesheets,formen):
    d=datetime.today()
    print("End of Download start of extract"
            +d.strftime('%Y-%m-%d'))
    
    #Save raw html text to file for debugging purposes, overwrite every time
    rawtextFilename='/Users/matthiaszunhammer/Dropbox/PY/HorseRacing/lastdownload.pickle'
    with open(rawtextFilename, 'wb') as wf:
        pickle.dump(zip(racesheets,formen), wf)
        
    # Extract racesheets and formen using html parser
    if len(racesheets)==len(formen):
        racelist=[Race(r.text,f)
                  for r,f
                  in zip(racesheets,formen)]
    else:
        print('RACESHEETS AND FORMEN HAVE DIFFERENT LENGTH')
    return racesheets

  
def save_racedata(racelist): #Save Race class instances
    basepath='/Users/matthiaszunhammer/Dropbox/PY/HorseRacing/pastraces/'
    for races in racelist: #for each race in r
        cfname=basepath+str(races.raceID)+'.pickle'
        with open(cfname, 'wb') as wf:
            pickle.dump(races, wf)
    
    #Print today's end of Download Message
    d=datetime.today()
    print("Finished: Import Races: "
            + d.strftime('%Y-%m-%d-%H-%M')
            +" Saved Data in "
           +basepath)

def main():
# get scraping target and login info from config file
    configFile='../hracing_private/scraping_payload.ini'
    pageConfig = configparser.ConfigParser()
    pageConfig.read(configFile)
    oriheader=dict(pageConfig['oriheader'])
    payload=dict(pageConfig['payload'])

    raceids, raceid_urls=download_list_of_races(oriheader)
    racesheets,formen=download_races(raceids, raceid_urls, oriheader, payload)
    racelist=extract_racedata(racesheets,formen)
    save_racedata(racelist)

if __name__ == "__main__":
    main()