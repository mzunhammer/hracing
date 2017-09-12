import sqlite3
import pymongo

from datetime import datetime
from bs4 import BeautifulSoup



def parse_racesheet(racesheet,verbose=False):
	 """ Parse html in racesheet, get content, put in mongoDB """
	 
    #Parse racesheet and get basic html segments
    html = BeautifulSoup(requests_instance[0].content,'html5lib')
    top_container=html.find('div',{'id':'racecardTopContainer'})
    race_info_box=top_container.find('div',{'class':'racesList'})
    racecard=html.find('div',{'class':'racecardList'}) #single horse containers
             
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

    ground=race_info_box.find('li',{'class':'raceGround'}).text
    ground=str(ground)
    
    race_type_allowance=race_info_box.find('div',{'class':'raceTypeAllowance'}).text
    race_type_allowance=str(race_type_allowance)   # Verbose version of race_type written in box
    
    race_type_symbol=top_container.i["class"]     # Short version of race_type from symbol (may miss steeplechase with hurdles)

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
        
        lofi_pastodds=[[float(row[6].replace(',','.').replace('-','nan'))
                             if self.isnumber(row[6]) else float('nan')
                             for row in horse]
                             for horse in lofi_formencells]         
            
        lofi_meanodds=[float(nanmean(horse))
                            if len(np.array(horse)) > 0 else float('nan')
                            for horse in self.lofi_pastodds]

		# Put data in hierarchical dict 
		race={raceID=int(top_container["data-raceid"]) #or get directly from import script?
    
    ## CONTINUE HERE AND PUT EVERYTHING ABOVE IN NESTED DICT FOR MONGODB
    #  DELETE ALL "PRECOMPUTED" VALUES
    #  CHECK STYLEGUIDE FOR NAMING
    #  
		{
        {"n_past_races":lofi_nracesrun,   
        "past_racedates":past_stakes,
        "past_finishes":past_stakes,
        "past_race_courses":past_jockey,
        "past_distances":past_jockey,
        "past_stakes":past_jockey,
        "past_jockeys":past_jockey,
		"past_odds":past_odds}
		}
		
    # Call mongoDB and dump race
    client = pymongo.MongoClient()
    db = client.races
    db.races.create_index([("raceID", pymongo.ASCENDING)])
    results=db.races.insert_one(race)
    	
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