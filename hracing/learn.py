# Standard library
from os import walk
from datetime import datetime
import re
import pickle
import sys
import time
import warnings
import collections # needed to check for type of variable (collections.Iterable) and exclude duplicates
from bs4 import BeautifulSoup

# 3rd party
import requests
import numpy as np
from numpy import nanmean
from sklearn import linear_model
import pandas as pd

# custom
from flatten import flatten


class Race: 
    """Race Class for:
        a) storing all data for a given horse-race
        a) extract that data from a raw race.html
        b) extract that data from horseforms.html
        d) allow to retrieve the stored data as a pd.table"""
    
    starters=float('nan')
    nonrunners=float('nan')
    raceID=float('nan')
    rtype=float('nan')
    rday=float('nan')
    rtime=float('nan')
    country=float('nan')
    rname=float('nan')
    rnum=float('nan')
    dist=float('nan')
    stakes=float('nan')
    stakes=float('nan')
    weights=float('nan')
    ages=float('nan')
    sex=float('nan')
    starters=float('nan')
    meanodds=float('nan')
    trendodds=float('nan')
    horsenames=float('nan')
    jockeynames=float('nan')
    jockeytrainers=float('nan')
    heritages1=float('nan')
    heritages2=float('nan')
    owners=float('nan')
    odds=float('nan')
    fillfinish=float('nan')
    finishers=float('nan')
    pastpl1=float('nan')
    pastpl2=float('nan')
    pastpl3=float('nan')
    pastpl4=float('nan')
    pastpl5=float('nan')
    lofi_meanodds=float('nan')
    lofi_trendodds=float('nan')
    lofi_nracesrun=float('nan')
    lofi_places=float('nan')
    lofi_pastpl1=float('nan')
    lofi_pastpl2=float('nan')
    lofi_pastpl3=float('nan')
    lofi_pastpl4=float('nan')
    lofi_pastpl5=float('nan')
    
    def __init__(self, textraw,formen,verbose=False):
        #self.textraw = textraw
        self.description = "Race from Germantote"
        self.author = "MZ"        
        self.extract(textraw,verbose) # FILLS ALL VARIABLES ABOVE
        self.getformen(formen) # FILLS ALL VARIABLES ABOVE
    
    def extract(self,textraw,verbose=False):
        """extract function is called on start and extracts race-specific data"""
        textraw2=re.split(
            '<div id="racecardTopContainer"',
            textraw)[1] # throw away top part of html
        racedaylist,raceslist=re.split(
            '<div class="racesList">',
            textraw2) # split rest into race day and single race info
        self.starters=int(re.findall(
                '<li class="starter">(\d+?) Starter</li>',
                raceslist)[0])
        if not self.starters: self.starters=float('nan')
        self.nonrunners=[bool(x)
                           for x
                           in  re.findall('<li class="clearfix(| nonrunner)">',
                           raceslist)]
        if not self.nonrunners: # strange "mix" races
            self.nonrunners=[bool(x)
                               for x
                               in  re.findall('<li class="clearfix mix(| nonrunner) runner_.*?">',
                               raceslist)]
        if len(self.nonrunners)!=self.starters:
            print('Error only '+str(len(self.nonrunners))+ ' nonrunners.')
            self.nonrunners=[bool(0)]*self.starters
        self.runners=[not i for i in self.nonrunners]
        self.ridraw=re.findall('data-raceid="(\d+?)">',racedaylist)[0]
        self.raceID=int(self.ridraw)#racedaylist or raceslist???
        if not self.raceID: self.raceID=float('nan')
        if verbose:
            print(self.raceID)
        self.rtype=re.findall(
            '<i class="raceType (.+?)"></i>',
            racedaylist)
        if self.rtype[0] is 'T':
            self.rtype='Flach' # Oddly, Flachrennen get a 'T' by germantote
        elif self.rtype[0] is 'H':
            self.rtype='Trab' # Oddly, Trabrennen get a 'H' by germantote
        else:
            self.rtype=2 # "Other"
        self.rday=datetime.strptime(re.findall(
                'Rennen am (.+?)</a>',
                racedaylist)[0],
                '%d.%m.%Y')
        if not self.rday: self.rday=float('nan')
        self.rtime=datetime.strptime(re.findall(
                '<li class="time">(\d\d\:\d\d)</li>',
                raceslist)[0],
                '%H:%M')
        if not self.rtime: self.rtime=float('nan')
        self.country=re.findall(
            'a href="/races\?country=(...)&date=',
            racedaylist)
        if not self.rtime: self.rtime=float('nan')
        self.rname=re.findall(
            '<i class="raceType ."></i> (.+?)\n',
            racedaylist)
        if not self.rname: self.rname='nan'
        self.rnum=int(re.findall(
                '<div class="counter">\s*(\d+)\s*</div>',
                raceslist)[0])
        if not self.rnum: self.rname=float('nan')
        self.dist=float(re.findall(
                '<li class="distance">(.+?) m</li>',
                raceslist)[0])
        if not self.dist: self.dist=float('nan')
        self.stakes=re.findall(
            '<li class="stakes">(.+?) (.+?)</li>',
            raceslist)
        if not self.stakes[0][0]: self.stakes[0][0]=float('nan')
        if not self.stakes[0][0]: self.stakes[0][0]='nan'
        #Extract horse-specific data from racesheet
        #Get starternumbers (str since replacementhorses often get something like 1a 1b)    
        self.starterNo1=re.findall(
            '<span class="count1">(.+?)</span>',
            raceslist)
        self.starterNo2=re.findall(
            '<span class="count2">(.+?)</span>',
            raceslist)
        #Horsenames
        self.horsenames=re.findall(
            '<span class="runnername">\s*<span class="string.*?">\n\s*?<a href=.*?>\s*(.+?)\s*?<.a>\n\s*?</span>',
            raceslist)
        if len(self.horsenames)!=self.starters:
            print('Error only '+str(len(self.horsenames))+ ' horsenames.')
        #Extract finish-data
        finish_raw=re.findall(
            '<table class="finishTable">.*?</table>',
            textraw,re.S)#get finishtable
        #self.finish_raw=finish_raw
        if finish_raw:
            trows=re.findall(
                '<tr>(.*?)</tr>',
                finish_raw[0],
                re.S) #gets all table rows
            self.finishall=[re.findall('<(?:th|td) .*?>(.*?)</(?:th|td)>',
                                row,re.S)
                            for row 
                            in trows] #gets all table headers or table cells for each row
            self.finisherNames=([x[2]
                             for x
                             in self.finishall[1:]]) # gets finisher's starter numbers from second row on in second column
            self.finishersRaw=([x[1]
                             for x
                             in self.finishall[1:]]) # gets finisher's starter numbers from second row on in second column
            self.placementsRaw=([int(x[0])
                             for x
                             in self.finishall[1:]])
        
            self.finishers=[float('nan')] * self.starters
            #VERSION 1:
            #fill all fields with mean finish of all starters not placed
            #PROBLEM: will systematically affect relationship between starters and finish >> starter only useful as a predictor of winners
            self.fillfinish=[np.mean([self.starters-sum(self.nonrunners),
                              1+len(self.finishersRaw)])]* self.starters
            #VERSION 2:
            #fill all fields with nan
            #PROBLEM: more horses will be dropped
            #self.fillfinish=[float('nan')]* self.starters
            #VERSION 3:
            #fill all fields with random numbers
            #PROBLEM: random variance added
            #IMPLEMENTED IN ANALYSIS-PRE-PROCESSING
            if self.finisherNames: # in case finisher list has names
                for i,finny in enumerate(self.finisherNames):
                    finindex=self.horsenames.index(finny)#get index of finisher 
                    self.finishers[finindex]=self.placementsRaw[i]
                    self.fillfinish[finindex]=self.placementsRaw[i]
            elif self.finishersRaw:
                for i,finny in enumerate(self.finishersRaw):
                    finindex=self.starterNo1.index(finny)#get index of finisher 
                    self.finishers[finindex]=self.placementsRaw[i]
                    self.fillfinish[finindex]=self.placementsRaw[i]
        else:
            self.finishall=[]
            self.finishersRaw=[]
            self.finishers=float('nan')
            self.fillfinish=float('nan')
            
        self.jockeynames=re.findall(
            '<span class="jockeyname.*?">\s*<span class="string.*?">(.*?)(?:</strong></span>|</span>)'
            ,raceslist)
        if len(self.jockeynames)!=self.starters:
            print('Error only '+str(len(self.jockeynames))+ ' jockeynames.')
        self.jockeytrainers=re.findall(
            '<div class="jockeytrainer.*?">(.*?)</div>',
            raceslist)
        if len(self.jockeytrainers)!=self.starters:
            print('Error only '+str(len(self.jockeynames))+ ' jockeytrainers.')
        self.owners=re.findall(
            'Besitzer:</span>\s(.+?)\s+?</div',
            raceslist)
        if len(self.owners)!=self.starters:
            print('Error only '+str(len(self.owners))+ ' owners.')
            self.owners='nan'
        self.heritages=re.findall(
            'Abstammung:</span> (.+?)â\x80\x93 (.+?)\s+<span class="label">Besitzer:',
            raceslist,
            re.S)
        self.heritages1=[heir[0] for heir in self.heritages]
        if len(self.heritages1)!=self.starters:
            print('Error only '+str(len(self.heritages1))+ ' heritages1.')
        self.heritages2=[heir[1] for heir in self.heritages]
        if len(self.heritages2)!=self.starters:
            print('Error only '+str(len(self.heritages2))+ ' heritages2.')
        weight=re.findall(
            '<span class="weight">(.+?) kg</span>',#(\d+,*\d*)
            raceslist)
        if weight:
            try:
                self.weights= [float(x.replace(',','.'))
                               for x in weight]
                if len(self.weights)!=self.starters:
                    print('Error only '+str(len(self.weights))+ ' weights in Race: '+str(self.raceID))
            except:
                self.weights= float('nan')
                print('Error extracting weights in Race: '+str(self.raceID))
            
        else:
            self.weights= float('nan')
         
        age_and_sex=re.findall(
            '<span class="horseage">(.+?)j\.(.+?)</span>',
            raceslist)
        self.ages=[float(x[0])
                  for x
                  in age_and_sex]
        if len(self.ages)!=self.starters:
            print('Error only '+str(len(self.ages))+ ' ages.')
        self.sex=[x[1]
                  for x
                  in age_and_sex]
        if len(self.sex)!=self.starters:
            print('Error only '+str(len(self.sex))+ ' sex.')
        
        # ODDS
        oddsraw=re.findall(
                '<div class="dCell odd">\s+(?:<span class="odds">|<span class="odds toteFav">)(.+?)</span>\s+</div>',
                raceslist)
        oddsraw=[float(x.replace(',','.').replace('-','nan'))
                       for x
                       in oddsraw]
        self.odds=[float('nan')]*self.starters
        if len(oddsraw)==self.starters:
            self.odds=oddsraw
        elif len(oddsraw)==sum(self.runners):
            irunners=[i for i,runner in enumerate(self.runners) if runner]    
            for j,i in enumerate(irunners):
                self.odds[i]=oddsraw[j]
        else:
            self.odds=oddsraw
            print('Error in '+ str(self.raceID) +' only '+str(len(oddsraw))+' / '+
                  str(self.starters) +' odds, but ' + str(sum(self.runners)) + ' runners.')
   
        #Low-Fidelity ("lofi") extract of horse history from "Formen" shown on racesheet.(formen-tables in the HiFi "Formen"-Subpages were empty from July 2016 on...)       
        self.lofi_formentables=re.findall(
                            '(<table\scellpadding="0"\scellspacing="0">\s+.+?\s</table>)|(<table\scellspacing="0"\scellpadding="0">\s+.+?\s</table>)|(<div\sclass="noStats">.+?</div>)',
                            raceslist,re.S)
                                     
        lofi_formenrows=[re.findall('<tr class=.+?>(.*?)</tr>',formtable[0],re.S)
                        for formtable in self.lofi_formentables]
        lofi_formencells=[[re.findall('<(?:th|td).+?>(.*?)</td>',row,re.S)
                        for row in horse]
                        for horse in lofi_formenrows]
        self.lofi_pastfinish=lofi_formencells
        
        self.lofi_places=[[float(row[1].replace('-','nan')) if self.isnumber(row[1]) else float('nan')
                            for row in horse]
                            for horse in lofi_formencells]
        if len(self.lofi_places)!=self.starters:
            print('Error only '+str(len(self.lofi_places))+ ' lofi_places.')
                    
        self.lofi_nracesrun=[float(len(horse)) if len(np.array(horse)) > 0 else float(0)
                for horse in self.lofi_places]
        if len(self.lofi_nracesrun)!=self.starters:
            print('Error only '+str(len(self.lofi_nracesrun))+ ' lofi_nracesrun.')
        with warnings.catch_warnings(): #Just to suppress NaN warning in case only NaN data are available for a given race
             warnings.simplefilter("ignore", category=RuntimeWarning) #Just to suppress NaN warning in case only NaN data are available for a given race

             self.lofi_meanplace=[float(nanmean(horse)) if len(np.array(horse)) > 0 else float('nan')
                    for horse in self.lofi_places]
             if len(self.lofi_meanplace)!=self.starters:
                 print('Error only '+str(len(self.lofi_meanplace))+ ' lofi_meanplace.')
            
             self.lofi_pastodds=[[float(row[6].replace(',','.').replace('-','nan')) if self.isnumber(row[6]) else float('nan')
                    for row in horse]
                    for horse in lofi_formencells]         
             if len(self.lofi_pastodds)!=self.starters:
                 print('Error only '+str(len(self.lofi_pastodds))+ ' lofi_pastodds.')
            
             self.lofi_meanodds=[float(nanmean(horse)) if len(np.array(horse)) > 0 else float('nan')
                    for horse in self.lofi_pastodds]
             if len(self.lofi_meanodds)!=self.starters:
                 print('Error only '+str(len(self.lofi_meanodds))+ ' lofi_meanodds.')
             lofi_mdl=linear_model.LinearRegression()
             self.lofi_trendodds=[lofi_mdl.fit(np.arange(0,
                                              len(np.array(horse)[~np.isnan(horse)]),
                                                1).reshape(-1,1),np.array(horse)[~np.isnan(horse)].reshape(-1, 1)).coef_[0][0]
                                        if len(np.array(horse)[~np.isnan(horse)])>1
                                        else float('nan')
                                    for horse
                                    in self.lofi_pastodds]
             if len(self.lofi_trendodds)!=self.starters:
                 print('Error only '+str(len(self.lofi_trendodds))+ ' lofi_trendodds.')
                  
    def getformen(self,formen):
        formentables=[re.findall(
                        '(<h2 class="clearfix">\s+Form\s+</h2>\s+<div class="scrollWrapper">\s+<div class="innerWrapper">\s+<table class="formTable">.*?</table>)',
                        form.text,re.S)
                      for form
                      in formen]
        #self.formentables=formentables
        formenrows=[re.findall('<tr>(.*?)</tr>',formtable[0],re.S) for formtable in formentables]
        self.pastfinish=[[re.findall(
                    '<(?:th|td).*?>(?:<span.*?>)?(.*?)(?:</span>)?</(?:th|td)>',
                    row,re.S)
                         for row in rows]
                         for rows in formenrows]
        self.nracesrun=[len(horse)-1 for horse in self.pastfinish]  #counts previous races, subtracts headerline
        if len(self.nracesrun)!=self.starters:
            print('Error only '+str(len(self.nracesrun))+ ' nracesrun.')
        # Get places as float
        self.places=[[float(row[2])
                                if self.isnumber(row[2])
                                else float('nan')
                            for row in horse[1:]]
                        for horse in self.pastfinish]
        with warnings.catch_warnings(): #Just to suppress NaN warning in case only NaN data are available for a given race
             warnings.simplefilter("ignore", category=RuntimeWarning) #Just to suppress NaN warning in case only NaN data are available for a given race

             # Calculate mean if not empty
             self.meanplace=[nanmean(horse)
                                if len(np.array(horse)[~np.isnan(horse)]) > 0
                                else float('nan')
                            for horse in self.places]
             if len(self.meanplace)!=self.starters:
                 print('Error only '+str(len(self.meanplace))+ ' meanplace.')
            
             self.pastodds=[[float(row[6].replace(',','.').replace('-','nan'))
                                    if self.isnumber(row[2])
                                    else float('nan')
                                for row in horse[1:]]
                            for horse in self.pastfinish]
             self.meanodds=[nanmean(horse)
                           if len(np.array(horse)[~np.isnan(horse)]) > 0
                           else float('nan')
                           for horse in self.pastodds]
             if len(self.meanodds)!=self.starters:
                 print('Error only '+str(len(self.meanodds))+ ' meanodds.')
    
             mdl=linear_model.LinearRegression()
             self.trendodds=[
                            mdl.fit(
                                    np.arange(0,
                                              len(np.array(horse)[~np.isnan(horse)]),
                                              1).reshape(-1,1),np.array(horse)[~np.isnan(horse)].reshape(-1, 1)).coef_[0][0]
                                if len(np.array(horse)[~np.isnan(horse)])>1
                                else float('nan')
                            for horse
                            in self.pastodds]
             if len(self.trendodds)!=self.starters:
                 print('Error only '+str(len(self.trendodds))+ ' trendodds.')
        #Macht noch trouble:    
        #self.days_since_last_race=[
        #    (self.rday-datetime.strptime(horse[1][0],
        #                                '%d.%m.%Y')).days
        #        if (horse[1][0])
        #        else float('nan')
        #    for horse
        #    in self.pastfinish]
            
    def dfexport(self,verbose=False):
        if len(self.odds)!=self.starters:
            self.odds= float('nan')
        if len(self.starterNo1)!=self.starters:
            self.starterNo1= float('nan')
        if len(self.starterNo2)!=self.starters:
            self.starterNo2= float('nan')
            
         # Add past race placements post-hoc (afraid to mess up import otherwise)
        self.pastpl1=[float(horse[0])
                            if len(np.array(horse)[~np.isnan(horse)]) > 0
                            else float('nan')
                            for horse in self.places]
        self.pastpl2=[float(horse[1])
                            if len(np.array(horse)[~np.isnan(horse)]) > 1
                            else float('nan')
                            for horse in self.places]
        self.pastpl3=[float(horse[2])
                            if len(np.array(horse)[~np.isnan(horse)]) > 2
                            else float('nan')
                            for horse in self.places]
        self.pastpl4=[float(horse[3])
                            if len(np.array(horse)[~np.isnan(horse)]) > 3
                            else float('nan')
                            for horse in self.places]
        self.pastpl5=[float(horse[4])
                            if len(np.array(horse)[~np.isnan(horse)]) > 4
                            else float('nan')
                            for horse in self.places]
        #Add a simple numeric version of starterNo (StarterNo 1 and 2 often contain starter numbers like 2A 3B etc...)
        self.starterNo=list(range(1, self.starters+1))
                   
        # Same for lofi history
        if isinstance(self.lofi_places, (list, tuple)): # Check if lofi_places contains list, otherwise don't do the stuff and keep the default nans.
            self.lofi_pastpl1=[float(horse[0])
                                if len(np.array(horse)[~np.isnan(horse)]) > 0
                                else float('nan')
                                for horse in self.lofi_places]
            self.lofi_pastpl2=[float(horse[1])
                                if len(np.array(horse)[~np.isnan(horse)]) > 1
                                else float('nan')
                                for horse in self.lofi_places]
            self.lofi_pastpl3=[float(horse[2])
                                if len(np.array(horse)[~np.isnan(horse)]) > 2
                                else float('nan')
                                for horse in self.lofi_places]
            self.lofi_pastpl4=[float(horse[3])
                                if len(np.array(horse)[~np.isnan(horse)]) > 3
                                else float('nan')
                                for horse in self.lofi_places]
            self.lofi_pastpl5=[float(horse[4])
                                if len(np.array(horse)[~np.isnan(horse)]) > 4
                                else float('nan')
                                for horse in self.lofi_places]

        d = {
            'nonrunners' :  self.nonrunners,
            'n_nonrunners' : sum(self.nonrunners),
            'raceID'  :   self.raceID,
            'rtype'  :   self.rtype,
            'rday'  :   self.rday,
            'rtime'  :   self.rtime,
            'country'  :   self.country[0],
            'rname'  :   self.rname[0],
            'rnum'  :   self.rnum,
            'dist'  :   self.dist,
            'stake'  :   self.stakes[0][0],
            'stake_curr'  : self.stakes[0][1],
            'weights'  :   self.weights,
            'ages'  :   self.ages,
            'sex'  :   self.sex,
            'starters' : self.starters,
            'starterNo1' : self.starterNo1, #String from racesheet
            'starterNo2' : self.starterNo2, #String from racesheet
            'starterNo' : self.starterNo,   #Simply starters counted (int)
            'real_starters' : self.starters-sum(self.nonrunners),
            'meanodds' : self.meanodds,
            'trendodds' : self.trendodds,
            'horsenames'  :   self.horsenames, # HIER WEITER, STING-LISTEN LASSEN SICH NICHT EINFACH EINFÜGEN!!
            'jockeynames'  :   self.jockeynames,
            'jockeytrainers'  :   self.jockeytrainers,
            'heritages1'  :   self.heritages1,
            'heritages2'  :   self.heritages2,
            'owners'  :   self.owners,
            'odds'    : self.odds,
            'finish' : self.fillfinish,
            'nanfinish' : self.finishers,
            'pastpl1' : self.pastpl1,
            'pastpl2' : self.pastpl2,
            'pastpl3' : self.pastpl3,
            'pastpl4' : self.pastpl4,
            'pastpl5' : self.pastpl5,
            'lofi_meanodds' : self.lofi_meanodds,
            'lofi_trendodds' : self.lofi_trendodds,
            'lofi_nracesrun' : self.lofi_nracesrun,
            'lofi_pastpl1' : self.lofi_pastpl1,
            'lofi_pastpl2' : self.lofi_pastpl2,
            'lofi_pastpl3' : self.lofi_pastpl3,
            'lofi_pastpl4' : self.lofi_pastpl4,
            'lofi_pastpl5' : self.lofi_pastpl5
        }
        
        if verbose:
            print({key: (len(value) if isinstance(value, list) else 's:'+str(value)) for (key, value) in d.items()})
       
        return pd.DataFrame(d)

    def isnumber(self,s): # Function checks if string can be converted to float and is >0
        try:
            f=float(s.replace(',','.'))
            if f > 0:
                return True
            else:
                return False
        except ValueError:
            return False
            
