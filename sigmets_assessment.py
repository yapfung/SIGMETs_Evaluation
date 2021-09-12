# -*- coding: utf-8 -*-
"""
Created on Fri Dec 28 16:13:31 2018

@author: opsuser
"""

import datetime as dt
import datetime as dt
import pandas as pd
import os
import logging
import calendar
import glob
import csv

class sigmets_assessment():
    
    def __init__(self, yyyymm, fir, headers, outputpath, tc_excluded, criteria_75):
        '''
        Initiates an instance to assess SIGMETs at every 10 minute
        '''
        self.yyyymm = str(yyyymm)
        self.previous_yyyymm = (dt.datetime.strptime(self.yyyymm + '010000', '%Y%m%d%H%M') - dt.timedelta(days = 20)).strftime('%Y%m')
        self.fir = fir
        self.headers = headers
        self.outputpath = outputpath
        self.tc_excluded = tc_excluded
        self.criteria_75 = criteria_75
        self.assessment = []
        self.assessment_df = None
        self.previous_assessment_df = None
        self.assessment_daily_df = None
        self.lead_times = []
        self.lead_times_df = None
        self.scores_df = None
        self.counter = 0
        
        
    def count_minutes(self, timedelta):
        '''
        Converts timedelta to neareast 10 minutes
        '''
        return timedelta.days*24*float(60) + timedelta.seconds/float(60)
    
    def safe_divide_percentage(self, numerator, denominator):
        '''
        Performs division and return None if undefined
        '''
        if denominator == 0:
            return 'None'
        return numerator/float(denominator)*100
    
    def apply_criteria_75(self):
        '''
        If the period of hit recorded is less than 75% of the validity period, all hits for all 10-minute intervals are changed to false alarms. Otherwise, all false alarms are changed to hits
        '''
        try:
            start_datetime = dt.datetime.strptime(self.yyyymm + '010000', '%Y%m%d%H%M')
            days_in_month = calendar.monthrange(int(self.yyyymm[:4]), int(self.yyyymm[-2:]))[1]
            end_datetime = dt.datetime.strptime(self.yyyymm, '%Y%m') + dt.timedelta(minutes = days_in_month*24*60 + 23*60 + 50)
            sigmet_filenames = list(self.assessment_df['sigmet_filename'].dropna().unique())
            for sigmet_filename in sigmet_filenames:
                validity_start = pd.to_datetime(self.assessment_df[self.assessment_df['sigmet_filename'] == sigmet_filename]['validity_start'].iloc[0])
                validity_end = pd.to_datetime(self.assessment_df[self.assessment_df['sigmet_filename'] == sigmet_filename]['validity_end'].iloc[0])
                if validity_start < start_datetime:
                    validity_start = start_datetime
                if validity_end > end_datetime:
                    validity_end = end_datetime
                duration_sigmet = self.count_minutes(validity_end - validity_start)
                duration_hits = self.assessment_df[self.assessment_df['sigmet_filename'] == sigmet_filename]['sigmet_hit'].sum() * 10
                print (duration_hits, duration_sigmet)
                if self.safe_divide_percentage(duration_hits, duration_sigmet) >= 75:
                    self.assessment_df.loc[self.assessment_df['sigmet_filename'] == sigmet_filename] = self.assessment_df.loc[self.assessment_df['sigmet_filename'] == sigmet_filename].assign(sigmet_hit = 1)
                    self.assessment_df.loc[self.assessment_df['sigmet_filename'] == sigmet_filename] = self.assessment_df.loc[self.assessment_df['sigmet_filename'] == sigmet_filename].assign(false_alarm = 0)
                else:
                    self.assessment_df.loc[self.assessment_df['sigmet_filename'] == sigmet_filename] = self.assessment_df.loc[self.assessment_df['sigmet_filename'] == sigmet_filename].assign(sigmet_hit = 0)
                    self.assessment_df.loc[self.assessment_df['sigmet_filename'] == sigmet_filename] = self.assessment_df.loc[self.assessment_df['sigmet_filename'] == sigmet_filename].assign(false_alarm = 1)
            self.assessment_df.to_csv(os.path.join(self.outputpath, self.yyyymm, 'SIGMETs_Assessments_%s_%s_method_%s.csv' %(self.yyyymm, self.fir, 1+self.criteria_75)), columns=['datetime', 'ts_id', 'sigmet_filename', 'issuance_datetime', 'validity_start', 'validity_end', 'sigmet_hit', 'hit', 'miss', 'false_alarm'])
        except Exception, e:
            logging.warning('Criteria 75 failed to be applied | $s' %e)
            print 'Criteria 75 failed to be applied| $s' %e
            
    def assess(self, datetime, sigmet_ts_df):
        '''
        Assess SIGMETs by comparing area coverage of TS within a 10-min interval
        '''
        ts_ids = list(sigmet_ts_df['TS_ID'].dropna().unique())
        if 0 in ts_ids: ts_ids.remove(0) # ts_id = 0 is the empty TS layer
        sigmet_filenames = list(sigmet_ts_df['filename'].dropna().unique())
        try:
            if ts_ids:
                for ts_id in ts_ids:
                    ts_area = sigmet_ts_df[sigmet_ts_df['TS_ID'] == ts_id]['TS_Area'].mean()
                    ts_area_covered_by_sigmet = sigmet_ts_df[(sigmet_ts_df['TS_ID'] == ts_id) & (sigmet_ts_df['type'] != 'Empty') & (sigmet_ts_df.type.notnull())]['Area'].sum()
                    if self.tc_excluded and 'TC' in sigmet_ts_df[sigmet_ts_df['TS_ID'] == ts_id]['type'].values:
                        self.assessment.append({'datetime': datetime, 'hit': 0, 'sigmet_hit': 0, 'miss': 0, 'false_alarm':0, 'ts_id': ts_id, 'sigmet_filename': None, 'issuance_datetime': None, 'validity_start': None})
                    elif ts_area_covered_by_sigmet/float(ts_area) >= 0.5:
                        self.assessment.append({'datetime': datetime, 'hit': 1, 'sigmet_hit': 0, 'miss': 0, 'false_alarm':0, 'ts_id': ts_id, 'sigmet_filename': None, 'issuance_datetime': None, 'validity_start': None})
                    elif ts_area_covered_by_sigmet/float(ts_area) < 0.5:
                        self.assessment.append({'datetime': datetime, 'hit': 0, 'sigmet_hit': 0, 'miss': 1, 'false_alarm':0, 'ts_id': ts_id, 'sigmet_filename': None, 'issuance_datetime': None, 'validity_start': None})
                        if not sigmet_ts_df[(sigmet_ts_df['TS_ID'] == ts_id) & (sigmet_ts_df['type'] != 'Empty')].empty:
                            sigmet_filename = sigmet_ts_df[(sigmet_ts_df['TS_ID'] == ts_id) & (sigmet_ts_df['type'] != 'Empty')]['filename'].iloc[0]
                            sigmet_area = sigmet_ts_df[sigmet_ts_df['filename'] == sigmet_filename]['SIG_Area'].mean()
                            sigmet_area_covered_by_ts = sigmet_ts_df[(sigmet_ts_df['filename'] == sigmet_filename) & (sigmet_ts_df['type'] != 'Empty') & (sigmet_ts_df.TS_ID.notnull()) & (sigmet_ts_df['TS_ID'] != 0)]['Area'].sum()
                            if sigmet_area_covered_by_ts/sigmet_area < 1/float(6):
                                print datetime
                                self.counter += 1
            if sigmet_filenames:
                for sigmet_filename in sigmet_filenames:
                    issuance_datetime = sigmet_ts_df[sigmet_ts_df['filename'] == sigmet_filename]['issue'].iloc[0]
                    validity_start = sigmet_ts_df[sigmet_ts_df['filename'] == sigmet_filename]['start'].iloc[0]
                    validity_end = sigmet_ts_df[sigmet_ts_df['filename'] == sigmet_filename]['end'].iloc[0]
                    sigmet_area = sigmet_ts_df[sigmet_ts_df['filename'] == sigmet_filename]['SIG_Area'].mean()
                    sigmet_area_covered_by_ts = sigmet_ts_df[(sigmet_ts_df['filename'] == sigmet_filename) & (sigmet_ts_df['type'] != 'Empty') & (sigmet_ts_df.TS_ID.notnull()) & (sigmet_ts_df['TS_ID'] != 0)]['Area'].sum()
                    if self.tc_excluded and 'TC' in sigmet_ts_df[sigmet_ts_df['filename'] == sigmet_filename]['type'].values:
                        self.assessment.append({'datetime': datetime, 'hit': 0, 'sigmet_hit': 0, 'miss': 0, 'false_alarm':0, 'ts_id': None, 'sigmet_filename': sigmet_filename, 'issuance_datetime': issuance_datetime, 'validity_start': validity_start, 'validity_end': validity_end})
                    elif sigmet_area_covered_by_ts/sigmet_area >= 1/float(6):
                        self.assessment.append({'datetime': datetime, 'hit': 0, 'sigmet_hit': 1, 'miss': 0, 'false_alarm':0, 'ts_id': None, 'sigmet_filename': sigmet_filename, 'issuance_datetime': issuance_datetime, 'validity_start': validity_start, 'validity_end': validity_end})
                    else:
                        self.assessment.append({'datetime': datetime, 'hit': 0, 'sigmet_hit': 0, 'miss': 0, 'false_alarm':1, 'ts_id': None, 'sigmet_filename': sigmet_filename, 'issuance_datetime': issuance_datetime, 'validity_start': validity_start, 'validity_end': validity_end})
        except Exception, e:
            logging.warning('Assessment not done for %s | $s' %(datetime, e))
            print 'Assessment not done for %s | $s' %(datetime, e)
        
    def calculate(self):
        '''
        Calculates scores
        '''
        datetime = dt.datetime.strptime(self.yyyymm + '010000', '%Y%m%d%H%M')
        days_in_month = calendar.monthrange(int(self.yyyymm[:4]), int(self.yyyymm[-2:]))[1]
        end_datetime = dt.datetime.strptime(self.yyyymm, '%Y%m') + dt.timedelta(days = days_in_month)
        while datetime < end_datetime:
            general_filename = '*%s*.csv' %datetime.strftime('%Y%m%d%H%M')
            if not glob.glob(os.path.join(self.outputpath, self.yyyymm, 'TS_and_SIGMETs', general_filename)):
                self.assessment.append({'datetime': datetime, 'hit': 0, 'sigmet_hit': 0, 'miss': 0, 'false_alarm':0, 'ts_id': None, 'sigmet_filename': None, 'issuance_datetime': None, 'validity_start': None, 'validity_end': None})
            else:
                try:
                    sigmet_ts_filename = glob.glob(os.path.join(self.outputpath, self.yyyymm, 'TS_and_SIGMETs', general_filename))[0]
                    sigmet_ts_df = pd.read_csv(sigmet_ts_filename, dtype={'issue':str, 'start':str, 'end':str})
                    sigmet_ts_df['issue'] = pd.to_datetime(sigmet_ts_df['issue'])
                    sigmet_ts_df['start'] = pd.to_datetime(sigmet_ts_df['start'])
                    sigmet_ts_df['end'] = pd.to_datetime(sigmet_ts_df['end'])
                    self.assess(datetime, sigmet_ts_df)
                except Exception, e:
                    logging.warning('00000000sigmet_ts_%s not read | %s' %(datetime, e))
                    print 'sigmet_ts_%s not read | %s' %(datetime, e)
                else:
                    pass
            datetime = datetime + dt.timedelta(minutes = 10) #Important for while loop
        try:
            self.assessment_df = pd.DataFrame(self.assessment)
            self.assessment_df.to_csv(os.path.join(self.outputpath, self.yyyymm, 'SIGMETs_Assessments_%s_%s_method_%s.csv' %(self.yyyymm, self.fir, 1+self.criteria_75)), columns=['datetime', 'ts_id', 'sigmet_filename', 'issuance_datetime', 'validity_start', 'validity_end', 'sigmet_hit', 'hit', 'miss', 'false_alarm'])
            self.assessment_df = pd.read_csv(os.path.join(self.outputpath, self.yyyymm, 'SIGMETs_Assessments_%s_%s_method_%s.csv' %(self.yyyymm, self.fir, 1+self.criteria_75)))
            self.assessment_df['datetime'] = pd.to_datetime(self.assessment_df['datetime'])
            self.assessment_df['issuance_datetime'] = pd.to_datetime(self.assessment_df['issuance_datetime'])
            self.assessment_df['validity_start'] = pd.to_datetime(self.assessment_df['validity_start'])
            self.assessment_df['validity_end'] = pd.to_datetime(self.assessment_df['validity_end'])
            self.previous_assessment_df = pd.read_csv(os.path.join(self.outputpath, self.previous_yyyymm, 'SIGMETs_Assessments_%s_%s_method_%s.csv' %(self.previous_yyyymm, self.fir, 1+self.criteria_75)))
            self.previous_assessment_df['datetime'] = pd.to_datetime(self.previous_assessment_df['datetime'])
            self.previous_assessment_df['issuance_datetime'] = pd.to_datetime(self.previous_assessment_df['issuance_datetime'])
            self.previous_assessment_df['validity_start'] = pd.to_datetime(self.previous_assessment_df['validity_start'])
            self.previous_assessment_df['validity_end'] = pd.to_datetime(self.previous_assessment_df['validity_end'])
        except Exception, e:
            logging.warning('Assessment dataframe not created | %s' %e)
            print 'Assessment dataframe not created | %s' %e
        else:
            pass
        try:
            self.previous_assessment_df = pd.read_csv(os.path.join(self.outputpath, self.previous_yyyymm, 'SIGMETs_Assessments_%s_%s_method_%s.csv' %(self.previous_yyyymm, self.fir, 1+self.criteria_75)))
            self.previous_assessment_df['datetime'] = pd.to_datetime(self.previous_assessment_df['datetime'])
            self.previous_assessment_df['issuance_datetime'] = pd.to_datetime(self.previous_assessment_df['issuance_datetime'])
            self.previous_assessment_df['validity_start'] = pd.to_datetime(self.previous_assessment_df['validity_start'])
            self.previous_assessment_df['validity_end'] = pd.to_datetime(self.previous_assessment_df['validity_end'])
        except Exception, e:
            logging.warning('Assessment dataframe for %s not created | %s' %(self.previous_yyyymm, e))
            print 'Assessment dataframe for %s not created | %s' %(self.previous_yyyymm, e)
        except:
            pass
        sigmet_filenames = list(self.assessment_df['sigmet_filename'].dropna().unique())
        if sigmet_filenames:
            for sigmet_filename in sigmet_filenames:
                try:
                    issuance_datetime = self.assessment_df[self.assessment_df['sigmet_filename'] == sigmet_filename]['issuance_datetime'].iloc[0]
                    validity_start = self.assessment_df[self.assessment_df['sigmet_filename'] == sigmet_filename]['validity_start'].iloc[0]
                    validity_lead_time = self.count_minutes(validity_start - issuance_datetime)
                    if issuance_datetime.strftime('%Y%m') == self.previous_yyyymm:
                        if not self.previous_assessment_df.empty and self.previous_assessment_df[(self.previous_assessment_df['sigmet_filename'] == sigmet_filename) & (self.previous_assessment_df['issuance_datetime'] == issuance_datetime)]['sigmet_hit'].max() == 1:
                            continue
                    first_ts_datetime = self.assessment_df[(self.assessment_df['sigmet_filename'] == sigmet_filename) & (self.assessment_df['sigmet_hit'] == 1)]['datetime'].min()
                    if pd.notnull(first_ts_datetime):
                        ts_lead_time = self.count_minutes(first_ts_datetime - issuance_datetime)
                    else:
                        ts_lead_time = None
                except Exception, e:
                    logging.warning('lead time for %s not calculated | %s' %(sigmet_filename, e))
                    print 'lead time for %s not calculated | %s' %(sigmet_filename, e)
                else:
                    self.lead_times.append({'sigmet_filename': sigmet_filename, 'validity_lead_time': validity_lead_time, 'ts_lead_time': ts_lead_time})
            self.lead_times_df = pd.DataFrame(self.lead_times)
        if self.criteria_75:
            self.apply_criteria_75()
        try:
            total_sigmet_h = self.assessment_df['sigmet_hit'].sum()
            total_h = self.assessment_df['hit'].sum()
            total_m = self.assessment_df['miss'].sum()
            total_fa = self.assessment_df['false_alarm'].sum()
            total_pod = self.safe_divide_percentage(total_h, total_h + total_m)
            total_far = self.safe_divide_percentage(total_fa, total_sigmet_h + total_fa)
            total_csi = self.safe_divide_percentage(total_h, total_h + total_m + total_fa)
        except Exception, e:
            logging.warning('Total scores not calculated | %s' %e)
            print 'Total scores not calculated | %s' %e
        else:
            pass
        try:
            with open(os.path.join(self.outputpath, self.yyyymm, 'SIGMETs_Evaluation_Scores_%s_%s_method_%s.csv' %(self.yyyymm, self.fir, 1+self.criteria_75)), 'wb') as csvfile:
                writer = csv.writer(csvfile, delimiter=',')
                writer.writerow([''])
                writer.writerow(['SUMMARY'])
                writer.writerow([''])
