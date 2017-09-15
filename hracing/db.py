import pymongo
import re

from datetime import datetime
from bs4 import BeautifulSoup

from hracing.tools import cols_from_html_tbl
from hracing.tools import isnumber

def parse_racesheet(racesheet,verbose = False):
    """ Parse html in racesheet, get content, return race as hierarchical dict """
     
    #Parse racesheet and get basic html segments
    html = BeautifulSoup(racesheet[0].content,'html5lib')
    top_container = html.find('div',{'id':'racecardTopContainer'})
    race_info_box = top_container.find('div',{'class':'racesList'})
    racecard = html.find('div',{'class':'racecardList'}) #single horse containers
    finish_table = html.find('table',{'class':'finishTable'})
    
    #Extract race-level data         
    race_ID = int(top_container["data-raceid"]) #or get directly from import script?
    
    n_starter = race_info_box.find('li',{'class':'starter'}).text
    n_starter = int(n_starter.split()[0])
    dateraw = top_container.h1.text.split()[-1]
    timeraw = race_info_box.find('li',{'class':'time'}).text
    race_date_time = datetime.strptime(dateraw+'_'+timeraw,'%d.%m.%Y_%H:%M')
    
    country_raw = top_container.h2.a['href']
    country = re.findall('/races\?country\s*=\s*(...)&date\s*=',country_raw)
    country = country[0]

    race_name = top_container.h2.text.strip()
    
    distance = race_info_box.find('li',{'class':'distance'}).text
    distance = float(distance.split()[0])

    ground = race_info_box.find('li',{'class':'raceGround'}).text
    ground = str(ground)
    
    race_type_allowance = race_info_box.find('div',{'class':'raceTypeAllowance'}).text
    race_type_allowance = str(race_type_allowance)   # Verbose version of race_type written in box
    
    race_type_symbol = top_container.i["class"][1]    # Short version of race_type from symbol (may miss steeplechase with hurdles)
    race_number = int(race_info_box('div',{'class':'counter'})[0].text.strip())

    stakes_raw = race_info_box.find('li',{'class':'stakes'}).text
    stakes = float(stakes_raw.split()[0])
    currency = stakes_raw.split()[1]
    
    race = {"race_ID": race_ID,
        "n_starter": n_starter,
        "race_date_time": race_date_time,
        "country": country,
        "race_name": race_name,
        "distance": distance,
        "ground": ground,
        "race_type_allowance": race_type_allowance,
        "race_type_symbol": race_type_symbol,
        "race_number": race_number,
        "stakes": stakes,
        "currency": currency
        }
   
    
   #Extract horse-level data
    horse_clearfixes = racecard.find_all('li',{'class','clearfix'})
    raw_starter_no1 = html.find_all('span',{'class':'count1'})
    raw_starter_no2 = html.find_all('span',{'class':'count2'})
    raw_name = html.find_all('span',{'class':'runnername'})
    raw_jockey = html.find_all('span',{'class':'jockeyname'})
    raw_trainer = html.find_all('div',{'class':'jockeytrainer'})
    statInfo = html.find_all('div',{'class':'statInfo'})
    raw_weight = html.find_all('span',{'class':'weight'})
    raw_age_and_sex = html.find_all('span',{'class':'horseage'})
    raw_odd = html.find_all('span',{'class':'odds'})

    horse_list = []
    #Loop over all horses and store corresponding data in dict
    for i,horse in enumerate(horse_clearfixes):
        if 'nonrunner' in horse_clearfixes[i]['class']:
            nonrunner =  True
        else:
            nonrunner =  False 
        starter_no1 =raw_starter_no1[i].text
        starter_no2 =raw_starter_no2[i].text
        name = raw_name[i].text.strip()
        jockey = raw_jockey[i].text.strip()
        trainer = raw_trainer[i].text.strip()
        heritage = statInfo[i].span.nextSibling
        heritage = re.split('–',heritage)
        heritage1 = heritage[0].strip()
        heritage2 = heritage[1].strip()
        owner = statInfo[i].span.nextSibling.nextSibling.nextSibling
        weight = raw_weight[i].text.split()[0].strip()
        weight = float(weight.replace(',','.'))
        age_and_sex = raw_age_and_sex[i].text.split('j. ')
        age = float(age_and_sex[0])
        sex = age_and_sex[1]
        odd = float(raw_odd[i].text.replace(',','.').replace('-','NaN'))
        
        horse_out = {
            "name" : name,
            "nonrunner" : nonrunner,
            "starter_no1" : starter_no1,
            "starter_no2" : starter_no2,
            "jockey" : jockey,
            "trainer" : trainer,
            "heritage1" : heritage1,
            "heritage2" : heritage2,
            "weight" : weight,
            "age" : age,
            "sex" : sex,
            "odd" : odd
            }
        
        #Extract forms (prior race performance) from tables in racecards. If there are no prior formen, there are is no table...
        if horse.table is not None:
            currtable = cols_from_html_tbl(horse.table)
            past_racedates = [datetime.strptime(i,'%d.%m.%y') for i in currtable[0]]
            past_finishes = [float(i.strip('.')) if isnumber(i.strip('.')) else float('nan') for i in currtable[1]]        
            past_race_courses=currtable[2]
            past_distances = [float(i.strip(' m')) if isnumber(i.strip(' m')) else float('nan') for i in currtable[3]]        
            past_stakes = [float(i) if isnumber(i) else 'nan' for i in currtable[4]]        
            past_jockeys = currtable[5]
            past_odds = [float(i.replace(',','.').replace('-','nan')) if isnumber(i) else float('nan') for i in currtable[6]]        
            n_past_races = len(currtable[0])
        else:
            past_racedates = []
            past_finishes = []
            past_race_courses = []
            past_distances = []
            past_stakes = []
            past_jockeys = []
            past_odds = []
            n_past_races = 'nan'
            
        form_out={"n_past_races" : n_past_races,   
                "past_racedates" : past_racedates,
                "past_finishes" : past_finishes,
                "past_race_courses" : past_race_courses,
                "past_distances" : past_distances,
                "past_stakes" : past_stakes,
                "past_jockeys" : past_jockeys,
                "past_odds" : past_odds
                 }
        horse_out['forms']=form_out
        horse_list.append(horse_out)
                       
    race["horses"] = horse_list

    #Extract finish-data
    finish_list = []
    if finish_table is not None: 
        finish_tbl = cols_from_html_tbl(finish_table)
        for i,row in enumerate(finish_tbl[0]):
            place = int(finish_tbl[0][i])
            starter_no1 = finish_tbl[1][i]
            name = finish_tbl[2][i]
            odd = float(finish_tbl[3][i].replace(',','.').replace('-','NaN'))
            jockey = finish_tbl[4][i]
            info = finish_tbl[5][i]
            
            finisher_out={"place" : place,   
                "starter_no1" : starter_no1,
                "name" : name,
                "odd" : odd,
                "jockey" : jockey,
                "info" : info
                 }
            finish_list.append(finisher_out)
            
    race["finish"] = finish_list
    
    return race
    
    ### TODO:
    ### 2.) PERFORM ONE COMPLETE IMPORT RUN ON NEW SITE
    ### 3.) TRANSFER OLD DB TO MONGODB
    ### 4.) ADD FANCY GRAPHS TO DATA DESCRIPTION
    ### 5.) REFACTURE AND IMPELEMENT OLD PIPELINE SETUP AND ML
              
    # Call mongoDB and dump race
def mongo_insert_race(race):
    """ Take single race, add to local mongoDB, make race_ID index """
    client = pymongo.MongoClient()
    db = client.races
    db.races.create_index([("race_ID", pymongo.ASCENDING)])
    results = db.races.insert_one(race)
        

