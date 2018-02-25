import pymongo
import re
import pandas as pd
import numpy as np
import warnings

from statsmodels.tsa.arima_model import ARIMA
from numpy.linalg import LinAlgError
from datetime import datetime
from bs4 import BeautifulSoup
from currency_converter import CurrencyConverter
from datetime import datetime

from hracing.tools import cols_from_html_tbl
from hracing.tools import isnumber
from hracing.tools import bf4_text # checks if bf4 elements exist
from hracing.tools import starter_no_2_int
from hracing.tools import past_place_to_float

from IPython.core.debugger import set_trace #set_trace()

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
        currheader, currtable = cols_from_html_tbl(formen_table)
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
    hdr, col = cols_from_html_tbl(form_main.table)
    if col:
        long_form = {}
        long_form['n_past_races'] = list(range(len(col[0]),0,-1)) #len(col[0])
        long_form['past_racedates'] = [datetime.strptime(i,'%d.%m.%Y')
            for i in col[hdr.index('Datum')]]
        long_form['past_race_courses'] = col[hdr.index('Rennbahn')]
        long_form['past_finishes'] = [float(i.strip('.')) if isnumber(i.strip('.'))
            else float('nan') for i in col[hdr.index('Platz')]]        
        long_form['past_distances'] = [float(i.strip(' m')) if isnumber(i.strip(' m'))
            else float('nan') for i in col[hdr.index('Distanz')]]        
        long_form['past_stakes'] = [float(i) if isnumber(i)
            else 'nan' for i in col[hdr.index('Dotierung')]]        
        long_form['past_odds'] = [float(i.replace(',','.').replace('-','nan')) if isnumber(i)
            else float('nan') for i in col[hdr.index('Ev.-Quote')]]
        try:
            long_form['past_jockeys'] = col[hdr.index('Reiter')]
        except:
            long_form['past_jockeys'] = col[hdr.index('Fahrer')]
            long_form['past_km_time'] = col[hdr.index('KM Zeit')]
    else:
        long_form={}
    return long_form 

def _parse_finish(html):
    #Parse html, return a list of dicts with finishers
    finish_table = html.find('table',{'class':'finishTable'})
    finish_list = []
    if finish_table is not None: 
        finish_hdr, finish_tbl = cols_from_html_tbl(finish_table)
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
    race_level_keys = race_dict.keys() - ['_id','horses','finish']
    race_generals = { k: race_dict[k] for k in race_level_keys }
    df_race_level = pd.DataFrame(race_generals,index=[race_generals['race_ID']])
    df_horse_level = pd.DataFrame(race_dict['horses'])
    df_finish=pd.DataFrame(race_dict['finish'])
    # Cross join race*horse (for some stupid reason not yet included in pandas so extra temp_keys cludge is needed)
    df_race_level['temp_key']=1
    df_horse_level['temp_key']=1
    df_race_n_horse=pd.merge(df_race_level,df_horse_level,on='temp_key')
    # Left join on starter_no1 to add info on winners
    try:
        df=pd.merge(df_race_n_horse,df_finish[['starter_no1','place']], on='starter_no1',how='left')
        df['key']=df['race_ID'].astype('str')+'_'+df['starter_no1']
        df.set_index('key',inplace=True, verify_integrity=False)
        return df
    except KeyError:
        if df_finish.empty:
            print('No finish data for race_ID: '+str(race_dict['race_ID'])+', file skipped.')
        else:
            print('Error extracting race_ID: '+str(race_dict['race_ID'])+' file skipped.')
            set_trace()

