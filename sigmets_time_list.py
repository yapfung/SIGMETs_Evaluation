# -*- coding: utf-8 -*-
"""
Created on Sun Dec 23 10:22:53 2018

@author: opsuser
"""

import datetime as dt
import pandas as pd
import logging
import os
import calendar
import csv

class sigmets_time_list():
    
    def __init__(self, yyyymm, fir, header, outputpath):
        '''
        Initiates an instance to create list of time and the valid SIMGETs at that time
        '''
        self.yyyymm = yyyymm
        self.previous_yyyymm = (dt.datetime.strptime(yyyymm, '%Y%m') - dt.timedelta(days = 20)).strftime('%Y%m')
        self.fir = fir
        self.header = header
        self.outputpath = outputpath
        self.time_list = {'datetime': [], 'sigmets': []}
        self.time_list_df = None
        self.df1 = None
        self.df2 = None
        
    def output_time_list(self):
        '''
        Reads decoded SIGMET issued in the evalution month and the month before the evaluation month, to get all SIMGETs valid in the evaluation month
        '''
        try:
            previous_yyyymm_filepath = os.path.join(self.outputpath, '%s' %self.previous_yyyymm, 'decoded_sigmets_%s_%s.csv' %(self.previous_yyyymm, self.fir))
            previous_yyyymm_df = pd.read_csv(previous_yyyymm_filepath)
            previous_yyyymm_df['validity_start'] = pd.to_datetime(previous_yyyymm_df['validity_start'])
            previous_yyyymm_df['updated_validity_end'] = pd.to_datetime(previous_yyyymm_df['updated_validity_end'])
        except Exception, e:
            logging.warning('Previous month\'s decoded sigmets not read | ' + str(e) + '\n')
            print 'Previous month\'s decoded sigmets not read | ' + str(e)
        else:
            pass
        try:
            yyyymm_filepath = os.path.join(self.outputpath, '%s' %self.yyyymm, 'decoded_sigmets_%s_%s.csv' %(self.yyyymm, self.fir))
            print yyyymm_filepath
            yyyymm_df = pd.read_csv(yyyymm_filepath)
            yyyymm_df['validity_start'] = pd.to_datetime(yyyymm_df['validity_start'])
            yyyymm_df['updated_validity_end'] = pd.to_datetime(yyyymm_df['updated_validity_end'])
        except Exception, e:
            logging.warning('Evaluation month\'s decoded sigmets not read | ' + str(e) + '\n')
            print 'Evaluation month\'s decoded sigmets not read | ' + str(e)
        else:
            datetime = dt.datetime.strptime(self.yyyymm + '010000', '%Y%m%d%H%M')
            days_in_month = calendar.monthrange(int(self.yyyymm[:4]), int(self.yyyymm[-2:]))[1]
            end_datetime = dt.datetime.strptime(self.yyyymm, '%Y%m') + dt.timedelta(days = days_in_month)
            while datetime < end_datetime:
                try:
                    yyyymm_sigmets = list(yyyymm_df[(yyyymm_df['validity_start'] <= datetime) & (yyyymm_df['updated_validity_end'] >= datetime)]['filename'])
                    self.time_list['datetime'].append(datetime)
                    if 'previous_yyyymm_sigmets_df' in locals():
                        previous_yyyymm_sigmets = list(previous_yyyymm_df[(previous_yyyymm_df['validity_start'] <= datetime) & (previous_yyyymm_df['updated_validity_end'] >= datetime)]['filename'])
                        self.time_list['sigmets'].append(previous_yyyymm_sigmets + yyyymm_sigmets)
                    else:
                        self.time_list['sigmets'].append(yyyymm_sigmets)
                except Exception, e:
                    logging.warning('SIMGETs for ' + datetime.strftime('%Y%m%d%H%M') + ' not found | ' + str(e) + '\n')
                    print 'SIMGETs for ' + datetime.strftime('%Y%m%d%H%M') + ' not found | ' + str(e)
                else:
                    pass
                datetime = datetime + dt.timedelta(minutes = 10) #Important for the while loop
        try:
            self.time_list_df = pd.DataFrame.from_dict(self.time_list)
            self.time_list_df.to_csv(os.path.join(self.outputpath, '%s' %self.yyyymm, 'sigmets_time_list_%s_%s.csv' %(self.yyyymm, self.fir)), sep=",", index=False, header=True)
        except Exception, e:
            logging.warning('Time list of SIGMETs not created | ' + str(e) + '\n')
            print 'Time list of SIGMETs not created | ' + str(e)
        else:
            pass
            
             
#tl = sigmets_time_list('201812', 'WSSR20', r'D:\SatTS\SIGMETs_Evaluation\Outputs\201812')
#tl.output_time_list()
