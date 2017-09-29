import pymongo
import re

from datetime import datetime
from bs4 import BeautifulSoup

from hracing.tools import cols_from_html_tbl
from hracing.tools import isnumber
from hracing.tools import bf4_text # checks if bf4 elements exist
from IPython.core.debugger import set_trace

#### DATA PARSING AND INPUT TO DB        

def parse_racesheet(racesheet,forms,verbose = False):
    """ Parse html in racesheet, get content, return race as hierarchical dict """
    #Parse racesheet and get basic html segments
    html = BeautifulSoup(racesheet.content,'html5lib')
    race = _parse_race_level(html)
    race["horses"] = _parse_horse_level(html,forms)
    race["finish"] = _parse_finish(html)
    return race

def _parse_race_level(html):
    #Extract race-level data from html, return as dict
    top_container = html.find('div',{'id':'racecardTopContainer'})
    race_info_box = top_container.find('div',{'class':'racesList'})
    race = {}
    race['race_ID'] = int(top_container["data-raceid"])
    n_starter_raw = bf4_text(race_info_box.find('li',{'class':'starter'}))
    race['n_starter'] = int(n_starter_raw.split()[0]) if n_starter_raw else 0
    dateraw = bf4_text(top_container.h1).split()[-1]
    timeraw = bf4_text(race_info_box.find('li',{'class':'time'}))
    race['race_date_time'] = datetime.strptime(dateraw + '_' + timeraw,'%d.%m.%Y_%H:%M')
    country_raw = top_container.h2.a['href']
    country = re.findall('/races\?country\s*=\s*(...)&date\s*=',country_raw)
    race['country'] = country[0]
    race['race_name'] = bf4_text(top_container.h2).strip()
    distance = bf4_text(race_info_box.find('li',{'class':'distance'}))
    race['distance'] = float(distance.split()[0]) if distance else float('nan')
    race['ground']=bf4_text(race_info_box.find('li',{'class':'raceGround'}))
    race['type_long'] = bf4_text(race_info_box.find('div',{'class':'raceTypeAllowance'}))
    race['type_short'] = top_container.i["class"][1]
    race['race_number'] = int(bf4_text(race_info_box('div',{'class':'counter'})[0]).strip())
    stakes_raw = bf4_text(race_info_box.find('li',{'class':'stakes'}))
    race['stakes'] = float(stakes_raw.split()[0].replace('.','')) if stakes_raw else float('nan')
    race['currency'] = stakes_raw.split()[1] if len(stakes_raw.split())>1 else ""
    return race

def _parse_horse_level(html,forms):
    #Parse html for racecards, return a list of dicts with horse-level info
    racecard = html.find('div',{'class':'racecardList'}) #single horse containers
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
    for i,clearfix in enumerate(horse_clearfixes):
        horse={}
        horse['nonrunner'] =  True if 'nonrunner' in horse_clearfixes[i]['class'] else False
        horse['starter_no1'] =bf4_text(raw_starter_no1[i])
        horse['starter_no2'] =bf4_text(raw_starter_no2[i])
        horse['name'] = bf4_text(raw_name[i]).strip()
        # Avoid writing horses without a name...
        if horse['name'].strip(): 
            horse['jockey'] = bf4_text(raw_jockey[i]).strip()
            horse['trainer'] = bf4_text(raw_trainer[i]).strip()
            heritage = statInfo[i].span.nextSibling
            heritage = re.split('–',heritage)
            horse['heritage1'] = heritage[0].strip()
            horse['heritage2'] = heritage[1].strip()
            horse['owner'] = statInfo[i].span.nextSibling.nextSibling.nextSibling
            weight = bf4_text(raw_weight[i]).split() if raw_weight else ""
            horse['weight'] = float(weight[0].strip().replace(',','.')) if weight else float('nan')
            age_and_sex = bf4_text(raw_age_and_sex[i])
            horse['age'] = float(age_and_sex.split('j. ')[0]) if age_and_sex else float('nan')
            horse['sex'] = age_and_sex.split('j. ')[1] if  age_and_sex else ""
            odd_txt = bf4_text(raw_odd[i])
            horse['odd'] = float(odd_txt.replace(',','.').replace('-','nan')) if odd_txt else float('nan')
            horse['short_forms']=_extract_short_forms(clearfix.table)
            horse['long_forms'] = _extract_long_forms(forms[i])
        else:
           print('Warning: Horse with name: could not be parsed properly.')
           horse = {}
        horse_list.append(horse)
    return horse_list

