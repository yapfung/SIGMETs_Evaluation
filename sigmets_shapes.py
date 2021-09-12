# -*- coding: utf-8 -*-
"""
Created on Tue Dec 11 16:02:24 2018

@author: opsuser
"""

from osgeo import gdal, ogr, osr
import shapely
from shapely import wkt
from shapely.ops import linemerge, unary_union, polygonize
from collections import OrderedDict
import datetime as dt
import time
import pandas as pd
import calendar
import os
import math
import logging
import ast

class sigmets_shapes():
    
    def __init__(self, yyyymm, fir, header, outputpath, fir_shapefiles):
        '''
        Initiates an instance to create shapefiles of SIGMETs
        '''
        self.yyyymm = yyyymm
        self.previous_yyyymm = (dt.datetime.strptime(self.yyyymm + '010000', '%Y%m%d%H%M') - dt.timedelta(days = 20)).strftime('%Y%m')
        self.header = header
        self.fir = fir
        self.outputpath = outputpath
        self.fir_shapefiles = fir_shapefiles
        self.decoded_sigmets = os.path.join(self.outputpath, self.yyyymm, 'decoded_sigmets_%s_%s.csv' %(self.yyyymm, self.fir))
        self.corners = {'WSJC': {'NE': [15, 120], 'SE': [-10, 120], 'SW': [-10, 90], 'NW': [15, 90]},\
                        'WMFC': {'NE': [10, 105], 'SE': [0, 105], 'SW': [0, 90], 'NW': [10, 90]},\
                        'WBFC': {'NE': [10, 120], 'SE': [0, 120], 'SW': [0, 105], 'NW': [10, 105]},\
                        'WIIZ': {'NE': [10, 120], 'SE': [-15, 120], 'SW': [-15, 90], 'NW': [10, 90]},\
                        'WAAZ': {'NE': [10, 150], 'SE': [-15, 150], 'SW': [-15, 110], 'NW': [10, 110]},\
                        'VVTS': {'NE': [20, 115], 'SE': [5, 115], 'SW': [5, 100], 'NW': [20, 100]}}
        self.previous_yyyymm_df = None
        self.yyyymm_df = None
        
    def aa(self, validity_time):
        return validity_time
        
    def count_minutes(self, timedelta):
        '''
        Converts timedelta to neareast 10 minutes
        '''
        return timedelta.days*24*float(60) + timedelta.seconds/float(60)

    def get_shape_type(self, sigmet_position):
        '''
        Identifies the type of SIGMET shape's construction
        '''
        print sigmet_position
        if 'WI'in sigmet_position:
            shape_type = 'polygon'
        elif type(sigmet_position.values()[0]) == list:
            shape_type = 'oblique line'
        elif len(sigmet_position) > 1 and ('SW' in sigmet_position or 'SE' in sigmet_position or 'NE' in sigmet_position or 'NW' in sigmet_position):
            shape_type = 'two oblique lines'
        elif len(sigmet_position) > 1 and (('E' in sigmet_position or 'W' in sigmet_position) and ('N' in sigmet_position or 'S' in sigmet_position)):
            shape_type = 'two perpendicular lines'
        elif len(sigmet_position) > 1 and (('E' in sigmet_position and 'W' in sigmet_position) or ('N' in sigmet_position and 'S' in sigmet_position)):
            shape_type = 'two parallel lines'
        elif type(sigmet_position.values()[0]) == float or type(sigmet_position.values()[0]) == int:
            shape_type = 'horizontal/vertical line'
        elif 'TC2' in sigmet_position:
            shape_type = 'two tc centres'
        elif 'TC1' in sigmet_position and 'TC2' not in sigmet_position:
            shape_type = 'one tc centre'
        return shape_type
    
    def gradient_and_x_direction(self, sigmet_position):
        '''
        Find the gradient and x_direction of the oblique line
        '''
        if sigmet_position.values()[0][1][1] - sigmet_position.values()[0][0][1] == 0:
            gradient = 9999
            x_direction = 0
        else:
            x_direction = (sigmet_position.values()[0][1][1] - sigmet_position.values()[0][0][1])/abs(sigmet_position.values()[0][1][1] - sigmet_position.values()[0][0][1])
            gradient = (sigmet_position.values()[0][1][0] - sigmet_position.values()[0][0][0])/(sigmet_position.values()[0][1][1] - sigmet_position.values()[0][0][1])
        return gradient, x_direction
    
    def extend_line(self, sigmet_position, gradient, x_direction):
        '''
        Lengthen the oblique line that divides the FIR region into two by 0.5 deg, so that there is no gap between the oblique line and FIR border
        '''
        if gradient == 9999:
            delta_y = 1
            if sigmet_position.values()[0][0][0] > sigmet_position.values()[0][1][0]:
                extended_oblique_line = [[sigmet_position.values()[0][0][0] + delta_y, sigmet_position.values()[0][0][1]], [sigmet_position.values()[0][1][0] - delta_y , sigmet_position.values()[0][1][1]]]
            else:
                extended_oblique_line = [[sigmet_position.values()[0][0][0] - delta_y, sigmet_position.values()[0][0][1]], [sigmet_position.values()[0][1][0] + delta_y , sigmet_position.values()[0][1][1]]]
        else:
            if abs(gradient) > 1:
                delta_y = gradient/abs(gradient)*0.5
                delta_x = abs(1/gradient)*0.5
            else:
                delta_y = gradient*0.5
                delta_x = 0.5
            extended_oblique_line = [[sigmet_position.values()[0][0][0] - x_direction*delta_y, sigmet_position.values()[0][0][1] - x_direction*delta_x], [sigmet_position.values()[0][1][0] + x_direction*delta_y, sigmet_position.values()[0][1][1] + x_direction*delta_x]]
        return extended_oblique_line
    
    def cut_fir(self, sigmet_fir, extended_oblique_line):
        '''
        Split FIR into two with the extended oblique line for 'oblique line' SIGMET to create SIGMET area
        '''
        fir = ogr.Open(self.fir_shapefiles[sigmet_fir])
        shape = fir.GetLayer()
        feature = shape.GetFeature(0)
        exported_feature = feature.ExportToJson(True)
        fir_shapely = shapely.geometry.shape(exported_feature['geometry'])
        extended_oblique_linestring = 'LINESTRING (%s %s, %s %s)' %(extended_oblique_line[0][1], extended_oblique_line[0][0], extended_oblique_line[1][1], extended_oblique_line[1][0])
        extended_oblique_line_shapely = shapely.wkt.loads(extended_oblique_linestring)
        merged = linemerge([fir_shapely.boundary, extended_oblique_line_shapely])
        merged_unioned = unary_union(merged)
        cut_polygons = list(polygonize(merged_unioned))
        cut_polygons = [polygon for polygon in cut_polygons if polygon.area >= 0.75]
        return cut_polygons

    def intersect_fir(self, sigmet_fir, interim_poly):
        '''
        Intersect interim_polygon created for 'two lines' and 'horizontal/vertical line' SIGMET to create the SIGMET area
        '''
        fir = ogr.Open(self.fir_shapefiles[sigmet_fir])
        shape = fir.GetLayer()
        feature = shape.GetFeature(0)
        geom = feature.GetGeometryRef()
        poly = interim_poly.Intersection(geom)
        return poly

    def create_polygon(self, datetime, sigmet_fir, shape_type, sigmet_position):
        '''
        Creates SIGMET polygons
        '''
        if shape_type == 'polygon':
            lat_lon_pairs = sigmet_position['WI']
            outRing = ogr.Geometry(ogr.wkbLinearRing)
            for lat_lon in lat_lon_pairs:
                outRing.AddPoint(lat_lon[1], lat_lon[0])
            poly = ogr.Geometry(ogr.wkbPolygon)
            poly.AddGeometry(outRing)
            return poly
        elif shape_type == 'two perpendicular lines':
            corners = self.corners[sigmet_fir]
            if 'E' in sigmet_position and 'N' in sigmet_position:
                lat_lon_pairs = [[sigmet_position['N'], sigmet_position['E']], [corners['NE'][0], sigmet_position['E']], corners['NE'], [sigmet_position['N'], corners['NE'][1]]]
            elif 'E' in sigmet_position and 'S' in sigmet_position:
                lat_lon_pairs = [[sigmet_position['S'], sigmet_position['E']], [sigmet_position['S'], corners['SE'][1]], corners['SE'], [corners['SE'][0], sigmet_position['E']]]
            elif 'W' in sigmet_position and 'S' in sigmet_position:
                lat_lon_pairs = [[sigmet_position['S'], sigmet_position['W']], [corners['SW'][0], sigmet_position['W']], corners['SW'], [sigmet_position['S'], corners['SW'][1]]]
            elif 'W' in sigmet_position and 'N' in sigmet_position:
                lat_lon_pairs = [[sigmet_position['N'], sigmet_position['W']], [sigmet_position['N'], corners['NW'][1]], corners['NW'], [corners['NW'][0], sigmet_position['W']]]
            lat_lon_pairs.append(lat_lon_pairs[0])            
            outRing = ogr.Geometry(ogr.wkbLinearRing)
            for lat_lon in lat_lon_pairs:
                outRing.AddPoint(lat_lon[1], lat_lon[0])
            interim_poly = ogr.Geometry(ogr.wkbPolygon)
            interim_poly.AddGeometry(outRing)
            poly = self.intersect_fir(sigmet_fir, interim_poly)
            return poly
        elif shape_type == 'oblique line':
            gradient, x_direction = self.gradient_and_x_direction(sigmet_position)
            extended_oblique_line = self.extend_line(sigmet_position,  gradient, x_direction)
            cut_polygons = self.cut_fir(sigmet_fir, extended_oblique_line)
            if 'N' in sigmet_position:
                cut_polygons.sort(key=lambda x: x.bounds[1], reverse=True) #bounds is a list of [xmin, ymin, xmax, ymax]
            elif 'E' in sigmet_position:
                cut_polygons.sort(key=lambda x: x.bounds[0], reverse=True)
            elif 'S' in sigmet_position:
                cut_polygons.sort(key=lambda x: x.bounds[3])
            elif 'W' in sigmet_position:
                cut_polygons.sort(key=lambda x: x.bounds[2])
            elif 'NE' in sigmet_position:
                cut_polygons.sort(key=lambda x: x.bounds[1], reverse=True)
                cut_polygons.sort(key=lambda x: x.bounds[0], reverse=True)
            elif 'SE' in sigmet_position:
                cut_polygons.sort(key=lambda x: x.bounds[3])
                cut_polygons.sort(key=lambda x: x.bounds[0], reverse=True)
            elif 'SW' in sigmet_position:
                cut_polygons.sort(key=lambda x: x.bounds[3])
                cut_polygons.sort(key=lambda x: x.bounds[2])
            elif 'NW' in sigmet_position:
                cut_polygons.sort(key=lambda x: x.bounds[2])
                cut_polygons.sort(key=lambda x: x.bounds[1], reverse=True)
            poly = cut_polygons[0]
            poly = ogr.CreateGeometryFromWkb(poly.wkb) #convert to similar forms with poly from other shape_types
            return poly
        elif shape_type == 'horizontal/vertical line':
            corners = self.corners[sigmet_fir]
            if 'E' in sigmet_position:
                lat_lon_pairs = [[corners['NE'][0], sigmet_position['E']], corners['NE'], corners['SE'], [corners['SE'][0], sigmet_position['E']]]
            elif 'S' in sigmet_position:
                lat_lon_pairs = [[sigmet_position['S'], corners['SE'][1]], corners['SE'], corners['SW'], [sigmet_position['S'], corners['SW'][1]]]
            elif 'W' in sigmet_position:
                lat_lon_pairs = [[corners['NW'][0], sigmet_position['W']], [corners['SW'][0], sigmet_position['W']], corners['SW'], corners['NW']]
            elif 'N' in sigmet_position:
                lat_lon_pairs = [[sigmet_position['N'], corners['NW'][1]], corners['NW'], corners['NE'], [sigmet_position['N'], corners['NE'][1]]]
            lat_lon_pairs.append(lat_lon_pairs[0])
            outRing = ogr.Geometry(ogr.wkbLinearRing)
            for lat_lon in lat_lon_pairs:
                outRing.AddPoint(lat_lon[1], lat_lon[0])
            interim_poly = ogr.Geometry(ogr.wkbPolygon)
            interim_poly.AddGeometry(outRing)
            poly = self.intersect_fir(sigmet_fir, interim_poly)
            return poly
        elif shape_type == 'two tc centres':
            datetime_tc1 = dt.datetime.strptime(sigmet_position['TC1'][0], '%Y%m%d%H%M')
            datetime_tc2 = dt.datetime.strptime(sigmet_position['TC2'][0], '%Y%m%d%H%M')
            lat_lon_pair_tc1 = sigmet_position['TC1'][1:]
            lat_lon_pair_tc2 = sigmet_position['TC2'][1:]
            if 'R' in sigmet_position:
                if sigmet_position['R'][-2:] == 'KM':
                    radius = float(sigmet_position['R'][:-2])/110
                elif sigmet_position['R'][-2:] == 'NM':
                    radius = sigmet_position['R']*1.852/110
            else:
                radius = 100/float(110)
            time_fraction = self.count_minutes(datetime - datetime_tc1)/float(self.count_minutes(datetime_tc2 - datetime_tc1))
            lat = lat_lon_pair_tc1[0] + time_fraction*(lat_lon_pair_tc2[0] - lat_lon_pair_tc1[0])
            lon = lat_lon_pair_tc1[1] + time_fraction*(lat_lon_pair_tc2[1] - lat_lon_pair_tc1[1])
            wkt = "POINT (%s %s)" %(lon, lat)
            pt = ogr.CreateGeometryFromWkt(wkt)
            bufferDistance = radius 
            interim_poly = pt.Buffer(bufferDistance)
            poly = self.intersect_fir(sigmet_fir, interim_poly)
            return poly
        elif shape_type == 'one tc centre':
            datetime_tc1 = dt.datetime.strptime(sigmet_position['TC1'][0], '%Y%m%d%H%M')
            lat_lon_pair_tc1 = sigmet_position['TC1'][1:]
            if 'R' in sigmet_position:
                if sigmet_position['R'][-2:] == 'KM':
                    radius = float(sigmet_position['R'][:-2])/110
                elif sigmet_position['R'][-2:] == 'NM':
                    radius = sigmet_position['R']*1.852/110
            else:
                radius = 100/float(110)
            time_elapsed = self.count_minutes(datetime - datetime_tc1)
            if 'MOV_D' in sigmet_position and 'MOV_S' in sigmet_position:
                direction = sigmet_position['MOV_D']
                speed_per_min = float(sigmet_position['MOV_S'][:-2])/60/60
                direction_to_angle = {'E': 0, 'ENE': math.pi/8, 'NE': math.pi/4, 'NNE': math.pi*3/8, 'N': math.pi/2, \
                                      'NNW': math.pi*5/8, 'NW': math.pi*6/8, 'WNW': math.pi*7/8, 'W': math.pi, \
                                      'WSW': math.pi*9/8, 'SW': math.pi*10/8, 'SSW': math.pi*11/8, 'S': math.pi*12/8, \
                                      'SSE': math.pi*13/8, 'SE': math.pi*14/8, 'ESE': math.pi*15/8}
                lat = lat_lon_pair_tc1[0] + time_elapsed*speed_per_min*math.sin(direction_to_angle[direction])
                lon = lat_lon_pair_tc1[1] + time_elapsed*speed_per_min*math.cos(direction_to_angle[direction])
            else:
                lat = lat_lon_pair_tc1[0]
                lon = lat_lon_pair_tc1[1]
            print lat, lon
            wkt = "POINT (%s %s)" %(lon, lat)
            pt = ogr.CreateGeometryFromWkt(wkt)
            bufferDistance = radius 
            interim_poly = pt.Buffer(bufferDistance)
            poly = self.intersect_fir(sigmet_fir, interim_poly)
            return poly
     
    def output_shape(self, datetime_path, poly, filename, sigmet_fir, issue_datetime, validity_start, updated_validity_end, sigmet_type, sigmet_number, sigmet_position):
        '''
        Outputs SIGMET area as shapefile
        '''
        # Convert it to a shapefile with OGR
        driver = ogr.GetDriverByName('Esri Shapefile')
        ds = driver.CreateDataSource(os.path.join(datetime_path, '%s_shape.shp' %filename))
        layer = ds.CreateLayer('', None, ogr.wkbPolygon)
        # Add one attribute
        layer.CreateField(ogr.FieldDefn('filename', ogr.OFTString))
        layer.CreateField(ogr.FieldDefn('fir', ogr.OFTString))
        layer.CreateField(ogr.FieldDefn('issue', ogr.OFTString))
        layer.CreateField(ogr.FieldDefn('start', ogr.OFTString))
        layer.CreateField(ogr.FieldDefn('end', ogr.OFTString))
        layer.CreateField(ogr.FieldDefn('type', ogr.OFTString))
        layer.CreateField(ogr.FieldDefn('number', ogr.OFTString))
        defn = layer.GetLayerDefn()
        ## If there are multiple geometries, put the "for" loop here
        # Create a new feature (attribute and geometry) # Beware of the length of the field value, use set length if possible
        feat = ogr.Feature(defn)
        feat.SetField('filename', str(filename))
        feat.SetField('fir', str(sigmet_fir))
        issue_datetime = pd.to_datetime(issue_datetime, unit='ns')
        validity_start = pd.to_datetime(validity_start, unit='ns')
        updated_validity_end = pd.to_datetime(updated_validity_end, unit='ns')
