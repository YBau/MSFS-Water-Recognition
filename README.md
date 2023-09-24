# MSFS Water Recognition

### Goal of the project
In Microsoft flight simulator 2020 (MSFS), water is placed on the map if an area is recognize as a water area in an online map (I think of Bing maps or OpenStreetMap).  
However, there are zones in the world where water areas are poorly treated such as the northern Canada or central Africa.  
This results in the game MSFS as dark areas (since these areas are dark in sattelite imagery), but with no water and even trees in it. You can't land with a seaplane in these areas and they do not reflect light as watered areas.  
This problem can be solved by editing the world with MSFS tool : SDK. You can manually add water.  
I don't like to treat hundreds of squared kilometers manually, moreover these zones are rarely flought (I imagine that's why there is no modification of these zones in open maps).  
Here comes this project which automatically recognizes water on satellite images and creates the corresponding SDK scenery file to edit areas.

### Requirements
(This is my setup)

* An anaconda installation
* Python 3.6.* with standard anaconda packages
* [SNAP](https://step.esa.int/main/download/snap-download/) which is the ESA tool for satellite images processing
* the python package snappy, [here is a short video which explains its installation](https://www.youtube.com/watch?v=14YM1kKdgA8)
* the python package gdal in order to read sentinel-2 products (I followed [this tutorial](https://pythongisandstuff.wordpress.com/2016/04/13/installing-gdal-ogr-for-python-on-windows/) for installation)

### How to use the project

* Download a sentinel-2 product (Level-2A or 2B) on [ESA copernicus map](https://scihub.copernicus.eu/dhus/#/home), you need to register, it's free. If the satellite image is not cloudless, take other one covering the same tile, cloudless where there are clouds on the first one. The tile do not need to be totally covered by the photography. Put the .zip files in the folder _Original_.
* Open your Python IDE in the snappy environment. 
* Edit main-NDWI with your configuration (change folder locations, file names).
* Run main-NDWI, it will create a .dim file in the _NDWI_ folder. The computation time is correlated with the number of images for the selected tile. It takes less than 5 minutes on my computer, but it takes a lot of memory.
* Edit main-Polygons with your configuration.
* Run it, it will create a .xml file in the _Output_ folder. The computation time is correlated with the number of lakes and islands. It takes less than 10 minutes on my computer.
* Then create a MSFS SDK project, close it and put the .xml file in the PackageSources folder. Modify PackageDefinition folder in consequence.
* Reload the project you just closed, open the scenery. If everything is fine, you should see the edition red lines in the area you choose for modification.
* Make some editions if you want, save, then build the package.

### Curent problems

* Resolution of sattelite images I use is 20 meters, so contours of the water areas (lakes and rivers) cannot be placed exactly where they should be. In its current configuration, water areas are created a bit smaller that what they should. Moreover, there might be not perfectly centered, the tolerable displacement for this project is around 10 meters because a pixel of the satellite images is 10 by 10 meters.
* I saw a maximal displacement of 30 meters, I don't know yet the reason why.
* Rivers are not always deep enough to be easily recognized as water. In the current version, the deepest part is set as water but not all the river. So in the "transition zone" it looks like small lakes placed on the river.
* Some small areas migh be covered by water while there are just trees in these areas (pretty rare)
* Some artificial areas (roofs, airport runways) might be covered by water. I need to change the method from NDWI to another to avoid this.
* Areas are treated tile by tile (100km x 100km). The next step for development is a way to merge .xml files and then choose and download automatically satellite images in the area you choose.

### How does it works

1. _main-NDWI_ reads all the .zip file, and computes the normalized difference water index (NDWI) which is the normalized difference between the green and near infrared frequency bands.  
The interseting fact about resulting NDWI is that areas with negative values are land and areas with positive values are water.
This water index is computed for each file of the same tile.
2. A cloud mask is created with the already computed "cloud index" in the data of the zip files. It includes the fact that images might not cover the entire tile.
3. Files are combined using an average and the cloud mask.
4. The NDWI band created is stored as a .dim file.
5. _main-Polygons_ loads the NDWI band, it detects from the NDWI band (which is just a black and white picture in an array) all the isolines equals to 0 (it's fast and precise with the contour() method of plt). The result is a list of polygons.
6. Then polygons are defined as water polygons or exclude water polygons, indeed, a polygon can delimit a lake, an island, an lake in an island...
7. Then elevation (required parameter for SDK) is downloaded for each polygon with opentopodata (this part is the longest).
8. Finally, the .xml file is written.

### You might be interested in 

* [Training for SNAP (free)](https://eo4society.esa.int/resources/copernicus-rus-training-materials/)

If you want to help me to develop the project, you can contact me by mail or private message (in english or french).