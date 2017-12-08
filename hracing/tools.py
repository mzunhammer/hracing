import time
import random
from pdb import set_trace

def flatten(l, ltypes=(list, tuple)):
    """ Flattens nested lists l to yield a 1-d list"""
    ltype = type(l)
    l = list(l)
    i = 0
    while i < len(l):
        while isinstance(l[i], ltypes):
            if not l[i]:
                l.pop(i)
                i -= 1
                break
            else:
                l[i:i + 1] = l[i]
        i += 1
    return ltype(l)

def bf4_text(bf4_element):
    """ Checks BeautifulSoup element for existence and returns str"""
    return "" if bf4_element is None else bf4_element.text

def cols_from_html_tbl(tbl):
    """ Extracts columns from html-table tbl and puts columns in a list.
    tbl must be a results-object from BeautifulSoup)"""
    #set_trace()
    rows_head = tbl.thead.find_all('tr')
    if rows_head:
        hcols = rows_head[0].find_all(['td','th'])
        for i,hcell in enumerate(hcols):
            if not 'head_list' in locals(): head_list=[]
            head_list.append(hcell.text)
    else:
        head_list=[]
    rows_body = tbl.tbody.find_all('tr')
    if rows_body:
        for row in rows_body:
            cols = row.find_all('td')
            for j,cell in enumerate(cols):
                if not 'col_list' in locals(): col_list=[[] for x in range(len(cols))]
                col_list[j].append(cell.text)
    else:
        col_list=[]
    return head_list, col_list
    
def isnumber(s):
    """ Checks if string can be converted to float and is >0"""
    try:
        f=float(s.replace(',','.'))
        if f > 0:
            return True
        else:
            return False
    except ValueError:
        return False

def delay_scraping(start_time, target_duration):
    """ Calcultes time spent in requests loop up to now, compares to target duration
     of loop and waits for the remainder.
     Slows scraping to avoid getting kicked from server"""
    curr_time=time.monotonic()-start_time
    wait_time=target_duration-curr_time+random.normalvariate(0, target_duration/2)
    if wait_time>0:
        time.sleep(wait_time) 
    
def shuffle_ids(raceids,raceid_urls):
    both = list(zip(raceids,raceid_urls))
    random.shuffle(both)
    raceids_shuffled,raceid_urls_shuffled = zip(*both)
    raceids_shuffled = list(raceids_shuffled)
    raceid_urls_shuffled = list(raceid_urls_shuffled)
    return raceids_shuffled,raceid_urls_shuffled