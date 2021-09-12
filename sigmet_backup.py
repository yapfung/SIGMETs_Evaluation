# -*- coding: utf-8 -*-
"""
Created on Mon Oct  1 12:35:53 2018

@author: opsuser
"""

# -*- coding: utf-8 -*-
"""
Created on Thu Aug  2 14:23:23 2018

@author: opsuser
"""

from osgeo import gdal, ogr, osr
from collections import OrderedDict
import datetime as dt
import os
import math
import logging

class sigmet():
    
    def __init__(self, folderpath, yyyymm, fir_shapefile):
        '''
        Initiates an instance to decode SIGMET and output shapefiles
        '''
        self.folderpath = folderpath
        self.yyyymm = yyyymm
        self.sigmet_number = None
        self.issue_datetime = None
        self.validity_start = None
        self.validity_end = None
        self.sigmet_type = None
        self.sigmet_position = {}
        self.shape_type = None
        self.corners = {'NE': [15, 120], 'SE': [-10, 120], 'SW': [-10, 90], 'NW': [15, 90]}
        self.fir_shapefile = fir_shapefile
        self.sigmet_shapefile = None
    
    def sort_clockwise(self, lat_lon_pairs):
        '''
        sorts lat lon pairs into clockwise order
        '''
        def centeroidpython(data):
            x, y = zip(*data)
            l = len(x)
            return sum(x) / l, sum(y) / l
        
        xy_pairs = lat_lon_pairs        
        centroid_x, centroid_y = centeroidpython(xy_pairs)
        xy_sorted = sorted(xy_pairs, key = lambda x: math.atan2((x[1]-centroid_y),(x[0]-centroid_x)))
        return xy_sorted

    def convert(self, deg_min):
        '''
        converts latitude and longitude from degrees and minutes into positive/negative decimals
        '''
        if deg_min[0] == 'S' or deg_min[0] == 'W':
            if len(deg_min) > 4:
                return round(-1*(int(deg_min[1:-2]) + float(deg_min[-2:])/60), 2)
            else:
                return -1*int(deg_min[1:])
        elif deg_min[0] == 'N' or deg_min[0] == 'E':
            if len(deg_min) > 4:
                return round(int(deg_min[1:-2]) + float(deg_min[-2:])/60, 2)
            else:
                return int(deg_min[1:])

    def trim_line(self, line):
        '''
        trim start and end of line to remove '=', space, or line break character
        '''
        while line[-1] == '\n' or line[-1] == '\r' or line[-1] == ' ' or line[-1] == '=':
            line = line[:-1]
        while line[0] == ' ':
            line = line[1:]                
        return line
    
    def extract_position_line(self, line):
        '''
        Identify and extract relevant part of line that bears the information of SIGMET position
        '''
        start_index = end_index = None
        for i, element in enumerate(line):
            if element == 'OBS' or element == 'FCST':
                start_index = i + 1
            elif 'TOP' in element or 'ABV' in element or 'FL' in element:
                end_index = i
                break
            elif 'STNR' in element or 'MOV' in element or 'WKN' in element:
                end_index = i
                break
            elif 'INTSF' in element or 'NC' in element:
                end_index = i
                break
        if not end_index and line[-1] == '=':
            line = line[:-1]
            end_index = len(line)
        elif not end_index and line[-1] != '=':
            end_index = len(line)
        return line[start_index:end_index]
    
    def extract_sigmet_position(self, position_line):
        '''
        Stores the lat lon information of sigmet areas in attribute "self.sigmet_position" and classifies the shape type
        '''
        if 'WI' in position_line:
            self.sigmet_position['WI'] = []
            for i in range(len(position_line)):
                if 'N' in position_line[i] or 'S' in position_line[i] and len(position_line[1]) > 2 :
                    self.sigmet_position['WI'].append([self.convert(position_line[i]), self.convert(position_line[i+1])])
        else:
            for i in range(len(position_line)):
                if position_line[i] == 'N' or position_line[i] == 'S' or position_line[i] == 'E' or position_line[i] == 'W' or position_line[i] == 'NE' or position_line[i] == 'NW' or position_line[i] == 'SE' or position_line[i] == 'SW':
                    if position_line[i+2] == 'LINE':
                        self.sigmet_position[position_line[i]] = [[self.convert(position_line[i+3]), self.convert(position_line[i+4])],  [self.convert(position_line[i+6]), self.convert(position_line[i+7])]]
                    else:
                        self.sigmet_position[position_line[i]] = self.convert(position_line[i+2])

    def get_shape_type(self):
        '''
        Identifies the type of SIGMET shape's construction
        '''            
        if 'WI'in self.sigmet_position:
            self.shape_type = 'polygon'
        elif len(self.sigmet_position) > 1:
            self.shape_type = 'two lines'
        elif type(self.sigmet_position.values()[0]) == list:
            self.shape_type = 'oblique line'
        elif type(self.sigmet_position.values()[0]) == float:
            self.shape_type = 'horizontal/vertical line'
    
    def intersect_fir(self, interim_poly):
        '''
        Intersect interim_polygon created for 'oblique line', 'two lines', 'horizontal/vertical line' SIGMET to create the SIGMET area
        '''
        fir = ogr.Open(self.fir_shapefile)
        shape = fir.GetLayer()
        feature = shape.GetFeature(0)
        geom = feature.GetGeometryRef()
        poly = interim_poly.Intersection(geom)
        return poly        
        
    def decode(self):
        '''
        reads SIGMET file and extract relevant information
        '''
        try:
            sigmet_file = open(self.filename)
            sigmet_lines = sigmet_file.readlines()
            line0 = self.trim_line(sigmet_lines[0])
            line1 = self.trim_line(sigmet_lines[1])
            line2 = self.trim_line(sigmet_lines[2])
            if len(sigmet_lines) > 3: # some files have more than 3 lines
                for line in sigmet_lines[3:]:
                    line2 = line2 + ' ' + self.trim_line(line) 
            line0 = line0.split(' ')
            line1 = line1.split(' ')
            line2 = line2.split(' ')
            self.issue_datetime = dt.datetime.strptime(self.yearmonth + line0[2][:-2], "%Y%m%d%H%M")
            self.issue_datetime = dt.datetime.strptime(self.yearmonth + line0[2][:-2], "%Y%m%d%H%M")
            self.sigmet_number = line1[2]
            self.validity_start = dt.datetime.strptime(self.yearmonth + line1[4][:6], "%Y%m%d%H%M")
            self.validity_end = dt.datetime.strptime(self.yearmonth + line1[4][7:], "%Y%m%d%H%M")
            self.sigmet_type = line2[3]
            if self.sigmet_type != 'CNL':
                position_line = self.extract_position_line(line2)
                self.extract_sigmet_position(position_line)
                
            elif self.sigmet_type == 'CNL':
                pass
        except Exception, e:
            logging.warning('%s not decoded | %s\r\n' %(self.filename, str(e)))
            print '%s not decoded | %s\r\n' %(self.filename, str(e))
            
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    def create_polygon(self):
        '''
        Creates SIGMET polygons
        '''
        if self.shape_type == 'polygon':
            lat_lon_pairs = self.sort_clockwise(self.sigmet_position['WI'])
            lat_lon_pairs = lat_lon_pairs[1:]
            lat_lon_pairs.append(lat_lon_pairs[0]) # first point is repeated in self.sigmet_position
            outRing = ogr.Geometry(ogr.wkbLinearRing)
            for lat_lon in lat_lon_pairs:
                outRing.AddPoint(lat_lon[1], lat_lon[0])
            poly = ogr.Geometry(ogr.wkbPolygon)
            poly.AddGeometry(outRing)
            return poly
        elif self.shape_type == 'two lines':
            if 'E' in self.sigmet_position and 'N' in self.sigmet_position:
                lat_lon_pairs = [[self.sigmet_position['N'], self.sigmet_position['E']], [self.corners['NE'][0], self.sigmet_position['E']], self.corners['NE'], [self.sigmet_position['N'], self.corners['NE'][1]]]
            elif 'E' in self.sigmet_position and 'S' in self.sigmet_position:
                lat_lon_pairs = [[self.sigmet_position['S'], self.sigmet_position['E']], [self.corners['SE'][0], self.sigmet_position['E']], self.corners['SE'], [self.sigmet_position['S'], self.corners['SE'][1]]]
            elif 'W' in self.sigmet_position and 'S' in self.sigmet_position:
                lat_lon_pairs = [[self.sigmet_position['S'], self.sigmet_position['W']], [self.corners['SW'][0], self.sigmet_position['W']], self.corners['SW'], [self.sigmet_position['S'], self.corners['SW'][1]]]
            elif 'W' in self.sigmet_position and 'N' in self.sigmet_position:
                lat_lon_pairs = [[self.sigmet_position['N'], self.sigmet_position['W']], [self.corners['NW'][0], self.sigmet_position['W']], self.corners['NW'], [self.sigmet_position['N'], self.corners['NW'][1]]]
            lat_lon_pairs = self.sort_clockwise(lat_lon_pairs)
            lat_lon_pairs.append(lat_lon_pairs[0])
            outRing = ogr.Geometry(ogr.wkbLinearRing)
            for lat_lon in lat_lon_pairs:
                outRing.AddPoint(lat_lon[1], lat_lon[0])
            interim_poly = ogr.Geometry(ogr.wkbPolygon)
            interim_poly.AddGeometry(outRing)
            poly = self.intersect_fir(interim_poly)
            return poly
        elif self.shape_type == 'oblique line':
            if 'E' in self.sigmet_position:
                lat_lon_pairs = [self.sigmet_position['E'][0], self.sigmet_position['E'][1], self.corners['NE'], self.corners['SE']]
            elif 'S' in self.sigmet_position:
                lat_lon_pairs = [self.sigmet_position['S'][0], self.sigmet_position['S'][1], self.corners['SE'], self.corners['SW']]
            elif 'W' in self.sigmet_position:
                lat_lon_pairs = [self.sigmet_position['W'][0], self.sigmet_position['W'][1], self.corners['SW'], self.corners['NW']]
            elif 'N' in self.sigmet_position:
                lat_lon_pairs = [self.sigmet_position['N'][0], self.sigmet_position['N'][1], self.corners['NW'], self.corners['NE']]
            elif 'SE' in self.sigmet_position:
                lat_lon_pairs = [self.sigmet_position['SE'][0], self.sigmet_position['SE'][1], self.corners['NE'], self.corners['SE'], self.corners['SW']]
            elif 'SW' in self.sigmet_position:
                lat_lon_pairs = [self.sigmet_position['SW'][0], self.sigmet_position['SW'][1], self.corners['SE'], self.corners['SW'], self.corners['NW']]
            elif 'NW' in self.sigmet_position:
                lat_lon_pairs = [self.sigmet_position['NW'][0], self.sigmet_position['NW'][1], self.corners['SW'], self.corners['NW'], self.corners['NE']]
            elif 'NE' in self.sigmet_position:
                lat_lon_pairs = [self.sigmet_position['NE'][0], self.sigmet_position['NE'][1], self.corners['NW'], self.corners['NE'], self.corners['SE']]
            lat_lon_pairs = self.sort_clockwise(lat_lon_pairs)
            lat_lon_pairs.append(lat_lon_pairs[0])
            outRing = ogr.Geometry(ogr.wkbLinearRing)
            for lat_lon in lat_lon_pairs:
                outRing.AddPoint(lat_lon[1], lat_lon[0])
            interim_poly = ogr.Geometry(ogr.wkbPolygon)
            interim_poly.AddGeometry(outRing)
            poly = self.intersect_fir(interim_poly)
            return poly
        elif self.shape_type == 'horizontal/vertical line':
            if 'E' in self.sigmet_position:
                lat_lon_pairs = [[self.corners['NE'][0], self.sigmet_position['E']], self.corners['NE'], self.corners['SE'], [self.corners['SE'][0], self.sigmet_position['E']]]
            elif 'S' in self.sigmet_position:
                lat_lon_pairs = [[self.sigmet_position['S'], self.corners['SE'][1]], self.corners['SE'], self.corners['SW'], [self.sigmet_position['S'], self.corners['SW'][1]]]
            elif 'W' in self.sigmet_position:
                lat_lon_pairs = [[self.corners['NW'][0], self.sigmet_position['W']], self.corners['NW'], self.corners['SW'], [self.corners['SW'][0], self.sigmet_position['W']]]
            elif 'N' in self.sigmet_position:
                lat_lon_pairs = [[self.sigmet_position['N'], self.corners['NE'][1]], self.corners['NE'], self.corners['NW'], [self.sigmet_position['N'], self.corners['NW'][1]]]
            lat_lon_pairs = self.sort_clockwise(lat_lon_pairs)
            lat_lon_pairs.append(lat_lon_pairs[0])
            outRing = ogr.Geometry(ogr.wkbLinearRing)
            for lat_lon in lat_lon_pairs:
                outRing.AddPoint(lat_lon[1], lat_lon[0])
            interim_poly = ogr.Geometry(ogr.wkbPolygon)
            interim_poly.AddGeometry(outRing)
            poly = self.intersect_fir(interim_poly)
            return poly
            
    def draw(self, poly):
        '''
        Draws SIGMET area and outputs as shapefile
        '''
