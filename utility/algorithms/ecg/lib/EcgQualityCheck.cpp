#include <cmath>
#include "EcgQualityCheck.h"
#include <vector>
#include <math.h>
#include <numeric>
#include <algorithm>
#include <iterator> 

////using std::vector;


int EcgQualityCheck_version() { return 001; };


//// Correlation Coefficient Calculation //
double corrcoef(std::vector<int>& X, std::vector<int>& Y, int n)
{
	double sum_X = 0, sum_Y = 0, sum_XY = 0;
	double squareSum_X = 0, squareSum_Y = 0;
	int X_Value = 0;
	int Y_Value = 0;
	for (int i = 0; i < n; i++)
	{
		X_Value = X.at(i);
		Y_Value = Y.at(i);

		// sum of elements of array X. 
		sum_X += X_Value;

		// sum of elements of array Y. 
		sum_Y += Y_Value;

		// sum of X[i] * Y[i]. 
		sum_XY += X_Value * Y_Value;

		// sum of square of array elements.

		squareSum_X += X_Value * X_Value;
		squareSum_Y += Y_Value * Y_Value;
	}

	// use formula for calculating correlation coefficient. 
	double corr = (double)(n * sum_XY - sum_X * sum_Y)
		/ sqrt((n * squareSum_X - sum_X * sum_X)
			* (n * squareSum_Y - sum_Y * sum_Y));

	return corr;
}


//// Pattern Clustering by CC //
double PatternCluster(std::vector<int>& Label, std::vector<std::vector<int> >& Pattern, double TH, std::vector<int>& BeatFlagArray)
{

	// 檢查輸入
	if (Label.size() == 0)
		return 0;
	if (Pattern.size() <= 1)
		return 0;
	if (TH < 0 || TH > 1)
		return 0;

	int N = Pattern.size(); // Number of Patterns	      

	// 計算Pattern彼此之間的CC
	std::vector<std::vector<int> > V; //各Pattern之間的關聯性群集
	std::vector<int> L; //各個V對應的數量
	for (int i = 0; i < N; i++) {
		std::vector<int> v;
		for (int j = 0; j < N; j++) {
			if (Pattern.at(i).empty() || Pattern.at(j).empty()) {
				continue;
			}

			double cc = corrcoef(Pattern.at(i), Pattern.at(j), Pattern.at(i).size());

			// 大於threshold，則視j與i有關聯性
			if (cc > TH)
				v.push_back(j);
		}

		// 紀錄第i個pattern與哪些pattern有關聯性
		if (v.size() > 1) {
			V.push_back(v);
			L.push_back(v.size());
		}
	}


	// 如果Pattern間皆無關聯性或Pattern為空，則返回
	if (V.empty()) {
		return 0;
	}

	// 將V按照對應的長度L排序	
	std::vector<int> Lidx(L.size());
	iota(Lidx.begin(), Lidx.end(), 0); //Lidx為L的原始indices
	auto comparator = [&L](int a, int b) {return L[a] > L[b]; }; //自訂排序方式:依照長度L的大小排序
	sort(Lidx.begin(), Lidx.end(), comparator); //排序Lidx		
	std::vector<std::vector<int> > Vsort; //Vsort為已排序的V
	for (int i = 0; i < Lidx.size(); i++)
		Vsort.push_back(V.at(Lidx[i]));


	// 交叉比對分群關係至Relation中
	std::vector<std::vector<int> > Relation;
	for (int i = 0; i < Vsort.size(); i++) {
		// 將有最多關聯性的群集V擺在Relation中的第一個
		if (Relation.empty())
			Relation.push_back(Vsort.at(i));
		else {
			for (int j = 0; j < Relation.size(); j++)
			{
				std::vector<int> inter;
				set_intersection(Relation.at(j).begin(), Relation.at(j).end(),
					Vsort.at(i).begin(), Vsort.at(i).end(), back_inserter(inter));
				//如果有交集，更新該Relation類別
				if (inter.size() >= 1) {
					std::vector<int> U;
					set_union(Relation.at(j).begin(), Relation.at(j).end(),
						Vsort.at(i).begin(), Vsort.at(i).end(), back_inserter(U));
					Relation.at(j).assign(U.begin(), U.end());
					continue;
				}
				//如果Vsort[i]與所有Relation皆無交集，加入新的Relation類別
				if (inter.empty() && j == Relation.size() - 1) {
					Relation.push_back(Vsort.at(i));
				}

			}
		}
	}


	///// 整理Relation之間的重複元素
	int rep_flag = 0;
	int RelationSize = Relation.size();
	for (int i = 0; i < RelationSize; i++)//// Relation.size()
	{
		for (int j = 0; j < RelationSize; j++) ///Relation.size()
		{
			if (i == j) {
				continue;
			}

			//計算兩兩差集
			std::vector<int> Di;
			set_difference(Relation.at(i).begin(), Relation.at(i).end(),
				Relation.at(j).begin(), Relation.at(j).end(), back_inserter(Di));
			std::vector<int> Dj;
			set_difference(Relation.at(j).begin(), Relation.at(j).end(),
				Relation.at(i).begin(), Relation.at(i).end(), back_inserter(Dj));
			// 無交集則繼續
			if (Di.size() == Relation[i].size() && Dj.size() == Relation[j].size()) {
				continue;
			}
			// Relation間有重複元素的話，計算重複元素的占比，從占比較小的刪除
			else {
				rep_flag = 1;
				double Pi = (double)Di.size() / Relation[i].size();
				double Py = (double)Dj.size() / Relation[j].size();
				if (Pi > Py)
					Relation.at(i).assign(Di.begin(), Di.end());
				else
					Relation.at(j).assign(Dj.begin(), Dj.end());
			}
		}
	}


	///// 如果有重複，重新整理排列群集
	if (rep_flag == 1) {
		std::vector<int> Lidx(Relation.size());
		iota(Lidx.begin(), Lidx.end(), 0);
		auto comparator = [&Relation](int a, int b) {return Relation[a].size() > Relation[b].size(); };
		sort(Lidx.begin(), Lidx.end(), comparator);

		std::vector<std::vector<int> > sortedRelation;
		for (int i = 0; i < Lidx.size(); i++)
			sortedRelation.push_back(Relation.at(Lidx[i]));
		Relation = sortedRelation;
	}

	// 輸出分群結果
	RelationSize = Relation.size();
	for (int i = 0; i < RelationSize; i++)
	{
		for (int j = 0; j < Relation[i].size(); j++) {
			Label[Relation.at(i).at(j)] = i + 1;
		}
	}

	//// 計算各群集所占比例Per
	double Total = Pattern.size();

	///std::vector<double> Per;
	RelationSize = Relation.size();
	double per = 0.0;
	double Total_per = 0.0;
	int PassGroupIndex = 0;
	for (int i = 0; i < RelationSize; i++)
	{
		per = Relation[i].size() / Total;
		if (per >= 0.2) ////占比大於0.2視為正確的Beat群，才加總
		{
			Total_per += per;
			PassGroupIndex = i + 1;
		}

		///Per.push_back(per);
	}

	for (int i = 0; i < N; i++)
	{
		if (Label[i] > 0 && Label[i] <= PassGroupIndex)
			BeatFlagArray.push_back(1);
		else
			BeatFlagArray.push_back(0);
	}

	return Total_per; //// Per.front();
}