class racePredictorSet:
    varlist=[]
    PredImputer=[]
    Xscaler=[]
    Predictors=[]
    
    def __init__(self, varlist,PredImputer,Xscaler,Predictors):
    #self.textraw = textraw
        self.description = "Set of"
        self.author = "MZ"        

        self.varlist=varlist
        self.PredImputer=PredImputer
        self.Xscaler=Xscaler
        self.Predictors=Predictors

        
def downloadSingleRace(raceID):
    baseurl='https://wettstar.de'
    downurl=baseurl+'/race?id='+str(raceID)
    #Print today's date 
    print("Start: ImportnPredic Single Race: "
           +downurl)
    
    #Define Header for Login (required in order to get Formen)
    oriheader={
    'Host':
        'wettstar.de', #non-crucial
    'User-Agent':
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.10; rv:45.0)\
        Gecko/20100101 Firefox/45.0', #non-crucial
    'Accept':
        'application/json, text/javascript, */*; q=0.01', #non-crucial
    'Accept-Language':
        'de,en-US;q=0.7,en;q=0.3', #non-crucial
    'Accept-Encoding':
        'gzip, deflate, br', #non-crucial
    'Content-Type':
        'application/x-www-form-urlencoded; charset=UTF-8',#, #crucial
    'Connection':
        'keep-alive' #non-crucial
    }
    payload ={
        'username':'Zunhias',
        'password':'Paranoia23#'
    }
    #Download race and associated formen
    racesheets=[]
    formen=[]
    formPTRN= "window.open\(\'(.+?)', \'Formguide\'";
    #For each race location...
    try: 
        #Open new session...
        with requests.Session() as s:              
            p = s.post('https://wettstar.de/auth/validatepostajax',
                       headers = oriheader,
                       data=payload) #, data=json.dumps(payload2)
        # Check if login was successful
            if not re.search('"login":true',p.text):
                #print(p.text) #Login-response received
                sys.exit("LOGIN FAILED")
        #For each single race at race location...
            #Get current racesheet
            racesheets.append(s.get(downurl,
                                    headers = oriheader,
                                    cookies=s.cookies))
            #Get horseformen urls for that race
            horseform_urls=(re.findall(formPTRN,
                                       racesheets[-1].text))
            curr_formen=[]
            #Get horseformen-sheets for that race
            for (k, horseform_url) in enumerate(horseform_urls):
                curr_formen.append(s.get(baseurl+horseform_url,
                                         headers = oriheader,
                                         cookies=s.cookies))
            formen.append(curr_formen)
            print("Time: "
                  +str(time.monotonic())
                  +" "+downurl
                  +"   n Formen: "+str(len(curr_formen)))
    #Exception of Request
    except requests.exceptions.RequestException as e:
        print(e)
    ### END OF DOWNLOAD START OF EXTRACT
    print("End of Download start of extract")
    if len(racesheets)==len(formen):
        racelist=[Race(r.text,f) for r,f in zip(racesheets,formen)]
    else:
        print('RACESHEETS AND FORMEN HAVE DIFFERENT LENGTH')
    return racelist,racesheets,formen        

        