#        outRing = ogr.Geometry(ogr.wkbLinearRing)
#        for lat_lon in self.sigmet_position['WI']:
#            outRing.AddPoint(lat_lon[1], lat_lon[0])
#        poly = ogr.Geometry(ogr.wkbPolygon)
#        poly.AddGeometry(outRing)
        # Now convert it to a shapefile with OGR    
        driver = ogr.GetDriverByName('Esri Shapefile')
        ds = driver.CreateDataSource('%s_shape.shp' %self.filename)
        layer = ds.CreateLayer('', None, ogr.wkbPolygon)
        # Add one attribute
        layer.CreateField(ogr.FieldDefn('id', ogr.OFTInteger))
        defn = layer.GetLayerDefn()
        ## If there are multiple geometries, put the "for" loop here
        # Create a new feature (attribute and geometry)
        feat = ogr.Feature(defn)
        feat.SetField('id', self.validity_end.strftime("%y%m%d%H%M"))
        #feat.SetField('sigmet_number', self.sigmet_number)
        # Make a geometry, from Shapely object
        geom = poly
        feat.SetGeometry(geom)    
        layer.CreateFeature(feat)
        feat = geom = None  # destroy these
        # Save and close everything
        ds = layer = feat = geom = None


fir_shapefile = r'C:\TYF\Shapefile\SG_FIR\Singapore_FIR.shp'
for filename in os.listdir(r'C:\TYF\Satellite_Thunderstorms\SIGMET'):
    if filename[:4] == 'WSSR' and filename[-4] != '.':
        sig = sigmet(r'C:\TYF\Satellite_Thunderstorms\SIGMET - Copy\\' + filename, '201807', fir_shapefile)
        sig.decode()
        if sig.sigmet_type != 'CNL':
            sig.get_shape_type()
            if sig.shape_type != 'polygon':
                poly = sig.create_polygon()
                sig.draw(poly)
        else:
            print sig.filename
    

