# # Get the data
#
# Pull all the relevant data from fingertips. This is slow and can probably be improved.

# +
import fingertips_py as ftp
import pandas as pd
import requests
import dateutil.parser
from pathlib import Path
import os
import json
import dateutil.parser

from pprint import pprint
from datetime import datetime

def write_data_for_profile(url):
    """
    Write all data for a domain, plus Measure Type, Standard Population and Unit of Measure to all_data.csv
    Also writes the domain to that csv.
    
    Additionally writes a metadata_for_profile.csv
    
    NOTE: uses whatever geography is in the url, kinda arbitrary.
    """
    
    # get the profile_key out of the url
    group_key = url.split("/profile/")[1].split("/")[0]

    # get the area id out of  the url
    area_type_id = url.split("/ati/")[1].split("/")[0]

    # use the group_key (from the url) to get the profile
    profile = [x for x in ftp.get_all_profiles() if x["Key"] == group_key]
    
    # For each domain within this profile
    all_indicator_dataframes = []
    for i, group in enumerate(profile[0]["GroupIds"]):
        
        # Get the indicator metadata for the domain
        r = requests.get("https://fingertips.phe.org.uk/api/indicator_metadata/by_group_id?group_ids=" + str(group))
        if r.status_code != 200:
            raise ValueError("Aborting, unable to acquire domain metadata for domain:" + str(group))
        
        indicator_metadata = r.json()
        
        # Get all the indicator data for this domain
        indicators = list(indicator_metadata.keys())
        indicator_data = ftp.get_data_by_indicator_ids(indicators, area_type_id)

        # get domain name as a string
        r2 = requests.get("https://fingertips.phe.org.uk/api/group_metadata?group_ids=" + str(group))
        if r2.status_code != 200:
            raise ValueError("Aborting. Cant get domain level data for: " + str(group))
        group_name = r2.json()[0]["Name"]
        
        # attach the domain name to the indicator data
        indicator_data["Group"] = group_name
        all_indicator_dataframes.append(indicator_data)

    # create a dataframe containing all profile level metadata
    metadata = ftp.get_metadata_for_profile_as_dataframe(profile[0]["Id"])
    metadata.to_csv("metadata_for_profile.csv", index=False)
    
    # TODO - this will be slow
    data = pd.concat(all_indicator_dataframes)
    unit_lookup = {}
    value_lookup = {}
    stat_pop_lookup = {}
    for indicator in metadata["Indicator ID"].unique():
        stat_pop_lookup[indicator] = metadata["Standard population/values"][metadata["Indicator ID"] == indicator].unique()[0]
        unit_lookup[indicator] = metadata["Unit"][metadata["Indicator ID"] == indicator].unique()[0]
        value_lookup[indicator] = metadata["Value type"][metadata["Indicator ID"] == indicator].unique()[0]
        
    data["Unit"] = data["Indicator ID"].map(lambda x: unit_lookup[int(x)])
    data["Standard population/values"] = data["Indicator ID"].map(lambda x: stat_pop_lookup[int(x)])
    data["Measure Type"] = data["Indicator ID"].map(lambda x: value_lookup[int(x)])
        
    # We're just gonna dump to csv for now, as it saves rerunning this slow bit after local restarts
    data.to_csv("all_data.csv", index=False)
    
write_data_for_profile("https://fingertips.phe.org.uk/profile-group/mental-health/profile/drugsandmentalhealth/data#page/0/gid/1938132935/pat/6/par/E12000006/ati/102/are/E06000055")

# -


# # Functions
#
# Some functions we'll reuse a few times

# +
from gssutils import *

def timeify(cell):
    """ Simple function to style time to match our requirements """
    
    if len(cell) == 4:
        return "year/"+cell
    elif len(cell) == 7:
        return "government-year/{}-{}".format(cell[:4], "20"+cell[-2:])
    elif " - " in cell:
        return "gregorian-interval/{}/PY2".format(cell.split(" - ")[0])
    else:
        raise ValueError("Unexpected time format: '{}'. We are expecting time values "
                         "with a length of either 4 or 7 characters".format(cell))
     
    
# TODO - we can probably remove this since pathify_label and make_notation look like the same thing
def pathify_label(value):
    """ As it says, change into something we can use for an output file name """
    
    unwanted = [")", "(", ",", ".", "/", "&"]
    for u in unwanted:
        value = value.lower().replace(u, "").replace(" ", "-").replace("---", "-").replace("--", "-")
    return value

