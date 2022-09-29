#pragma once

#ifdef MYDLL_EXPORTS
#define MYDLL_API
#else
#define MYDLL_API
#endif

// ­pºâ¼Ú¤ó¶ZÂ÷¡]Euclidean Distance¡^¨ç¼Æ
extern "C" MYDLL_API double EcgQualityCheck(int* ECGArr, int ECGLen, int* RidxsArr, int RidxLen, int RRIq1,double CCThre);
extern "C" MYDLL_API int EcgQualityCheck_version();