double EcgQualityCheck(int* ECGArr, int ECGLen, int* RidxsArr,int RidxLen, int RRIq1,double CCThr)
{
    std::vector<int> ECG;
    std::vector<int> Ridxs;
    std::vector<int> BeatFlagArray;
	
	for (int i=0;i< ECGLen;i++)
		ECG.push_back(ECGArr[i]);

	for (int i = 0; i < RidxLen; i++)
		Ridxs.push_back(RidxsArr[i]);

	

    if (Ridxs.empty()) {
        ////printf("There's no R peaks.\n");
        return false;
    }

    int beforeR = int(0.33 * 0.6 * RRIq1); 
    int afterR = int(0.67 * 0.6 * RRIq1);  

    int Len = beforeR + afterR;          
    int ignore_count = 0;

   
    std::vector<std::vector<int>> Beats(Ridxs.size());
    int N = Ridxs.size();
    for (int i = 0; i < N; i++) {
        int Ridx = Ridxs.at(i);
        
        std::vector<int> beat;
        beat.reserve(Len);
        for (int j = Ridx - beforeR; j <= Ridx + afterR; j++) 
        {
            if (j < 0) 
                beat.push_back(ECG.at(0));
            else if (j >= ECG.size()) 
                beat.push_back(ECG.at(ECG.size() - 1));
            else
                beat.push_back(ECG.at(j));
        }

        Beats[i] = beat;
    }

    std::vector<int> Label(Ridxs.size());
    double MaxGroupPer = PatternCluster(Label, Beats, CCThr, BeatFlagArray);
	return MaxGroupPer;

	/*
	if (BeatFlagArray.size() >= 3)   
    {
        for (int k = 1; k < BeatFlagArray.size() - 1; k++) 
        {
            if (BeatFlagArray.at(k) == 0)
                return false;

        }
    }
    else 
    {
        return false;
    }

    if (MaxGroupPer >= 0.66) 
        return true;
    else
        return false;
	*/
}