def loadSingleRace(raceID,racetime='past'):
    if racetime is 'past':
        racelistFolder='/Users/matthiaszunhammer/Dropbox/PY/HorseRacing/pastraces/'
    elif racetime is 'future':  
        racelistFolder='/Users/matthiaszunhammer/Dropbox/PY/HorseRacing/futureraces/'
    else:
        print('Error: racetime not set as ''past'' or ''future''. Please select whether you want past or future racepickle loaded')
    
    with open(racelistFolder+raceID+'.pickle','rb') as rf: 
            r_raw=pickle.load(rf)
    return r_raw
    
        
def loadRacePickleAsDF(racetime='past',racetype = 'Flachrennen'):
    # Function that 
    # a) loads the pickle containing tomorrows race objects and
    # b) extracts a table from the race objects
    # c) Returns either Flachrennen (default) or Trabrennen
    if racetime is 'past':
        racelistFolder='/Users/matthiaszunhammer/Dropbox/PY/HorseRacing/pastraces/'
    elif racetime is 'future':  
        racelistFolder='/Users/matthiaszunhammer/Dropbox/PY/HorseRacing/futureraces/'
    else:
        print('Error: racetime not set as ''past'' or ''future''. Please select whether you want past or future racepickle loaded')
    
    allfiles = []
    for (dirpath, dirnames, filenames) in walk(racelistFolder):
        allfiles.append(filenames)
        break
    allfiles = allfiles[0]
    
    r_raw=[]
    for file in allfiles:
        with open(racelistFolder+file,'rb') as rf: 
            r_raw.append(pickle.load(rf))
        
    # BRING RACE CLASSES IN SHAPE / COUNT
    # Flatten list
    print("Aufgezeichnete Renntage: " + str(len(r_raw)))
    r=flatten(r_raw)
    print("Aufgezeichnete Rennen: " + str(len(r)))
    # Extract basic info ahead
    rNos=[races.raceID for races in r]
    # Identify duplicate races
    dupli_r=[k for k,v in collections.Counter(rNos).items() if v>1]
    print("Duplicate Entries: "+str(len(dupli_r)))
    # Count number of Flach- and Trabrennen

    #HERE ARE THE TRABRENNEN
    
        
    #EXPORT TO PANDAS DATAFRAME
    drf=[]
    if racetype is 'Flachrennen':
            #HERE ARE THE FLACHRENNEN
        rf=[races for races in r if races.rtype=="Flach"]
        print("Aufgezeichnete Flachrennen: " + str(len(rf)))
        # drf=[races.dfexport() for races in rf] # Faster but failing if race instances are erronenous
        for races in rf:
            #print(races.raceID)
            try:
                drf.append(races.dfexport())
            except:
                print('Error in Df Export of '+ str(races.raceID))        
    elif racetype is 'Trabrennen':
            #HERE ARE THE FLACHRENNEN
        rf=[races for races in r if races.rtype=="Trab"]
        print("Aufgezeichnete Trabrennen: " + str(len(rf)))
        # drf=[races.dfexport() for races in rf]
        for races in rf:
            #print(races.raceID)
            try:
                drf.append(races.dfexport())
            except:
                print('Error in Df Export of '+ str(races.raceID))    
    else:
        print("Input variable racetype specified incorrectly. Either enter ""Flachrennen"" (default) or ""Trabrennen""")
        drf=[]
        
    drf=pd.concat(drf,ignore_index=True)
    df=drf.drop_duplicates(keep='last')
    return df
    
    
