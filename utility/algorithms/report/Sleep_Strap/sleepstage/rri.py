import numpy as np
import hrvanalysis as hrv

def filter(Ridxs, Fs, minThr, maxThr):
    RRI = np.diff(Ridxs)*1000/Fs
    RRIs = [int(rri) for rri in RRI if rri>minThr and rri<maxThr]
    Med = np.median(RRIs)
    NNIs = [rri for rri in RRIs if rri>=0.45*Med and rri<=1.62*Med]
    return NNIs

def nni_filter(Ridxs, Fs):
    RRI = np.diff(Ridxs)*1000/Fs
    RRIs = [int(rri) for rri in RRI if rri>300 and rri<2000]
    NNIs = []
    if len(RRIs) > 0:
        for i in range(1,len(RRIs)):
            rr_spread = abs((RRIs[i-1]-RRIs[i])/RRIs[i-1])
            if rr_spread < 0.3:
                NNIs.append(RRIs[i])
    return NNIs

def get_features(NNIs, feature_list):
    feature = {}
    if feature_list['time']:
        feature.update(hrv.get_time_domain_features(NNIs))
    if feature_list['freq']:
        feature.update(hrv.get_frequency_domain_features(NNIs))
    if feature_list['poincare']:
        feature.update(hrv.get_poincare_plot_features(NNIs))
    
    feature_name = list(feature.keys())
    feature_value = [float(num) for num in feature.values()]
    return feature_name, feature_value