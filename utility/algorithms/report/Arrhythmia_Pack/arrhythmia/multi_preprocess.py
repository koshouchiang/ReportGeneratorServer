import numpy as np
from ..ecg.baseline import BaselineRemove
from .irregular_v1 import Irregular

# A global dictionary storing the variables passed from the initializer.
var_dict = {}

def init_worker(X, X_shape):
    # Using a dictionary is not strictly necessary. You can also
    # use global variables.
    var_dict['X'] = X
    var_dict['X_shape'] = X_shape

def segment_preprocess(i):
    # Simply computes the sum of the i-th row of the input matrix X
    X_np = np.frombuffer(var_dict['X']).reshape(var_dict['X_shape'])
    ecg = X_np[i]
    # Remove Baseline and Pulse
    ecg_filt = BaselineRemove(ecg)
    # Check Output Length
    if len(ecg_filt) < 2500:
        output = np.zeros(2500)
        output[:len(ecg_filt)] = ecg_filt
    else:
        output = ecg_filt[:2500]
    return output.tolist()

def EcgAnalysis(idx):
    # Get data from shared memory
    X_np = np.frombuffer(var_dict['X']).reshape(var_dict['X_shape'])
    sig = X_np[idx]

    # Detect irregularity
    results = Irregular(idx,sig)
    return results