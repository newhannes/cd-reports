import streamlit as st
import pandas as pd
import os
import streamlit.components.v1 as components
# from CD_Script import create_html_report, varids_to_nicknames, df, df_2020, df_vars, social_vars, econ_vars, industry_vars, housing_vars

# # Set up the Streamlit app
# st.title("Congressional District Report Generator")

# # User input for congressional district
# congressional_district = st.text_input("Enter Congressional District (e.g., NC-11):")

# # Button to generate report
# if st.button("Generate Report"):
#     if congressional_district:
#         # Generate the report
#         social_vars_v = varids_to_nicknames(social_vars, df_vars, df)
#         econ_vars_v = varids_to_nicknames(econ_vars, df_vars, df)
#         industry_vars_v = varids_to_nicknames(industry_vars, df_vars, df)
#         housing_vars_v = varids_to_nicknames(housing_vars, df_vars, df)
        
#         html_report = create_html_report(congressional_district, df, df_2020, social_vars_v, econ_vars_v, industry_vars_v, housing_vars_v)
        
#         # Save the report to a file
#         report_filename = f"{congressional_district}_report.html"
#         with open(report_filename, "w") as f:
#             f.write(html_report)
        
#         # Display the report using components.html
#         components.html(html_report, height=800, scrolling=True)
        
#         # Provide a download link for the report
#         with open(report_filename, "rb") as f:
#             st.download_button(
#                 label="Download Report",
#                 data=f,
#                 file_name=report_filename,
#                 mime="text/html"
#             )
#     else:
#         st.error("Please enter a valid congressional district.")


######### ======== Get your feet wet ======= ##########
import requests
import json
import pandas as pd
import us
from jinja2 import Template
## test
######### ======== Helper Functions ======= ##########
## MARK: Helper Functions
@st.cache_data
def get_acs2022_1yr_profile_data(variables, state="*", district="*"):
    try:
        url = f"https://api.census.gov/data/2022/acs/acs1/profile?get={variables}&for=congressional%20district:{district}&in=state:{state}"
        response = requests.get(url)
        data = response.json()
        df = pd.DataFrame(data)
        df.columns = df.iloc[0]
        df = df[1:]
        new_cols = pd.Series(df.columns).map(var_lab_dict).fillna(pd.Series(df.columns)).tolist()
        df.columns = new_cols
        return df
    except Exception as e:
        print("Error with call: ", url)
        print(e)

def get_variables(url):
    response = requests.get(url)
    try:
        data = response.json()
        vars = data["variables"]
        var_lab_dict = {}
        for var in vars:
            var_lab_dict[var] = vars[var]["label"]
        return var_lab_dict
    except Exception as e:
        print(response.text)
        print(e)

@st.cache_data
def get_acs2020_5yr_profile_data(variables, state="*", district="*"):
    try:
        url = f"https://api.census.gov/data/2020/acs/acs5/profile?get={variables}&for=congressional%20district:{district}&in=state:{state}"
        response = requests.get(url)
        data = response.json()
        df = pd.DataFrame(data)
        df.columns = df.iloc[0]
        df = df[1:]
        new_cols = pd.Series(df.columns).map(var_lab_dict).fillna(pd.Series(df.columns)).tolist()
        df.columns = new_cols
        return df
    except Exception as e:
        print("Error with call: ", url)
        print(e)

def clean_acs_data(df, rename_dict):
    df["NAME"] = df["state_abbrev"] + "-" + df["congressional district"]
    df.drop(columns=["state", "congressional district", "state_abbrev"], inplace=True)
    state_col = df.pop('STATE')
    df.insert(1, 'STATE', state_col)
    for col in df.columns[2:]:
        df[col] = pd.to_numeric(df[col])
    df[['NAME', 'STATE']] = df[['NAME', 'STATE']].astype(str)
    df.rename(columns=rename_dict, inplace=True)
    df = df[list(df.columns[:2]) + [v for v in rename_dict.values()]] # reorder
    # DROP DC and ones with ZZ in the name
    df = df[~df["NAME"].str.contains("ZZ")]
    df = df[df["STATE"] != "None"]
    return df

def print_district(state, district, df):
    district = df.loc[(df["state"] == state) & (df["congressional district"] == district), "NAME"].values[0]
    print(district)

