#!/usr/bin/env python
# coding: utf-8

# In[148]:


import pandas as pd
from gssutils import *
from databaker.framework import *
from gssutils.metadata import THEME
    
def findnth(haystack, needle, n):
    parts= haystack.split(needle, n+1)
    if len(parts)<=n+1:
        return -1
    return len(haystack)-len(parts[-1])-len(needle)

def left(s, amount):
    return s[:amount]

def right(s, amount):
    return s[-amount:]

scraper = Scraper('https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/employmentandemployeetypes/datasets/labourmarketstatusofdisabledpeoplea08')
scraper


# In[157]:


dist = scraper.distributions[0]
tabs = (t for t in dist.as_databaker() if 'Rates' not in t.name)
tidied_sheets = []

for tab in tabs:    
    if 'GSS_Standard' in tab.name or 'Equality_Act' in tab.name or 'Self-Report' in tab.name in tab.name:
        
        tabName = str(tab.name)
        
        """
        if 'not seasonally adjusted' in str(tab.excel_ref('A4')).lower():
            SA = 'not-seasonally-adjusted'
        elif 'seasonally adjusted' not in str(tab.excel_ref('A4')).lower():
            SA = 'ERROR - CHECK TAB'
        elif 'not' not in str(tab.excel_ref('A4')).lower():
            SA = 'seasonally-adjusted'
        else:
            SA = 'ERROR - CHECK TAB'
        """ # Currently every tab in the data is not-seasonally adjusted, if this changes then uncomment and add back to output
        
        cell = tab.excel_ref("B5")
        
        remove = tab.filter("Total aged 16-64: Including those who did not state their health situation").expand(DOWN)
    
        period = cell.shift(0,3).expand(DOWN).is_not_blank().shift(LEFT)
        
        disability = cell.expand(RIGHT).is_not_blank() - remove
        
        econActive = cell.shift(DOWN).expand(RIGHT).is_not_blank()
        
        observations = period.shift(RIGHT).expand(RIGHT).is_not_blank() - remove
        #remember to devide by 1000 to match the unit of the source data
        
        dimensions = [
                #HDimConst('Dimension Name', 'Variable'),
                HDimConst('Sex', right(tabName, len(tabName) - findnth(tabName.replace('-', '_'), '_', 2) - 1)),
                #HDimConst('Seasonally Adjusted', SA),
                HDim(period, 'Month', DIRECTLY, LEFT), 
                HDim(period, 'Year', DIRECTLY, LEFT), 
                HDim(disability, 'GSS Harmonised', CLOSEST, LEFT),
                HDim(econActive, 'Economic Activity', DIRECTLY, ABOVE),
                HDimConst('Measure Type','Count'),
                HDimConst('Unit','Person'),
                HDimConst('Age','16-64')
        ]
        
        c1 = ConversionSegment(observations, dimensions, processTIMEUNIT=True)
        savepreviewhtml(c1, fname="Preview.html")
        tidied_sheets.append(c1.topandas())
        
    if 'DDA' in tab.name:
        
        tabName = str(tab.name)
        
        """
        if 'not seasonally adjusted' in str(tab.excel_ref('A4')).lower():
            SA = 'not-seasonally-adjusted'
        elif 'seasonally adjusted' not in str(tab.excel_ref('A4')).lower():
            SA = 'ERROR - CHECK TAB'
        elif 'not' not in str(tab.excel_ref('A4')).lower():
            SA = 'seasonally-adjusted'
        else:
            SA = 'ERROR - CHECK TAB'
        """ # Currently every tab in the data is not-seasonally adjusted, if this changes then uncomment and add back to output
        
        cell = tab.excel_ref("B2")
    
        period = cell.shift(0,3).expand(DOWN).is_not_blank().shift(LEFT)
        
        remove = tab.filter('Source: Labour Force Survey').expand(LEFT).expand(DOWN)
        
        remove2 = tab.filter('Mar-May 1983')
        
        disability = cell.expand(RIGHT).is_not_blank() - remove
        
        econActive = cell.shift(DOWN).expand(RIGHT).is_not_blank()
        
        observations = period.shift(RIGHT).expand(RIGHT).is_not_blank() - remove
        #remember to devide by 1000 to match the unit of the source data
        
        sex = cell.shift(-1,3).expand(DOWN).is_not_blank() - remove - remove2 - observations.shift(LEFT)
        
        dimensions = [
                #HDimConst('Dimension Name', 'Variable'),
                HDim(sex, 'Sex', CLOSEST, ABOVE),
                #HDimConst('Seasonally Adjusted', SA),
                HDim(period, 'Month', DIRECTLY, LEFT), 
                HDim(period, 'Year', DIRECTLY, LEFT), 
                HDim(disability, 'GSS Harmonised', CLOSEST, LEFT),
                HDim(econActive, 'Economic Activity', DIRECTLY, ABOVE),
                HDimConst('Measure Type','Count'),
                HDimConst('Unit','Person'),
                HDimConst('Age','16-64')
        ]
        
        c1 = ConversionSegment(observations, dimensions, processTIMEUNIT=True)
        savepreviewhtml(c1, fname="Preview.html")
        tidied_sheets.append(c1.topandas())
        
    else:
        continue


