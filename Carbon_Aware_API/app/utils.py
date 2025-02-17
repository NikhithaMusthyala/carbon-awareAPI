import os, requests, json, re
import pandas as pd
from flask import request, make_response, render_template, current_app
from werkzeug.utils import secure_filename
import dateutil.parser as parser
from requests.auth import HTTPBasicAuth
import statistics
import datetime
from datetime import datetime as dt
from app.caches.AzureDataCenter import AzureDataCenterInfo

ALLOWED_EXTENSIONS = set(['csv','json','xlsx'])
NAME_TO_DISPLAY = json.load(open('./app/static/name_to_display.json', 'r'))
DISPLAY_TO_NAME = json.load(open('./app/static/display_to_name.json', 'r'))

HOURS_IN_DAY = 24
MINUTES_IN_HOUR = 60
MINUTES_IN_DAY = 3600

# hard code of Time zone offsets from UTC
timezone_info = {
        "A": 1 * 3600, "ACDT": 10.5 * 3600, "ACST": 9.5 * 3600,"ACT": -5 * 3600,"ACWST": 8.75 * 3600,"ADT": 4 * 3600, "AEDT": 11 * 3600,
        "AEST": 10 * 3600, "AET": 10 * 3600,"AFT": 4.5 * 3600, "AKDT": -8 * 3600, "AKST": -9 * 3600, "ALMT": 6 * 3600,"AMST": -3 * 3600,
        "AMT": -4 * 3600,"ANAST": 12 * 3600,"ANAT": 12 * 3600,"AQTT": 5 * 3600, "ART": -3 * 3600,"AST": 3 * 3600,"AT": -4 * 3600, 
        "AWDT": 9 * 3600,"AWST": 8 * 3600, "AZOST": 0 * 3600, "AZOT": -1 * 3600, "AZST": 5 * 3600, "AZT": 4 * 3600, "AoE": -12 * 3600,
        "B": 2 * 3600,"BNT": 8 * 3600, "BOT": -4 * 3600, "BRST": -2 * 3600, "BRT": -3 * 3600, "BST": 6 * 3600, "BTT": 6 * 3600,
        "C": 3 * 3600,"CAST": 8 * 3600, "CAT": 2 * 3600, "CCT": 6.5 * 3600, "CDT": -5 * 3600, "CEST": 2 * 3600, "CET": 1 * 3600,
        "CHADT": 13.75 * 3600, "CHAST": 12.75 * 3600, "CHOST": 9 * 3600, "CHOT": 8 * 3600, "CHUT": 10 * 3600, "CIDST": -4 * 3600, 
        "CIST": -5 * 3600, "CKT": -10 * 3600,"CLST": -3 * 3600, "CLT": -4 * 3600, "COT": -5 * 3600, "CST": -6 * 3600,  "CT": -6 * 3600,"CVT": -1 * 3600,
        "CXT": 7 * 3600, "ChST": 10 * 3600, "D": 4 * 3600, "DAVT": 7 * 3600, "DDUT": 10 * 3600, "E": 5 * 3600, "EASST": -5 * 3600, 
        "EAST": -6 * 3600, "EAT": 3 * 3600, "ECT": -5 * 3600, "EDT": -4 * 3600,"EEST": 3 * 3600, "EET": 2 * 3600, "EGST": 0 * 3600, 
        "EGT": -1 * 3600, "EST": -5 * 3600, "ET": -5 * 3600,  "F": 6 * 3600, "FET": 3 * 3600, "FJST": 13 * 3600, "FJT": 12 * 3600,
        "FKST": -3 * 3600, "FKT": -4 * 3600, "FNT": -2 * 3600, "G": 7 * 3600, "GALT": -6 * 3600,"GAMT": -9 * 3600,"GET": 4 * 3600,
        "GFT": -3 * 3600, "GILT": 12 * 3600,"GMT": 0 * 3600, "GST": 4 * 3600,"GYT": -4 * 3600, "H": 8 * 3600, "HDT": -9 * 3600, 
        "HKT": 8 * 3600,"HOVST": 8 * 3600,"HOVT": 7 * 3600,"HST": -10 * 3600, "I": 9 * 3600, "ICT": 7 * 3600, "IDT": 3 * 3600,
        "IOT": 6 * 3600, "IRDT": 4.5 * 3600,"IRKST": 9 * 3600,"IRKT": 8 * 3600,"IRST": 3.5 * 3600,"IST": 5.5 * 3600, "JST": 9 * 3600,
        "K": 10 * 3600,"KGT": 6 * 3600,"KOST": 11 * 3600, "KRAST": 8 * 3600, "KRAT": 7 * 3600, "KST": 9 * 3600, "KUYT": 4 * 3600,
        "L": 11 * 3600, "LHDT": 11 * 3600, "LHST": 10.5 * 3600, "LINT": 14 * 3600, "M": 12 * 3600,"MAGST": 12 * 3600,"MAGT": 11 * 3600, "MART": 9.5 * 3600,"MAWT": 5 * 3600,
        "MDT": -6 * 3600, "MHT": 12 * 3600, "MMT": 6.5 * 3600,"MSD": 4 * 3600,"MSK": 3 * 3600, "MST": -7 * 3600, "MT": -7 * 3600, 
        "MUT": 4 * 3600, "MVT": 5 * 3600,"MYT": 8 * 3600, "N": -1 * 3600, "NCT": 11 * 3600,"NDT": 2.5 * 3600, "NFT": 11 * 3600,
        "NOVST": 7 * 3600, "NOVT": 7 * 3600,"NPT": 5.5 * 3600,"NRT": 12 * 3600,"NST": 3.5 * 3600,"NUT": -11 * 3600,"NZDT": 13 * 3600, "NZST": 12 * 3600,
        "O": -2 * 3600,"OMSST": 7 * 3600,"OMST": 6 * 3600,"ORAT": 5 * 3600, "P": -3 * 3600,"PDT": -7 * 3600,"PET": -5 * 3600,
        "PETST": 12 * 3600, "PETT": 12 * 3600,"PGT": 10 * 3600, "PHOT": 13 * 3600, "PHT": 8 * 3600, "PKT": 5 * 3600,"PMDT": -2 * 3600,
        "PMST": -3 * 3600,"PONT": 11 * 3600,"PST": -8 * 3600,"PT": -8 * 3600, "PWT": 9 * 3600, "PYST": -3 * 3600, "PYT": -4 * 3600,
        "Q": -4 * 3600,"QYZT": 6 * 3600, "R": -5 * 3600,"RET": 4 * 3600,"ROTT": -3 * 3600,"S": -6 * 3600,"SAKT": 11 * 3600,"SAMT": 4 * 3600, "SAST": 2 * 3600,"SBT": 11 * 3600, 
        "SCT": 4 * 3600, "SGT": 8 * 3600, "SRET": 11 * 3600, "SRT": -3 * 3600, "SST": -11 * 3600,"SYOT": 3 * 3600,"T": -7 * 3600, 
        "TAHT": -10 * 3600, "TFT": 5 * 3600,"TJT": 5 * 3600, "TKT": 13 * 3600, "TLT": 9 * 3600,"TMT": 5 * 3600,"TOST": 14 * 3600,
        "TOT": 13 * 3600,"TRT": 3 * 3600,"TVT": 12 * 3600,"U": -8 * 3600,"ULAST": 9 * 3600,"ULAT": 8 * 3600,"UTC": 0 * 3600,"UYST": -2 * 3600,"UYT": -3 * 3600,
        "UZT": 5 * 3600, "V": -9 * 3600,"VET": -4 * 3600,"VLAST": 11 * 3600, "VLAT": 10 * 3600,"VOST": 6 * 3600,"VUT": 11 * 3600,"W": -10 * 3600,
        "WAKT": 12 * 3600,"WARST": -3 * 3600,"WAST": 2 * 3600,"WAT": 1 * 3600, "WEST": 1 * 3600, "WET": 0 * 3600,"WFT": 12 * 3600,
        "WGST": -2 * 3600,"WGT": -3 * 3600, "WIB": 7 * 3600,"WIT": 9 * 3600,"WITA": 8 * 3600,"WST": 14 * 3600,"WT": 0 * 3600,"X": -11 * 3600,
        "Y": -12 * 3600,"YAKST": 10 * 3600,"YAKT": 9 * 3600, "YAPT": 10 * 3600, "YEKST": 6 * 3600,"YEKT": 5 * 3600,"Z": 0 * 3600,
}       