def dflean(df):
    #Drop temporary key
    df.drop("temp_key", axis=1, inplace=True)
    #Clean string variables
    df['owner'] = df['owner'].str.strip()
    #Exclude nonsensical entries
    df.drop(df[df["age"].isnull() |
                  (df["age"] < 0) |
                  (df["age"] > 20)].index, axis=0,inplace=True)
    df.drop(df[df["distance"].isnull() |
                  (df["distance"] < 100)].index, axis=0,inplace=True)
    df.drop(df[df["weight"].isnull() |
                  (df["weight"] < 40) |
                  (df["weight"] > 125)].index, axis=0,inplace=True)
    df.drop(df[df["n_starter"].isnull() |
                  (df["n_starter"] < 2) |
                  (df["n_starter"] > 30)].index, axis=0,inplace=True)
    df.drop(df[(~((df["sex"] == "Stute") |
                    (df["sex"] == "Hengst") |
                    (df["sex"] == "Wallach")))].index, axis=0,inplace=True)
    # Categorize race type. CAVE: Order below matters!
    df['race_type']='flat' # Flat is default
    df.loc[(df['type_short']=='T') &
             (df['type_long'].str.contains('Hürdenrennen')),'race_type']='hurdle'
    df.loc[(df['type_short']=='T') &
             (df['type_long'].str.contains('Jagdrennen')),'race_type']='hunt'
    df.loc[(df['type_short']=='T') &
             (df['type_long'].str.contains('Verkaufsrennen')),'race_type']='sale' # Verkaufsrennen overwrites the former!
    df.loc[df['type_short']=='H','race_type']='harness' # =TRABRENNEN Harness is default if type_short=='H'
    # Assign categorical types
    df["sex"] = df["sex"].astype('category')
    df["country"] = df["country"].astype('category')
    df["race_name"] = df["race_name"].astype('category')
    df["type_short"] = df["type_short"].astype('category')
    df['race_type'] = df["race_type"].astype('category')
    # Assign numeric types
    df['starter_no1_int']=df['starter_no1'].apply(starter_no_2_int)
    df['starter_no2_int']=df['starter_no2'].apply(starter_no_2_int)
    # Calculate uninformed and informed probabilities based on starters and odds
    # Odds are provided as decimal (European) odds, i.e.
    # potential winnings (net returns) + the stake (e.g. 6/5 or 1.2 plus 1 = 2.2).
    # " See: https://en.wikipedia.org/wiki/Odds#Odds_against "
    df['p_starter'] = (1/(df['n_starter']))
    df['p_odd'] = (1/(df['odd']))
    # Derivatives of place
    # Derivate outcomes
    df=df.assign(winner = 0) # Usually using one unit per bet
    df.loc[df['place']==1,'winner']= 1 # Winner (for classification)
    # Winner*Odds > Winnings (for regression)
    df=df.assign(winning = -1) # Usually using one unit per bet
    df.loc[df['place']==1,'winning']= df.odd[df['place']==1]-1 # ATTENTIONE: Winning horses get you A NET WIN OF ODDS MINUS YOUR BETSUM (! YOU HAVE TO SPEND MONEY FIRST, BEFORE GETTING THE RETURN)
    # Convert Currencies
    df.loc[(df["currency"]=="") & (df["country"]=="DEU"),"currency"]="EUR"
    df.loc[(df["currency"]=="") & (np.isclose(df["stakes"],0)),"currency"]="EUR"
    df["currency"].replace(to_replace="S$", value="SGD",inplace=True)
    df["currency"].replace(to_replace="Eur", value="EUR",inplace=True)
    df["currency"].replace(to_replace="AED", value="",inplace=True)
    df.drop(df[df["currency"]==""].index, axis=0,inplace=True)
    df["currency"]=df["currency"].astype('category')
    c=CurrencyConverter()
    df["stakes_eur"]=[c.convert(row["stakes"], row['currency'], 'EUR') for _,row in df.iterrows()]
    
    # Calculate within-race versions of predictor variables
    with warnings.catch_warnings(): #Just to suppress NaN warning in case only NaN data are available for a given race
        warnings.simplefilter("ignore", category=RuntimeWarning) #Just to suppress NaN warning in case only NaN data are available for a given race
        byID=df.groupby('race_ID')
        df=df.assign(WIage=byID['age'].transform(lambda x: x-np.nanmean(x)))
        df=df.assign(WIweight=byID['weight'].transform(lambda x: x-np.nanmean(x)))
        df=df.assign(bookieMargin=byID['p_odd'].transform(lambda x: (np.sum(x)-1) if np.sum(x)>1 else 'nan'))
    return df
