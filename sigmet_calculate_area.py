# -*- coding: utf-8 -*-
"""
Created on Tue Dec 11 11:30:09 2018

@author: opsuser
"""

path_to_shp_data = r'C:\Users\MSS11700835\Desktop\validts.shp'

driver = ogr.GetDriverByName("ESRI Shapefile")
dataSource = driver.Open(path_to_shp_data, 1)
layer = dataSource.GetLayer()
new_field = ogr.FieldDefn("Area", ogr.OFTReal)
new_field.SetWidth(32)
new_field.SetPrecision(2) #added line to set precision
layer.CreateField(new_field)

for feature in layer:
    geom = feature.GetGeometryRef()
    area = geom.GetArea() 
    print area
    feature.SetField("Area", area)
    layer.SetFeature(feature)

dataSource = None 