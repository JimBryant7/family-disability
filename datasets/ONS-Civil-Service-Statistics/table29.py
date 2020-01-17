# ---
# jupyter:
#   jupytext:
#     formats: ipynb,py:light
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.4'
#       jupytext_version: 1.1.1
#   kernelspec:
#     display_name: Python 3
#     language: python
#     name: python3
# ---

# Civil Service Statistics (unvalidated)

# +
import json
import pandas as pd
import numpy as np
from gssutils import *

scraper = Scraper('https://www.ons.gov.uk/employmentandlabourmarket/peopleinwork/publicsectorpersonnel/datasets/civilservicestatistics')
scraper
# -


# Table : 29   Civil Service employment; median and mean earnings by department 1 2
# Full time employees 

tabs = {tab.name: tab for tab in scraper.distribution(latest=True).as_databaker()}
tab = tabs['Table 29']

measure_type = tab.excel_ref('C5').expand(RIGHT).is_not_blank()
department = tab.excel_ref('B11').expand(DOWN).is_not_blank() - tab.excel_ref('B194').expand(DOWN)
remove_1 = tab.excel_ref('E6')
remove_2 = tab.excel_ref('I6')
gender = tab.excel_ref('C6').expand(RIGHT).is_not_blank() - remove_1 - remove_2
observations = gender.fill(DOWN).is_not_blank() - tab.excel_ref('B194').expand(DOWN).expand(RIGHT) - remove_1.expand(DOWN) - remove_2.expand(DOWN)
#savepreviewhtml(measure_type)

dimensions = [
    HDimConst('Year', '2018'),
    HDimConst('ONS Age Range', 'all'),
    HDimConst('Region name', 'all'),
    HDimConst('Nationality', 'all'),
    HDimConst('Salary Band', 'all'),
    HDimConst('Ethnicity', 'all'),
    HDimConst('Responsibility Level', 'all-employees'),
    HDimConst('Disability Status', 'not-applicable'),
    HDimConst('Profession of Post', 'all'),
    HDimConst('Entrants or Leavers', 'not-applicable'),
    HDimConst('Type of Employment', 'full-time-employees'),
    HDimConst('Status of Employment', 'not-applicable'),
    HDimConst('NUTS Area Code', 'not-applicable'),
    HDimConst('ONS area code', 'not-applicable'),
    HDim(gender, 'Sex', DIRECTLY, ABOVE),
    HDim(department, 'Department', DIRECTLY, LEFT), 
    HDim(measure_type, 'Measure Type', CLOSEST, LEFT),
]
c1 = ConversionSegment(observations, dimensions, processTIMEUNIT=True)
new_table = c1.topandas()


new_table.rename(columns={'OBS': 'Value'}, inplace=True)
if 'DATAMARKER' in new_table.columns:
    print('marker found in columns')
    new_table['DATAMARKER'].replace('..', 'between-one-and-five', inplace=True)
    new_table['DATAMARKER'].replace('-', 'not-applicable', inplace=True)
    new_table = new_table.rename(columns={'DATAMARKER':'Marker'})
    new_table = new_table.fillna('not-applicable') 
else:
    print('marker not found in colmns making it')
    new_table['DATAMARKER'] = 'not-applicable'
    new_table = new_table.rename(columns={'DATAMARKER':'Marker'})

new_table['Department'] = new_table['Department'].map(lambda x: pathify(x))
new_table['Measure Type'] = new_table['Measure Type'].map(lambda x: pathify(x))
new_table['Sex'] = new_table['Sex'].map(lambda x: pathify(x))
new_table = new_table.replace({'Sex' : {'male19' : 'M','female19' : 'F','total' : 'T' }})
new_table