WattTime_abbrevs = {
    'PJM Roanoke':'PJM_ROANOKE',
    'PJM DC':'PJM_DC',
    'ERCOT San Antonio':'ERCOT_SANANTONIO',
    'PUD No 2 of Grant County':'GCPD',
    'National Electricity Market (Australia)':'NEM',
    'Ireland':'IE',
    'United Kingdom':'UK',
    'Netherlands':'NL',
    'MISO Madison City':'MISO_MASON_CITY',
    'PJM Chicago':'PJM_CHICAGO',
    'California ISO Northern':'CAISO_NORTH',
    'Independent Electricity System Operator (Ontario)':'IESO',
    'France':'FR',
    'Germany and Luxembourg':'DE_LU',
    'PacifiCorp East':'PACE',
    'Hydro Quebec':'HQ',
    'Arizona Public Service Co':'AZPS',
    'Norway':'NO'
}


ALLOWED_EXTENSIONS = set(['csv','json','xlsx'])
no_symbol = re.compile(r'[^\d.]+')

azure_data_center_info = AzureDataCenterInfo()

def get_token():
    '''
    this gets user name and password for WattTime from static file
    uses the credentials to ping WattTime API to generate a token to retrieve data
    '''
    # calling creds
    SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
    json_url = os.path.join(SITE_ROOT, "static", "login_creds.json")
    login_data = json.load(open(json_url))
    # WattTime ping with creds
    login_url = 'https://api2.watttime.org/v2/login'
    token = requests.get(login_url, auth=requests.auth.HTTPBasicAuth(login_data['username'], login_data['password'])).json()['token']
    return token