def preproRaceDF(df,racetime='past'):  
    df = df.drop(df[df.nonrunners==1].index)
    df = df.drop(df[df.raceID==1].index) #Drop races with invalid raceID)
    
    # Derive categorical variables to creaty dummy variables
    # Clean sex ;)
    df.sex=df.sex.str.strip()
    df.loc[(df.sex!='Hengst')&(df.sex!='Stute')&(df.sex!='Wallach'),'sex']=np.nan#'NaN' #First clean all odd sexes
    df.sex=df.sex.astype('category',categories=["Hengst","Stute","Wallach"])
    dd=pd.get_dummies(df[['sex']], prefix='dummy', prefix_sep='_', dummy_na=False, sparse=False, drop_first=False)
    # Country
    df.country=df.country.astype('category')

    #add dummy variables to df
    dd=pd.get_dummies(df[['sex','country']], prefix='dummy', prefix_sep='_', dummy_na=False, sparse=False, drop_first=False)
    df = pd.concat([df,dd], axis=1)
    
    # Calculate uninformed and informed probabilities based on starters and odds
    #Wettstar provides decimal (European) odds, i.e. potential winnings (net returns) + the stake (e.g. 6/5 or 1.2 plus 1 = 2.2). " See: https://en.wikipedia.org/wiki/Odds#Odds_against "
    df=df.assign(p_starters = 1/df.real_starters)
    df=df.assign(p_real_starters = 1/df.real_starters)
    df=df.assign(p_odds = 1/(df.odds))
    
    # Replace "HiFi" Horse-Forms with "LoFi" Horse-Forms if NaN
    df.loc[np.isnan(df['meanodds']),'meanodds']= df.loc[np.isnan(df['meanodds']),'lofi_meanodds']
    df.loc[np.isnan(df['trendodds']),'trendodds']= df.loc[np.isnan(df['trendodds']),'lofi_trendodds']
    df.loc[np.isnan(df['pastpl1']),'pastpl1']= df.loc[np.isnan(df['pastpl1']),'lofi_pastpl1']
    df.loc[np.isnan(df['pastpl2']),'pastpl2']= df.loc[np.isnan(df['pastpl2']),'lofi_pastpl2']
    df.loc[np.isnan(df['pastpl3']),'pastpl3']= df.loc[np.isnan(df['pastpl3']),'lofi_pastpl3']
    df.loc[np.isnan(df['pastpl4']),'pastpl4']= df.loc[np.isnan(df['pastpl4']),'lofi_pastpl4']
    df.loc[np.isnan(df['pastpl5']),'pastpl5']= df.loc[np.isnan(df['pastpl5']),'lofi_pastpl5']
    
    #Clean absurd weights
    df.loc[(df.weights<10),'weights']=np.nan#'NaN' #First clean all odd sexes
    df.loc[(df.weights>150),'weights']=np.nan#'NaN' #First clean all odd sexes
    
    #Clean absurd ages
    df.loc[(df.ages>25),'ages']=np.nan#'NaN' #First clean all odd sexes
    df.loc[(df.ages<0),'ages']=np.nan#'NaN' #First clean all odd sexes
    
    #Clean absurd past-places
    df.loc[(df.pastpl1>35),'pastpl1']=35#
    df.loc[(df.pastpl2>35),'pastpl2']=35#
    df.loc[(df.pastpl3>35),'pastpl3']=35#
    df.loc[(df.pastpl4>35),'pastpl4']=35#
    df.loc[(df.pastpl5>35),'pastpl5']=35#

    #Clean absurd starternumbers
    df.loc[df.real_starters<3,'real_starters']=np.nan

    #Normalize Age
    #df.logages=np.log(df.ages+1)
    df=df.assign(logages = np.log(df.ages+1))
    
    #Normalize meanodds
    df=df.assign(logmeanodds = np.log(df.meanodds+1))
    
    #Normalize Trendodds
    df=df.assign(sqrttrendodds = np.nan)
    #df=df.assign(sqrttrendodds = np.log(1/np.sqrt(df.trendodds-100)))
    
    with warnings.catch_warnings(): #Just to suppress NaN warning in case only NaN data are available for a given race
        warnings.simplefilter("ignore", category=RuntimeWarning) #Just to suppress NaN warning in case only NaN data are available for a given race
        byID=df.groupby('raceID')
        df=df.assign(WIages=byID['ages'].transform(lambda x: x-np.nanmean(x)))
        df=df.assign(WIlogages=byID['logages'].transform(lambda x: x-np.nanmean(x)))
        df=df.assign(WImeanodds=byID['meanodds'].transform(lambda x: x-np.nanmean(x)))
        df=df.assign(WItrendodds=byID['trendodds'].transform(lambda x: x-np.nanmean(x)))
        df=df.assign(WIweights=byID['weights'].transform(lambda x: x-np.nanmean(x)))
        df=df.assign(WImeanodds=byID['meanodds'].transform(lambda x: x-np.nanmean(x)))
        df=df.assign(WIpastpl1=byID['pastpl1'].transform(lambda x: x-np.nanmean(x)))
        df=df.assign(bookieMargin=byID['p_odds'].transform(lambda x: (np.sum(x)-1) if np.sum(x)>1 else 'nan'))
        df=df.assign(knwn_finish=byID['finish'].transform(lambda x: np.sum(~np.isnan(x))))
        df=df.assign(mssng_finish=byID['finish'].transform(lambda x: np.sum(np.isnan(x))))
        
        
    # DROP RACES WHERE THERE IS A NEGATIVE BOOKIE-MARGIN (indicative of erronenous odds)    
    df = df.drop(df[df.bookieMargin<0].index) #Drop races with invalid raceID)    
    
    # DEFINE TARGET VARIABLE!!!
    # For Classification    
    df=df.assign(winners = 0) # Usually using one unit per bet
    df.loc[df.finish==1,'winners']= 1
    # To predict winners
    df=df.assign(winnings = -1) # Usually using one unit per bet
    df.loc[df.finish==1,'winnings']= df.odds[df.finish==1]-1 # ATTENTIONE: Winning horses get you A NET WIN OF ODDS MINUS YOUR BETSUM (! YOU HAVE TO SPEND MONEY FIRST, BEFORE GETTING THE RETURN)
      
    return df
    