#        feat.SetField('issue', issue_datetime)
#        feat.SetField('start', validity_start)
#        feat.SetField('end', updated_validity_end)
        feat.SetField('issue', issue_datetime.strftime('%Y%m%d%H%M'))
        feat.SetField('start', validity_start.strftime('%Y%m%d%H%M'))
        feat.SetField('end', updated_validity_end.strftime('%Y%m%d%H%M'))
        feat.SetField('type', str(sigmet_type))
        feat.SetField('number', int(sigmet_number))
        # Make a geometry, from Shapely object
        geom = poly
        feat.SetGeometry(geom)    
        layer.CreateFeature(feat)
        feat = geom = None  # destroy these
        # Save and close everything
        ds = layer = feat = geom = None
        
    def draw(self, datetime, datetime_path, decoded_sigmet):
        '''
        Draws and outputs SIGMET areas
        '''
        filename = decoded_sigmet['filename'].values[0]
        sigmet_fir = decoded_sigmet['sigmet_fir'].values[0]
        issue_datetime = decoded_sigmet['issue_datetime'].values[0]
        validity_start = decoded_sigmet['validity_start'].values[0]
        updated_validity_end = decoded_sigmet['updated_validity_end'].values[0]
        sigmet_type = decoded_sigmet['sigmet_type'].values[0]
        sigmet_number = decoded_sigmet['sigmet_number'].values[0]
        ts_sigmet_position = ast.literal_eval(decoded_sigmet['ts_sigmet_position'].values[0])
        tc_sigmet_position = ast.literal_eval(decoded_sigmet['tc_sigmet_position'].values[0])
        if sigmet_type != 'CNL' and sigmet_type in ['EMBD', 'OCNL', 'FREQ']:
            shape_type = self.get_shape_type(ts_sigmet_position)
            poly = self.create_polygon(datetime, sigmet_fir, shape_type, ts_sigmet_position)
            self.output_shape(datetime_path, poly, filename, sigmet_fir, issue_datetime, validity_start, updated_validity_end, sigmet_type, sigmet_number, ts_sigmet_position)
        elif sigmet_type != 'CNL' and sigmet_type == 'TC':
            shape_type = self.get_shape_type(tc_sigmet_position)
            poly = self.create_polygon(datetime, sigmet_fir, shape_type, tc_sigmet_position)
            self.output_shape(datetime_path, poly, filename, sigmet_fir, issue_datetime, validity_start, updated_validity_end, sigmet_type, sigmet_number, tc_sigmet_position)
    
    def read_decoded_sigmets(self):
        '''
        reads decoded sigmets for previous and evaluation months
        '''
        print os.path.join(self.outputpath, '%s' %self.previous_yyyymm, 'decoded_sigmets_%s_%s.csv' %(self.previous_yyyymm, self.fir))
        try:
            previous_yyyymm_filepath = os.path.join(self.outputpath, '%s' %self.previous_yyyymm, 'decoded_sigmets_%s_%s.csv' %(self.previous_yyyymm, self.fir))
            print previous_yyyymm_filepath
            self.previous_yyyymm_df = pd.read_csv(previous_yyyymm_filepath)
            self.previous_yyyymm_df['issue_datetime'] = pd.to_datetime(self.previous_yyyymm_df['issue_datetime'])
            self.previous_yyyymm_df['validity_start'] = pd.to_datetime(self.previous_yyyymm_df['validity_start'])
            self.previous_yyyymm_df['updated_validity_end'] = pd.to_datetime(self.previous_yyyymm_df['updated_validity_end'])
        except Exception, e:
            logging.warning('Previous month\'s decoded sigmets not read | ' + str(e) + '\n')
            print 'Previous month\'s decoded sigmets not read | ' + str(e)
            self.previous_yyyymm_df = pd.DataFrame({})
        else:
            pass
        try:
            yyyymm_filepath = os.path.join(self.outputpath, '%s' %self.yyyymm, 'decoded_sigmets_%s_%s.csv' %(self.yyyymm, self.fir))
            self.yyyymm_df = pd.read_csv(yyyymm_filepath)
            self.yyyymm_df['issue_datetime'] = pd.to_datetime(self.yyyymm_df['issue_datetime'])
            self.yyyymm_df['validity_start'] = pd.to_datetime(self.yyyymm_df['validity_start'])
            self.yyyymm_df['updated_validity_end'] = pd.to_datetime(self.yyyymm_df['updated_validity_end'])
        except Exception, e:
            logging.warning('Evaluation month\'s decoded sigmets not read | ' + str(e) + '\n')
            print 'Evaluation month\'s decoded sigmets not read | ' + str(e)
        
    def generate_shapes(self):
        '''
        Draws and outputs shapes for every 10 minutes
        '''
        if self.yyyymm_df.empty:
            logging.warning('No decoded sigmets read \n')
            print 'No decoded sigmets read \n'
            raise Exception, 'Evaluation stops\n'
        datetime = dt.datetime.strptime(self.yyyymm + '010000', '%Y%m%d%H%M')
        days_in_month = calendar.monthrange(int(self.yyyymm[:4]), int(self.yyyymm[-2:]))[1]
        end_datetime = dt.datetime.strptime(self.yyyymm, '%Y%m') + dt.timedelta(days = days_in_month)
        while datetime < end_datetime:
            datetime_path = os.path.join(self.outputpath, self.yyyymm, 'SIGMET_Shapes', datetime.strftime('%Y%m%d%H%M'))
            if not os.path.exists(datetime_path):
                os.makedirs(datetime_path)
            if not self.previous_yyyymm_df.empty:
                previous_yyyymm_sigmets = list(self.previous_yyyymm_df[(self.previous_yyyymm_df['validity_start'] <= datetime) & (self.previous_yyyymm_df['updated_validity_end'] > datetime)]['filename'])
                for filename in previous_yyyymm_sigmets:
                    decoded_sigmet = self.previous_yyyymm_df[self.previous_yyyymm_df['filename'] == filename]
                    self.draw(datetime_path, datetime_path, decoded_sigmet)
            yyyymm_sigmets = list(self.yyyymm_df[(self.yyyymm_df['validity_start'] <= datetime) & (self.yyyymm_df['updated_validity_end'] > datetime)]['filename'])
            for filename in yyyymm_sigmets:
                decoded_sigmet = self.yyyymm_df[self.yyyymm_df['filename'] == filename]
                self.draw(datetime, datetime_path, decoded_sigmet)
            datetime = datetime + dt.timedelta(minutes = 10) #Important for the while loop





#fir_shapefiles = {'WSJC': r'C:\TYF\Shapefile\FIRs\WSJC_FIR.shp', 'WMFC': r'C:\TYF\Shapefile\FIRs\WMFC_FIR.shp', \
#                  'WBFC': r'C:\TYF\Shapefile\FIRs\WBFC_FIR.shp', 'WIIZ': r'C:\TYF\Shapefile\FIRs\WIIZ_FIR.shp', \
#                  'WAAZ': r'C:\TYF\Shapefile\FIRs\WAAZ_FIR.shp', 'VVTS': r'C:\TYF\Shapefile\FIRs\VVTS_FIR.shp'}
#sigmets = r'D:\SatTS\SIGMETs_Evaluation\Outputs\201812\decoded_sigmets_201812.csv'
#outputpath = r'C:\TYF\SIGMETs_Evaluation\Outputs'
#sig_shape = sigmets_shapes(201812, 'WSSR20', outputpath, fir_shapefiles)
#
#sig_shape.output_shapes()