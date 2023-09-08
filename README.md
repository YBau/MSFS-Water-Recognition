# MSFS Water Recognition
####Goal of the project
In Microsoft flight simulator 2020 (MSFS), water is placed on the map if an area is recognize as water area in an online map (I think of Bing maps or OpenStreetMap).  
However, there areas in the world where zones are poorly treated such as the northern Canada or Africa.  
This results in the game MSFS as dark areas (since these areas are dark in sattelite imagery, but with no water or even trees in it. You can't land with a seaplane in these areas and they do not reflect light as watered areas.  
This problem can be solved by editing the world with MSFS tool : SDK. You can manually add water.  
I don't like to treat hundreds of squared kilometers manually, moreover these zones are rarely flought (I imagine that's why there is no modification of these zones in open maps).  
Here comes this project which automatically recognizes water on satellite images and creates the corresponding SDK scenery file to edit areas.

####Requirements
(This is my setup)

* An anaconda installation
* Python 3.6.* with standard anaconda packages
* [SNAP](https://step.esa.int/main/download/snap-download/) which is the ESA tool for satellite images processing
* the python package snappy [Here is a short video which explains installation](https://www.youtube.com/watch?v=14YM1kKdgA8)
* the python package gdal in order to read sentinel-2 products (I followed [this tutorial](https://pythongisandstuff.wordpress.com/2016/04/13/installing-gdal-ogr-for-python-on-windows/) for installation)

####How to use the project

* Download a sentinel-2 product (Level-2A or 2B) on [ESA copernicus map](https://scihub.copernicus.eu/dhus/#/home), you need to register, it's free. Verify that the image you take is cloudless, especially over the water areas. Put the .zip file in the folder _Original_.
* Open your Python IDE on the snappy environment. 
* Edit main-NDWI with your configuration.
* Run main-NDWI, it will create a .tif file in the _NDWI_ folder. It takes some minutes, less than 5 on my computer.
* Edit main-Polygons with your configuration.
* Run it, it will create a .xml file in the _Output_ folder. It takes less than 10 minutes on my computer.
* Then create a MSFS SDK project, close it and put the .xml file in the PackageSources folder.
* Reload the project you just close, open the scenery. If everything is fine, you should see the edition red lines in the area you are checked.
* Make some editions if you want then build the package.

####Curent problems

* Resolution of sattelite images I use is 20 meters, so contours of the water areas (lakes and rivers) cannot be placed exactly where they should be. In its current configuration, water areas are created a bit smaller that what they should. Moreover, there might be not perfectly centered, the tolerable displacement for this project is around 10 meters because a pixel of the satellite images is 10 by 10 meters.
* I saw a maximal displacement of 30 meters, I don't know yet the reason why.
* Rivers are not always deep enough to be easily recognize as water. In the current version, the deepest part is set as water but not all the river. So in the "transition zone" it looks like small lakes placed on the river.
* Some small areas migh be covered by water while there are just trees in these areas (pretty rare)

####How does it works

1. _main-NDWI_ load read the zip, and computes the normalized difference water index (NDWI) which is the normalized difference between the green and near infrared frequency band.  
The interseting fact about resulting NDWI is that areas with negative values are land and areas with positive values are water.
2. The NDWI band create is stored as a .tif file.
3. _main-Polygons_ loads the NDWI band, it detects from the NDWI band (which is just a black and white picture in an array) all the isolines equals to 0 (it's fast and precise with the contour() method of plt). The result is a list of polygons.
4. Then polygons are attributed as water polygons ore exclude water polygons, indeed, inside a polygon there are lakes (as we want) but also islands, lakes in islands...
5. Then elevation (required parameter for SDK) is found for each polygon with opentopodata (this part is the longest).
6. Finally, the .xml file is written.

####You might be interested in 

* [Training for SNAP (free)](https://eo4society.esa.int/resources/copernicus-rus-training-materials/)

If you want to help me to develop the project, you can contact me by mail or private message (in english or french).