def fips_to_state_name(fips, abbr=False):
    state = us.states.lookup(fips)
    if abbr:
        return state.abbr if state else None
    else:
        return state.name if state else None

def varids_to_nicknames(list_of_vars, df_vars, df):
    nicknames = df_vars[df_vars["Variable ID"].isin(list_of_vars)]["Nickname"].tolist()
    nicknames = [var for var in df.columns if var in nicknames] # return in order of df columns
    return nicknames

def ordinaltg(n):
  return str(n) + {1: 'st', 2: 'nd', 3: 'rd'}.get(4 if 10 <= n % 100 < 20 else n % 10, "th")

## Create an html table for a given district that has each variable and its value for the three groups
def immigrant_comparison_table(district, df_native, df_foreign_cit, df_foreign_notcit):
    def process_df(df, column_name):
        processed_df = df.loc[df["NAME"] == district].drop(columns=["NAME"]).transpose()
        processed_df.columns = [column_name]
        return processed_df
    df_native = process_df(df_native, "Native")
    df_foreign_cit = process_df(df_foreign_cit, "Foreign born; Naturalized citizen")
    df_foreign_notcit = process_df(df_foreign_notcit, "Foreign born; Not a U.S. citizen")
    df = pd.concat([df_native, df_foreign_cit, df_foreign_notcit], axis=1).rename(columns={0: "Variable"})
    def format_value(value, variable_name):
        try:
            value = float(value)
            if value > 100:
                formatted_value = f"${value:,.0f}"
            else:
                formatted_value = value
        except ValueError:
            formatted_value = value
        
        if "Median" not in variable_name and "Mean" not in variable_name:
            formatted_value = f"{formatted_value}%"
        
        return formatted_value
    
    for column in df.columns:
        if column != "Variable":
            df[column] = df.apply(lambda row: format_value(row[column], row.name), axis=1)
    
    return df.to_html()


#### ==== Variables ACS5 Profile (MetaData) ==== ####
## MARK: Get Data
var_lab_dict = get_variables("https://api.census.gov/data/2022/acs/acs1/profile/variables.json")
var_lab_dict_immi = get_variables("https://api.census.gov/data/2022/acs/acs5/subject/groups/S0501.json")


### Get acs2022_1yr_selected_data
var_prefix = "S0501"
immigrant_vars = ["013E", "042E", "047E", "049E", "052E", "087E", "088E", "093E", "095E", "097E", "100E", "101E", "107E"]
occupation_vars = [str(i).zfill(3) + "E" for i in range(61, 66)]
groups = ["C02", 'C04', "C05"]
vars = []
for group in groups:
    vars += [var_prefix + f"_{group}_" + var for var in immigrant_vars + occupation_vars]
vars = vars + ["NAME"]
url = "https://api.census.gov/data/2022/acs/acs5/subject?get=group(S0501)&ucgid=pseudo(0100000US$5000000)"
response = requests.get(url)
data = response.json()
df_immi = pd.DataFrame(data)
df_immi.columns = df_immi.iloc[0]
df_immi = df_immi[1:]
df_immi = df_immi[[col for col in df_immi.columns if col in vars]]
df_immi["district"] = df_immi["NAME"].str.extract(r"(\d+)")[0].str.zfill(2) # select first number from the NAME column
df_immi["state"] = df_immi["NAME"].str.extract(r",\s*(.+)$") # select all characters before the comma beginning at the end of the string
df_immi["state_abbrev"] = df_immi["state"].apply(fips_to_state_name, abbr=True)
df_immi["NAME"] = df_immi["state_abbrev"] + "-" + df_immi["district"]
df_immi = df_immi[[col for col in df_immi.columns if col in vars]]


df_natives = df_immi[["NAME"]+[col for col in df_immi.columns if "_C02_" in col]]
df_foreign_cit = df_immi[["NAME"]+[col for col in df_immi.columns if "_C04_" in col]]
df_foreign_notcit = df_immi[["NAME"]+[col for col in df_immi.columns if "_C05_" in col]]
list_immi = [df_natives, df_foreign_cit, df_foreign_notcit]


