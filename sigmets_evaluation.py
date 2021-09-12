# -*- coding: utf-8 -*-
"""
Created on Mon Feb 18 10:49:59 2019

@author: opsuser
"""

from osgeo import gdal, ogr, osr
from collections import OrderedDict
import datetime as dt
import pandas as pd
import calendar
import os
import math
import logging
from sigmets_messages import sigmets_messages
from sigmets_time_list import sigmets_time_list
from sigmets_shapes import sigmets_shapes
from sigmets_assessment import sigmets_assessment


part = '2' #1 or 2
#yyyymm = (dt.datetime.now() - dt.timedelta(days = 27)).strftime('%Y%m')
yyyymm = '202010'
firs = ['WSJC']
tc_excluded = 0
criteria_75 = 1
fir_to_headers = {'WSJC': ['WCSR20', 'WSSR20'], \
                  'WMFC': ['WCMS31', 'WSMS31'], \
                  'WBFC': ['WCMS31', 'WSMS31'], \
                  'WIIZ': ['WCID20', 'WSID20'], \
                  'WAAZ': ['WCID21', 'WSID21'], \
                  'VVTS': ['WCVV31', 'WSVV31']}
fir_shapefiles = {'WSJC': r'C:\TYF\Shapefile\FIRs\WSJC_FIR.shp', \
                  'WMFC': r'C:\TYF\Shapefile\FIRs\WMFC_FIR.shp', \
                  'WBFC': r'C:\TYF\Shapefile\FIRs\WBFC_FIR.shp', \
                  'WIIZ': r'C:\TYF\Shapefile\FIRs\WIIZ_FIR.shp', \
                  'WAAZ': r'C:\TYF\Shapefile\FIRs\WAAZ_FIR.shp', \
                  'VVTS': r'C:\TYF\Shapefile\FIRs\VVTS_FIR.shp'}
inputpath = r'X:\Evaluation\SIGMET'
outputpath = r'C:\TYF\SIGMETs_Evaluation\Outputs'
outputpath_SINGV = r'C:\TYF\SIGMETs_Evaluation\Outputs_SINGV'

if part == '1' or part == '2':
    if not os.path.exists(os.path.join(outputpath, yyyymm)):
        os.makedirs(os.path.join(outputpath, yyyymm))
    if not os.path.exists(os.path.join(outputpath, yyyymm, 'TS_and_SIGMETs')):
        os.makedirs(os.path.join(os.path.join(outputpath, yyyymm), 'TS_and_SIGMETs'))
else:
    if not os.path.exists(os.path.join(outputpath_SINGV, yyyymm)):
        os.makedirs(os.path.join(outputpath_SINGV, yyyymm))
    if not os.path.exists(os.path.join(outputpath_SINGV, yyyymm, 'TS_and_SIGMETs')):
        os.makedirs(os.path.join(outputpath_SINGV, yyyymm, 'TS_and_SIGMETs'))
    
if part == '1':
    for fir in firs:
        headers = fir_to_headers[fir]
        messages = sigmets_messages(yyyymm, fir, headers, inputpath, outputpath)
        messages.decode()
        messages.update()
#        time_list = sigmets_time_list(yyyymm, fir, headers, outputpath)
#        time_list.output_time_list()
        shapes = sigmets_shapes(yyyymm, fir, headers, outputpath, fir_shapefiles)
        shapes.read_decoded_sigmets()
        shapes.generate_shapes()
        
if part == 'SINGV1':
    for fir in firs:
        headers = fir_to_headers[fir]
        shapes = sigmets_shapes(yyyymm, fir, headers, outputpath_SINGV, fir_shapefiles)
        shapes.read_decoded_sigmets()
        shapes.generate_shapes()

if part == '2':
    for fir in firs:
        headers = fir_to_headers[fir]
        assessment = sigmets_assessment(yyyymm, fir, headers, outputpath, tc_excluded, criteria_75)
        assessment.calculate()
        assessment.calculate_daily()

if part == 'SINGV2':
    for fir in firs:
        headers = fir_to_headers[fir]
        assessment = sigmets_assessment(yyyymm, fir, headers, outputpath_SINGV, tc_excluded, criteria_75)
        assessment.calculate()
        assessment.calculate_daily()    
    
#def rerun():
#    '''
#    
#    '''
#    start_yyyymm = '201901'
#    end_yyyymm = '201910'
#    for i in range(int(start_yyyymm), 1+int(end_yyyymm)):
#        yyyymm = str(i)
#        firs = ['WSJC']
#        tc_excluded = 0
#        fir_to_headers = {'WSJC': ['WCSR20', 'WSSR20'], \
#                          'WMFC': ['WCMS31', 'WSMS31'], \
#                          'WBFC': ['WCMS31', 'WSMS31'], \
#                          'WIIZ': ['WCID20', 'WSID20'], \
#                          'WAAZ': ['WCID21', 'WSID21'], \
#                          'VVTS': ['WCVV31', 'WSVV31']}
#        fir_shapefiles = {'WSJC': r'C:\TYF\Shapefile\FIRs\WSJC_FIR.shp', \
#                          'WMFC': r'C:\TYF\Shapefile\FIRs\WMFC_FIR.shp', \
#                          'WBFC': r'C:\TYF\Shapefile\FIRs\WBFC_FIR.shp', \
#                          'WIIZ': r'C:\TYF\Shapefile\FIRs\WIIZ_FIR.shp', \
#                          'WAAZ': r'C:\TYF\Shapefile\FIRs\WAAZ_FIR.shp', \
#                          'VVTS': r'C:\TYF\Shapefile\FIRs\VVTS_FIR.shp'}
#        inputpath = r'X:\Evaluation\SIGMET'
#        outputpath = r'C:\TYF\SIGMETs_Evaluation\Outputs'
#        for j in range(0,2):
#            criteria_75 = j
#            for fir in firs:
#                headers = fir_to_headers[fir]
#                assessment = sigmets_assessment(yyyymm, fir, headers, outputpath, tc_excluded, criteria_75)
#                assessment.calculate()
#                assessment.calculate_daily()
#
#rerun()
        