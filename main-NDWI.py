import gdal
import matplotlib.colors as colors      # create visualizations
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

import sys
from functions import read_zip_name, output_view, output_RGB, land_water_cmap

# Change module setting
pd.options.display.max_colwidth = 80    # Longer text in pd.df
 
# =============================================================================
# %% Manual
# =============================================================================

# print(subprocess.Popen(['gpt','-h', 'Speckle-Filter'], stdout=subprocess.PIPE, universal_newlines=True).communicate()[0])

# =============================================================================
# %% Load products
# =============================================================================

# Set target folder and extract metadata
product_path = "Original/"
input_S2_files = sorted(list(iglob(join(product_path, 'S2*_T*.zip'), recursive=True)))

selected_tile = "T14UPF"

Read_Products = [] # all of the products read cover the same tile
for i in input_S2_files:
    tile = read_zip_name(i)[5]
    if tile == selected_tile :
        read_zip_name(i, display = True)
        Read_Products.append(snappy.ProductIO.readProduct(i))

n_prod = len(Read_Products)

print(colored('Products read :', 'green'), n_prod, colored(f'product{"s" if n_prod > 1 else ""} selected, tile', "green"), selected_tile)

assert n_prod > 0, f"No product match tile {selected_tile}"
    

# =============================================================================
# %% Resample Product
# =============================================================================
# In order that all bands are of the same size

parameters = snappy.HashMap()
parameters.put('referenceBand', 'B2')

Resampled_Products = []
for product in Read_Products :
    Resampled_Products.append(snappy.GPF.createProduct('Resample', parameters, product))
    
print(colored('Products Resampled', 'green'))

# =============================================================================
# %% NDWI (Normalized difference water index)
# =============================================================================

BandDescriptor = jpy.get_type('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor')
targetBand1 = BandDescriptor()
targetBand1.name = 'NDWI'
targetBand1.type = 'float32'
targetBand1.expression = 'if (B3<=0 and B8<=0) then 1 else (max(0,B3) - max(0,B8))/(max(0,B3) + max(0,B8))' # there can't be negative values in original bands

# mNDWI is said to be better than NDWI, however bands imply in its calculation are less precise
# targetBand2 = BandDescriptor()
# targetBand2.name = 'mNDWI'
# targetBand2.type = 'float32'
# targetBand2.expression = 'if (B3<=0 and B11<=0) then 1 else (max(0,B3) - max(0,B11))/(max(0,B3) + max(0,B11))' # there can't be negative values in original bands

targetBands = jpy.array('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor', 1)
targetBands[0] = targetBand1
# targetBands[1] = targetBand2

parameters = snappy.HashMap()
parameters.put('targetBands', targetBands)

NDWI_Products = []
for i, product in enumerate(Resampled_Products) :
    print(colored(f'\tCreating NDWI band for product {i}...', 'green'))
    NDWI_Products.append(snappy.GPF.createProduct('BandMaths', parameters, product))

print(colored('NDWI bands created', 'green'))

# output_view(new_bands, ['NDWI','SWIR_based_NDWI'])

# =============================================================================
# %% Clouds handling
# =============================================================================

NDWI_Arrays = []
Cloud_Data = []
Cloud_Masks = []
Known_Masks = []
max_tolerable_cloud_proba_percent = 20

for i in range(n_prod) :
    print(colored(f'\tExtracting data from product {i}...', 'green'))
    band_ndwi = NDWI_Products[i].getBand("NDWI")
    band_clouds = Resampled_Products[i].getBand("quality_cloud_confidence")
    band_classification = Resampled_Products[i].getBand("quality_scene_classification")
    w = band_ndwi.getRasterWidth()
    h = band_ndwi.getRasterHeight()
    NDWI_data = np.zeros(w * h, np.float32)
    Cloud_data = np.zeros(w * h, np.float32)
    Classification_data = np.zeros(w * h, np.float32)
    band_ndwi.readPixels(0, 0, w, h, NDWI_data)
    band_clouds.readPixels(0, 0, w, h, Cloud_data)
    band_classification.readPixels(0, 0, w, h, Classification_data)
    NDWI_data.shape = h, w
    Cloud_data.shape = h, w
    Classification_data.shape = h, w
    NDWI_Arrays.append(NDWI_data)
    Cloud_Data.append(Cloud_data)
    Cloud_mask = (Cloud_data > max_tolerable_cloud_proba_percent)*1 # =1 where there are too much clouds, 0 otherwise
    Cloud_Masks.append(Cloud_mask)
    Known_mask = (Classification_data!=0)*1 # =1 when there is data; =0 when there isn't
    Known_Masks.append(Known_mask)

Classified0_area = Known_Masks[0]
for i in range(1, n_prod) :
    Classified0_area = np.logical_or(Classified0_area, Known_Masks[i])
unknown_area = np.sum(1-Classified0_area)
if unknown_area > 0 :
    print(colored('Warning :', 'red'), f'{unknown_area} pixels still uncovered')

print(colored('NDWI, cloud and classification arrays extracted', 'green'))

