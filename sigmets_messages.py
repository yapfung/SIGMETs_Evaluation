# -*- coding: utf-8 -*-
"""
Created on Thu Aug  2 14:23:23 2018

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

class sigmets_messages():
    
    def __init__(self, yyyymm, fir, headers, inputpath, outputpath):
        '''
        Initiates an instance to decode SIGMET messages
        '''
        self.inputpath = inputpath
        self.outputpath = outputpath
        self.yyyymm = yyyymm
        self.fir = fir
        self.headers = headers
        self.sigmets = {'filename':[], 'sigmet_number':[], 'sigmet_fir': [], 'issue_datetime':[], 'validity_start':[], 'validity_end':[], 'updated_validity_end':[], 'sigmet_type':[], 'sigmet_number_to_cancel':[], 'ts_sigmet_position':[], 'tc_sigmet_position':[]}
        self.sigmets_df = None
        self.corners = {'NE': [15, 120], 'SE': [-10, 120], 'SW': [-10, 90], 'NW': [15, 90]}

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
    
    def get_tc_position_datetime(self, hhmmZ, validity_start, tc_order):
        '''
        get datetime of the tc position
        '''
        if tc_order == 'TC1' and hhmmZ[:-1] > validity_start.strftime('%H%M'):
            return (validity_start + dt.timedelta(days = -1)).strftime('%Y%m%d') + hhmmZ[:-1]
            #return dt.datetime.strptime(yyyymmddhhmm, '%Y%m%d%H%M')
        else: 
            return validity_start.strftime('%Y%m%d') + hhmmZ[:-1]
            #return dt.datetime.strptime(yyyymmddhhmm, '%Y%m%d%H%M')
    
    def extract_ts_position_line(self, line):
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
    
    def extract_tc_position_line(self, line):
        '''
        Identify and extract relevant part of line that bears the information of SIGMET position
        '''
        start_index = end_index = None
        for i, element in enumerate(line):
            if element == 'OBS' or element == 'FCST':
                start_index = i
                break
        return line[start_index:]
    
    def extract_ts_sigmet_position(self, ts_position_line):
        '''
        Stores the lat lon information of ts sigmet areas in attribute "self.ts_sigmet_position" and classifies the shape type
        '''
        ts_sigmet_position = {}
        while '' in ts_position_line:
            ts_position_line.remove('')
        if 'WI' in ts_position_line:
            ts_sigmet_position['WI'] = []
            for i in range(len(ts_position_line)):
                if 'N' in ts_position_line[i] or 'S' in ts_position_line[i] and len(ts_position_line[i]) > 2 :
                    ts_sigmet_position['WI'].append([self.convert(ts_position_line[i]), self.convert(ts_position_line[i+1])])
        else:
            for i in range(len(ts_position_line)):
                if ts_position_line[i] == 'N' or ts_position_line[i] == 'S' or ts_position_line[i] == 'E' or ts_position_line[i] == 'W' or ts_position_line[i] == 'NE' or ts_position_line[i] == 'NW' or ts_position_line[i] == 'SE' or ts_position_line[i] == 'SW':
                    if ts_position_line[i+2] == 'LINE':
                        ts_sigmet_position[ts_position_line[i]] = [[self.convert(ts_position_line[i+3]), self.convert(ts_position_line[i+4])],  [self.convert(ts_position_line[i+6]), self.convert(ts_position_line[i+7])]]
                    else:
                        ts_sigmet_position[ts_position_line[i]] = self.convert(ts_position_line[i+2])
        return ts_sigmet_position
    
    def extract_tc_sigmet_position(self, tc_position_line, validity_start):
        '''
        Stores the lat lon information of tc sigmet areas in attribute "self.tc_sigmet_position" and classifies the shape type
        '''
        tc_sigmet_position = {}
        while '' in tc_position_line:
            tc_position_line.remove('')
        for i in range(len(tc_position_line) - 1):
            if tc_position_line[i] == 'WI':
                tc_sigmet_position['R'] = tc_position_line[i+1]
            if tc_position_line[i] == 'MOV':
                tc_sigmet_position['MOV_D'] = tc_position_line[i+1] 
                tc_sigmet_position['MOV_S'] = tc_position_line[i+2]
            if 'TC1' not in tc_sigmet_position:
                if tc_position_line[i-1][-1] == 'Z' and tc_position_line[i][0] in ['N', 'S'] and tc_position_line[i+1][0] in ['E', 'W']:
                    tc_sigmet_position['TC1'] = [self.get_tc_position_datetime(tc_position_line[i-1], validity_start, 'TC1'), self.convert(tc_position_line[i]), self.convert(tc_position_line[i+1])]
                elif tc_position_line[i-1][-1] != 'Z' and tc_position_line[i][0] in ['N', 'S'] and tc_position_line[i+1][0] in ['E', 'W']:
                    tc_sigmet_position['TC1'] = [validity_start.strftime('%Y%m%d%H%M'), self.convert(tc_position_line[i]), self.convert(tc_position_line[i+1])]
            elif 'TC1' in tc_sigmet_position:
                if tc_position_line[i-3][-1] == 'Z' and tc_position_line[i][0] in ['N', 'S'] and tc_position_line[i+1][0] in ['E', 'W']:
                    tc_sigmet_position['TC2'] = [self.get_tc_position_datetime(tc_position_line[i-3], validity_start, 'TC2'), self.convert(tc_position_line[i]), self.convert(tc_position_line[i+1])]
        return tc_sigmet_position
        
    def decode(self):
        '''
        reads SIGMET file and extract relevant information
        '''
        for header in self.headers:
            for dd in os.listdir(os.path.join(self.inputpath, header, self.yyyymm)):
                for filename in os.listdir(os.path.join(self.inputpath, header, self.yyyymm, dd)):
                    try:
                        filepath = os.path.join(os.path.join(self.inputpath, header, self.yyyymm, dd), filename)
                        sigmet_file = open(filepath)
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
                        issue_datetime = dt.datetime.strptime(str(self.yyyymm) + line0[2][:], "%Y%m%d%H%M")
                        sigmet_fir = line1[0]
                        sigmet_number = line1[2]
                        validity_start = dt.datetime.strptime(str(self.yyyymm) + line1[4][:6], "%Y%m%d%H%M")
                        validity_end = dt.datetime.strptime(str(self.yyyymm) + line1[4][7:13], "%Y%m%d%H%M")
                        if int(issue_datetime.strftime('%d')) == calendar.monthrange(int(self.yyyymm)/100,  int(self.yyyymm)%100)[1]:
                            if validity_start.strftime('%H%M') < issue_datetime.strftime('%H%M'):
                                validity_start = validity_start + dt.timedelta(days = calendar.monthrange(int(self.yyyymm)/100,  int(self.yyyymm)%100)[1])
                            if validity_end.strftime('%H%M') < issue_datetime.strftime('%H%M'):
                                validity_end = validity_end + dt.timedelta(days = calendar.monthrange(int(self.yyyymm)/100,  int(self.yyyymm)%100)[1])
                        sigmet_type = line2[line2.index('FIR') + 1]
                        if sigmet_type != 'CNL' and sigmet_type != 'TC':
                            ts_position_line = self.extract_ts_position_line(line2)
                            ts_sigmet_position = self.extract_ts_sigmet_position(ts_position_line)
                            sigmet_number_to_cancel = 0
                            tc_sigmet_position = {}
                        elif sigmet_type != 'CNL' and sigmet_type == 'TC':
                            tc_position_line = self.extract_tc_position_line(line2)
                            tc_sigmet_position = self.extract_tc_sigmet_position(tc_position_line, validity_start)
                            sigmet_number_to_cancel = 0
                            ts_sigmet_position = {}
                        elif sigmet_type == 'CNL':
                            ts_sigmet_position = {}
                            tc_sigmet_position = {}
                            sigmet_number_to_cancel = line2[line2.index('FIR') + 3]
                    except Exception, e:
                        logging.warning('%s not decoded | %s\r\n' %(filename, str(e)))
                        print '%s not decoded | %s\r\n' %(filename, str(e))
                    else:
                        if sigmet_fir == self.fir:
                            self.sigmets['filename'].append(filename)
                            self.sigmets['issue_datetime'].append(issue_datetime)
                            self.sigmets['sigmet_fir'].append(sigmet_fir)
                            self.sigmets['sigmet_number'].append(sigmet_number)
                            self.sigmets['validity_start'].append(validity_start)
                            self.sigmets['validity_end'].append(validity_end)
                            self.sigmets['updated_validity_end'].append(validity_end)
                            self.sigmets['sigmet_type'].append(sigmet_type)
                            self.sigmets['ts_sigmet_position'].append(ts_sigmet_position)
                            self.sigmets['tc_sigmet_position'].append(tc_sigmet_position)
                            self.sigmets['sigmet_number_to_cancel'].append(sigmet_number_to_cancel)
        self.sigmets_df = pd.DataFrame(self.sigmets, columns = ['filename', 'sigmet_fir', 'issue_datetime', 'validity_start', 'validity_end', 'updated_validity_end', 'sigmet_type', 'sigmet_number', 'sigmet_number_to_cancel', 'ts_sigmet_position', 'tc_sigmet_position'])

    def update(self):
        '''
        updates the validity end time of SIGMET if the SIGMET is cancelled, new validity end will be stored in the column of "updated_validity_end"
        '''
        cancellations_df = self.sigmets_df[self.sigmets_df['sigmet_type'] == 'CNL']
        for index, row in cancellations_df.iterrows():
            cancellation_datetime = row['validity_start']
            sigmet_number_to_cancel = row['sigmet_number_to_cancel']
            
            self.sigmets_df.loc[(self.sigmets_df['sigmet_number']==sigmet_number_to_cancel) & (self.sigmets_df['validity_end']==row['validity_end']), 'updated_validity_end'] = cancellation_datetime
        self.sigmets_df.to_csv(os.path.join(self.outputpath, self.yyyymm, 'decoded_sigmets_%s_%s.csv' %(self.yyyymm, self.fir)))
        return self.sigmets


#fir_shapefile = r'C:\TYF\Shapefile\SG_FIR\Singapore_FIR.shp'
#inputpath = r'D:\SatTS\SIGMETs_Evaluation\SIGMETs\%s' %201812
#outputpath = r'D:\SatTS\SIGMETs_Evaluation\Outputs\%s' %201812
#sig = sigmets_messages(201812, inputpath, outputpath)
#sig.decode()
#sig.update()