def protected_token():

    '''
    this gets user name and password for WattTime from a user input
    uses the credentials to ping WattTime API to generate a token to retrieve data
    '''

    user_name = request.args.get("user_name", None)
    pass_word = request.args.get("pass_word", None)
    login_url = 'https://api2.watttime.org/v2/login'
    token = requests.get(login_url, auth=HTTPBasicAuth(user_name, pass_word)).json()['token']
    return token


def getloc_helper(data_center_diplayName):

    '''
    this function takes in the full name of a Data Center grabs usefull data
    that can be used for various operations
    the data schema is:
    {Data Center Display Name, Balancing Authority Name, Balancing Authority Abbreviation, 
     Latitude of DC, Longitude of DC, Balancing Authority id}
    '''

    data_center_info = azure_data_center_info.get_az()

    # allow query string to be used in place of form POST
    if not data_center_diplayName:
        try:
            data_center_diplayName = request.form.get('data', None)
            if data_center_diplayName == 'nada':
                msg = 'ensure all required parameters were entered'
                return make_response(render_template('data_error.html' , msg=msg), 404 )
        except ValueError:
            msg= 'begin a search first'
            return make_response(render_template('data_error.html', msg=msg), 502 )
    
    key = "displayName"
    input_value = data_center_diplayName
    token = get_token()

    # finding coords for the passed AZ_region
    # finds where the value of the key is equal to the input query value
    # this parses the Data Center information json  
    # 
    data_center_dict = next(filter(lambda x: x.get(key) == input_value, data_center_info), None)
    if data_center_dict == None:
        msg= 'verify a valid Azure region was used.'
        return make_response(render_template('data_error.html', msg=msg), 404 )

    #calling coords of AZ region
    data_center_latitude = data_center_dict['metadata']['latitude']
    data_center_longitude = data_center_dict['metadata']['longitude']

    # WattTime connection to get ba
    region_url = 'https://api2.watttime.org/v2/ba-from-loc'
    headers = {'Authorization': 'Bearer {}'.format(token)}
    params = {'latitude': data_center_latitude, 'longitude': data_center_longitude}
    rsp=requests.get(region_url, headers=headers, params=params)

    # WattTime response and adding the azure region for output
    data = json.loads(rsp.text)
    data['AZ_Region'] = data_center_diplayName
    print(f"getloc_helper data = {data}")

    return data

