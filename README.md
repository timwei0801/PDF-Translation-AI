# README.md
# 生成式AI應用：專業PDF英譯中系統

本專案是一個使用Claude API的專業PDF英譯中翻譯系統，專為翻譯學術論文和專業期刊設計，能夠處理專業術語、數學公式和圖表等特殊元素。

## 功能特色

- **PDF內容解析**：自動識別和分離文本、公式、表格和圖像
- **專業術語處理**：使用RAG（檢索增強生成）確保專業術語翻譯一致性
- **數學公式處理**：保留公式結構，僅翻譯文字部分
- **圖表處理**：識別並翻譯圖表中的文字
- **雙語對照PDF**：生成原文+譯文對照的PDF文件
- **MCP協議整合**：自動從翻譯內容生成PPT演示文稿

## 快速開始

### 安裝

1. 克隆此專案：
```bash
git clone https://github.com/yourusername/pdf-translator.git
cd pdf-translator
```

2. 安裝依賴：
```bash
pip install -e .
```

3. 配置API密鑰：
```bash
cp .env.example .env
# 編輯.env文件，添加您的Anthropic API密鑰
```

### 使用方法

1. 將英文PDF文件放入`raw_pdfs`目錄

2. 運行翻譯：
```bash
python -m src.main
```

3. 查看結果：
   - 翻譯後的PDF將保存在`translated_pdfs`目錄
   - 生成的PPT將保存在`presentations`目錄

### 自定義專業術語

1. 使用模板添加專業術語：
```bash
# 編輯 terminology/your_domain.csv 或 terminology/your_domain.json
```

2. 自動提取術語：
```bash
python -m src.main --extract-terms
```

## 系統架構

本系統由四個主要模組組成：

1. **PDF處理器**：負責解析PDF文件，提取結構化內容
2. **專業術語RAG**：管理專業術語資料庫，確保翻譯一致性
3. **Claude翻譯器**：使用Claude API進行高質量翻譯
4. **MCP PPT生成器**：使用多模態對話協議自動生成演示文稿

## 參與貢獻

歡迎提交問題報告和改進建議。如果您想貢獻程式碼，請遵循以下步驟：

1. Fork此專案
2. 創建您的功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交您的更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 打開Pull Request

## 授權協議

本專案基於MIT授權協議 - 詳見 [LICENSE](LICENSE) 文件

## 致謝

- Anthropic的Claude API提供強大的翻譯能力
- SentenceTransformers提供多語言嵌入模型
- PyMuPDF和PDFPlumber提供PDF處理功能