def elastic_predict(df,predset):
    Xraw=df[predset.varlist].as_matrix()
    nanrowsX=np.isnan(Xraw).any(axis=1)
    print('For Xpure, ', str(sum(nanrowsX)), 'rows()', str(sum(nanrowsX)/len(nanrowsX)*100),'%) out of', str(len(nanrowsX)), 'were dropped.')
    df=df.drop(df[nanrowsX].index)    
    X=df[predset.varlist].as_matrix()
    mdl=linear_model.ElasticNetCV(l1_ratio=[1], #[.1, .5, .9, .99, .999, 1]
                          fit_intercept=True,
                          normalize=False)
    mdl.intercept_=predset.Predictors[0]
    mdl.coef_=predset.Predictors[1]
    predicted_values=mdl.predict(X)
    df=df.assign(pred_y=predicted_values)
    return df
   
def elastic_predict_odds(df,predset):
    # Odds have to be represented by first coefficient
    X=df[predset.varlist[1:]].as_matrix() #exclude odds from varlist
    mdl=linear_model.ElasticNetCV()
    mdl.intercept_=predset.Predictors[0]
    mdl.coef_=predset.Predictors[1][1:] #exclude odds from prediction
    predicted_odds=(mdl.predict(X)/(predset.Predictors[1][0]))*1 #scale by predicted odds
    return predicted_odds   
    
