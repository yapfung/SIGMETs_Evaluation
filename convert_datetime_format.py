# -*- coding: utf-8 -*-
"""
Created on Fri Mar  8 15:42:42 2019

@author: opsuser
"""

import os
import pandas as pd


inputpath = r'C:\TYF\SIGMETs_Evaluation\Outputs\201901\TS_and_SIGMETs'
outputpath = r'C:\TYF\SIGMETs_Evaluation\Outputs\201901\TS_and_SIGMETs2'
os.chdir(inputpath)
for sigmet_ts_filename in os.listdir(inputpath):
    if sigmet_ts_filename[-3:] == 'csv':
        print sigmet_ts_filename
        sigmet_ts_df = pd.read_csv(sigmet_ts_filename)
        sigmet_ts_df['issue'] = pd.to_datetime(sigmet_ts_df['issue'])
        sigmet_ts_df['start'] = pd.to_datetime(sigmet_ts_df['start'])
        sigmet_ts_df['end'] = pd.to_datetime(sigmet_ts_df['end'])
#        sigmet_ts_df['issue'].dt.strftime('%Y%m%d%H%M')
#        sigmet_ts_df['start'].dt.strftime('%Y%m%d%H%M')
#        sigmet_ts_df['end'].dt.strftime('%Y%m%d%H%M')
        sigmet_ts_df.to_csv(os.path.join(outputpath, sigmet_ts_filename), date_format = '%Y%m%d%H%M')