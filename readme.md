**分支定義**
- master :　主要開發環境, win10主機
- test : github CI Testing
- develop : ubuntu 18.04 主機(NO GPU)
- release : ubuntu 18.04 主機(GPU)

pip freeze > requirements.txt


### API擴充筆記
- 新增API對象 -> 擴充REQUEST_INSTANCE_MAP
**Health Server Request**
- 新增報告種類 -> 擴充algorithm_setting_map
- 新增post API -> 擴充data_completed_map