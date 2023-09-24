import gdal
import matplotlib.pyplot as plt         # create visualizations
from matplotlib import cm
from matplotlib.colors import ListedColormap
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
from functions import read_zip_name, seconds_to_time, get_multiple_elevation_opentopodata
from functions import lines_exclude_water_polygon, lines_water_polygon

# Change module setting
pd.options.display.max_colwidth = 80    # Longer text in pd.df    

# =============================================================================
# %% Manual
# =============================================================================

# print(subprocess.Popen(['gpt','-h', 'Speckle-Filter'], stdout=subprocess.PIPE, universal_newlines=True).communicate()[0])

# =============================================================================
# %% Read NDWI products
# =============================================================================

t0 = time.time()

# Set target folder and extract metadata
selected_tile = "T14UPC"

product_path = "NDWI/"
input_S2_files = iglob(join(product_path, '*.dim'), recursive=True)

found = False
for i in input_S2_files:
    tile = i[-10:].strip('.dim')
    # Read with snappy
    if tile == selected_tile :
        NDWI_read = snappy.ProductIO.readProduct(i)
        found=True
        break

assert found, f"No product match tile {selected_tile}"

print(colored(f'Products read : {seconds_to_time(time.time()-t0)}', 'green'))

# =============================================================================
# %% Create contours via plt
# =============================================================================

## create new color map
Blues = cm.get_cmap('Blues', 256)
Greens = cm.get_cmap('Greens', 256)
newcolors = Blues(np.linspace(0, 1, 256))
new_greens = Greens(np.linspace(0, 1, 256))


t0 = time.time()

NDWI_band = 'NDWI_combined'
lvl = [0] # the level where you separate land and water, should be 0

# first import product in a numpy array
band = NDWI_read.getBand(NDWI_band)
w = band.getRasterWidth()
h = band.getRasterHeight()
NDWI_data = np.zeros(w * h, np.float32)
band.readPixels(0, 0, w, h, NDWI_data)
NDWI_data.shape = h, w

# This part take into account the inclination of the picture and the fact it's not exactly a square
# then create a plt figure, set coordintates and apply contour method
fig, ax = plt.subplots(1,2, figsize = (18,9), constrained_layout=True)
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

lim = int(256 + 256*(lvl[0]-1)/2)
newcolors[:lim, :] = np.flip(new_greens[256-lim:256, :], axis = 0)
newcmp = ListedColormap(newcolors)

cset = ax[0].contour(x_mesh, y_mesh, NDWI_data, levels = lvl)
# in geography positives are toward the north
ax[0].set_title(f"{selected_tile} contours, threshold = {lvl[0]}")
im = ax[1].imshow(NDWI_data, cmap = newcmp)
fig.colorbar(ax = ax[1], mappable = im, shrink=0.6)
ax[1].set_title(f"{selected_tile} NDWI")
# plt.tight_layout()
plt.show()

print(colored(f'Contours created : {seconds_to_time(time.time()-t0)}', 'green'))

# =============================================================================
# %% Water polygons or exclude water polygons ?
# =============================================================================

t0 = time.time()

Segments = cset.allsegs[0]
i=0
while i < len(Segments) :
    if len(Segments[i]) < 3 :
        Segments.pop(i)
    else : i+= 1
n_poly = len(Segments)

point_list = []
polygon_list = []
for seg in Segments :
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

t0 = time.time()

elevation_points = np.zeros((n_poly, 2)) # latitude, longitude of points where to take elevation.
altitude_list = np.zeros((n_poly,))
random_set = np.random.random((1000,2)) # it's faster to create a large set of random numbers than calling each time new ones

for i_seg, seg in enumerate(Segments) :
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

t0 = time.time()

altitude_list = get_multiple_elevation_opentopodata(elevation_points)

print(colored(f'Altitudes got : {seconds_to_time(time.time()-t0)}', 'green'))

# =============================================================================
# %% Write output 
# =============================================================================

# water_type=1 because if you make a different water, on junction with default water filled areas, different water types may cause exclusions

t0 = time.time()
    
output_folder = 'Output'
output_file = f'{selected_tile}.xml' # tile number

f = open(f"{output_folder}\\{output_file}", 'w')
f.write('<?xml version="1.0"?>\n<FSData version="9.0">\n')
lines = []
for i in range(n_poly):
    if len(Segments[i]) > 5 : # more than 5 points, to avoid parasites
        if exclude_water[i] :
            l_poly = lines_exclude_water_polygon(Segments[i], group_index = i+1)
        else :
            l_poly = lines_water_polygon(Segments[i], group_index = i+1, altitude = altitude_list[i])
        lines += l_poly
f.writelines(lines)
f.write('</FSData>')
f.close()

print(colored(f'File wrote : {seconds_to_time(time.time()-t0)}', 'green'))

