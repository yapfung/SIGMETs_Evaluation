##SatTS_SIGMET=name
##satelliteimagefolder=folder
##sigmetshapefolder=folder
##firshape=vector
##emptysigmetshape=vector
##emptytsshape=vector
##outputfolder=folder
##logfolder=folder
##yyyymm=string

#satelliteimagefolder = r'C:\TYF\OuterStacks_Evaluation\Satellite_Images'
#sigmetshapefolder = r'C:\TYF\SIGMETs_Evaluation\Outputs\201901\SIGMET_Shapes'
#firshape= r'C:\TYF\Shapefile\SG_FIR.shp'
#emptysigmetshape = r'C:\TYF\Shapefile\empty_sigmet.shp'
#outputfolder = r'C:\TYF\SIGMETs_Evaluation\Outputs\201901\TS_and_SIGMETs'
#logfolder = r'CC:\TYF\SIGMETs_Evaluation\Outputs\201901'
#yyyymm = '201901'

import os
import logging
import csv
import ast
import datetime as dt

firs = ['WSJC']

for fir in firs:
    print os.getcwd()
    logging.basicConfig(filename= os.path.join(logfolder, 'qgis_sigmets_and_ts_%s_%s.txt' %(yyyymm, fir)), format='%(asctime)s ~%(levelname)s : %(message)s', level=logging.INFO)
    error_counter = 0
#    sigmet_time_list = {}
    
#    with open(os.path.join(timelistfolder, 'sigmets_time_list_%s_%s.csv' %(yyyymm, header)), "r") as sigmet_time_list_file:
#        reader = csv.reader(sigmet_time_list_file, delimiter=";") # must choose a delimiter different from the actual one of the csv
#        for row in list(reader)[1:]:
#            row = row[0].translate(None, '"') #remove extra extra "" in the string
#            datetime = dt.datetime.strptime(row[:19], '%Y-%m-%d %H:%M:%S').strftime('%Y%m%d%H%M')
#            sigmetfilenames = ast.literal_eval(row[20:])
#            sigmet_time_list[datetime] = sigmetfilenames
    
    for satelliteimagefilename in os.listdir(satelliteimagefolder):
        try:
            outputfile = os.path.join(outputfolder, 'sigmet_' + satelliteimagefilename[:-4] + 'csv')
            satelliteimage = os.path.join(satelliteimagefolder, satelliteimagefilename)
            #satelliteimagefilename = satelliteimagefilename.encode("utf-8")
            datetime = satelliteimagefilename[:12]
            sigmets_to_be_merged = []