Hidden_zone = Cloud_Masks[0] + np.logical_not(Known_Masks[0])*1 # 1 where the pixel is always covered by clouds or not covered at all by photography
for i in range(1, n_prod) :
    Hidden_zone *= (Cloud_Masks[i] + np.logical_not(Known_Masks[i]))

print(colored('Remaining clouds and unknown pixels :', 'green'), f"{np.sum(Hidden_zone)}/{w*h}")

NDWI_sum = NDWI_Arrays[0]*0
Cloud_sum = NDWI_Arrays[0]*0
for i in range(n_prod) :
    Weight_matrix = (1-np.minimum(Cloud_Data[i]/max_tolerable_cloud_proba_percent, 1))
    NDWI_sum += NDWI_Arrays[i] * Known_Masks[i] * Weight_matrix
    Cloud_sum += Known_Masks[i] * Weight_matrix
NDWI_combined = np.divide(NDWI_sum, Cloud_sum, out = np.zeros(Cloud_sum.shape, dtype=float)+2, where=Cloud_sum!=0)

print(colored('NDWI arrays combined', 'green'))

# now there are 2 where there are only clouds, so we will use the pixels arounds to guess the value of NDWI (2 is an impossible value of NDWI)
if np.sum(Hidden_zone)/(w*h) < 0.01 :
    Coordinates_remaining_clouds = np.transpose(np.where(Cloud_sum==0))
    NDWI_not_set=list(range(len(Coordinates_remaining_clouds)))
    
    x_neighbours = [0,+1,0,-1]
    y_neighbours = [+1,0,-1,0]
    min_neighbours = 2
    i1 = i2 = 0
    len0=len(NDWI_not_set)
    while len(NDWI_not_set)>0 :
        if i1 == len(NDWI_not_set) : 
            i1=0 # reset loop
            if len0 == len1 : # we check all pixels not set but we change none : we make conditions more flexible
                min_neighbours=1
            len0 = len1
            
        i2 = NDWI_not_set[i1]
        x,y = Coordinates_remaining_clouds[i2]
        num = div = 0
        for j in range(4):
            xn, yn = x+x_neighbours[j], y+y_neighbours[j]
            if 0 <= xn < w and 0 <= yn < h and NDWI_combined[xn, yn] != 2 :
                num += NDWI_combined[xn, yn]
                div += 1
        if div >= min_neighbours : 
            NDWI_combined[x,y] = num/div
            NDWI_not_set.pop(i1)
        else : 
            i1+=1
        len1 = len(NDWI_not_set)
        
    print(colored('Combined array completed, remaining hidden pixels :', 'green'), np.sum(NDWI_combined==2))

# =============================================================================
# %% Plot bands
# =============================================================================

# band = Read_Products[3].getBand("quality_scene_classification")
# W = band.getRasterWidth()
# H = band.getRasterHeight()
# data = np.zeros(W * H, np.float32)
# band.readPixels(0, 0, W, H, data)
# data.shape = H, W

# fig, ax = plt.subplots(1,2, figsize = (18,9))
# ax[0].imshow(data == 6)
# ax[1].imshow(NDWI_combined)
# plt.show()

if np.sum(Hidden_zone) > 0 :
    fig, ax = plt.subplots(1,2, figsize = (18,9))
    ax[0].imshow(Cloud_sum==0)
    im = ax[1].imshow(NDWI_combined, cmap = land_water_cmap(0), vmin=-1)
    fig.colorbar(ax = ax[1], mappable = im, shrink=0.6)
    ax[0].set_title(f"{selected_tile} Cloud_sum==0")
    ax[1].set_title(f"{selected_tile} NDWI")
    plt.show()

assert np.sum(Hidden_zone)/(w*h) < 0.01, "too much unknown areas"

# =============================================================================
# %% Write output 
# =============================================================================

# we write the array as a product since we need to keep coordinates

NDWI_line = np.zeros(w * h, np.float32)
for i in range(h):
    NDWI_line[i*w: (i+1)*w] = NDWI_combined[i]

outpath_name = 'NDWI/{}.dim'.format(selected_tile)

targetP = snappy.Product('new_product', 'new_type', w, h)
snappy.ProductUtils.copyMetadata(NDWI_Products[0], targetP)
snappy.ProductUtils.copyTiePointGrids(NDWI_Products[0], targetP)
snappy.ProductUtils.copyGeoCoding(NDWI_Products[0], targetP)
targetP.setProductWriter(snappy.ProductIO.getProductWriter('BEAM-DIMAP'))
targetP.setProductReader(snappy.ProductIO.getProductReader('BEAM-DIMAP'))
snappy.ProductIO.writeProduct(targetP, outpath_name, 'BEAM-DIMAP')

targetB = targetP.addBand('NDWI_combined', snappy.ProductData.TYPE_FLOAT32)
targetB.setUnit('1')
targetP.writeHeader(outpath_name)
targetB.writePixels(0,0,w,h,NDWI_line)

targetP.closeIO()

print(colored('Product succesfully saved in:', 'green'), outpath_name)