def rescale_coefs(intercept,coefficient_list,scaler): # Used to rescale estimated coefs AND intercept
    intercept = intercept - np.dot(coefficient_list, scaler.mean_/scaler.scale_)
    coefficient_list=np.true_divide(coefficient_list,  scaler.scale_)
    return intercept, coefficient_list
    
def betting_suggestion(df):
    #For each race get horse with best prediction
    with warnings.catch_warnings(): #Just to suppress NaN warning in case only NaN data are available for a given race
        warnings.simplefilter("ignore", category=RuntimeWarning) #Just to suppress NaN warning in case only NaN data are available for a given race
        byID=df.groupby('raceID')
        df=df.assign(bestpred=byID['pred_y'].transform(lambda x: x==max(x)))
    #For each race decide to bet if best prediction > 0 (indicating gain)
    df=df.assign(bets=False)
    df.loc[(df.pred_y>0)&(df.bestpred==1),'bets']=True
    #For each race calculate the suggested betsum in money units
    df=df.assign(betsum=df.pred_y[df.bets]*10)
    df.loc[np.isnan(df.betsum),'betsum',]=0
    df.loc[(df.betsum>0)&(df.betsum<1),'betsum']=1 #account for the fact that minimum betsum is 1
    return df









def cols_from_html_tbl(tbl):  #Helper function for extracting columns from html-table tbl (table must be passed as Results-Object from BeautifulSoup)
    rows = tbl.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        for i,cell in enumerate(cols):
            if not'col_list' in locals():
                col_list=[[] for x in range(len(cols))]
            col_list[i].append(cell.text)
    return col_list

def isnumber(s): # Function checks if string can be converted to float and is >0
    try:
        f=float(s.replace(',','.'))
        if f > 0:
            return True
        else:
            return False
    except ValueError:
        return False
    