#                writer.writerow(['total_sigmet_hit', total_sigmet_h])
                writer.writerow(['total_hit', total_h])
                writer.writerow(['total_miss', total_m])
                writer.writerow(['total_false_alarm', total_fa])
                writer.writerow(['POD', total_pod])
                writer.writerow(['FAR', total_far])
                writer.writerow(['CSI', total_csi])
        except:
            logging.warning('Total scores not saved | %s' %e)
            print 'Total scores not saved | %s' %e
        else:
            pass
        print total_h, total_m, total_fa, total_pod, total_far, total_csi
        print 'counterrrrrrrrr   ' + str(self.counter)
        
    def calculate_daily(self):
        '''
        Calculates daily scores for the month to outputs days with scores in the worst 30 percentile for POD and FAR
        '''
        self.assessment_df = pd.read_csv(os.path.join(self.outputpath, self.yyyymm, 'SIGMETs_Assessments_%s_%s_method_%s.csv' %(self.yyyymm, self.fir, 1+self.criteria_75)))
        print type(self.assessment_df['datetime'])
        self.assessment_df['datetime'] = pd.to_datetime(self.assessment_df['datetime'])
        self.assessment_daily_df = self.assessment_df.resample('D', on='datetime').sum()
        self.assessment_daily_df['pod'] = self.assessment_daily_df['hit'] / (self.assessment_daily_df['hit'] + self.assessment_daily_df['miss'])
        self.assessment_daily_df['far'] = self.assessment_daily_df['false_alarm'] / (self.assessment_daily_df['hit'] + self.assessment_daily_df['miss'])
        self.assessment_daily_df['csi'] = self.assessment_daily_df['hit'] / (self.assessment_daily_df['hit'] + self.assessment_daily_df['miss'] + self.assessment_daily_df['false_alarm'])
        self.assessment_daily_df['remarks'] = ''
        self.assessment_daily_df.loc[self.assessment_daily_df['pod'] < self.assessment_daily_df['pod'].quantile(0.3), 'remarks'] += 'low POD;'
        self.assessment_daily_df.loc[self.assessment_daily_df['far'] > self.assessment_daily_df['far'].quantile(0.7), 'remarks'] += 'high FAR;'
        self.assessment_daily_df = self.assessment_daily_df[self.assessment_daily_df['remarks'] != '']
        self.assessment_daily_df.to_csv(os.path.join(self.outputpath, self.yyyymm, 'SIGMETs_Assessments_Daily_%s_%s_method_%s.csv' %(self.yyyymm, self.fir, 1+self.criteria_75)))
        

#sa = sigmets_assessment(201901, 'WSJC', ['WSSR20', 'WCSR20'], r'C:\TYF\SIGMETs_Evaluation\Outputs', 1, 1)
#sa.calculate()