# for balancing authority input
def from_ba_helper(BA_full_name):

    '''
    this function takes in the full name of a WattTime balancing authority grabs usefull data
    that can be used for various operations
    the data schema is:
    {Data Center Display Name, Balancing Authority Name, Balancing Authority Abbreviation, 
     Latitude of DC, Longitude of DC, Balancing Authority id}
    '''

    data_center_info = azure_data_center_info.get_az()
    df = WT_Regions
    # allow for swagger GET
    if BA_full_name != None:
        pass
    # next
    else:
        try:
            if len(request.form.get('data', None)) == 0:
                return make_response(render_template('ba_error.html'), 404 )
            elif len(request.form.get('data', None)) != 0:
                BA_full_name = request.form.get('data', None)
                if BA_full_name == 'nada':
                    return make_response(render_template('ba_error.html'), 404 )
        # if no parameters are received throw an error
        except ValueError:
            msg= 'begin a search first'
            return make_response(render_template('data_error.html', msg=msg), 502 )

    for sublist in df:
        if BA_full_name in sublist:
            index_val = df.index(sublist)
            print(df.index(sublist))
            data_center_displayName = (az_coords_WT_joined[0][index_val]['displayName'])
            df = str.strip(re.sub('[^A-Z]', ' ', df[index_val][18:42]))
            ba_abbrev = re.sub('[^A-Z]', '_', df)
            ba_abbrev = ba_abbrev.split('___', 1)[0]
            data = {'AZ_Region':data_center_displayName,
             'name':BA_full_name, 'abbrev':ba_abbrev,
             'latitude':data_center_info[index_val]['metadata']['latitude'], 
             'longitude' : data_center_info[index_val]['metadata']['longitude'],
             'id' : no_symbol.sub('', WT_Regions[index_val][6:9])
            }
            print(data)
            
            return data
    return ''

def allowed_file(filename):
    '''
    calls the ALLOWED_EXTENSIONS folder to check and make sure the submitted file
    is an accepted type. .xslx , .csv , or .json are accepted
    '''
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def get_file_data():
    if request.method == 'POST':
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            print(filename)
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
            file.save(file_path)
            print('file uploaded')
            #SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
            #file_url = os.path.join(SITE_ROOT, "uploads", filename)

            return file_path
    return ''

def get_start_end(filename):

    '''
    reads the last charcaters of the file name string to determine load method.
    this then finds and outputs the first and last timestamp as start and stop
    these are the start and end times for the energy profile
    '''

    file_type_check = str(filename)

    if file_type_check[-4:] == 'xlsx':
        intro = pd.read_excel(filename, engine='openpyxl')
        return get_start_end_tabular(intro)  
    elif file_type_check[-3:] == 'csv':
        intro = pd.read_csv(filename)
        return get_start_end_tabular(intro)
    else:
        startstop = json.load(open(filename, 'rb'))['timespan'].split('/')
        start = pd.to_datetime(startstop[0]).isoformat()
        stop = pd.to_datetime(startstop[1]).isoformat()
        return start, stop