def make_notation(value):
        """ Take the value of on cell of a 'Label' column and modify to be suitable for a notation column """

        value = value.lower()
        replacers = [
            ["<", "less-than-"],
            ["&", ""],
            ["%", "-percent"],
            [",", ""],
            [":", ""],
            [")", ""],
            ["(", ""],
            ["/", ""],
            [".", ""],
            [" ", "-"], 
            ["--", "-"],
            ["---", "-"],
            ["yrs", "years"]
        ]
        
        for replacer in replacers:
            value = value.replace(replacer[0], replacer[1])
            
        # reformat if its greater than
        if "+" in value:
            value = value.replace("years", "")
            value = value.replace("+", "-years-and-older")

        return value.rstrip("-").lstrip("-").replace("--", "-")
    


# -

# # Clean the data
#
# We're keeping the data within a single dataframe while we clean up the entires (it's simpler this way)

# +

# for when we need to fill some blanks
UNSPECIFIED_TREND = "not-known"
UNSPECIFIED_STAT_POP = "not-applicable"

# load the data
all_data = pd.read_csv("all_data.csv")

# Create the principle dataframe of everything
tidy_sheet = pd.DataFrame()
tidy_sheet["Indicator"] = all_data["Indicator Name"].apply(make_notation)
tidy_sheet["Area"] = all_data["Area Code"]
tidy_sheet["PHE Sex"] = all_data["Sex"].apply(make_notation)
tidy_sheet["PHE Age"] = all_data["Age"].apply(make_notation)
tidy_sheet["Period"] = all_data["Time period"].astype(str).apply(timeify)
tidy_sheet["Value"] = all_data["Value"]
tidy_sheet["Trend"] = all_data["Recent Trend"].astype(str).apply(make_notation)
tidy_sheet["PHE Unit"] = all_data["Unit"].astype(str).apply(make_notation)
tidy_sheet["Category Type"] = all_data["Category Type"].astype(str).map(lambda x: x.replace(".)", ")"))
tidy_sheet["Category"] = all_data["Category"].astype(str).apply(make_notation)
tidy_sheet["PHE Standard Population"] = all_data["Standard population/values"].astype(str).apply(make_notation)
tidy_sheet["Measure Type"] = all_data["Measure Type"]
tidy_sheet["PHE Group"] = all_data["Group"].apply(make_notation)

# Get rid of unsorted nan values
# TODO - there's a function for this that I can't remember
for col in tidy_sheet.columns.values:
    tidy_sheet[col] = tidy_sheet[col].map(lambda x: str(x).replace("nan", ""))
    
# Tweaks and things that I can't really genericize
# ------------------------------------------------
tidy_sheet["PHE Unit"] = tidy_sheet["PHE Unit"].map(lambda x: x.replace("precent", "percentage"))
tidy_sheet["PHE Standard Population"][tidy_sheet["PHE Standard Population"] == ""] = UNSPECIFIED_STAT_POP
tidy_sheet["Trend"][tidy_sheet["Trend"] == ""] = UNSPECIFIED_TREND

# Remove rows without values and output
tidy_sheet = tidy_sheet[tidy_sheet["Value"].astype(str) != ""]

# Add default units
tidy_sheet["PHE Unit"][tidy_sheet["Indicator"] == "deprivation-score-imd-2015"] = "index"
tidy_sheet["PHE Unit"][tidy_sheet["Indicator"] == "number-in-treatment-at-specialist-drug-misuse-services"] = "number"
tidy_sheet["PHE Unit"][tidy_sheet["Indicator"] == "number-in-treatment-at-specialist-alcohol-misuse-services"] = "number"

# Some changes for Measure Type
tidy_sheet["Measure Type"][tidy_sheet["Measure Type"] == "Proportion"] = "Percentage"

# Possible back end issues with "/"'s, remove for now to confirm
# TODO fix the back end, not the input
tidy_sheet["Category Type"] = tidy_sheet["Category Type"].astype(str).map(lambda x: x.replace("/", ""))

tidy_sheet.to_csv("all_but_tidied.csv", index=False)
# -
# # Split the data
#
# Now the data is ready, we're going to split it up by category.

# +

list_of_categories = []