#sig = sigmet(r'C:\TYF\SIGMET\WSSR20WSSS272339', "201807")
#sig = sigmet(r'C:\TYF\SIGMET\WSSR20WSSS310620', "201807")
#sig = sigmet(r'C:\TYF\SIGMET\WSSR20WSSS010530', "201807")
#sig.decode()
#sig.draw()





#outRing = ogr.Geometry(ogr.wkbLinearRing)
#outRing.AddPoint(103.1, -2)
#outRing.AddPoint(103.1, 4)
#outRing.AddPoint(104.1, 4)
#outRing.AddPoint(104.1, -2)
#outRing.AddPoint(103.1, -2)
#poly = ogr.Geometry(ogr.wkbPolygon)
#poly.AddGeometry(outRing)
#
#
## Now convert it to a shapefile with OGR    
#driver = ogr.GetDriverByName('Esri Shapefile')
#ds = driver.CreateDataSource('my.shp')
#layer = ds.CreateLayer('', None, ogr.wkbPolygon)
## Add one attribute
#layer.CreateField(ogr.FieldDefn('id', ogr.OFTInteger))
#defn = layer.GetLayerDefn()
#
### If there are multiple geometries, put the "for" loop here
#
## Create a new feature (attribute and geometry)
#feat = ogr.Feature(defn)
#feat.SetField('id', 123)
#
## Make a geometry, from Shapely object
#geom = poly
#feat.SetGeometry(geom)
#
#layer.CreateFeature(feat)
#feat = geom = None  # destroy these
#
## Save and close everything
#ds = layer = feat = geom = None
    