def get_start_end_tabular(intro):

    '''
    for xlsx and csv dtypes from get_start_end()
    grabs the first and last timestamps for the energy profile's start and
    end times
    '''
    
    intro_times = intro.iloc[1:3,0]
    # print("\n\n")
    # print("Intro", intro.columns, intro.shape, intro.iloc[0:4,1:3])
    # If the file contains the local timezone in parentheses
    print(intro_times)
    if '(' in intro_times.iloc[0]:
        start = re.search(r"[... \d][^\(]+", intro_times.iloc[0]).group(0).strip()
        end = re.search(r"[... \d][^\(]+", intro_times.iloc[1]).group(0).strip()
        start = pd.to_datetime(re.search(r"^[A-Za-z1-9].+:\d\d", start).group(0) + re.search(r".{5}$", start).group(0)).isoformat()
        end = pd.to_datetime(re.search(r"^[A-Za-z1-9].+:\d\d", end).group(0) + re.search(r".{5}$", end).group(0)).isoformat()
    # Otherwise, the file is in UTC
    else:
        start = pd.to_datetime(re.search(r"\d{2} ... \d{4} \d{2}:\d{2}:\d{2}", intro_times.iloc[0]).group(0)).isoformat()
        end = pd.to_datetime(re.search(r"\d{2} ... \d{4} \d{2}:\d{2}:\d{2}", intro_times.iloc[1]).group(0)).isoformat()
    return start, end



# get real-time data via lat/lon inputs
def get_realtime_data_loc(lat, lon):
    token = get_token()
    index_url  = 'https://api2.watttime.org/index'
    headers = {'Authorization': 'Bearer {}'.format(token)}
    params = {'latitude': lat, 'longitude':lon}
    rsp = requests.get(index_url, headers=headers, params=params)
    return rsp.json()

# get a dict of forecast data via balancing authority abbrev
def get_region_forcast(ba):
    token = get_token()
    forecast_url = 'https://api2.watttime.org/v2/forecast'
    headers = {'Authorization': 'Bearer {}'.format(token)}
    params = {'ba': ba}
    rsp = requests.get(forecast_url, headers=headers, params=params)
    return rsp.json()

# ==========================================================
# begining logs for impact tracking
# ==========================================================

def update_usage_data():
    '''
    Updates json file with newest entry from user input
    Records the data from the prediction as well as if the prediction was used
    '''

    usage = request.args.get('usage', None)# get indicator of if the cron time was accepted
    payload = request.args.get('pred_data', None) # output of prediction
    new_usage_data = [[usage, payload]].to_dict()
    if not os.path.isdir("./local_files"): #If this directory doesn't exist, the json file containing the history doesn't as well.
        os.mkdir("./local_files")
        data = [new_usage_data]
    else: # Directory + cached file exists    
        data = json.load(open("./local_files/usage_data.json",))
        data.append(new_usage_data)
    with open("./local_files/usage_data.json", "w") as cachedfile:
            json.dump(data, cachedfile)


def avg_carbon_saved():
    '''
    Opens cached log with schema {'usage', 'payload'} which is 
        a logical response of if the prediction was accepted 0=Not accepted, 1=accepted
        payload is the prediction data containing (see /geotime_shift) current_starttime
        and percentage_decrease which are the time the prediction was made and the percent
        difference of the current WS emissions and the prediciton WS emissions
    '''

    with open("./local_files/usage_data.json", "r") as file_in:
        carbon_data = json.loads(json.load(file_in)) # Read in as string json. doing a second json.loads deserializes into json/dict object. 
    
    used_preds_perc_diff = []
    # getting only perc_diff that were used. ignores unused predictions
    for prediction in range(len(carbon_data)):
        if carbon_data[prediction]['usage'] == 1:
            carbon_percdiff = carbon_data[prediction]['payload']['percentage_decrease']
            used_preds_perc_diff.append(carbon_percdiff)
    carbon_avg_percdiff = statistics.mean(used_preds_perc_diff)

    return carbon_avg_percdiff

# Initialization
WT_Regions = []

# calling Data Center information from json file in static folder. 
az_coords = azure_data_center_info.get_az()

token = get_token()
# loop to associate WattTime regions to AZ regions 
for i in range(len(az_coords)):
    region_url = 'https://api2.watttime.org/v2/ba-from-loc'
    headers = {'Authorization': 'Bearer {}'.format(token)}
    params = {'latitude': az_coords[i]['metadata']['latitude'],
              'longitude': az_coords[i]['metadata']['longitude']}
    rsp=requests.get(region_url, headers=headers, params=params)
    WT_Regions.append(rsp.text)
    #print(rsp.text)

