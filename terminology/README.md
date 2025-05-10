# terminology/README.md
# 專業術語資料庫

此目錄用於保存專業術語的定義文件。

- 文件格式支持CSV和JSON
- 文件名將作為該術語集的領域名稱（例如：physics.csv代表物理領域術語）
- 使用template_csv.csv或template_json.json作為模板來添加新術語

您也可以使用以下命令自動從PDF中提取術語：

```bash
python -m src.main --extract-terms
```

提取的術語將保存為`extracted_terms.json`，您可以根據需要編輯和分類這些術語。