def extract(requests_instance,verbose=False):
    html = BeautifulSoup(requests_instance[0].content,'html5lib')

    #Basic html segments
    top_container=html.find('div',{'id':'racecardTopContainer'})
    race_info_box=top_container.find('div',{'class':'racesList'})
    racecard=html.find('div',{'class':'racecardList'}) #single horse containers
    
    #Race-specific data
    raceID=int(top_container["data-raceid"]) #or get directly from import script?
    
    starter=race_info_box.find('li',{'class':'starter'}).text
    starter=int(starter.split()[0])
    
    dateraw=top_container.h1.text.split()[-1]
    rday=datetime.strptime(dateraw,'%d.%m.%Y')

    timeraw=race_info_box.find('li',{'class':'time'}).text
    rtime=datetime.strptime(timeraw,'%H:%M')

    country_raw=top_container.h2.a['href']
    country=re.findall('/races\?country=(...)&date=',country_raw)
    country=country[0]

    rname=top_container.h2.text.strip()
    
    dist=race_info_box.find('li',{'class':'distance'}).text
    dist=float(dist.split()[0])

    stakes=race_info_box.find('li',{'class':'stakes'}).text
    stakes=float(stakes.split()[0])
    
    ground=race_info_box.find('li',{'class':'raceGround'}).text
    ground=str(ground)
    
    race_type_allowance=race_info_box.find('div',{'class':'raceTypeAllowance'}).text
    race_type_allowance=str(race_type_allowance)   # Verbose version of race_type written in box
    
    race_type_symbol=top_container.i["class"]     # Short version of race_type from symbol (may miss steeplechase with hurdles)
    if race_type_symbol[0] is 'T':
        rtype='Flach' # Oddly, Flachrennen get a 'T' by germantote
    elif race_type_symbol[0] is 'H':
        rtype='Trab' # Oddly, Trabrennen get a 'H' by germantote
    else:
        rtype=2 # "Other"

    rnum=int(race_info_box('div',{'class':'counter'})[0].text.strip())

    stakes_raw=race_info_box.find('li',{'class':'stakes'}).text
    stakes=float(stakes_raw.split()[0])
    stakes_currency=stakes_raw.split()[1]

    #Extract horse-specific data from racesheet
    horse_clearfixes=racecard.find_all('li',{'class','clearfix'})
    nonrunners=[True if 'nonrunner' in i['class'] else False for i in horse_clearfixes]

    starterNo1=html.find_all('span',{'class':'count1'})
    starterNo1=[i.text for i in starterNo1]
    
    starterNo2=html.find_all('span',{'class':'count2'})
    starterNo2=[i.text for i in starterNo2]
    
    horsenames=html.find_all('span',{'class':'runnername'})
    horsenames=[i.text.strip() for i in horsenames]

    jockeynames=html.find_all('span',{'class':'jockeyname'})
    jockeynames=[i.text.strip() for i in jockeynames]

    jockeytrainers=html.find_all('div',{'class':'jockeytrainer'})
    jockeytrainers=[i.text.strip() for i in jockeytrainers]

    statInfo=html.find_all('div',{'class':'statInfo'})
    heritage=[]
    owners=[]
    for i in statInfo:
        heritage.append(i.span.nextSibling)
        owners.append(i.span.nextSibling.nextSibling.nextSibling)
    heritage=[re.split('–',i) for i in heritage]
    heritages1=[i[0].strip() for i in heritage]
    heritages2=[i[1].strip() for i in heritage]
    
    weights=html.find_all('span',{'class':'weight'})
    weights=[i.text.split()[0].strip() for i in weights]
    weights=[float(i.replace(',','.')) for i in weights]
    
    age_and_sex=html.find_all('span',{'class':'horseage'})
    age_and_sex=[x.text.split('j. ') for x in age_and_sex]
    age=[float(i[0]) for i in age_and_sex]
    sex=[i[1] for i in age_and_sex]

    odds=html.find_all('span',{'class':'odds'})
    odds=[float(i.text.replace(',','.').replace('-','NaN')) for i in odds]

    #Low-Fidelity ("lofi") horse history from "Formen" shown on racesheet.(formen-tables in the HiFi "Formen"-Subpages were empty from July 2016 on...)       
    
    
    past_dates=[]
    lofi_pastfinish=[]
    past_racedates=[]
    past_race_courses=[]
    past_dist=[]
    past_stakes=[]
    past_jockey=[]
    past_odds=[]
    
    for horse in horse_clearfixes:
        currtable=(cols_from_html_tbl(horse.table))
        
        raw_past_date=[datetime.strptime(i,'%d.%m.%y') for i in currtable[0]]
        past_dates.append(raw_past_date)
        
        raw_pastfinish=[float(i.strip('.')) if isnumber(i.strip('.')) else float('nan') for i in currtable[1]]        
        lofi_pastfinish.append(raw_pastfinish)
        lofi_places=lofi_pastfinish #for backwards-compatibility
        
        past_race_courses.append(currtable[2])
        
        raw_pastdist=[float(i.strip(' m')) if isnumber(i.strip(' m')) else float('nan') for i in currtable[3]]        
        past_dist.append(raw_pastdist)

        raw_paststakes=[float(i) if isnumber(i) else 'nan' for i in currtable[4]]        
        past_stakes.append(raw_paststakes)
        
        past_jockey.append(currtable[5])
        
        raw_pastodds=[float(i.replace(',','.')) if isnumber(i) else 'nan' for i in currtable[6]]        
        past_odds.append(raw_pastodds)

        lofi_nracesrun=len(currtable[0])

        lofi_meanplace=[float(nanmean(horse))
                             if len(horse) > 0 else float('nan')
                             for horse in lofi_places]
             