#combining on index
az_coords_WT_joined = [az_coords, WT_Regions]
WT_names = pd.DataFrame([json.loads(x) for x in WT_Regions])[['name','abbrev']].dropna()


def format_json(filename):
    '''
    Convert json file into a pandas dataframe
    '''
    Monitor_data = json.load(open(filename))
    az_file = pd.DataFrame(Monitor_data['value'][0]['timeseries'][0]['data']).dropna()
    az_file.columns = ['Time', 'Total']
    return az_file

def format_dataframe(df, gpuutil_flag):
    '''
    Reformat input pandas dataframe to match the requirements needed for latter functions. Check number of columns, ensure index is represented, followed by datetime. 
    Check for GPUUtilization column and name all of them properly.
    Arguments:
        df: pandas dataframe converted from either csv or xlsx filetype
        gpuutil_flag: boolean of whether or not the user wanted to add gputilization to their output
    '''
    df_loc = df[10:].dropna()
    #print(df_loc)

    columns = df.iloc[9,:]
    df_loc.columns = [col for col in columns]

    ## If first column contains datetimes as datetimes or strings, add an index column
    if (type(df_loc.iloc[0,0]) == type(datetime.datetime.now())) |(type(df_loc.iloc[0,0]) == type('a')):
        df_loc.reset_index(inplace = True)
    ## Else if first column is not an integer (is not an index), then return an error
    elif (type(df_loc.iloc[0,0]) != type(1)):
        msg = 'use either a .xlsx, .csv, or .json file with the proper column formatting.'
        return make_response(render_template('data_error.html',msg=msg), 411) 
    # Name first two cols
    df_loc.columns.values[0] = 'Index'
    df_loc.columns.values[1] = 'Time'


    # create new df to hold reconfigured data; begin with index and time
    az_file = df_loc[['Index','Time']]
    for col in df_loc.columns:
        print(col)
        # search for Joules metric; add it when found
        if 'GpuEnergyJoules' in col:
            az_file = pd.concat((az_file, df_loc[col]), axis = 1)
            az_file.columns.values[2] = 'Total'
        # currently just check for if it exists; we should also decide on whether or not to add logic for the user filling out the form indicating GPUUtil option is active
        # grab GPUUtilization if it is found 
        print('GpuUtilization' in col)
        print(gpuutil_flag == 1)
        if ('GpuUtilization' in col) & (gpuutil_flag == 1):
            az_file = pd.concat((az_file, df_loc[col]), axis = 1)
            az_file.columns.values[3] = 'GPUUtil'
            print("Marked")
    # throw error if not found
    if 'Total' not in az_file.columns:
        msg = 'use either a .xlsx, .csv, or .json file with a column representing GPUEnergyJoules metric.'
        return make_response(render_template('data_error.html',msg=msg), 411) 
    #print(az_file)
    return az_file

def compare_intervals(df):
    '''
    Integity check to ensure that time intervals are 300 seconds apart.
    Arguments:
        df: pandas dataframe properly formatted to contain the `Time` column
    
    Output:
        Boolean stating whether or not the time intervals are 300 seconds
    '''
    ## grab the middle time value
    time_1_choice = df['Time'][int(len(df)/2)]
    try:
        t1 = time_1_choice.split(" ")[1]
    except:
        try:
            FMT = '%H:%M:%S'
            time_1_choice = dt.strftime(time_1_choice, FMT)
            print(time_1_choice)
            t1 = time_1_choice
        except:
            FMT = '%H:%M'
            t1 = time_1_choice
    ## grab middle +1 time value
    time_2_choice = df['Time'][int(len(df)/2)+1]
    try:
        t2 = time_2_choice.split(" ")[1]
    except:
        try:
            FMT = '%H:%M:%S'
            time_2_choice = dt.strftime(time_2_choice, FMT)
            print(time_2_choice)
            t2 = time_2_choice
        except:
            FMT2 = '%H:%M'
            print(time_2_choice)
            t2 = time_2_choice

    ### Setup comparison for 5 min intervals
    try:
        tdelta = dt.strptime(t2, FMT) - dt.strptime(t1, FMT)
    except:
        tdelta = dt.strptime(t2, FMT2) - dt.strptime(t1, FMT2)
    bench = datetime.timedelta(seconds = 300)

    return tdelta == bench

