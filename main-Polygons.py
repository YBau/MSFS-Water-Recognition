import gdal
import matplotlib.pyplot as plt         # create visualizations
from termcolor import colored           # prints colored text
from zipfile import ZipFile             # zip file manipulation
from os.path import join                # data access in file manager  
from glob import iglob                  # data access in file manager
import pandas as pd                     # data analysis and manipulation
import numpy as np                      # scientific computing
import subprocess                       # external calls to system
import snappy                           # SNAP python interface
import jpy                              # Python-Java bridge

from PIL import Image, ImageOps
import time
from shapely.geometry import Point, Polygon
import uuid


import sys
from functions import read_zip_name, output_view, output_RGB

# Change module setting
pd.options.display.max_colwidth = 80    # Longer text in pd.df

def seconds_to_time(seconds, n_decimals=2) :
    h = int(seconds//3600)
    m = int(seconds//60 - h*60)
    s = seconds - m*60 - h*3600
    if h > 0 :
        return f'{h:0>2}:{m:0>2}:{round(s):0>2}'
    elif m > 0 : return f'{m:0>2}:{round(s):0>2}'
    else : return '{:.{}f}s'.format(s, n_decimals)
    

# =============================================================================
# %% Manual
# =============================================================================

# print(subprocess.Popen(['gpt','-h', 'Speckle-Filter'], stdout=subprocess.PIPE, universal_newlines=True).communicate()[0])

# =============================================================================
# %% Read NDWI products
# =============================================================================

t0 = time.time()

# Set target folder and extract metadata
product_path = "NDWI/"
input_S2_files = iglob(join(product_path, 'NDWI_set.tif'), recursive=True)

for i in input_S2_files:
    read_zip_name(i,display = True)
    # Read with snappy
    NDWI_read = snappy.ProductIO.readProduct(i)
    
print(colored(f'Products read : {seconds_to_time(time.time()-t0)}', 'green'))

# =============================================================================
# %% Create contours via plt
# =============================================================================

def meters_to_degrees(m) :
    r_earth = 6371e3
    # r_earth * arc_rad = m
    arc_rad = m/r_earth
    arc_deg = arc_rad * 180/np.pi
    return arc_deg

t0 = time.time()

NDWI_band = 'NDWI'
lvl = [-0.2] # the level where you separate land and water, empirical

# first import product in a numpy array
band = NDWI_read.getBand(NDWI_band)
w = band.getRasterWidth()
h = band.getRasterHeight()
NDWI_data = np.zeros(w * h, np.float32)
band.readPixels(0, 0, w, h, NDWI_data)
NDWI_data.shape = h, w

# This part take into account the inclination of the picture and the fact it's not exactly a square
# then create a plt figure, set coordintates and apply contour method
fig_contour, ax_contour = plt.subplots(1,1, figsize = (9,9))
x_mesh, y_mesh = np.meshgrid(np.arange(w)/w, np.arange(h)/h)

# you can't use linear interp with just corners : pictures are taken with straight line in x, but curved lines in angle
boundary = snappy.ProductUtils.createGeoBoundary(NDWI_read, 1) # coordinates given at pixels center

x_left = ([coo.lon for coo in list(boundary)[2*w+h-3:]] + [boundary[0].lon]) # longitude
x_left.reverse()
x_right =  [coo.lon for coo in list(boundary)[w-1:w+h-1]]
y_top = [coo.lat for coo in list(boundary)[:w]] # latitudes
y_bottom = [coo.lat for coo in list(boundary)[w+h-2:2*w+h-2]]
y_bottom.reverse()

for i in range(len(x_mesh)) : # for each line i
    x_mesh[i] = x_left[i] + (x_right[i] - x_left[i])*np.arange(w)/(w-1)
for j in range(len(x_mesh[0])) : # for each column j
    y_mesh[:,j] = y_top[j] + (y_bottom[j] - y_top[j])*np.arange(h)/(h-1)
        
cset = ax_contour.contour(x_mesh, y_mesh, NDWI_data, levels = lvl)
# in geography positives are toward the north
plt.tight_layout()

print(colored(f'Contours created : {seconds_to_time(time.time()-t0)}', 'green'))

# =============================================================================
# %% Water polygons or exclude water polygons ?
# =============================================================================

t0 = time.time()

n_poly = len(cset.allsegs[0])

point_list = []
polygon_list = []
for seg in cset.allsegs[0] :
    point_list.append(Point(seg[len(seg)//2])) # take a point in the middle of the segment avoids to take one on the external side
    polygon_list.append(Polygon(seg))

islands_of_i = {i:[] for i in range(n_poly)}
exclude_water = np.zeros((n_poly,))
for i_point in range(n_poly) :
    point = point_list[i_point]
    n=0 # number of inside : a polygon inside 2 others is a pond inside an island in a lake
    for i_polygon in range(n_poly) :
        if i_polygon == i_point : continue
        poly = polygon_list[i_polygon]
        if poly.contains(point) :
            n +=1
            islands_of_i[i_polygon].append(i_point)
    if n%2 == 1 :
        exclude_water[i_point] = 1
    
print(colored(f'Islands found : {seconds_to_time(time.time()-t0)}', 'green'))

# =============================================================================
# %% Get altitudes points
# =============================================================================

import requests

t0 = time.time()

elevation_points = np.zeros((n_poly, 2)) # latitude, longitude of points where to take elevation.
altitude_list = np.zeros((n_poly,))
random_set = np.random.random((1000,2)) # it's faster to create a large set of random numbers than calling each time new ones

for i_seg, seg in enumerate(cset.allsegs[0]) :
    if exclude_water[i_seg] :
        # print(f'\tnot water')
        # if in the case you exclude_water, altitude doesn't matter
        elevation_points[i_seg] = [seg[0,1], seg[0,0]]
    else :
        # you can't just use average coordinates because you need to check that you are in water
        lon_max, lat_max = seg.max(axis = 0)
        lon_min, lat_min = seg.min(axis = 0)
        i_rd = 0
        while True :
            # print(f'\twhile loop : {i_rd} ')
            # find a point in the polygon
            rd1, rd2 = random_set[i_rd]
            i_rd +=1
            if i_rd == 1000 :
                print('\trd reset')
                i_rd = 0
                random_set = np.random.random((1000,2))
            lon = lon_min + (lon_max - lon_min)*rd1
            lat = lat_min + (lat_max - lat_min)*rd2
            pt = Point(lon, lat)
            if not polygon_list[i_seg].contains(pt) : continue
            # verify that this point is not on an island
            all_outside_islands = True
            for i_poly in islands_of_i[i_seg] :
                if polygon_list[i_poly].contains(pt): 
                    all_outside_islands=False
                    break
            if all_outside_islands : break # exit the while loop with valid lon and lat
        elevation_points[i_seg] = [lat, lon]
      
print(colored(f'Altitudes points got : {seconds_to_time(time.time()-t0)}', 'green'))

# =============================================================================
# %% Get altitudes
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

t0 = time.time()

altitude_list = get_multiple_elevation_opentopodata(elevation_points)

print(colored(f'Altitudes got : {seconds_to_time(time.time()-t0)}', 'green'))

# =============================================================================
# %% Write output 
# =============================================================================

# water_type=1 because if you make a different water, on junction with default water filled areas, different water types may cause exclusions

t0 = time.time()

def lines_water_polygon(segment, group_index = 1, water_type=1, altitude=200, name = "Water Polygon"):
    """
    segment : the np array with all vertices coordinates
    group_index : the number to increment
    water_type : 0=River; 1=Water; 4=Lake
    altitude : the elevation of the water area
    name : the name of the water which will be visible on SDK
    """
    lines = []
    # open polygon environment
    lines.append(f'\t<Polygon displayName="{name}" groupIndex="{group_index}" altitude="{altitude}">\n')
    # then attributes :
    lines.append('\t\t<Attribute name="UniqueGUID" guid="{359C73E8-06BE-4FB2-ABCB-EC942F7761D0}" type="GUID" value="{' + str(uuid.uuid4()) + '}"/>\n')
    lines.append('\t\t<Attribute name="IsWater" guid="{684AFC09-9B38-4431-8D76-E825F54A4DFF}" type="UINT8" value="1"/>\n')
    lines.append('\t\t<Attribute name="WaterType" guid="{3F8514F8-FAA8-4B94-AB7F-DC2078A4B888}" type="UINT32" value="' + str(water_type) + '"/>\n')
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

def lines_exclude_water_polygon(segment, group_index = 1, water_type=1, altitude=200, name = "Exclusion Polygon"):
    """
    segment : the np array with all vertices coordinates
    group_index : the number to increment
    water_type : 0=River; 1=Water; 4=Lake
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
    lines.append('\t\t<Attribute name="WaterType" guid="{3F8514F8-FAA8-4B94-AB7F-DC2078A4B888}" type="UINT32" value="' + str(water_type) + '"/>\n')
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
    
output_folder = 'Output'
output_file = 'T14UPE.xml' # tile number

f = open(f"{output_folder}\\{output_file}", 'w')
f.write('<?xml version="1.0"?>\n<FSData version="9.0">\n')
lines = []
for i in range(n_poly):
    if exclude_water[i] :
        l_poly = lines_exclude_water_polygon(cset.allsegs[0][i], group_index = i+1)
    else :
        l_poly = lines_water_polygon(cset.allsegs[0][i], group_index = i+1, altitude = altitude_list[i])
    lines += l_poly
f.writelines(lines)
f.write('</FSData>')
f.close()

print(colored(f'File wrote : {seconds_to_time(time.time()-t0)}', 'green'))

