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

# ONS - Children living in long-term workless households, by disability status (Table H)

# +
from gssutils import *
import pandas as pd

scraper = Scraper('https://www.ons.gov.uk/employmentandlabourmarket/peoplenotinwork/unemployment/datasets/hchildrenlivinginlongtermworklesshouseholdsandworklesshouseholdsbydisabilitystatus')
# -

#One tab containing 5 tables: a - e.  tables a,c,e only required
tabs = {tab.name: tab for tab in scraper.distribution(latest=True, mediaType=Excel).as_databaker()}
tab = tabs['CILTWH H']

# +
#TABLE A
a_year = tab.excel_ref('A5').fill(DOWN).is_not_blank() - tab.excel_ref('A21').expand(DOWN).is_not_blank()
a_workless_household_type = tab.excel_ref('B3').is_not_blank()
a_household_disability_status = tab.excel_ref('B4').expand(RIGHT).is_not_blank() - tab.excel_ref('E4').expand(RIGHT).is_not_blank()
a_observations = tab.excel_ref('B5').expand(RIGHT).expand(DOWN).is_not_blank().is_number() - tab.excel_ref('B21').expand(RIGHT).expand(DOWN).is_not_blank().is_number()
a_exclude_totals = tab.excel_ref('E5').expand(DOWN).expand(RIGHT).is_not_blank() - tab.excel_ref('E21').expand(RIGHT).expand(DOWN).is_not_blank()
a_observations = a_observations - a_exclude_totals

Dimensions = [
             HDim(a_year,'Year',DIRECTLY,LEFT),
             HDim(a_household_disability_status,'Household Disability Status',DIRECTLY,ABOVE),
             HDim(a_workless_household_type,'Workless Household Type',CLOSEST,ABOVE),
             HDimConst('Measure Type', 'Count'), 
             HDimConst('Unit','People (thousands)')
             ]
c1 = ConversionSegment(a_observations, Dimensions, processTIMEUNIT=True)
tbl_a = c1.topandas()

# +
#TABLE C
c_year = tab.excel_ref('A45').fill(DOWN).is_not_blank() - tab.excel_ref('A61').expand(DOWN).is_not_blank()
c_workless_household_type = tab.excel_ref('B43').is_not_blank()
c_household_disability_status = tab.excel_ref('B44').expand(RIGHT).is_not_blank() - tab.excel_ref('E44').expand(RIGHT).is_not_blank()
c_observations = tab.excel_ref('B45').expand(RIGHT).expand(DOWN).is_not_blank().is_number() - tab.excel_ref('B61').expand(RIGHT).expand(DOWN).is_not_blank().is_number()
c_exclude_totals = tab.excel_ref('E45').expand(DOWN).expand(RIGHT).is_not_blank() - tab.excel_ref('E61').expand(RIGHT).expand(DOWN).is_not_blank()
c_observations = c_observations - c_exclude_totals

Dimensions = [
             HDim(c_year,'Year',DIRECTLY,LEFT),
             HDim(c_household_disability_status,'Household Disability Status',DIRECTLY,ABOVE),
             HDim(c_workless_household_type,'Workless Household Type',CLOSEST,ABOVE),
             HDimConst('Measure Type', 'Count'), 
             HDimConst('Unit','People (thousands)')
             ]
c2 = ConversionSegment(c_observations, Dimensions, processTIMEUNIT=True)
tbl_c = c2.topandas()

# +
#TABLE e
e_year = tab.excel_ref('A85').fill(DOWN).is_not_blank() - tab.excel_ref('A101').expand(DOWN).is_not_blank()
e_workless_household_type = tab.excel_ref('B83').is_not_blank()
e_household_disability_status = tab.excel_ref('B84').expand(RIGHT).is_not_blank() - tab.excel_ref('E84').expand(RIGHT).is_not_blank()
e_observations = tab.excel_ref('B85').expand(RIGHT).expand(DOWN).is_not_blank().is_number() - tab.excel_ref('B101').expand(RIGHT).expand(DOWN).is_not_blank().is_number()
e_exclude_totals = tab.excel_ref('E85').expand(DOWN).expand(RIGHT).is_not_blank() - tab.excel_ref('E101').expand(RIGHT).expand(DOWN).is_not_blank()
e_observations = e_observations - e_exclude_totals

Dimensions = [
             HDim(e_year,'Year',DIRECTLY,LEFT),
             HDim(e_household_disability_status,'Household Disability Status',DIRECTLY,ABOVE),
             HDim(e_workless_household_type,'Workless Household Type',CLOSEST,ABOVE),
             HDimConst('Measure Type', 'Count'), 
             HDimConst('Unit','People (thousands)')
             ]
c3 = ConversionSegment(e_observations, Dimensions, processTIMEUNIT=True)
tbl_e = c3.topandas()
# -

#concatenate tables a,c,e
new_table = pd.concat([tbl_a, tbl_c, tbl_e]).fillna('')

#Tidy
import numpy as np
new_table = new_table[~new_table['Year'].isin(['break in series'])]
new_table['Year'] = new_table['Year'].str[:4]
new_table['Year'] = new_table['Year'].apply(lambda x: pd.to_numeric(x, downcast='integer'))
new_table['Workless Household Type'] = new_table['Workless Household Type'].str[:-1]
new_table['OBS'] = new_table['OBS'].apply(lambda x: pd.to_numeric(x, downcast='integer'))
new_table['OBS'].replace('', np.nan, inplace=True)
new_table.dropna(subset=['OBS'], inplace=True)
new_table.rename(columns={'OBS': 'Value'}, inplace=True)
new_table = new_table[['Year','Household Disability Status','Workless Household Type','Value','Measure Type', 'Unit']]
new_table['Household Disability Status'] = new_table.apply(lambda x: pathify(x['Household Disability Status']), axis = 1)
new_table['Household Disability Status'] = new_table.apply(lambda x: x['Household Disability Status'].replace('/', 'or'), axis = 1)
new_table['Workless Household Type'] = new_table.apply(lambda x: pathify(x['Workless Household Type']), axis = 1)
new_table['Workless Household Type'] = new_table.apply(lambda x: x['Workless Household Type'].replace('/', 'or'), axis = 1)
new_table



# +
#Set up the folder path for the output files

destinationFolder = Path('out')
destinationFolder.mkdir(exist_ok=True, parents=True)

TAB_NAME = 'observations'

new_table.drop_duplicates().to_csv(destinationFolder / f'{TAB_NAME}.csv', index = False)

# +
scraper.dataset.family = 'disability'

with open(destinationFolder / f'{TAB_NAME}.csv-metadata.trig', 'wb') as metadata:
    metadata.write(scraper.generate_trig())
    

csvw = CSVWMetadata('https://gss-cogs.github.io/family-disability/reference/')
csvw.create(destinationFolder / 'observations.csv', destinationFolder / 'observations.csv-schema.json')
# -


