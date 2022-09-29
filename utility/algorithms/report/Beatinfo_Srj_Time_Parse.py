# -*- coding: utf-8 -*-

import os
import sys
import tqdm
import json
import numpy as np
from scipy.interpolate import interp1d
from scipy.ndimage import median_filter

#import matplotlib.pyplot as plt

def document_process_(import_path, export_path):
    
    if not os.path.exists(export_path): os.makedirs(export_path)
    
    srj_files = [srj_file for srj_file in os.listdir(import_path) if srj_file.endswith('srj')]
    
    if not import_path.endswith("\\"): import_path = import_path + "//"
    if not export_path.endswith("\\"): export_path = export_path + "//"
    
    file_number = len(srj_files)
    
    print("[Progress] Parse Datas")

    with tqdm.tqdm(total=file_number,desc='  [進度]',file=sys.stdout) as pbar:
        
        for i, srj_file in enumerate(srj_files):
            #print("Processing File ({}/{}): {}".format(i+1, file_number, srj_file))
            file_process_(import_path + srj_file, export_path + srj_file)
            pbar.update()
            
def file_process_(import_file, export_file):
    
    with open(import_file) as f:
        srj_lines = f.readlines()
        f.close()
    
    srj_lines = abnormal_signal_remove_(srj_lines)
    srj_lines, srj_tts, srj_losts = abnormal_time_remove_(srj_lines)
    srj_lines, srj_tts = tt_fix_by_lost_zero_(srj_lines, srj_tts, srj_losts)
    #ecgs_x, ecgs_y, breaths_x, breaths_y, temps_x, temps_y, motions_x, motions_y = signal_list_concat_(srj_lines, srj_tts)
    
    #plt.figure(figsize=(100,30))
    #plt.plot(ecgs_y[:10000], linewidth=0.7)
    
    #ecgs_y = delete_impulse_(ecgs_y)
    #ecgs_y = BaselineRemove(ecgs_y)
    #ecgs_y = delete_impulse_(ecgs_y)
    
    #plt.figure(figsize=(100,30))
    #plt.plot(ecgs_y[:10000], linewidth=0.7)
    
    srj_lines = linear_250hz_interpolation_(srj_lines)
    
    export_string = ""
    
    for srj_line in srj_lines: export_string += str(srj_line).replace("\'","\"").replace(" ","") + '\n'
    
    with open(export_file, 'w') as f:
        f.write(export_string)
        f.close()
    
def abnormal_signal_remove_(srj_lines):
    
    #print("Data Segment Number: {}".format(len(srj_lines)))
    
    result_lines = []
    
    count = -1
    num_signal = -1
    
    abnormal_signal_number = 0
    
    while num_signal != 2500:
        abnormal_signal_number += 1
        count += 1
        num_signal = int(json.loads(srj_lines[count])["ecgno"])
    
    p_line = srj_lines[count]
    result_lines.append(p_line)
    
    for c_line in srj_lines[(count+1):]:
        
        if (int(json.loads(c_line)["tt"]) - int(json.loads(p_line)["tt"])) != 0 and int(json.loads(c_line)["ecgno"]) == 2500:
            result_lines.append(c_line)
        else :
            abnormal_signal_number += 1
        
        p_line = c_line
    
    #print("Abnormal Signal Number: {}".format(abnormal_signal_number))
    
    return result_lines

