import numpy as np
from scipy.ndimage import median_filter

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