#             
#             if len(self.lofi_meanplace)!=self.starters:
#                 print('Error only '+str(len(self.lofi_meanplace))+ ' lofi_meanplace.')
#            
#             self.lofi_pastodds=[[float(row[6].replace(',','.').replace('-','nan')) if self.isnumber(row[6]) else float('nan')
#                    for row in horse]
#                    for horse in lofi_formencells]         
#             if len(self.lofi_pastodds)!=self.starters:
#                 print('Error only '+str(len(self.lofi_pastodds))+ ' lofi_pastodds.')
#            
#             self.lofi_meanodds=[float(nanmean(horse)) if len(np.array(horse)) > 0 else float('nan')
#                    for horse in self.lofi_pastodds]
#             if len(self.lofi_meanodds)!=self.starters:
#                 print('Error only '+str(len(self.lofi_meanodds))+ ' lofi_meanodds.')
#             lofi_mdl=linear_model.LinearRegression()
#             self.lofi_trendodds=[lofi_mdl.fit(np.arange(0,
#                                              len(np.array(horse)[~np.isnan(horse)]),
#                                                1).reshape(-1,1),np.array(horse)[~np.isnan(horse)].reshape(-1, 1)).coef_[0][0]
#                                        if len(np.array(horse)[~np.isnan(horse)])>1
#                                        else float('nan')
#                                    for horse
#                                    in self.lofi_pastodds]
#             if len(self.lofi_trendodds)!=self.starters:
#                 print('Error only '+str(len(self.lofi_trendodds))+ ' lofi_trendodds.')
#                  
#    def getformen(self,formen):
#        formentables=[re.findall(
#                        '(<h2 class="clearfix">\s+Form\s+</h2>\s+<div class="scrollWrapper">\s+<div class="innerWrapper">\s+<table class="formTable">.*?</table>)',
#                        form.text,re.S)
#                      for form
#                      in formen]
#        #self.formentables=formentables
#        formenrows=[re.findall('<tr>(.*?)</tr>',formtable[0],re.S) for formtable in formentables]
#        self.pastfinish=[[re.findall(
#                    '<(?:th|td).*?>(?:<span.*?>)?(.*?)(?:</span>)?</(?:th|td)>',
#                    row,re.S)
#                         for row in rows]
#                         for rows in formenrows]
#        self.nracesrun=[len(horse)-1 for horse in self.pastfinish]  #counts previous races, subtracts headerline
#        if len(self.nracesrun)!=self.starters:
#            print('Error only '+str(len(self.nracesrun))+ ' nracesrun.')
#        # Get places as float
#        self.places=[[float(row[2])
#                                if self.isnumber(row[2])
#                                else float('nan')
#                            for row in horse[1:]]
#                        for horse in self.pastfinish]
#        with warnings.catch_warnings(): #Just to suppress NaN warning in case only NaN data are available for a given race
#             warnings.simplefilter("ignore", category=RuntimeWarning) #Just to suppress NaN warning in case only NaN data are available for a given race
#
#             # Calculate mean if not empty
#             self.meanplace=[nanmean(horse)
#                                if len(np.array(horse)[~np.isnan(horse)]) > 0
#                                else float('nan')
#                            for horse in self.places]
#             if len(self.meanplace)!=self.starters:
#                 print('Error only '+str(len(self.meanplace))+ ' meanplace.')
#            
#             self.pastodds=[[float(row[6].replace(',','.').replace('-','nan'))
#                                    if self.isnumber(row[2])
#                                    else float('nan')
#                                for row in horse[1:]]
#                            for horse in self.pastfinish]
#             self.meanodds=[nanmean(horse)
#                           if len(np.array(horse)[~np.isnan(horse)]) > 0
#                           else float('nan')
#                           for horse in self.pastodds]
#             if len(self.meanodds)!=self.starters:
#                 print('Error only '+str(len(self.meanodds))+ ' meanodds.')
#    
#             mdl=linear_model.LinearRegression()
#             self.trendodds=[
#                            mdl.fit(
#                                    np.arange(0,
#                                              len(np.array(horse)[~np.isnan(horse)]),
#                                              1).reshape(-1,1),np.array(horse)[~np.isnan(horse)].reshape(-1, 1)).coef_[0][0]
#                                if len(np.array(horse)[~np.isnan(horse)])>1
#                                else float('nan')
#                            for horse
#                            in self.pastodds]
#             if len(self.trendodds)!=self.starters:
#                 print('Error only '+str(len(self.trendodds))+ ' trendodds.')
#        #Macht noch trouble:    
#        #self.days_since_last_race=[
#        #    (self.rday-datetime.strptime(horse[1][0],
#        #                                '%d.%m.%Y')).days
#        #        if (horse[1][0])
#        #        else float('nan')
#        #    for horse
#        #    in self.pastfinish]


#        #Extract finish-data
#        finish_raw=re.findall(
#            '<table class="finishTable">.*?</table>',
#            textraw,re.S)#get finishtable
#        #self.finish_raw=finish_raw
#        if finish_raw:
#            trows=re.findall(
#                '<tr>(.*?)</tr>',
#                finish_raw[0],
#                re.S) #gets all table rows
#            self.finishall=[re.findall('<(?:th|td) .*?>(.*?)</(?:th|td)>',
#                                row,re.S)
#                            for row 
#                            in trows] #gets all table headers or table cells for each row
#            self.finisherNames=([x[2]
#                             for x
#                             in self.finishall[1:]]) # gets finisher's starter numbers from second row on in second column
#            self.finishersRaw=([x[1]
#                             for x
#                             in self.finishall[1:]]) # gets finisher's starter numbers from second row on in second column
#            self.placementsRaw=([int(x[0])
#                             for x
#                             in self.finishall[1:]])
#        
#            self.finishers=[float('nan')] * self.starters
#            #VERSION 1:
#            #fill all fields with mean finish of all starters not placed
#            #PROBLEM: will systematically affect relationship between starters and finish >> starter only useful as a predictor of winners
#            self.fillfinish=[np.mean([self.starters-sum(self.nonrunners),
#                              1+len(self.finishersRaw)])]* self.starters
#            #VERSION 2:
#            #fill all fields with nan
#            #PROBLEM: more horses will be dropped
#            #self.fillfinish=[float('nan')]* self.starters
#            #VERSION 3:
#            #fill all fields with random numbers
#            #PROBLEM: random variance added
#            #IMPLEMENTED IN ANALYSIS-PRE-PROCESSING
#            if self.finisherNames: # in case finisher list has names
#                for i,finny in enumerate(self.finisherNames):
#                    finindex=self.horsenames.index(finny)#get index of finisher 
#                    self.finishers[finindex]=self.placementsRaw[i]
#                    self.fillfinish[finindex]=self.placementsRaw[i]
#            elif self.finishersRaw:
#                for i,finny in enumerate(self.finishersRaw):
#                    finindex=self.starterNo1.index(finny)#get index of finisher 
#                    self.finishers[finindex]=self.placementsRaw[i]
#                    self.fillfinish[finindex]=self.placementsRaw[i]
#        else:
#            self.finishall=[]
#            self.finishersRaw=[]
#            self.finishers=float('nan')
#            self.fillfinish=float('nan')