def abnormal_time_remove_(srj_lines):
    
    srj_tts = []
    srj_losts = []
    
    #data_segment_number = len(srj_lines)
    
    lost_zero_status_number = 0
    
    for srj_line in srj_lines:
        
        srj_json = json.loads(srj_line)
        srj_tts.append(srj_json["tt"])
        
        srj_lost = srj_json["lost"]
        
        if srj_lost == 0:
            lost_zero_status_number += 1
        
        srj_losts.append(srj_lost)
        
    srj_deltas = np.diff(np.array(srj_tts))
    
    abnormal_time_number = 0
    
    for i, srj_delta in enumerate(srj_deltas):
        
        if srj_delta > 11000 or srj_delta < 9000:
            srj_losts[i] = 1
            srj_losts[i+1] = 1
        
        if srj_delta > 30000:
            
            try :
                
                j = 1
                
                while srj_deltas[i+j] > 15000: j = j + 1
                
                if 9000 <= srj_deltas[i+j] <= 11000:
                    
                    abnormal_time_number += 1
                    
                    srj_losts[i] = 0
                    srj_losts[i+1] = 0
                    srj_signal = json.loads(srj_lines[i-1])["rows"]["ecgs"][-1]
                    srj_delay = json.loads(srj_lines[i])
                    srj_delay["rows"]["ecgs"] = [srj_signal]*2500
                    srj_lines[i] = json.dumps(srj_delay)
                    
            except : pass
        
    srj_losts[0] = 0
    srj_losts[-1] = 0
    
    #print("Abnormal Time Number: {}".format(abnormal_time_number))
    #print("Lost Zero Status Percentage: {:.2f}%".format(lost_zero_status_number/data_segment_number*100))
    
    return srj_lines, srj_tts, srj_losts

def tt_fix_by_lost_zero_(srj_lines, srj_tts, srj_losts):
    
    p_i = -1
    
    for i, srj_lost in enumerate(srj_losts):
        
        if srj_lost == 0:
            
            i_delta = i-p_i
            
            if p_i > -1 and i_delta > 1:
                
                tt_delta = (srj_tts[i]-srj_tts[p_i])/i_delta
                
                for j in range(1,i_delta):
                    srj_tts[p_i+j] = srj_tts[p_i] + tt_delta*j
            
            p_i = i
                
    for i, srj_tt in enumerate(srj_tts):         
        
        srj_segment = json.loads(srj_lines[i])
        srj_segment["tt"] = srj_tt
        srj_lines[i] = json.dumps(srj_segment)
        
    return srj_lines, srj_tts

def signal_list_concat_(srj_lines, srj_tts):
    
    srj_ecgs_y = []
    srj_breaths_y = []
    srj_temps_y = []
    srj_motions_y = []
    
    for srj_line in srj_lines:
        srj_ecgs_y.append(json.loads(srj_line)["rows"]["ecgs"])
        srj_breaths_y.append(json.loads(srj_line)["rows"]["breaths"])
        srj_temps_y.append(json.loads(srj_line)["rows"]["temps"])
        srj_motions_y.append(json.loads(srj_line)["rows"]["motions"])
        
    srj_ecgs_x = []
    srj_breaths_x = []
    srj_temps_x = []
    srj_motions_x = []
    
    p_tt = srj_tts[0]
    
    for c_tt, p_ecgs, p_breaths, p_temps, p_motions in zip(srj_tts[1:], srj_ecgs_y[:-1], srj_breaths_y[:-1], srj_temps_y[:-1], srj_motions_y[:-1]):
        
        srj_ecgs_x.append(np.linspace(p_tt, c_tt, num=len(p_ecgs), endpoint=False).tolist())
        srj_breaths_x.append(np.linspace(p_tt, c_tt, num=len(p_breaths), endpoint=False).tolist())
        srj_temps_x.append(np.linspace(p_tt, c_tt, num=len(p_temps), endpoint=False).tolist())
        srj_motions_x.append(np.linspace(p_tt, c_tt, num=len(p_motions), endpoint=False).tolist())
        
        p_tt = c_tt
    
    srj_tts_s = srj_tts[-1]
    srj_tts_e = srj_tts[-1] + 10021
    
    srj_ecgs_x.append(np.linspace(srj_tts_s, srj_tts_e, num=len(srj_ecgs_y[-1]), endpoint=False).tolist())
    srj_breaths_x.append(np.linspace(srj_tts_s, srj_tts_e, num=len(srj_breaths_y[-1]), endpoint=False).tolist())
    srj_temps_x.append(np.linspace(srj_tts_s, srj_tts_e, num=len(srj_temps_y[-1]), endpoint=False).tolist())
    srj_motions_x.append(np.linspace(srj_tts_s, srj_tts_e, num=len(srj_motions_y[-1]), endpoint=False).tolist())
    
    srj_ecgs_y = [y for ys in srj_ecgs_y for y in ys]
    srj_breaths_y = [y for ys in srj_breaths_y for y in ys]
    srj_temps_y = [y for ys in srj_temps_y for y in ys]
    srj_motions_y = [y for ys in srj_motions_y for y in ys]
    
    srj_ecgs_x = [x for xs in srj_ecgs_x for x in xs]
    srj_breaths_x = [x for xs in srj_breaths_x for x in xs]
    srj_temps_x = [x for xs in srj_temps_x for x in xs]
    srj_motions_x = [x for xs in srj_motions_x for x in xs]
    
    return srj_ecgs_x, srj_ecgs_y, srj_breaths_x, srj_breaths_y, srj_temps_x, srj_temps_y, srj_motions_x, srj_motions_y