for cat in tidy_sheet["Category Type"].unique():
    
    temp_sheet = tidy_sheet[tidy_sheet["Category Type"].astype(str) == str(cat)]
    
    if str(cat) == "" or str(cat) == "nan":
        temp_sheet = temp_sheet.drop("Category", axis=1)
        cat = "Uncategorised"
    else:
        temp_sheet = temp_sheet.rename({'Category': cat}, axis=1)
    temp_sheet = temp_sheet.drop("Category Type", axis=1)
        
    cat = pathify_label(cat)
    list_of_categories.append(cat)
    
    # Standard population only applies to a narrow subet of the data
    # if no observation in this slice have it - rip it out
    all_stat_pop = list(temp_sheet["PHE Standard Population"].unique())
    if len(all_stat_pop) == 1 and all_stat_pop[0] == UNSPECIFIED_STAT_POP:
        temp_sheet = temp_sheet.drop("PHE Standard Population", axis=1)

    # For some categories, no observations have trend information
    # if no observation in this slice have it - rip it out
    all_trends = list(temp_sheet["Trend"].unique())
    if len(all_trends) == 1 and all_trends[0] == UNSPECIFIED_TREND:
        temp_sheet = temp_sheet.drop("Trend", axis=1)

    out = Path('out')
    out.mkdir(exist_ok=True)
    
    temp_sheet = temp_sheet.drop_duplicates()
    
    out_path = out / "{}.csv".format(cat)
    temp_sheet.to_csv(out_path, index = False)

# -


# # TODO - replace

# +
# dictionary mapping in-csv column names to the notation field in columns.csv..... ewwwwww

# TODO - nasty hack as I was puzzling through this, what we SHOULD do, is get some dictionaries of Label, Notation, 
# Pathified-Label early on for all potential columns and just refer to as needed.
notation_lookup = {
    "Indicator": "indicator",
    "Area": "area",
    "PHE Sex": "phe_sex",
    "PHE Age": "phe_age",
    "Period": "period",
    "Trend": "trend",
    "PHE Unit": "phe_unit",
    "PHE Standard Population": "phe_standard_population",
    'County & UA (pre Apr2019) deprivation deciles in England (IMD2015)': 'county-ua-pre-apr2019-deprivation-deciles-in-england-imd2015'.replace("-", "_"),
    'District & UA (pre Apr2019)  deprivation deciles in England (IMD2015)': 'district-ua-pre-apr2019-deprivation-deciles-in-england-imd2015'.replace("-", "_"),
    'County & UA deprivation deciles in England (IMD2015, 419 geog)': 'county-ua-deprivation-deciles-in-england-imd2015-419-geog'.replace("-", "_"),
    'District & UA deprivation deciles in England (IMD2015, 419 geog)': 'district-ua-deprivation-deciles-in-england-imd2015-419-geog'.replace("-", "_"),
    'County & UA deprivation deciles in England (IMD2019, 419 geog)': 'county-ua-deprivation-deciles-in-england-imd2019-419-geog'.replace("-", "_"),
    'District & UA deprivation deciles in England (IMD2019, 419 geog)': 'district-ua-deprivation-deciles-in-england-imd2019-419-geog'.replace("-", "_"),
    'County & UA deprivation deciles in England (IMD2010)': 'county-ua-deprivation-deciles-in-england-imd2010'.replace("-", "_"),
    'District & UA deprivation deciles in England (IMD2010)': 'district-ua-deprivation-deciles-in-england-imd2010'.replace("-", "_"),
    'Ethnic groups': 'ethnic-groups'.replace("-", "_"),
    'Sexuality - 4 categories': 'sexuality-4-categories'.replace("-", "_"),
    'Socioeconomic group (18-64 yrs)': 'socioeconomic-group-18-64-yrs'.replace("-", "_"),
    'Religion - 8 categories': 'religion-8-categories'.replace("-", "_"),
    'Country of birth': 'country-of-birth'.replace("-", "_"),
    'Health status': 'health-status'.replace("-", "_"),
    'Sexuality - 5 categories': 'sexuality-5-categories'.replace("-", "_"),
    'LSOA11 deprivation deciles in England (IMD2015)': 'lsoa11-deprivation-deciles-in-england-imd2015'.replace("-", "_"),
    'Value':"value",
    "Measure Type": "measure_type",
    "Domain": "domain",
    "PHE Group": "phe_group"
}
# -

# # Generate trig files
#
# These are almost (but not quite) identical. To get things working I've used a template and some hacky substitutions.

# +

import os

all_data = pd.read_csv("all_data.csv")
all_dates = []

