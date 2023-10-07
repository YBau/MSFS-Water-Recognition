import os
from termcolor import colored           # prints colored text
import time
from functions import seconds_to_time

listdir = os.listdir('NDWI')
list_tiles = [x.strip('.dim') for x in listdir if x.split('.')[-1] == 'dim']
for tile in list_tiles :
    t0 = time.time()
    print(colored('Ongoing tile :', 'cyan'), tile )
    os.system(f'python main-Polygons.py {tile}')
    print(colored('Tile processed :', 'cyan'), seconds_to_time(time.time()-t0))