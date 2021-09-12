# SIGMETs Evaluation

## Overview

This is a program to evaluate SIGMETs. \
The program uses both QGIS and Python scripts. \
The evalution is run on the workstation 192.168.101.39. 


## Data Flow (Simplified)

    SIGMETs forecast files
            |
            |
    PY scripts (part 1 in `sigmets_evaluation.py`)
            |
            |
            V
    SIGMETs SHP files                SatTS TIFF files
            |                                 |
            |_________________________________|
                            |
                            |
                            V
                    PY scripts for QGIS
                            |
                            |
                            V
                TS_and_SIGMETs CSV files
                            |
                            |
                            V
            PY scripts (part 2 in `sigmets_evaluation.py`)
                            |
                            |
                            V
                Scores and other output CSV files
            

## Input Data

| Category               | Description |
| ---                    |  ------  |
| SatTS TIFF files       | 192.168.16.15:/Data90TB/general/HPC/forecast_archive/SatTS_tiff |
| SIGMETs forecast files | \\\\192.168.5.26\nowcast\Evaluation\SIGMET\WSSR20 |


## Output Data

| Category                         | Description |
| ---                              |  ------  |
| SIGMETs SHP files                | \\\\192.168.101.39:TYF\SIGMETs_Evaluation\Outputs\yyyymm\ |
| Score and other output CSV files | \\\\192.168.101.39:TYF\SIGMETs_Evaluation\Outputs\ |

## Configuration

Program configuration can be found and ammended accordingly in `sigmets_evaluation.py`

           