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
from functions import read_zip_name, output_view, output_RGB

# Change module setting
pd.options.display.max_colwidth = 80    # Longer text in pd.df
 
# =============================================================================
# %% Manual
# =============================================================================

# print(subprocess.Popen(['gpt','-h', 'Speckle-Filter'], stdout=subprocess.PIPE, universal_newlines=True).communicate()[0])

# =============================================================================
# %% Plot preview
# =============================================================================

# We start the analysis by setting the folder where the files we want to processed are located.
# Next, one of the files wil be used as input for this exercise and will be imported with `snappy`.
# In addition, a quicklook availalbe in the original data folder is displayed.

# Set target folder and extract metadata
product_path = "Original/"
input_S2_files = sorted(list(iglob(join(product_path, '**', '*S2*.zip'), recursive=True)))

for i in input_S2_files:
    read_zip_name(i,display = True)
    # Read with snappy
    s2_read = snappy.ProductIO.readProduct(i)

# output_RGB(s2_read, ['B2', 'B3', 'B4'])
# output_view(s2_read, list(s2_read.getBandNames())[:4])

print(colored('Products read', 'green'))


# =============================================================================
# %% Resample Product
# =============================================================================
# In order that all bands are of the same size

parameters = snappy.HashMap()
parameters.put('referenceBand', 'B2')
resampled = snappy.GPF.createProduct('Resample', parameters, s2_read)
print(colored('Resampling done', 'green'))


# =============================================================================
# %% NDWI (Normalized difference water index)
# =============================================================================

BandDescriptor = jpy.get_type('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor')
targetBand1 = BandDescriptor()
targetBand1.name = 'NDWI'
targetBand1.type = 'float32'
targetBand1.expression = 'if (B3<=0 and B8<=0) then 1 else (max(0,B3) - max(0,B8))/(max(0,B3) + max(0,B8))' # there can't be negative values in original bands
targetBands = jpy.array('org.esa.snap.core.gpf.common.BandMathsOp$BandDescriptor', 2)
targetBands[0] = targetBand1

targetBand2 = BandDescriptor()
targetBand2.name = 'SWIR_based_NDWI'
targetBand2.type = 'float32'
targetBand2.expression = 'if (B3<=0 and B11<=0) then 1 else (max(0,B3) - max(0,B11))/(max(0,B3) + max(0,B11))' # there can't be negative values in original bands
targetBands[1] = targetBand2

parameters = snappy.HashMap()
parameters.put('targetBands', targetBands)
new_bands = snappy.GPF.createProduct('BandMaths', parameters, resampled)

print(colored('NDWI band created', 'green'))

output_view(new_bands, ['NDWI','SWIR_based_NDWI'])

# =============================================================================
# %% Write output 
# =============================================================================

# Once we have completed all preprocessing steps we can write our SAR product to file. 
# In this occasion we will chooose the GeoTIFF format.

# Set output path and name
outpath_name = 'NDWI/NDWI_set.tif'

# Write Operator - snappy
# snappy.ProductIO.writeProduct(new_bands, outpath_name, 'GeoTIFF')
# print(colored('Product succesfully saved in:', 'green'), outpath_name)