def get_percent_zero(ba):
    token = get_token()
    endtime = datetime.datetime.now().isoformat()
    starttime = (datetime.datetime.now() - datetime.timedelta(days=7)).isoformat()
    data_url = 'https://api2.watttime.org/v2/data'
    headers = {'Authorization': 'Bearer {}'.format(token)}
    params = {'ba': ba, 
            'starttime': starttime, 
            'endtime': endtime}
    rsp = requests.get(data_url, headers=headers, params=params)
    
    parsed_rsp = rsp.json()

    count_moer = 0
    count_zero = 0
    
    for i in parsed_rsp:
        if int(i["value"]) == 0:
            count_zero+=1    
        count_moer+=1

    percent_zero = round((count_zero/count_moer)*100, 2)
    return percent_zero



def get_SKU_table():
    SITE_ROOT = os.path.realpath(os.path.dirname(__file__))
    csv_url = os.path.join(SITE_ROOT, "static", "Region-SKU-Tags.csv")
    SKU_data_table = pd.read_csv(csv_url).dropna()
    return SKU_data_table


def Law_filter(SKU_data_table, sensitive_check_box, Az_region):
    '''
    function to filter based on sovereignty laws.  
    if user specifies the shift contains protected data that is subject to migration laws
    limits regions in geo shift to only compliant regions
    '''
    try:
        if sensitive_check_box == 'on':
            geo = pd.DataFrame([SKU_data_table[SKU_data_table['region']==Az_region]['R_Tag_lock'].values])
            print(f"Regional Lock Tag for current region is {geo}")
            SKU_data_table_filtered = SKU_data_table[SKU_data_table['R_Tag_lock'] == geo[0].values[0]].reset_index()
        else:
            SKU_data_table_filtered = SKU_data_table.reset_index()
    except KeyError:   # if name was provided as an name not displayName
        if sensitive_check_box == 'on':
            geo = pd.DataFrame([SKU_data_table[SKU_data_table['region']==NAME_TO_DISPLAY[Az_region]]['R_Tag_lock'].values])
            print(f"Regional Lock Tag for current region is {geo}")
            SKU_data_table_filtered = SKU_data_table[SKU_data_table['R_Tag_lock'] == geo[0].values[0]].reset_index()
        else:
            SKU_data_table_filtered = SKU_data_table.reset_index()
        
    return SKU_data_table_filtered
   
def Gpu_filter(SKU_data_table_filtered,desired_GPU):
    '''
    function to take in region sku/law list which is either filtered by law or not
    looks at if a region has the desired GPU available
    if not, removes the region from potential shifting list
    '''
    GPU_Regions = []
    if desired_GPU == 'nada':
        for x in range(len(SKU_data_table_filtered)):
            GPU_Regions.append(SKU_data_table_filtered['region'][x])
    else:
        for x in range(len(SKU_data_table_filtered)):
            if desired_GPU in SKU_data_table_filtered['sku'][x]:
                GPU_Regions.append(SKU_data_table_filtered['region'][x])
    
    return GPU_Regions


def get_average_emission(ba):
    token = get_token()
    endtime = datetime.datetime.now().isoformat()
    starttime = (datetime.datetime.now() - datetime.timedelta(days=365)).isoformat()
    data_url = 'https://api2.watttime.org/v2/avgemissions/'
    headers = {'Authorization': 'Bearer {}'.format(token)}
    params = {'ba': ba, 
            'starttime': starttime, 
            'endtime': endtime}
    rsp = requests.get(data_url, headers=headers, params=params)
    
    rsp_list = rsp.json()
    
    count_aoer = len(rsp_list)
    sum_aoer = 0
    if count_aoer == 0:
        avg_aoer = 0
    else:
        for i in rsp_list:
            sum_aoer = sum_aoer + int(i["value"])
        avg_aoer = (sum_aoer/count_aoer)
    
    return round(avg_aoer, 2)