# DROP RACES WHERE THERE IS A NEGATIVE BOOKIE-MARGIN (indicative of erronenous odds)    
#    df = df.drop(df[df.bookieMargin<0].index) #Drop races with invalid raceID)    

    
def long_form_dict_to_df(l_form):
    if l_form:
        df_l_form=pd.DataFrame(l_form)
        #1. Correct wrong import of past_finishes (saved as str in the past_race_courses column...)
        if df_l_form['past_finishes'].isnull().all():
            df_l_form['past_finishes']=df_l_form['past_race_courses'].apply(past_place_to_float)
            if not df_l_form['past_finishes'].isnull().all():
                df_l_form['past_race_courses']='NaN'
        df_l_form.loc[df_l_form['past_finishes']==0,'past_finishes']=float('NaN') # C
        #2. Correct wrong import of n_past_races (should not be the same for all, but increase with time)
        if (df_l_form['n_past_races']==df_l_form['n_past_races'][0]).all(): # if all entries of n_past_races are the same as the first...
            df_l_form['n_past_races'] = list(range(df_l_form.shape[0],0,-1)) #count backwards the number of race entries in long_forms        
    else:
        df_l_form={}
    return df_l_form
    
def prepro_long_forms(df):
    if isinstance(df['long_forms_unpacked'], pd.DataFrame):
        # For every long-form add horse and racedate
        df['long_forms_unpacked']['past_horsename'] = df['name']
        df['long_forms_unpacked']['key'] = df['long_forms_unpacked']['past_racedates'].astype('str')+'_'+df['long_forms_unpacked']['past_horsename']
        df['long_forms_unpacked'].set_index('key',inplace=True, verify_integrity=False)
        # For every long-form-entry compute time since todays race.
        df['long_forms_unpacked']['past_racedates_diff']=(df['race_date_time']-
                                                          df['long_forms_unpacked']['past_racedates'])/ np.timedelta64(1, 'D')
        # Drop race_dates from the same date (new result has already been forwarded to database).
        df['long_forms_unpacked'].drop(df['long_forms_unpacked'][(df['long_forms_unpacked']["past_racedates_diff"] < 1)].index, axis=0,inplace=True)
        # Drop race_dates unrealistically long ago.
        df['long_forms_unpacked'].drop(df['long_forms_unpacked'][(df['long_forms_unpacked']["past_racedates_diff"] > 365*25)].index, axis=0,inplace=True)
    return df

    # Get distance from last race.
def transfer_long_form_info_to_df(df):
    if isinstance(df['long_forms_unpacked'], pd.DataFrame):
        df['d_since_last_race'] = df['long_forms_unpacked']['past_racedates_diff'].min()
        df['n_past_races'] = df['long_forms_unpacked']['n_past_races'].max()
        df['mean_past_place'] = df['long_forms_unpacked']['past_finishes'].mean(skipna=True)
        clean_jockey_name=re.sub("[\(\[].*?[\)\]]", "", df['jockey']) # When matchin jockey names cut any brackets (containing country-names etc.). They will cause trouble in matching below
        df['n_races_w_jockey'] = df['long_forms_unpacked']['past_jockeys'].str.match(clean_jockey_name).sum()
        # Finally add a logical to df helping with selecting entries with no long_forms
        df['long_form_exists'] = True
    else:
        df['d_since_last_race'] = float('NaN')
        df['n_past_races'] = 0
        df['mean_past_place'] = float('NaN')
        df['n_races_w_jockey'] = 0
        df['long_form_exists'] = False
    return df