def _extract_short_forms(formen_table):
    #Extract forms (prior race performance) from tables in racecards. If there are no prior formen, there are is no table...
    if formen_table is not None:
        currtable = cols_from_html_tbl(formen_table)
        short_form={}
        short_form['past_racedates'] = [datetime.strptime(i,'%d.%m.%y') for i in currtable[0]]
        short_form['past_finishes'] = [float(i.strip('.')) if isnumber(i.strip('.'))
            else float('nan') for i in currtable[1]]        
        short_form['past_race_courses'] = currtable[2]
        short_form['past_distances'] = [float(i.strip(' m')) if isnumber(i.strip(' m'))
            else float('nan') for i in currtable[3]]        
        short_form['past_stakes'] = [float(i) if isnumber(i)
            else 'nan' for i in currtable[4]]        
        short_form['past_jockeys'] = currtable[5]
        short_form['past_odds'] = [float(i.replace(',','.').replace('-','nan')) if isnumber(i)
            else float('nan') for i in currtable[6]]        
        short_form['n_past_races'] = len(currtable[0])
    else:
        short_form={}
    return short_form

def _extract_long_forms(form):
    form_html = BeautifulSoup(form.content,'html5lib')
    overview = form_html.find('section',{'id':'formguideOverview'})
    form_main = form_html.find('section',{'id':'formguideForm'})
    col = cols_from_html_tbl(form_main.table)
    if col:
        long_form={}
        long_form['past_racedates'] = [datetime.strptime(i,'%d.%m.%Y') for i in col[0]]
        long_form['past_race_courses'] = col[2]
        long_form['past_finishes'] = [float(i.strip('.')) if isnumber(i.strip('.'))
            else float('nan') for i in col[1]]        
        long_form['past_distances'] = [float(i.strip(' m')) if isnumber(i.strip(' m'))
            else float('nan') for i in col[3]]        
        long_form['past_stakes'] = [float(i) if isnumber(i)
            else 'nan' for i in col[4]]        
        long_form['past_jockeys'] = col[5]
        long_form['past_odds'] = [float(i.replace(',','.').replace('-','nan')) if isnumber(i)
            else float('nan') for i in col[6]]        
        long_form['n_past_races'] = len(col[0])
    else:
        long_form={}
    return long_form 

def _parse_finish(html):
    #Parse html, return a list of dicts with finishers
    finish_table = html.find('table',{'class':'finishTable'})
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
    return finish_list
            
        
    ### TODO:
    ### 1.) Function for creating pandas df from mongoDB
    ### 2.)
    ### 3.) DESCRIPTICE GRAPHS FOR PRESENTATION
    ### 3.) ADD FANCY GRAPHS TO DATA DESCRIPTION
    ### 5.) REFACTURE AND IMPELEMENT OLD PIPELINE SETUP AND ML
              
def mongo_insert_race(race):
    """ Take single race, add to local mongoDB, make race_ID index """
    client = pymongo.MongoClient()
    db = client.races
    db.races.create_index([("race_ID", pymongo.ASCENDING)], unique=True)
    results = db.races.insert_one(race)

#### DATA EXTRACTION FROM DB        
def race_to_df(race_dict):
    '''Function that generating a pandas df from a db race entry.
    Df will contain one line per runner with race-level and finish info'''
    # Generate tables with race-level, horse-level, and finsh info 
    race_level_keys=race_dict.keys()-['_id','horses','finish']
    race_generals = { k: race_dict[k] for k in race_level_keys }
    df_race_level=pd.DataFrame(race_generals,index=[race_generals['race_ID']])
    df_horse_level=pd.DataFrame(race_dict['horses'])
    df_finish=pd.DataFrame(race_dict['finish'])
    # Cross join race*horse (for some stupid reason not yet included in pandas so extra temp_keys cludge is needed)
    df_race_level['temp_key']=1
    df_horse_level['temp_key']=1
    df_race_n_horse=pd.merge(df_race_level,df_horse_level,on='temp_key')
    # Left join on starter_no1 to add info on winners
    df=pd.merge(df_race_n_horse,pd_finish[['starter_no1','place']], on='starter_no1',how='left')
    return df
