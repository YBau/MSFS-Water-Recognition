from termcolor import colored
import numpy as np
import matplotlib.pyplot as plt

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
                colored('Product discriminator : ', 'cyan') + '{}/{}/{} at {}:{}:{}\n'.format(d2[6:8], d2[4:6], d2[0:4], d2[9:11], d2[11:13], d2[13:])
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