def delete_impulse_(ecgs):
    
    ecgs_diff = np.diff(ecgs)
    diff_len = len(ecgs_diff) - 1
    
    j = 0
    
    for i, (ecg, ecg_diff) in enumerate(zip(ecgs[:-1], ecgs_diff)):
        
        if j == 0 :
        
            if ecg_diff < -500:
                
                j = 1
                
                while ecgs_diff[i+j] == 0 and i + j < diff_len: j += 1
                
                if ecgs_diff[i+j] > 500:
                    
                    for k in range(i+1,i+j+1): ecgs[k]=(ecgs[i]+ecgs[i+j+1])/2
        
            elif ecg_diff > 700:
                
                j = 1
                
                while ecgs_diff[i+j] == 0 and i + j < diff_len: j += 1
                
                if ecgs_diff[i+j] < -700:
                    
                    for k in range(i+1,i+j+1): ecgs[k]=(ecgs[i]+ecgs[i+j+1])/2
        else :
            
            j = j - 1
           
    return ecgs

def BaselineRemove(ecg):
    ecg = np.array(ecg, dtype='int32')
    '''
    # Remove Baseline
    baseline = median_filter(ecg, size=125, mode='constant', origin=-62)
    baseline = baseline[:len(baseline)-125] #去除median filter後面的padding
    ecg_filt = ecg[125:] - baseline
    '''
    # Remove Baseline
    baseline = median_filter(ecg, size=int(0.2*250), mode='nearest')
    baseline = median_filter(baseline, size=int(0.6*250), mode='nearest')
    ecg_filt = ecg - baseline

    # Remove Pulse
    Diff = np.diff(ecg_filt)
    pulseIdx = np.argwhere(abs(Diff) > 1000).flatten()
    if len(pulseIdx) > 0:
        for idx in pulseIdx:
            ecg_filt[idx+1] = ecg_filt[idx]

    return ecg_filt

def linear_250hz_interpolation_(srj_lines):
    
    for srj_i, srj_line in enumerate(srj_lines):
        
        srj_json = json.loads(srj_line)
        
        srj_motion = srj_json["rows"]["motions"]
        
        motion_num = len(srj_motion)
        
        new_srj_motion = []
        
        if 0 < motion_num < 20:
            
            new_srj_motion = srj_motion
            
            for i_motion in range( 20 - motion_num ):
                new_srj_motion.append(srj_motion[-1])
                
        elif motion_num == 20:
            
            new_srj_motion = srj_motion
            
        elif motion_num > 20:
            
            motion_T = np.array(srj_motion).T
            
            time_origin = np.linspace(1, 20, num=motion_num, endpoint=True)
            time_20 = np.linspace(1, 20, num=20, endpoint=True)
            
            motion_new = []
            
            for i_motion in range(10):
                
                motion_axis = motion_T[i_motion]
                f_axis = interp1d(time_origin, motion_axis, kind='linear')
                motion_axis_new = f_axis(time_20).tolist()
                motion_new.append(motion_axis_new)
            
            new_srj_motion = np.array(motion_new).T.tolist()
            
        srj_json["rows"]["motions"] = new_srj_motion
        
        srj_lines[srj_i] = json.dumps(srj_json)
     
    return srj_lines

if __name__ == '__main__':
    
    import_path = 'Data\\'
    export_path = 'Export\\'
    
    document_process_(import_path, export_path)