natives_nicknames = {
    'Estimate!!Native!!Total population!!SEX AND AGE!!Median age (years)': 'Median age',
    "Estimate!!Native!!EDUCATIONAL ATTAINMENT!!Population 25 years and over!!Bachelor's degree": "Pct with Bachelor's degree (25+ years)",
    'Estimate!!Native!!LANGUAGE SPOKEN AT HOME AND ABILITY TO SPEAK ENGLISH!!Population 5 years and over!!Language other than English!!Speak English less than "very well"': 'Pct of English 2nd language speakers who speak English less than "very well"',
    'Estimate!!Native!!EMPLOYMENT STATUS!!Population 16 years and over!!In labor force': 'Labor force participation rate',
    'Estimate!!Native!!EMPLOYMENT STATUS!!Population 16 years and over!!In labor force!!Civilian labor force!!Unemployed': 'Unemployment rate',
    'Estimate!!Native!!Civilian employed population 16 years and over!!OCCUPATION!!Management, business, science, and arts occupations': 'Management, business, science, and arts occupations',
    'Estimate!!Native!!Civilian employed population 16 years and over!!OCCUPATION!!Service occupations': 'Service occupations',
    'Estimate!!Native!!Civilian employed population 16 years and over!!OCCUPATION!!Sales and office occupations': 'Sales and office occupations',
    'Estimate!!Native!!Civilian employed population 16 years and over!!OCCUPATION!!Natural resources, construction, and maintenance occupations': 'Natural resources, construction, and maintenance occupations',
    'Estimate!!Native!!Civilian employed population 16 years and over!!OCCUPATION!!Production, transportation, and material moving occupations': 'Production, transportation, and material moving occupations',
    'Estimate!!Native!!EARNINGS IN THE PAST 12 MONTHS (IN 2022 INFLATION-ADJUSTED DOLLARS) FOR FULL-TIME, YEAR-ROUND WORKERS!!Population 16 years and over with earnings!!Median earnings (dollars) for full-time, year-round workers:!!Male': 'Median earnings (full-time male workers)',
    'Estimate!!Native!!EARNINGS IN THE PAST 12 MONTHS (IN 2022 INFLATION-ADJUSTED DOLLARS) FOR FULL-TIME, YEAR-ROUND WORKERS!!Population 16 years and over with earnings!!Median earnings (dollars) for full-time, year-round workers:!!Female': 'Median earnings (full-time female workers)',
    'Estimate!!Native!!INCOME IN THE PAST 12 MONTHS (IN 2022 INFLATION-ADJUSTED DOLLARS)!!Households!!With Social Security income!!Mean Social Security income (dollars)': 'Mean Social Security income for households',
    'Estimate!!Native!!INCOME IN THE PAST 12 MONTHS (IN 2022 INFLATION-ADJUSTED DOLLARS)!!Households!!With Supplemental Security Income!!Mean Supplemental Security Income (dollars)': 'Mean Supplemental Security Income for households',
    'Estimate!!Native!!INCOME IN THE PAST 12 MONTHS (IN 2022 INFLATION-ADJUSTED DOLLARS)!!Households!!With cash public assistance income!!Mean cash public assistance income (dollars)': 'Mean cash public assistance income for households',
    'Estimate!!Native!!INCOME IN THE PAST 12 MONTHS (IN 2022 INFLATION-ADJUSTED DOLLARS)!!Households!!With Food Stamp/SNAP benefits': 'Pct Households receiving Food Stamp/SNAP benefits',
    'Estimate!!Native!!INCOME IN THE PAST 12 MONTHS (IN 2022 INFLATION-ADJUSTED DOLLARS)!!Households!!Median Household income (dollars)': 'Median household income',
    'Estimate!!Native!!POVERTY STATUS IN THE PAST 12 MONTHS!!POVERTY RATES FOR FAMILIES FOR WHOM POVERTY STATUS IS DETERMINED!!All families': 'Pct families in poverty',
}
foreign_cit_nicknames = {k.replace("Native", "Foreign born; Naturalized citizen"):v for k,v in natives_nicknames.items()}
foreign_notcit_nicknames = {k.replace("Native", "Foreign born; Not a U.S. citizen"):v for k,v in natives_nicknames.items()}
rename_dicts = [natives_nicknames, foreign_cit_nicknames, foreign_notcit_nicknames]


