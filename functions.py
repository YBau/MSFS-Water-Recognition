from termcolor import colored
import numpy as np
import matplotlib.pyplot as plt
from matplotlib import cm
from matplotlib.colors import ListedColormap
import requests
import time
import pandas as pd
import uuid


# =============================================================================
# %% General functions
# =============================================================================

def seconds_to_time(seconds, n_decimals=2) :
    h = int(seconds//3600)
    m = int(seconds//60 - h*60)
    s = seconds - m*60 - h*3600
    if h > 0 :
        return f'{h:0>2}:{m:0>2}:{round(s):0>2}'
    elif m > 0 : return f'{m:0>2}:{round(s):0>2}'
    else : return '{:.{}f}s'.format(s, n_decimals)

def meters_to_latitude(m) :
    """
    Convert a vertical distance on earth into a latitude angle
    """
    r_earth = 6371e3
    # r_earth * arc_rad = m
    arc_rad = m/r_earth
    arc_deg = arc_rad * 180/np.pi
    return arc_deg

def land_water_cmap(threshold=0) :
    """
    Create a blue/green colormap of 256 values with a clear limit between green and blues.
    This limit is located at threshold for values going from -1 to 1.
    """
    Blues = cm.get_cmap('Blues', 256)
    Greens = cm.get_cmap('Greens', 256)
    newcolors = Blues(np.linspace(0, 1, 256))
    new_greens = Greens(np.linspace(0, 1, 256))
    lim = int(256 + 256*(threshold-1)/2)
    newcolors[:lim, :] = np.flip(new_greens[256-lim:256, :], axis = 0)
    newcmp = ListedColormap(newcolors)
    return newcmp

# =============================================================================
# %% For Snappy functions
# =============================================================================

def read_zip_name(name, display=False):
    # first get rid of path and '.zip'
    name = name.strip('.zip').split('\\')[-1]
    dic = {}
    
    #gather first data
    dic['mission id'] = mission_id = name.split('_')[0]
    if 'S1' in dic['mission id'] :
        mission_id, mode_beam, x1, x2, d1, d2, n_orbit_abs, mission_datatake, ID = name.split('_')
        prod_type = x1[:3]
        res_class = x1[3:]
        processing_lvl = x2[0]
        prod_class = x2[1]
        polarization = x2[2:]
        if display :
            print(
                colored('Mission identifier : ', 'cyan') + f'{mission_id}\n' +
                colored('Mode beam : ', 'cyan') + {'IW':'Interferometric wide (IW)', 'SM':'S1-6 (SM)', 'EW':'EW', 'WW':'WW'}[mode_beam] + '\n' + 
                colored('Product type : ', 'cyan') + "{}\n".format({'SLC':'Single look complex (SLC)', 'GRD':'Ground range detection (GRD)', 'OCN':'OCN'}[prod_type]) +
                colored('Resolution class : ', 'cyan') + f'{res_class}\n'*(prod_type=='GRD') +
                colored('Processing level : ', 'cyan') + f'{processing_lvl}\n' +
                colored('Product class : ', 'cyan') + '{}\n'.format({'S':'Standard (S)', 'A':'Annotation (A)'}[prod_class]) +
                colored('Polarization : ', 'cyan') + {'SH':'Single HH', 'SV':'Single VV', 'DH':'Dual HH+HV', 'DV':'Dual VV+VH'}[polarization] + '\n' +
                colored('Starting date : ', 'cyan') + '{}/{}/{} at {}:{}:{}\n'.format(d1[6:8], d1[4:6], d1[:4], d1[9:11], d1[11:13], d1[13:]) +
                colored('Ending date : ', 'cyan') + '{}/{}/{} at {}:{}:{}\n'.format(d2[6:8], d2[4:6], d2[:4], d2[9:11], d2[11:13], d2[13:]) +
                colored('Absolute orbit number : ', 'cyan') + '{}\n'.format(int(n_orbit_abs)) +
                colored('Mission data-take : ', 'cyan') + f'{mission_datatake}\n' +
                colored('Product unique ID : ', 'cyan') + f'{ID}'
                )
        return mission_id, mode_beam, prod_type, res_class, processing_lvl, prod_class, polarization, d1, d2, n_orbit_abs, mission_datatake, ID
    if 'S2' in dic['mission id'] :
        mission_id, prod_lvl, date, proc_bl, rel_orbit, tile_num, d2 = name.split('_')
        if display :
            print(
                colored('Mission identifier : ', 'cyan') + f'{mission_id}\n' +
                colored('Product level : ', 'cyan') + "{}\n".format({'MSIL1C':'Level-1C','MSIL2A':'Level-2A','MSIL2Ap':'Level-2Ap'}[prod_lvl]) +
                colored('Starting date : ', 'cyan') + '{}/{}/{} at {}:{}:{}\n'.format(date[6:8], date[4:6], date[0:4], date[9:11], date[11:13], date[13:]) +
                colored('Processing baseline number : ', 'cyan') + '{}\n'.format(proc_bl) +
                colored('Relative orbit number : ', 'cyan') + '{}\n'.format(int(rel_orbit[1:])) +
                colored('Tile number : ', 'cyan') + f'{tile_num}\n' +
                colored('Ingestion Date : ', 'cyan') + '{}/{}/{} at {}:{}:{}\n'.format(d2[6:8], d2[4:6], d2[0:4], d2[9:11], d2[11:13], d2[13:])
                )
        return name.split('_')
        

def output_view(product, band_names, minima=None, maxima=None):
    '''
    Creates visualization of product data
    
    Keyword arguments:
    product       -- snappy GPF product --> input Sentinel-1 product 
    band          -- List --> product's band to be visualized
    minima        -- List --> minimum values for each band, for visualisation
    maxima        -- List --> maximum values for each band, for visualisation
    '''
    band_data_list = []
    n = len(band_names)
    if minima == None : minima = [None]*n 
    if maxima == None : maxima = [None]*n
    assert len(minima) == n, "minima has not the required number of elements"
    assert len(maxima) == n, "maxima has not the required number of elements"
    
    for i in band_names:
        band = product.getBand(i)
        w = band.getRasterWidth()
        h = band.getRasterHeight()
        band_data = np.zeros(w * h, np.float32)
        band.readPixels(0, 0, w, h, band_data)
        band_data.shape = h, w
        band_data_list.append(band_data)
    
    n_rows = (n+1)//2
    fig, ax = plt.subplots(n_rows,min(n,2), figsize=(min(n,2)*9,9)) # (length, height)
    if n == 1 :
        ax = [ax]
    if n > 2 :
        ax1 = []
        for i in range(n_rows) :
            for j in range(2) :
                ax1.append(ax[i][j])
        ax = ax1
    for i in range(n) :
        ax[i].imshow(band_data_list[i], cmap='gray', vmin=minima[i] , vmax=maxima[i])
        ax[i].set_title(band_names[i])
        
    
    for ax in fig.get_axes():
        ax.label_outer()
    plt.tight_layout()

def output_RGB(product, RGB_band_names):
    '''
    Creates visualization of product data in RGB
    
    Keyword arguments:
    product       -- snappy GPF product --> input Sentinel-1 product 
    band          -- List --> 3 product's band to be visualized in order RGB
    minima        -- List --> minimum values for each band, for visualisation
    maxima        -- List --> maximum values for each band, for visualisation
    '''
    assert len(RGB_band_names)==3, 'There must be 3 bands'
    RGB_bands = []
    for i, band_name in enumerate(RGB_band_names):
        band = product.getBand(band_name)
        if i == 0 :
            w = band.getRasterWidth()
            h = band.getRasterHeight()
        color_band = np.zeros(w*h, np.float32)
        band.readPixels(0, 0, w, h, color_band)
        min_color = min(color_band); max_color = max(color_band)
        RGB_bands.append((color_band-min_color)/(max_color-min_color)) # put the image on 0 to 1 scale
    
    RGB = np.dstack(RGB_bands)
    RGB.shape = h, w, 3
    
    fig, ax = plt.subplots(1,1, figsize=(10,10)) # (length, height)
    ax.imshow(RGB)
    ax.set_title('RGB')
    plt.tight_layout()

def search_online_prod(filename = "*", footprint=[], max_cloudcoverpercentage = 20, username="ybau", password="Copernicus.city7"):
    """
    Returns product names corresponding to the search
    See https://scihub.copernicus.eu/userguide/OpenSearchAPI for more details
    No ice or snow tolerated on pictures : snowicepercentage == 0
    
    Keyword arguments:
    filename    -- string --> filename of the product, can be written with * and ?.
    footprint   -- list --> list of points (1, 3 or more) which must be intersected by the images. 0 point means ignoring this parameter
        example : footprint = [(41.9, 12.5)] 
        !!! Latitude, Longitude format !!!
    max_cloudcoverpercentage --float --> maximum tolerable cloud coverage in percent

    """
    
    assert (len(footprint) != 2), "more than 2 points are required to create a polygon"
    if len(footprint) == 0 : footprinturl = "*"
    elif len(footprint) == 1 : footprinturl = f"{footprint[0][0]},{footprint[0][1]}"
    else :
        footprinturl = "POLYGON(("
        for point in footprint :
            footprinturl += f"{point[0]} {point[1]},"
        footprinturl = footprinturl[:-1] + "))" # delete last coma and close parenthesis        
    
    def request_productdata(start_index=0, rows=100):
        url0 = 'https://scihub.copernicus.eu/dhus/search?'
        url1 = f'start={start_index}&rows={rows}&'
        url2 = f'q=filename:{filename}'
        if footprinturl != "*":
            url3 = f' AND footprint:"intersects({footprinturl})"'
        else : url3 = ""
        url4 = "&orderby=beginposition desc"
        query = (url0 + url1 + url2 + url3 + url4)
        # print(query)
        response = requests.get(query, auth=requests.auth.HTTPBasicAuth(username, password))
        dic = xmltodict.parse(response.text)
        if 'error' in dic['feed'].keys() :
            code = dic['feed']['error']['code']
            mes = dic['feed']['error']['message']
            print(colored(f'error {code} :', 'red'))
            print(mes)
        return dic
    
    dic = request_productdata()
    if 'error' in dic['feed'].keys() : return []
    
    selected_products = {}
    n_prod = int(dic["feed"]["opensearch:totalResults"])
    if n_prod == 0 : 
        print("no product found")
        return []
    
    start_index = 0
    last_index =0
    while start_index + last_index +1 < n_prod :
        # print(n_prod, dic.keys(), start_index, last_index)
        if last_index!= 0:
            dic = request_productdata(start_index=start_index+last_index+1)
            if 'error' in dic['feed'].keys() : return []
        
        start_index = int(dic["feed"]["opensearch:startIndex"]) # new start_index
        list_prod = dic["feed"]["entry"]
        
        for i in range(len(list_prod)) :
            name = list_prod[i]["title"]
            cloudcoverpercentage = -1
            snowicepercentage = -1
            double_list = list_prod[i]["double"]
            for dic2 in double_list :
                if dic2["@name"] == "mediumprobacloudpercentage" : 
                    cloudcoverpercentage = float(dic2["#text"])
                if dic2["@name"] == "snowicepercentage" : 
                    snowicepercentage = float(dic2["#text"])
            if snowicepercentage == 0 and cloudcoverpercentage <= max_cloudcoverpercentage :
                selected_products[name] = list_prod[i]["link"][0]["@href"]
        last_index = len(list_prod)-1
    
    return selected_products

# =============================================================================
# %% Elevation functions
# =============================================================================
    
def get_elevation_openelevation(lat, lon):
    """
    Return elevation from latitude, longitude based on the SRTM mesh, pretty long to respond
    """
    assert -60 <= lat <= 60, "SRTM dataset has data only in latitudes between -60° and 60°"
    query = ('https://api.open-elevation.com/api/v1/lookup'
             f'?locations={lat},{lon}')
    # one approach is to use pandas json functionality:
    # elevation = pd.io.json.json_normalize(r, 'results')['elevation'].values[0]
    loop = True
    while loop :
        try : # sometime the request fails, so restart
            r = requests.get(query).json()  # json object, various ways you can extract value
            loop = False
        except : loop = True
    elevation = pd.json_normalize(r, 'results')['elevation'].values[0]
    return elevation

def get_elevation_opentopodata(lat, lon, source = 'mapzen'):
    query = (f'https://api.opentopodata.org/v1/{source}'
              f'?locations={lat},{lon}')
    # one approach is to use pandas json functionality:
    # elevation = pd.io.json.json_normalize(r, 'results')['elevation'].values[0]
    loop = True
    while loop :
        try : # sometime the request fails, so restart
            r = requests.get(query).json()  # json object, various ways you can extract value
            if r['status'] != 'OK' : 
                if 'error' in r.keys() :
                    print(r['error'])
                else :
                    print(r)
            loop = False
        except : loop = True
    elevation = pd.json_normalize(r, 'results')['elevation'].values[0]
    return elevation

def get_multiple_elevation_opentopodata(lat_lon_array, source = 'mapzen'):
    """ 
    Entry : lat_lon_array, an array of shape (n, 2) where n is the number of coordinates
            and coordinates are presented in the order lat, lon in the decimal format
    Output : an array of shape (n,) with all altitudes at the given points.
    """
    # maximum query must be 100 points long
    n = len(lat_lon_array)
    elevations = np.zeros(n,)
    i0 = i = 0
    t0 = time.time()
    t_wait = 1 # time to wait between requests
    while i0 < n :
        query = f'https://api.opentopodata.org/v1/{source}?locations='
        i=0
        while i < 100 and i0 + i < n :
            lat, lon = lat_lon_array[i0+i]
            query += f'{lat},{lon}|'
            i+=1
        query = query[:-1] # remove last bar
        if time.time()-t0 <t_wait :
            time.sleep(t_wait - (time.time()-t0))
        t0 = time.time()
        r = requests.get(query).json()
        if 'error' in r.keys() :
            print(r['error'])
        elevations[i0:i0+i] = pd.json_normalize(r, 'results')['elevation']
        i0+=i
        
    return elevations

# =============================================================================
# %% XML writing functions
# =============================================================================

def lines_water_polygon(segment, group_index = 1, water_type=1, altitude=0, name = "Water Polygon"):
    """
    segment : the np array with all vertices coordinates
    group_index : the number to increment
    water_type : 0=River; 1=Waste Water; 3=Pond; 4=Lake; 5=Ocean; -1 = Water # Warning : Ocean set the altitude at 0; Lake set constant altitude
    altitude : the elevation of the water area
    name : the name of the water which will be visible on SDK
    """
    lines = []
    # open polygon environment
    lines.append(f'\t<Polygon displayName="{name}" groupIndex="{group_index}" altitude="{altitude}">\n')
    # then attributes :
    lines.append('\t\t<Attribute name="UniqueGUID" guid="{359C73E8-06BE-4FB2-ABCB-EC942F7761D0}" type="GUID" value="{' + str(uuid.uuid4()) + '}"/>\n')
    lines.append('\t\t<Attribute name="IsWater" guid="{684AFC09-9B38-4431-8D76-E825F54A4DFF}" type="UINT8" value="1"/>\n')
    if water_type !=-1 : lines.append('\t\t<Attribute name="WaterType" guid="{3F8514F8-FAA8-4B94-AB7F-DC2078A4B888}" type="UINT32" value="' + str(water_type) + '"/>\n')
    if not (segment[-1] - segment[0]).any() : # the last vertex is the same as the first
        n = len(segment)-1
    else :
        n = len(segment)
    # all vertices
    for i in range(n) :
        lon, lat = segment[i]
        lines.append(f'\t\t<Vertex lat="{lat}" lon="{lon}"/>\n')
    # close the polygon environment
    lines.append('\t</Polygon>\n')
    return lines

def lines_exclude_water_polygon(segment, group_index = 1, water_type=-1, altitude=0, name = "Exclusion Polygon"):
    """
    segment : the np array with all vertices coordinates
    group_index : the number to increment
    water_type : 0=River; 1=Waste Water; 3=Pond; 4=Lake; 5=Ocean; -1 = Water
    altitude : the elevation of the water area
    name : the name of the water which will be visible on SDK
    """
    lines = []
    # open polygon environment
    lines.append(f'\t<Polygon displayName="{name}" groupIndex="{group_index}" altitude="{altitude}">\n')
    # then attributes :
    lines.append('\t\t<Attribute name="UniqueGUID" guid="{359C73E8-06BE-4FB2-ABCB-EC942F7761D0}" type="GUID" value="{' + str(uuid.uuid4()) + '}"/>\n')
    lines.append('\t\t<Attribute name="IsWater" guid="{684AFC09-9B38-4431-8D76-E825F54A4DFF}" type="UINT8" value="1"/>\n')
    lines.append('\t\t<Attribute name="IsWaterExclusion" guid="{972B7BAC-F620-4D6E-9724-E70BF8A450DD}" type="UINT8" value="1"/>\n')
    if water_type !=-1 : lines.append('\t\t<Attribute name="WaterType" guid="{3F8514F8-FAA8-4B94-AB7F-DC2078A4B888}" type="UINT32" value="' + str(water_type) + '"/>\n')
    if not (segment[-1] - segment[0]).any() : # the last vertex is the same as the first
        n = len(segment)-1
    else :
        n = len(segment)
    # all vertices
    for i in range(n) :
        lon, lat = segment[i]
        lines.append(f'\t\t<Vertex lat="{lat}" lon="{lon}"/>\n')
    # close the polygon environment
    lines.append('\t</Polygon>\n')
    # and write all of this
    return lines