# config.py 或主程式開頭
import os
from dotenv import load_dotenv

# 加載 .env 檔案中的環境變數
load_dotenv()

# 獲取環境變數
API_KEY = os.getenv("CLAUDE_API_KEY")
API_URL = os.getenv("CLAUDE_API_URL")
MODEL_NAME = os.getenv("MODEL_NAME")

# 驗證環境變數是否存在
if not API_KEY:
    raise ValueError("未設定 CLAUDE_API_KEY 環境變數。請在 .env 檔案中設定。")

# 設置Anthropic API密鑰
os.environ["ANTHROPIC_API_KEY"] = "your-api-key-here"

# 初始化客戶端
client = anthropic.Anthropic()

# 基本配置
CONFIG = {
    "model": "claude-3-5-sonnet-20240620",  # 使用Claude 3.5 Sonnet模型
    "max_tokens": 4000,  # 單次回應的最大標記數
    "temperature": 0.1,  # 較低的溫度確保一致性
    "terminology_path": "terminology/terminology_mapping.csv",  # 術語對照表路徑
    "extracted_folder": "extracted_text",  # 提取文本的文件夾
    "translation_folder": "translations"  # 翻譯結果的文件夾
}