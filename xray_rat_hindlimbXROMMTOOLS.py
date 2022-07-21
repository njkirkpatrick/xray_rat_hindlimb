#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
xray_rat_hindlimnbXROMMTOOLS
Developed by Nathan Kirkpatrick 
edited from existing code by J.D. Laurence-Chasen (xrommtools, Laurence-Chasen et al. JEB 2020)
using code described in Kane et al. eLife 2020

Kane, Gary A., Lopes, Goncalo, Saunders, Jonny L., Mathis, Alexander and Mathis, Mackenzie W.
    “Real-Time, Low-Latency Closed-Loop Feedback Using Markerless Posture Tracking.” 
    ELife, vol. 9, Dec. 2020, p. e61909. https://doi.org/10.7554/eLife.61909.

Laurence-Chasen, J. D., Manafzadeh, A. R., Hatsopoulos, N. G., Ross, C. F. and Arce-McShane, F. I. 
    (2020). Integrating XMALab and DeepLabCut for high-throughput XROMM. 
    The Journal of Experimental Biology, 223. 


Functions:

dlc_to_xma: convert output of DeepLabCut to XMALab format 2D points file
analyze_xromm_videos_external_model: use pre-trained models to generate XMALab-ready labels


"""
import os
import pandas as pd
from dlclive import benchmark_videos

def dlc_to_xma(cam1data,cam2data,trialname,savepath):
    
    h5_save_path = savepath+"/"+trialname+"-Predicted2DPoints.h5"
    csv_save_path = savepath+"/"+trialname+"-Predicted2DPoints.csv"
    
    if isinstance(cam1data, str): #is string
        if ".csv" in cam1data:

            cam1data=pd.read_csv(cam1data, sep=',',header=None)
            cam2data=pd.read_csv(cam2data, sep=',',header=None)
            pointnames = list(cam1data.loc[1,1:].unique())
            
            # reformat CSV / get rid of headers
            cam1data = cam1data.loc[3:,1:]
            cam1data.columns = range(cam1data.shape[1])
            cam1data.index = range(cam1data.shape[0])
            cam2data = cam2data.loc[3:,1:]
            cam2data.columns = range(cam2data.shape[1])
            cam2data.index = range(cam2data.shape[0])
            
        elif ".h5" in cam1data:# is .h5 file
            cam1data = pd.read_hdf(cam1data)
            cam2data = pd.read_hdf(cam2data)
            pointnames = list(cam1data.columns.get_level_values('bodyparts').unique())

        else:
            raise ValueError('2D point input is not in correct format')
    else:
        
        pointnames = list(cam1data.columns.get_level_values('bodyparts').unique())
    
    # make new column names
    nvar = len(pointnames)
    pointnames = [item for item in pointnames for repetitions in range(4)]
    post = ["_cam1_X", "_cam1_Y", "_cam2_X", "_cam2_Y"]*nvar
    cols = [m+str(n) for m,n in zip(pointnames,post)]


    # remove likelihood columns
    cam1data = cam1data.drop(cam1data.columns[2::3],axis=1)
    cam2data = cam2data.drop(cam2data.columns[2::3],axis=1)

    # replace col names with new indices
    c1cols = list(range(0,cam1data.shape[1]*2,4)) + list(range(1,cam1data.shape[1]*2,4))
    c2cols = list(range(2,cam1data.shape[1]*2,4)) + list(range(3,cam1data.shape[1]*2,4))
    c1cols.sort()
    c2cols.sort()
    cam1data.columns = c1cols
    cam2data.columns = c2cols

    df = pd.concat([cam1data,cam2data],axis=1).sort_index(axis=1)
    df.columns = cols
    df.to_hdf(h5_save_path, key="df_with_missing", mode="w")
    df.to_csv(csv_save_path,na_rep='NaN',index=False)



def analyze_xromm_videos_external_model(path_data_to_analyze,cam1_model2use, cam2_model2use,path_models,save_video_flag=False):
    #modified from xrommtools by Laurence-Chasen
#INPUTS:
    #path_data_to_analyze = parent folder organized as follows
            # path_data_to_analyze
            #   - trial1
            #       - trial1-cam1.avi
            #       - trial1-cam2.avi
            #   - trial2
            #       - trial2-cam1.avi
            #       - trial2-cam2.avi
    #cam1_model2use = 1 or 2, which model is most like your cam1 videos. 
    #                 1 = if your cam1 videos have the animal’s RIGHT hindlimb 
    #                     to the LEFT SIDE of the left hindlimb with 
    #                     the animal walking to the left of the frame.
    #                 2 = if your cam1 videos have the animal's RIGHT hindlimb
    #                     to the RIGHT SIDE of the left hindlimb with 
    #                     the animal walking to the left of the frame.  
    #cam2_model2use = same as cam1_model2use but for your cam2 videos. 
    #path_models = path to parent folder containing the unzipped contents of
    #              xray_rat_hindlimb-cam1.tar.gz and xray_rat_hindlimb-cam2.tar.gz
    #save_video_flag = True or False, if True, a labeled video will be generated. WARNING: this will be slow

    #Example
    #analyze_xromm_videos_external_model("/Users/nathan/Documents/Data/Xray-Videos/Collection1",
    #                                    1, 2, 
    #                                    "/Users/nathan/Documents/Data/xray_rat_hindlimb-distributed_models",False)

    # analyze videos
    cameras = [1,2]
    subs =[["c01","c1","C01","C1","Cam1","cam1","Cam01","cam01","Camera1","camera1"],["c02","c2","C02","C2","Cam2","cam2","Cam02","cam02","Camera2","camera2"]]
    vidTypes = [".avi", ".mp4"]
    trialnames = os.listdir(path_data_to_analyze)
    
    models2use = [cam1_model2use, cam2_model2use]
    modelNames = ["DLC_xray_rat_hindlimb_cam1_resnet_50_iteration-0_shuffle-1", "DLC_xray_rat_hindlimb_cam2_resnet_50_iteration-0_shuffle-1"]

    for trialnum,trial in enumerate(trialnames):
        if not trial.startswith('.'): #ignoring hidden files in the directories
            trialpath = path_data_to_analyze + "/" + trial
            contents = os.listdir(trialpath)
            savepath = trialpath + "/" + "Labels"
            if os.path.exists(savepath):
                temp = os.listdir(savepath)
                if temp:
                    raise ValueError('There are already predicted points in the Labels subfolders')
            else:
                os.makedirs(savepath) # make new folder
            # get video file
            for camera in cameras:
                file = []
                for name in contents:
                    if any(x in name for x in subs[camera-1]) and any(y in name for y in vidTypes):
                        #if filename has appropriate camera text and is a video file
                        file = name
                if not file:
                    raise ValueError('Cannot locate %s video file' %trial)
                    
                #picking the model to use
                thisModel = models2use[camera-1]
                thisModelPath = path_models + "/" + modelNames[thisModel-1]
                
                video = trialpath + "/" + file
                #analyze video
                benchmark_videos(thisModelPath,
    		 	   	video,
    				n_frames=0,
    				save_poses=True,
    				#output=savepath, #including the output path causes crashes on some machines
    				save_video=save_video_flag)
                #moving the generated file
                thisOutputFile = os.path.splitext(video)[0] + "_DLCLIVE_POSES.h5"
                thisOutputFileBase = os.path.basename(thisOutputFile)
                thisOutputFileNewHome = savepath + "/" + thisOutputFileBase
                os.rename(thisOutputFile, thisOutputFileNewHome)
    
            # get filenames and read analyzed data
            contents = os.listdir(savepath)
            datafiles = [s for s in contents if '.h5' in s]
            if not datafiles:
                raise ValueError('Cannot find predicted points. Some wrong with DeepLabCut?')
            cam1data = pd.read_hdf(savepath+"/"+datafiles[0])
            cam2data = pd.read_hdf(savepath+"/"+datafiles[1]) 
            dlc_to_xma(cam1data,cam2data,trial,savepath) #converting to XMALab format     