count = 1 # can't use enumerate as ns2 is in use. Probably a cleaner way though (as per everything)
for cat in list_of_categories:
    
    # Skip counts of 2, as its's being used in '@prefix ns2: <urn:x-rdflib:>'
    if count == 2:
        count+= 1
    
    fp = "out/{}.csv".format(pathify_label(cat))
    df = pd.read_csv(fp)
    
    # Get the release/modified date of every indicator in this obs file
    for indicator in list(df["Indicator"].unique()):
        
        indicator_ids = list(all_data["Indicator ID"][all_data["Indicator Name"].apply(make_notation) == indicator].unique())
        if len(indicator_ids) != 1:
            raise ValueError("Unable to determine specific indicator ID for indicator: " + ",".join(indicators))
        indicator_id = indicator_ids[0]
        
        url = "https://fingertips.phe.org.uk/api/data_changes?indicator_id="+str(indicator_id)
        r = requests.get(url)
        if r.status_code != 200:
            raise ValueError("Failed to get date changed information for indicator via: " + url)

        date =r.json()["LastUploadedAt"]
        all_dates.append(dateutil.parser.parse(date))
    
    # Now create our variables to write in 
    issued_date = str(max(all_dates)).replace(" ", "T")
    last_modified = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    
    title = "Co-occurring substance misuse and mental health issues"
    dataset_url = "http://gss-data.org.uk/data/gss_data/disability/phe-co-occurring-substance-misuse-and-mental-health-issues"
    if cat != "uncategorised":
        title_cat = [k for k,v in notation_lookup.items() if v.replace("_", "-") == cat][0]
        title = "Co-occurring substance misuse and mental health issues: " + title_cat
        dataset_url = dataset_url + "/" + cat 
        
    lines_for_new_trig = []
    with open("template-trig.txt", "r") as f:
        for line in f:

            line = line.replace("<ISSUED_DATETIME_REPLACE_ME>", issued_date)
            line = line.replace("<MODIFIED_DATETIME_REPLACE_ME>", last_modified)
            line = line.replace("<TITLE_REPLACE_ME>", title)
            line = line.replace("DATASET_URL_REPLACE_ME", dataset_url)
            line = line.replace("GRAPH_URL_REPLACE_ME", dataset_url.replace("/data/", "/graph/"))
            line = line.replace("<LABEL_REPLACE_ME>", title)
            line = line.replace("<DATASET_COUNT_REPLACE_ME>", str(count))
                
            lines_for_new_trig.append(line)
            
    with open(fp+"-metadata.trig", "w") as f:
        
        for line in lines_for_new_trig:
            f.write(line)
            
    # Use a counter to unique match dataset and metadata identifier ns1, ns2 etc
    count+=1
    
# -

# # Generate Schema Files
#
# We'll just generate these on the fly, using the load observation csvs.
#

# +

for cat in list_of_categories:
    
    fp = "out/{}.csv".format(pathify_label(cat))
    df = pd.read_csv(fp)

    schema = {
        "@context": ["http://www.w3.org/ns/csvw",{"@language": "en"}],
        "tables": []
    }
    
    # Tables for codelists
    for col in [x for x in df.columns.values if x != "Value" and x != "Measure Type"]:
        
        if col not in ["Area", "Period"]:
            
            col = col.lower()
            if not col.startswith("phe"):
                col = pathify_label("phe-"+col)
            col = col.replace(" ", "-")

            schema["tables"].append({
                "url": "https://gss-cogs.github.io/family-disability/reference/codelists/{}.csv".format(col),
                "tableSchema": "https://gss-cogs.github.io/ref_common/codelist-schema.json",
                "suppressOutput": True
            })
        
    obs_tableSchema = {}
        
    # Tableschema for the observations files
    obs_tableSchema["columns"] = []
    obs_tableSchema["foreignKeys"] = []
    obs_tableSchema["primaryKey"] = []
    for col in df.columns.values:
        
        if not col.lower().startswith("phe"):
            path_col = pathify_label("phe-"+col.lower())
        else:
            path_col = pathify_label(col.lower())
        
        if col == "Value":
            data_type = "number"
        else:
            data_type = "string"
            
        obs_tableSchema["columns"].append({
                "titles": col,
                "required": True,
                "name": notation_lookup[col],
                "datatype": data_type
                })
        
        # only add a foreign key if its a codelist I've made
        if col not in ["Area", "Period", "Value", "Measure Type"]:
            obs_tableSchema["foreignKeys"].append({
                "columnReference": notation_lookup[col],
                "reference": {
                    "resource": "https://gss-cogs.github.io/family-disability/reference/codelists/{}.csv".format(path_col),
                    "columnReference": "notation"
                    }
                })
        
        obs_tableSchema["primaryKey"].append(notation_lookup[col])
    
    # Table for obs file
    schema["tables"].append({
        "url": fp[4:],
        "tableSchema": obs_tableSchema
    })

    with open(str(fp)+"-schema.json", "w") as f:
        json.dump(schema, f)
    
# -