# In[158]:


pd.set_option('display.float_format', lambda x: '%.0f' % x)
new_table = pd.concat(tidied_sheets, ignore_index = True, sort = True).fillna('')
new_table['Year'] = new_table['Year'].map(lambda x: right(x, 4))
new_table['Month'] = new_table['Month'].map(lambda x: left(x, len(x) - 9))
new_table = new_table.replace({'Month' : {'Apr' : '04','Jan' : '01','Jul' : '07','Oct' : '10',}})
new_table.rename(columns={'OBS':'Value'}, inplace=True)
new_table['Economic Activity'] = new_table['Economic Activity'].map(lambda x: 'All' if 'Total' in x else x)
new_table['GSS Harmonised'] = new_table['GSS Harmonised'].map(lambda x: pathify(x))
new_table['Economic Activity'] = new_table['Economic Activity'].map(lambda x: pathify(x))
new_table['Period'] = 'gregorian-interval/' + new_table['Year'] + '-' +  new_table['Month'] + '-01T00:00:00/P3M'
new_table


# In[159]:


tidy = new_table[['Period','Age','Sex','GSS Harmonised','Economic Activity','Measure Type','Value','Unit']]
tidy = tidy.replace({'Sex' : {
    'Men' : 'M',
    'People' : 'T',
    'Women' : 'F'}})

tidy = tidy.replace({'GSS Harmonised' : {
    'equality-act-core-disabled2' : 'equality-act-core-disabled',
    'harmonised-standard-definition-disabled1' : 'harmonised-standard-definition-disabled',
    'no-self-reported-ill-health3' : 'no-self-reported-ill-health',
    'people-who-do-not-meet-the-equality-act-core-definition-of-disability-excluding-those-who-did-not-state-their-health-situation-3' : 'not-equality-act-core-disabled',
    'people-who-do-not-meet-the-harmonised-standard-definition-of-disability-excluding-those-who-did-not-state-their-health-situation-2' : 'not-harmonised-standard-definition-disabled',
    'self-reported-ill-health2' : 'self-reported-ill-health',
    'work-limiting-disabled1' : 'work-limiting-disabled',
    'all-people-with-a-long-term-health-problem-or-disability3' : 'all-people-with-a-long-term-health-problem-or-disability',
    'all-people-with-a-long-term-health-problem-or-disability4' : 'all-people-with-a-long-term-health-problem-or-disability',
    'people-with-disabilities-that-limit-their-day-to-day-activities2' : 'people-with-disabilities-that-limit-their-day-to-day-activities',
    'people-with-disabilities-that-limit-their-day-to-day-activities3' : 'people-with-disabilities-that-limit-their-day-to-day-activities',
    'people-with-work-limiting-disabilities1' : 'people-with-work-limiting-disabilities',
    'people-with-work-limiting-disabilities2' : 'people-with-work-limiting-disabilities'}})

from IPython.core.display import HTML
for col in tidy:
    if col not in ['Value']:
        tidy[col] = tidy[col].astype('category')
        display(HTML(f"<h2>{col}</h2>"))
        display(tidy[col].cat.categories)


# In[160]:


destinationFolder = Path('out')
destinationFolder.mkdir(exist_ok=True, parents=True)

TAB_NAME = 'observations'

tidy.drop_duplicates().to_csv(destinationFolder / f'{TAB_NAME}.csv', index = False)

scraper.dataset.family = 'disability'

with open(destinationFolder / f'{TAB_NAME}.csv-metadata.trig', 'wb') as metadata:
    metadata.write(scraper.generate_trig())

csvw = CSVWMetadata('https://gss-cogs.github.io/family-disability/reference/')
csvw.create(destinationFolder / f'{TAB_NAME}.csv', destinationFolder / f'{TAB_NAME}.csv-schema.json')
tidy


# In[ ]:



