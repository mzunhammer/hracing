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