## rename columns
for df, rename_dict in zip(list_immi, rename_dicts):
    df.rename(columns=var_lab_dict_immi, inplace=True)
    df.rename(columns=rename_dict, inplace=True)
    df.rename(columns={"Geographic Area Name": "NAME"}, inplace=True)


## Create an html table for a given district that has each variable and its value for the three groups
# def immigrant_comparison_table(district, df_native, df_foreign_cit, df_foreign_notcit):
#     def process_df(df, column_name):
#         processed_df = df.loc[df["NAME"] == district].drop(columns=["NAME"]).transpose()
#         processed_df.columns = [column_name]
#         return processed_df
#     df_native = process_df(df_native, "Native")
#     df_foreign_cit = process_df(df_foreign_cit, "Foreign born; Naturalized citizen")
#     df_foreign_notcit = process_df(df_foreign_notcit, "Foreign born; Not a U.S. citizen")
#     df = pd.concat([df_native, df_foreign_cit, df_foreign_notcit], axis=1).rename(columns={0: "Variable"})
#     return df.to_html()


######### ========= Variables and Nicknames ========= ##########
## MARK: Variables/Nicknames
meta_vars = ["NAME"]
social_vars = ["DP02_0017E", "DP02_0068PE", "DP02_0094PE", "DP05_0018E", "DP02_0097PE"]
econ_vars = ["DP03_0002PE", "DP03_0005PE", "DP03_0062E", "DP03_0092E", "DP03_0119PE"]
industry_vars = ["DP03_0032E"] + [f"DP03_00"+str(i)+"PE" for i in range(33, 46)]
housing_vars = ["DP04_0001E", "DP04_0002E", "DP04_0003E", "DP04_0089E", "DP04_0134E", "DP04_0101E", "DP04_0047E", "DP04_0046E", "DP04_0115PE", "DP04_0142PE"]
all_vars = meta_vars + social_vars + econ_vars + industry_vars + housing_vars
all_vars_str = ",".join(all_vars)
var_dict = {k: var_lab_dict[k] for k in all_vars if k in var_lab_dict} # used only to get the info needed to give chatGPT
# Nicknames generated by chatGPT:
census_variable_nicknames = {
    "Estimate!!SEX AND AGE!!Total population!!Median age (years)": "Median Age",
    "Estimate!!HOUSEHOLDS BY TYPE!!Total households!!Average family size": "Avg Family Size",
    "Percent!!EDUCATIONAL ATTAINMENT!!Population 25 years and over!!Bachelor's degree or higher": "Pct Bachelors Or Higher",
    "Percent!!PLACE OF BIRTH!!Total population!!Foreign born": "Pct Foreign Born",
    'Percent!!U.S. CITIZENSHIP STATUS!!Foreign-born population!!Not a U.S. citizen': "Pct ForeignBorn Non-Citizen",
    "Percent!!EMPLOYMENT STATUS!!Population 16 years and over!!In labor force": "Pct In Labor Force",
    "Percent!!EMPLOYMENT STATUS!!Population 16 years and over!!In labor force!!Civilian labor force!!Unemployed": "Pct Unemployed",
    "Estimate!!INCOME AND BENEFITS (IN 2022 INFLATION-ADJUSTED DOLLARS)!!Total households!!Median household income (dollars)": "Median Household Income",
    "Estimate!!INCOME AND BENEFITS (IN 2022 INFLATION-ADJUSTED DOLLARS)!!Median earnings for workers (dollars)": "Median Worker Earnings",
    "Percent!!PERCENTAGE OF FAMILIES AND PEOPLE WHOSE INCOME IN THE PAST 12 MONTHS IS BELOW THE POVERTY LEVEL!!All families": "Pct Families Below Poverty Level",
    "Estimate!!INDUSTRY!!Civilian employed population 16 years and over": "Total Employed",
    "Percent!!INDUSTRY!!Civilian employed population 16 years and over!!Agriculture, forestry, fishing and hunting, and mining": "Pct Agriculture Mining",
    "Percent!!INDUSTRY!!Civilian employed population 16 years and over!!Construction": "Pct Construction",
    "Percent!!INDUSTRY!!Civilian employed population 16 years and over!!Manufacturing": "Pct Manufacturing",
    "Percent!!INDUSTRY!!Civilian employed population 16 years and over!!Wholesale trade": "Pct Wholesale Trade",
    "Percent!!INDUSTRY!!Civilian employed population 16 years and over!!Retail trade": "Pct Retail Trade",
    "Percent!!INDUSTRY!!Civilian employed population 16 years and over!!Transportation and warehousing, and utilities": "Pct Transportation and Warehousing, and Utilities",
    "Percent!!INDUSTRY!!Civilian employed population 16 years and over!!Information": "Pct Information",
    "Percent!!INDUSTRY!!Civilian employed population 16 years and over!!Finance and insurance, and real estate and rental and leasing": "Pct Finance and Insurance, and Real Estate",
    "Percent!!INDUSTRY!!Civilian employed population 16 years and over!!Professional, scientific, and management, and administrative and waste management services": "Pct Professional, scientific, and management, and administrative and waste management services",
    "Percent!!INDUSTRY!!Civilian employed population 16 years and over!!Educational services, and health care and social assistance": "Pct Education, Healthcare, and Social Assistance",
    "Percent!!INDUSTRY!!Civilian employed population 16 years and over!!Arts, entertainment, and recreation, and accommodation and food services": "Pct Arts, Entertainment, Recreation, and Accommodation and Food Services",
    "Percent!!INDUSTRY!!Civilian employed population 16 years and over!!Other services, except public administration": "Pct Other Services",
    "Percent!!INDUSTRY!!Civilian employed population 16 years and over!!Public administration": "Pct Public Admin",
    "Estimate!!HOUSING OCCUPANCY!!Total housing units": "Total Housing Units",
    "Estimate!!HOUSING OCCUPANCY!!Total housing units!!Occupied housing units": "Occupied Housing Units",
    "Estimate!!HOUSING TENURE!!Occupied housing units!!Renter-occupied": "Renter Occupied Units",
    "Estimate!!HOUSING TENURE!!Occupied housing units!!Owner-occupied": "Owner Occupied Units",
    "Estimate!!HOUSING OCCUPANCY!!Total housing units!!Vacant housing units": "Vacant Housing Units",
    "Estimate!!VALUE!!Owner-occupied units!!Median (dollars)": "Median House Value",
    "Estimate!!GROSS RENT!!Occupied units paying rent!!Median (dollars)": "Median Gross Rent",
    "Estimate!!SELECTED MONTHLY OWNER COSTS (SMOC)!!Housing units with a mortgage!!Median (dollars)": "Owner Median Monthly Housing Costs (Mortgage)",
    "Percent!!SELECTED MONTHLY OWNER COSTS AS A PERCENTAGE OF HOUSEHOLD INCOME (SMOCAPI)!!Housing units with a mortgage (excluding units where SMOCAPI cannot be computed)!!35.0 percent or more": "Pct Owners Paying 35%+ HH Income (mortgage)",
    "Percent!!GROSS RENT AS A PERCENTAGE OF HOUSEHOLD INCOME (GRAPI)!!Occupied units paying rent (excluding units where GRAPI cannot be computed)!!35.0 percent or more": "Pct Renters Paying 35%+ HH Income",
}

