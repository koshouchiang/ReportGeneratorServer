import numpy as np
from scipy.ndimage import median_filter

def BaselineRemove(ecgs, pulse_thr=1000):
    '''
    Perform baseline removal on an 1-D array.
    
    Apply a pulse filter to the input array using a threshold given by pulse_thr. 
    The filtered pulse will padded by previous value.
    
    Parameters:
      ecg: list
          A list of input ecg signal.
      pulse_thr: float, optional
          A threshold for pulse filter to detect a pulse. The pulse would be padded by previous value. Number of pulse_thr should be positive. Default number is 1000.
    
    Returns:
      out: list
          A list the same size as input list containing the result.
    '''

    ecgs = np.array(ecgs, dtype='int32')

    # Remove Baseline
    baseline = median_filter(ecgs, size=int(0.2*250), mode='nearest')
    baseline = median_filter(baseline, size=int(0.6*250), mode='nearest')
    ecg_filt = ecgs - baseline

    # Remove Pulse
    Diff = np.diff(ecg_filt)
    pulseIdx = np.argwhere(abs(Diff) > pulse_thr).flatten()
    if len(pulseIdx) > 0:
        for idx in pulseIdx:
            ecg_filt[idx+1] = ecg_filt[idx]

    return ecg_filt.tolist()

def Rescaling(ecgs):
    '''
    Rescale the magnitude of input ecg signal.

    Parameters:
        ecgs: list
            A list of input signal.
    Returns:
        ecg_rescale: list
            A list of rescaled signal with same length of input.
    '''

    ecgs = np.array(ecgs)
    scale = 1
    if 300 >= max(ecgs) > 150:
        scale = 2
    elif 150 >= max(ecgs):
        scale = 4
    else:
        scale = 1
    ecg_rescale = ecgs * scale

    return ecg_rescale.tolist()
