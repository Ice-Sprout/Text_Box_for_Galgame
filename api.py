import requests
import json
import os
from typing import Literal, Optional

# 情绪配置常量
EMOTION_COUNT = 15  # 情绪总数
DEFAULT_EMOTION = 2  # 默认情绪（开心）
EMOTION_MAPPING = {
    1: "平静",
    2: "开心", 
    3: "惊讶",
    4: "气恼",
    5: "看乐子/开玩笑",
    6: "伤心",
    7: "尴尬", 
    8: "慌乱",
    9: "卖萌",
    10: "认真",
    11: "疲劳/鄙夷",
    12: "疑惑", 
    13: "悲伤",
    14: "哭泣",
    15: "愤怒"
}

# 全局实例
emotion_analyzer = None

def init_emotion_analyzer(api_key: str = ""):
    """初始化情绪分析器"""
    global emotion_analyzer
    emotion_analyzer = EmotionAnalyzer(api_key)

class EmotionAnalyzer:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    
    def set_api_key(self, api_key: str):
        """设置API Key"""
        self.api_key = api_key
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
        print("API Key已更新")
    
    def analyze_emotion(self, text: str) -> int:
        """
        分析文本情绪，返回1-15的情绪编号
        如果识别失败，返回默认情绪2（平静）
        """
        if not text or not text.strip():
            return DEFAULT_EMOTION
        
        # 如果API Key为空，直接返回默认情绪
        if not self.api_key:
            print("API Key未设置，使用默认情绪")
            return DEFAULT_EMOTION
        
        try:
            # 构建提示词
            prompt = self._build_emotion_prompt(text)
            response = self._call_deepseek_api(prompt)
            emotion_id = self._parse_emotion_response(response)
            return emotion_id
            
        except Exception as e:
            print(f"情绪分析失败: {e}，使用默认情绪")
            return DEFAULT_EMOTION
    
    def _build_emotion_prompt(self, text: str) -> str:
        """构建情绪分析提示词"""
        return f"""请分析以下文本的情绪，并从1-15的数字中选择最匹配的情绪编号：
1-平静, 2-开心, 3-惊讶, 4-气恼, 5-看乐子/开玩笑, 6-伤心, 7-尴尬, 8-慌乱, 9-卖萌, 10-认真, 11-疲劳/鄙夷, 12-疑惑, 13-悲伤, 14-哭泣, 15-愤怒
文本情绪不明显时，返回2
示例：
文本："这游戏真好玩" -> 2  
文本："不是，哥们" -> 3
文本："你怎么能这样" -> 4
文本："杂鱼杂鱼" -> 5
文本："呜~我不想学了" -> 6
文本："额" -> 7
文本："啊啊啊吓死我了" -> 8
文本："略略略" -> 9
文本："好的，我知道了" -> 10
文本："累了，不想说话" -> 11
文本："嗯？怎么回事" -> 12
文本："呜呜呜，好难过" -> 13
文本："哥求你了，我给你道个歉，你把我当个屁放了吧" -> 14
文本："我真的生气了" -> 15

现在分析这个文本："{text}"
只返回数字，不要其他内容："""
    
    def _call_deepseek_api(self, prompt: str) -> str:
        """调用DeepSeek API"""
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 10,
            "temperature": 0.1
        }
        
        # 设置超时避免长时间等待
        response = requests.post(
            self.base_url, 
            headers=self.headers, 
            json=payload, 
            timeout=10
        )
        
        if response.status_code != 200:
            raise Exception(f"API请求失败: {response.status_code}")
        
        result = response.json()
        return result['choices'][0]['message']['content'].strip()
    
    def _parse_emotion_response(self, response_text: str) -> int:
        """解析API返回的情绪编号"""
        # 提取数字
        import re
        numbers = re.findall(r'\d+', response_text)
        
        if not numbers:
            return DEFAULT_EMOTION
        
        emotion_id = int(numbers[0])
        
        # 验证情绪编号在有效范围内
        if 1 <= emotion_id <= EMOTION_COUNT:
            return emotion_id
        else:
            return DEFAULT_EMOTION

# 初始化情绪分析器
init_emotion_analyzer()

def get_emotion_from_text(text: str) -> int:
    """对外接口：从文本获取情绪编号"""
    global emotion_analyzer
    if emotion_analyzer is None:
        init_emotion_analyzer()
    return emotion_analyzer.analyze_emotion(text)

def get_emotion_name(emotion_id: int) -> str:
    """根据情绪编号获取情绪名称"""
    return EMOTION_MAPPING.get(emotion_id, "未知情绪")

def set_api_key(api_key: str):
    """设置API Key"""
    global emotion_analyzer
    if emotion_analyzer is None:
        init_emotion_analyzer(api_key)
    else:
        emotion_analyzer.set_api_key(api_key)