# make a dataframe with the variable id, label, and nickname
df_vars = pd.DataFrame(var_dict.items(), columns=["Variable ID", "Label"])
df_vars["Nickname"] = df_vars["Label"].map(census_variable_nicknames)
df_vars["Type"] = df_vars["Label"].apply(lambda x: "Dollars" if "dollars" in x else "Percentage" if "Percent" in x else "Number")


######## ========= Get Data and Clean Up ========= ########
### ACS1YR 2022 
variables = all_vars_str
df_raw = get_acs2022_1yr_profile_data(variables)
df_raw['state_abbrev'] = df_raw["state"].apply(fips_to_state_name, abbr=True)
df_raw['STATE'] = df_raw["state"].apply(fips_to_state_name)
df = df_raw.copy()
df = clean_acs_data(df, census_variable_nicknames)


### ACS5YR 2020
variables = all_vars_str
df_raw_2020 = get_acs2020_5yr_profile_data(variables)
df_raw_2020['state_abbrev'] = df_raw_2020["state"].apply(fips_to_state_name, abbr=True)
df_raw_2020['STATE'] = df_raw_2020["state"].apply(fips_to_state_name)
df_2020 = df_raw_2020.copy()
df_2020 = clean_acs_data(df_2020, census_variable_nicknames)

