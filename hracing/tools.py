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

def cols_from_html_tbl(tbl): 
    """ Extracts columns from html-table tbl and puts columns in a list.
    tbl must be a results-object from BeautifulSoup)"""
    rows = tbl.find_all('tr')
    for row in rows:
        cols = row.find_all('td')
        for i,cell in enumerate(cols):
            if not'col_list' in locals():
                col_list=[[] for x in range(len(cols))]
            col_list[i].append(cell.text)
    return col_list
    
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