#            if datetime in sigmet_time_list:
#                for sigmetfilename in sigmet_time_list[datetime]:
#                    sigmet = os.path.join(sigmetshapefolder, 'sigmet_shapes_%s' %header, sigmetfilename + '_shape.shp')
#                    sigmets_to_be_merged.append(processing.runalg('qgis:reprojectlayer', sigmet,'EPSG:3857',None)['OUTPUT'])
            for sigmetfilename in os.listdir(os.path.join(sigmetshapefolder, datetime)):
                if sigmetfilename[-3:] == 'shp':
                    sigmet = os.path.join(sigmetshapefolder, datetime, sigmetfilename)
                    sigmets_to_be_merged.append(processing.runalg('qgis:reprojectlayer', sigmet,'EPSG:3857',None)['OUTPUT']) 
            if not sigmets_to_be_merged:
                sigmets_to_be_merged.append(processing.runalg('qgis:reprojectlayer', emptysigmetshape,'EPSG:3857',None)['OUTPUT'])
            outputs_GDALOGRCLIPRASTERBYMASKLAYER_1=processing.runalg('gdalogr:cliprasterbymasklayer', satelliteimage,firshape,None,True,True,True,5,4,75.0,6.0,1.0,False,0,False,None,None)
            outputs_GDALOGRRASTERCALCULATOR_1=processing.runalg('gdalogr:rastercalculator', outputs_GDALOGRCLIPRASTERBYMASKLAYER_1['OUTPUT'],'1',outputs_GDALOGRCLIPRASTERBYMASKLAYER_1['OUTPUT'],'2',outputs_GDALOGRCLIPRASTERBYMASKLAYER_1['OUTPUT'],'3',None,'1',None,'1',None,'1','((A+B+C)/3)>0',None,5,None,None)
            outputs_GDALOGRSIEVE_1=processing.runalg('gdalogr:sieve', outputs_GDALOGRRASTERCALCULATOR_1['OUTPUT'],10.0,0,None)
            outputs_QGISMERGEVECTORLAYERS_1=processing.runalg('qgis:mergevectorlayers', sigmets_to_be_merged,None)
            outputs_GDALOGRPOLYGONIZE_1=processing.runalg('gdalogr:polygonize', outputs_GDALOGRSIEVE_1['OUTPUT'],'DN',None)
            outputs_QGISFIELDCALCULATOR_3=processing.runalg('qgis:fieldcalculator', outputs_QGISMERGEVECTORLAYERS_1['OUTPUT'],'SIG_Area',0,15.0,5.0,True,'$area',None)
            outputs_QGISEXTRACTBYEXPRESSION_1=processing.runalg('qgis:extractbyexpression', outputs_GDALOGRPOLYGONIZE_1['OUTPUT'],'"DN" = 1',None)
            outputs_QGISREPROJECTLAYER_1=processing.runalg('qgis:reprojectlayer', outputs_QGISEXTRACTBYEXPRESSION_1['OUTPUT'],'EPSG:3857',None)
            outputs_QGISSMOOTHGEOMETRY_1=processing.runalg('qgis:smoothgeometry', outputs_QGISREPROJECTLAYER_1['OUTPUT'],5.0,0.25,None)
            outputs_QGISFIXEDDISTANCEBUFFER_1=processing.runalg('qgis:fixeddistancebuffer', outputs_QGISSMOOTHGEOMETRY_1['OUTPUT_LAYER'],37040.0,10.0,False,None)
            outputs_QGISDISSOLVE_1=processing.runalg('qgis:dissolve', outputs_QGISFIXEDDISTANCEBUFFER_1['OUTPUT'],False,'DN',None)
            outputs_QGISFIXEDDISTANCEBUFFER_2=processing.runalg('qgis:fixeddistancebuffer', outputs_QGISDISSOLVE_1['OUTPUT'],-37040.0,10.0,False,None)
            outputs_QGISMULTIPARTTOSINGLEPARTS_1=processing.runalg('qgis:multiparttosingleparts', outputs_QGISFIXEDDISTANCEBUFFER_2['OUTPUT'],None)
            outputs_QGISFIELDCALCULATOR_2=processing.runalg('qgis:fieldcalculator', outputs_QGISMULTIPARTTOSINGLEPARTS_1['OUTPUT'],'TS_Area',0,10.0,6.0,True,'$area',None)
            outputs_QGISEXTRACTBYEXPRESSION_2=processing.runalg('qgis:extractbyexpression', outputs_QGISFIELDCALCULATOR_2['OUTPUT_LAYER'],'"TS_Area" >= 10000000000',None)
            outputs_QGISSMOOTHGEOMETRY_2=processing.runalg('qgis:smoothgeometry', outputs_QGISEXTRACTBYEXPRESSION_2['OUTPUT'],10.0,0.5,None)
            outputs_QGISFIELDCALCULATOR_1=processing.runalg('qgis:fieldcalculator', outputs_QGISSMOOTHGEOMETRY_2['OUTPUT_LAYER'],'TS_ID',1,10.0,3.0,True,'$rownum',None)
            outputs_QGISFIELDCALCULATOR_4=processing.runalg('qgis:fieldcalculator', outputs_QGISFIELDCALCULATOR_1['OUTPUT_LAYER'],'TS Area',0,15.0,5.0,True,'$area',None)
            outputs_QGISREPROJECTLAYER_7=processing.runalg('qgis:reprojectlayer', emptytsshape,'EPSG:3857',None)
            outputs_QGISMERGEVECTORLAYERS_2=processing.runalg('qgis:mergevectorlayers', [outputs_QGISFIELDCALCULATOR_4['OUTPUT_LAYER'],outputs_QGISREPROJECTLAYER_7['OUTPUT']],None)
            outputs_QGISREPROJECTLAYER_6=processing.runalg('qgis:reprojectlayer', outputs_QGISMERGEVECTORLAYERS_2['OUTPUT'],'EPSG:3857',None)
            outputs_QGISUNION_1=processing.runalg('qgis:union', outputs_QGISREPROJECTLAYER_6['OUTPUT'],outputs_QGISFIELDCALCULATOR_3['OUTPUT_LAYER'],None)
            outputs_QGISREMOVENULLGEOMETRIES_1=processing.runalg('qgis:removenullgeometries', outputs_QGISUNION_1['OUTPUT'],None)
            outputs_QGISDELETEDUPLICATEGEOMETRIES_1=processing.runalg('qgis:deleteduplicategeometries', outputs_QGISREMOVENULLGEOMETRIES_1['OUTPUT_LAYER'],None)
            outputs_QGISFIELDCALCULATOR_5=processing.runalg('qgis:fieldcalculator', outputs_QGISDELETEDUPLICATEGEOMETRIES_1['OUTPUT'],'Area',0,15.0,5.0,True,'$area',None)
            outputs_QGISEXTRACTBYEXPRESSION_3=processing.runalg('qgis:extractbyexpression', outputs_QGISFIELDCALCULATOR_5['OUTPUT_LAYER'],'"Empty_TS" != 1 or "number" > -9999',None)
            outputs_GDALOGRCONVERTFORMAT_1=processing.runalg('gdalogr:convertformat', outputs_QGISEXTRACTBYEXPRESSION_3['OUTPUT'],12,None,outputfile)
        except Exception, e:
            logging.warning(satelliteimagefilename + ' not processed | ' + str(e) + '\r\n')
            print 'WARNING: ' + satelliteimagefilename + ' not processed | ' + str(e)
        else:
            print satelliteimagefilename + ' and sigmets (if any) processed'
    logging.info('Processing for %s for %s completed' %(yyyymm, fir))
    print 'Processing for %s for %s completed' %(yyyymm, fir)
    logging.info(error_counter)