## MARK: MAIN
def number_formatter(value, variable):
    filtered_df = df_vars[df_vars["Nickname"] == variable]
    if filtered_df.empty:
        return "N/A"  # or handle it in another appropriate way
    var_type = filtered_df["Type"].values[0]
    if var_type == "Percentage":
        return f"{value:.1f}%"
    if var_type == "Dollars":
        return f"${value:,.0f}"
    if value < 100:
        return f"{value:.1f}"
    else:
        return f"{value:,.0f}"
    
def create_html_report(congressional_district, national_df, df2020, social_vars_v, econ_vars_v, industry_vars_v, housing_vars_v):
    df = national_df.query(f"NAME == '{congressional_district}'")
    industry_vars_v = sorted(industry_vars_v, key=lambda x: df[x].values[0], reverse=True)
    state = df["STATE"].values[0]
    state_df = national_df[national_df["STATE"] == state]
    template = Template('''
    <!DOCTYPE html>
    <html>
    <head>
        <title> {{ congressional_district }} Report</title>
        <style>
            table {
                border-collapse: collapse;
                width: 700px;
            }
            th, td {
                border: 1px solid black;
                padding: 6px;
                text-align: left;
                width: 50px;
            }
            th {
                background-color: #f2f2f2;
            }
        </style>
    </head>
    <body>
        <h1> {{ congressional_district }} Report</h1>
        <p> Data from the 2022 American Community Survey 1-Year and 2020 ACS 5-Year</p>
        <h2>Demographics</h2>
        <table>
            <tr>
                <th>Variable</th>
                <th>{{ congressional_district }} (118th)</th>
                <th> 2020 (116th)</th>
                <th> {{ state }} Districts</th>
                <th> Rank in {{ state }} </th>
                <th>All Districts</th>
                <th> Rank in US </th>
            </tr>
            {% for var in social_vars_v %}
            <tr>
                <td>{{ var }}</td>
                <td>{{ df[var] }}</td>
                <td>{{ df2020[var] }}</td>
                <td>{{ state_averages[var] }}</td>
                <td>{{ state_rank[var] }}</td>
                <td>{{ national_averages[var] }}</td>
                <td>{{ national_rank[var] }}</td>
            </tr>
            {% endfor %}
        </table>
        
        <h2>Economics</h2>
        <table>
            <tr>
                <th>Variable</th>
                <th>{{ congressional_district }} (118th)</th>
                <th> 2020 (116th)</th>
                <th> {{ state }} Districts</th>
                <th> Rank in {{ state }} </th>
                <th>All Districts</th>
                <th> Rank in US </th>
            </tr>
            {% for var in econ_vars_v %}
            <tr>
                <td>{{ var }}</td>
                <td>{{ df[var] }}</td>
                <td>{{ df2020[var] }}</td>
                <td>{{ state_averages[var] }}</td>
                <td>{{ state_rank[var] }}</td>
                <td>{{ national_averages[var] }}</td>
                <td>{{ national_rank[var] }}</td>
            </tr>
            {% endfor %}
        </table>
        
        <h2>Industry</h2>
        <table>
            <tr>
                <th>Variable</th>
                <th>{{ congressional_district }} (118th)</th>
                <th> 2020 (116th)</th>
                <th> {{ state }} Districts</th>
                <th> Rank in {{ state }} </th>
                <th>All Districts</th>
                <th> Rank in US </th>
            </tr>
            {% for var in industry_vars_v %}
            <tr>
                <td>{{ var }}</td>
                <td>{{ df[var] }}</td>
                <td>{{ df2020[var] }}</td>
                <td>{{ state_averages[var] }}</td>
                <td>{{ state_rank[var] }}</td>
                <td>{{ national_averages[var] }}</td>
                <td>{{ national_rank[var] }}</td>
            </tr>
            {% endfor %}
        </table>
        
        <h2>Housing</h2>
        <table>
            <tr>
                <th>Variable</th>
                <th>{{ congressional_district }} (118th)</th>
                <th> 2020 (116th)</th>
                <th> {{ state }} Districts</th>
                <th> Rank in {{ state }} </th>
                <th>All Districts</th>
                <th> Rank in US </th
            </tr>
            {% for var in housing_vars_v %}
            <tr>
                <td>{{ var }}</td>
                <td>{{ df[var] }}</td>
                <td>{{ df2020[var] }}</td>
                <td>{{ state_averages[var] }}</td>
                <td>{{ state_rank[var] }}</td>
                <td>{{ national_averages[var] }}</td>
                <td>{{ national_rank[var] }}</td>
            </tr>
            {% endfor %}
        </table>
        <h2> Immigrant Comparison </h2>
        <p> Data from the 2022 ACS 5-Year</p>
        {{ immigrant_table }}
    </body>
    </html>
    ''')

    state_averages = state_df.iloc[:, 2:].mean().to_dict()
    national_averages = national_df.iloc[:, 2:].mean().to_dict()
    df = df.iloc[0, 2:].to_dict()
    df2020 = df2020.iloc[0, 2:].to_dict()

    #For the values in the df, ID the rank of the value in the state and national averages
    state_rank = {}
    national_rank = {}
    for var in df.keys():
        ranked_df = national_df.sort_values(by=var, ascending=False).reset_index() # Create a new DataFrame that ranks each district based on the variable
        rank = ranked_df[ranked_df['NAME'] == congressional_district].index[0] + 1 # Find the rank of the specified district    
        state_ranked_df = state_df.sort_values(by=var, ascending=False).reset_index() # Create a new DataFrame that ranks each district based on the variable
        state_rank_val = state_ranked_df[state_ranked_df['NAME'] == congressional_district].index[0] + 1 # Find the rank of the specified district
        state_rank[var] = state_rank_val
        national_rank[var] = rank
    state_rank = {var: ordinaltg(value) for var, value in state_rank.items()}
    national_rank = {var: ordinaltg(value) for var, value in national_rank.items()}

    df = {var: number_formatter(value, var) for var, value in df.items()}
    df2020 = {var: number_formatter(value, var) for var, value in df2020.items()}
    state_averages = {var: number_formatter(value, var) for var, value in state_averages.items()}
    national_averages = {var: number_formatter(value, var) for var, value in national_averages.items()}

    immigrant_table = immigrant_comparison_table(congressional_district, df_natives, df_foreign_cit, df_foreign_notcit)

    html_report = template.render(
        congressional_district=congressional_district,
        state=state,
        df=df,
        df2020=df2020,
        state_rank=state_rank,
        national_rank=national_rank,
        social_vars_v=social_vars_v,
        econ_vars_v=econ_vars_v,
        industry_vars_v=industry_vars_v,
        housing_vars_v=housing_vars_v,
        state_averages=state_averages,
        national_averages=national_averages,
        number_formatter=number_formatter,
        immigrant_table = immigrant_table
    )
    return html_report


st.title("Congressional District Report Generator")
# User input for congressional district
congressional_district = st.text_input("Enter Congressional District (e.g., NC-11):")

# Button to generate report
if st.button("Generate Report"):
    if congressional_district:
        # Generate the report
        social_vars_v = varids_to_nicknames(social_vars, df_vars, df)
        econ_vars_v = varids_to_nicknames(econ_vars, df_vars, df)
        industry_vars_v = varids_to_nicknames(industry_vars, df_vars, df)
        housing_vars_v = varids_to_nicknames(housing_vars, df_vars, df)
        
        html_report = create_html_report(congressional_district, df, df_2020, social_vars_v, econ_vars_v, industry_vars_v, housing_vars_v)
        
        # Save the report to a file
        report_filename = f"{congressional_district}_report.html"
        with open(report_filename, "w") as f:
            f.write(html_report)
        
        # Display the report using components.html
        components.html(html_report, height=800, scrolling=True)
        
        # Provide a download link for the report
        with open(report_filename, "rb") as f:
            st.download_button(
                label="Download Report",
                data=f,
                file_name=report_filename,
                mime="text/html"
            )
    else:
        st.error("Please enter a valid congressional district.")



