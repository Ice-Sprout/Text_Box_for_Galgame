import requests
import json
import os
import time
from typing import Literal, Optional, List
import sys


# ===== Resource helper: prefer `resource/` next to exe/script =====
def _resource_path(relative_path: str) -> str:
    exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else None
    script_dir = os.path.dirname(os.path.abspath(__file__))
    candidates = []
    if exe_dir:
        candidates.append(os.path.join(exe_dir, 'resource'))
    candidates.append(os.path.join(script_dir, 'resource'))
    for base in candidates:
        candidate = os.path.join(base, relative_path)
        # if file exists or base exists, return resolved path (caller will check existence when needed)
        if os.path.exists(candidate) or os.path.exists(base):
            return candidate
    # fallback to script dir
    return os.path.join(script_dir, relative_path)

# 情绪配置常量
EMOTION_COUNT = 15  # 情绪总数
DEFAULT_EMOTION = 1  # 默认情绪（开心）
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

# 历史对话配置
MAX_HISTORY_COUNT = 10  # 最大保存历史对话条数（避免Prompt过长）
# 历史对话持久化文件 - 优先放到 resource/ 下，便于随 release 一起分发并保持可编辑。
HISTORY_FILE = _resource_path("chat_history.json")

# ========== 读取API Key ==========
API_KEY = ""  # 初始化API Key

# 优先从 resource/api.txt 读取，其次从脚本目录下的 api.txt
api_txt_path = _resource_path("api.txt")
try:
    with open(api_txt_path, "r", encoding="utf-8") as f:
        lines = f.readlines()
        if len(lines) < 4:
            print(f"错误：{api_txt_path} 文件行数不足，至少需要4行配置")
        else:
            enable_flag = lines[1].strip("\n").strip().lower()
            if enable_flag == "true":
                API_KEY = lines[3].strip("\n").strip()
                if not API_KEY:
                    print("警告：API key is empty，请在api.txt文件的第四行输入您的API Key")
                else:
                    print("API key loading successful，已加载有效API Key")
            else:
                print("API key loading is skipped，配置为不加载API Key")
except FileNotFoundError:
    print(f"警告：未找到{api_txt_path}，若需启用API请把 api.txt 放到 resource/ 或脚本目录下")
except PermissionError:
    print(f"错误：没有读取{api_txt_path}文件的权限，请检查文件权限设置")
except Exception as e:
    print(f"读取API Key时发生未知错误：{str(e)}")


class EmotionAnalyzer:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or API_KEY
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 创建会话池，复用TCP连接以减少延迟
        self.session = requests.Session()
        
        # 配置连接池参数
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,      # 连接池数量
            pool_maxsize=20,          # 最大连接数
            max_retries=3,            # 重试次数
            pool_block=False          # 非阻塞模式
        )
        self.session.mount('https://', adapter)
        
        # 新增：历史对话存储（格式：[("用户文本1", 情绪编号1), ("用户文本2", 情绪编号2), ...]）
        self.chat_history: List[tuple[str, int]] = []
        # 初始化时加载持久化的历史对话
        self.load_history_from_file()

    def __del__(self):
        """析构函数，关闭会话池"""
        if hasattr(self, 'session'):
            self.session.close()

    def analyze_emotion(self, text: str) -> int:
        """
        分析文本情绪（结合历史对话），返回1-15的情绪编号
        分析后自动将当前文本和情绪加入历史对话
        """
        if not text or not text.strip():
            emotion_id = DEFAULT_EMOTION
            self.add_to_history(text, emotion_id)  # 空文本也加入历史（可选）
            return emotion_id

        try:
            # 构建带历史上下文的Prompt
            prompt = self._build_emotion_prompt(text)
            response = self._call_deepseek_api(prompt)
            emotion_id = self._parse_emotion_response(response)
            # 新增：将当前文本和情绪加入历史对话
            self.add_to_history(text, emotion_id)
            # 保存历史对话到文件（可选）
            self.save_history_to_file()
            return emotion_id

        except Exception as e:
            print(f"情绪分析失败: {e}，使用默认情绪")
            emotion_id = DEFAULT_EMOTION
            self.add_to_history(text, emotion_id)
            return emotion_id

    def _build_emotion_prompt(self, text: str) -> str:
        """构建带历史对话上下文的情绪分析Prompt"""
        # 拼接历史对话字符串
        history_str = ""
        if self.chat_history:
            history_str = "【历史对话上下文】\n"
            for idx, (history_text, history_emotion) in enumerate(self.chat_history[:-1]):  # 排除当前文本（还未分析）
                emotion_name = EMOTION_MAPPING.get(history_emotion, "未知")
                history_str += f"{idx + 1}. 文本：{history_text} → 情绪：{emotion_name}（{history_emotion}）\n"
            history_str += "\n"

        # 核心Prompt：结合历史上下文分析当前文本情绪
        prompt = f"""请结合
【历史对话上下文】和【当前文本】，分析用户情绪变化，选择最匹配的情绪编号。

情绪编号对应：
1-平静, 2-开心, 3-惊讶, 4-气恼, 5-看乐子/开玩笑, 6-伤心, 7-尴尬, 8-慌乱, 9-卖萌, 10-认真, 11-疲劳/鄙夷, 12-疑惑, 13-悲伤, 14-哭泣, 15-愤怒

关键分析原则：
- 当前文本判断权重占比0.8，历史占比0.2
- 避免惯性思维，每次都要重新评估文本情绪
- 只返回数字，不要其他内容

【历史文本】{history_str}
【当前文本】：{text}
【情绪编号】："""
        return prompt

    def _call_deepseek_api(self, prompt: str) -> str:
        """调用DeepSeek API，使用会话池优化"""
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 10,
            "temperature": 0.1,
            "top_p": 0.9
        }

        try:
            # 使用会话池进行请求，复用TCP连接
            response = self.session.post(
                self.base_url,
                headers=self.headers,
                json=payload,
                timeout=10
            )

            if response.status_code != 200:
                raise Exception(f"API请求失败: {response.status_code}，响应：{response.text}")

            result = response.json()
            return result['choices'][0]['message']['content'].strip()
            
        except requests.exceptions.ConnectionError as e:
            # 连接错误时，重置会话以清除可能的无效连接
            print(f"连接错误，重置会话池: {e}")
            self._reset_session()
            raise
        except Exception as e:
            raise Exception(f"API调用失败: {e}")

    def _reset_session(self):
        """重置会话池，用于处理连接问题"""
        if hasattr(self, 'session'):
            self.session.close()
        
        # 重新创建会话池
        self.session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=3,
            pool_block=False
        )
        self.session.mount('https://', adapter)

    def _parse_emotion_response(self, response_text: str) -> int:
        """解析API返回的情绪编号"""
        import re
        numbers = re.findall(r'\d+', response_text)

        if not numbers:
            return DEFAULT_EMOTION

        emotion_id = int(numbers[0])

        # 验证情绪编号在有效范围内
        if 1 <= emotion_id <= EMOTION_COUNT:
            print(f"情绪编号：{emotion_id}")
            return emotion_id
        else:
            return DEFAULT_EMOTION

    # ========== 新增：历史对话管理方法 ==========
    def add_to_history(self, text: str, emotion_id: int) -> None:
        """添加对话到历史，自动限制最大条数"""
        self.chat_history.append((text.strip(), emotion_id))
        # 超过最大条数时，删除最早的对话
        if len(self.chat_history) > MAX_HISTORY_COUNT:
            self.chat_history.pop(0)

    def clear_history(self) -> None:
        """清空历史对话"""
        self.chat_history = []
        self.save_history_to_file()  # 同步清空文件
        print("历史对话已清空")

    def get_history(self) -> List[tuple[str, int]]:
        """获取历史对话"""
        return self.chat_history.copy()

    # ========== 可选：历史对话持久化（保存到文件） ==========
    def save_history_to_file(self) -> None:
        """将历史对话保存到JSON文件"""
        try:
            history_data = [
                {
                    "text": text,
                    "emotion_id": emotion_id,
                    "emotion_name": EMOTION_MAPPING.get(emotion_id, "未知"),
                    "timestamp": time.time()  # 记录时间戳
                }
                for text, emotion_id in self.chat_history
            ]
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(history_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"保存历史对话失败: {e}")

    def load_history_from_file(self) -> None:
        """从JSON文件加载历史对话"""
        if not os.path.exists(HISTORY_FILE):
            return
        try:
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                history_data = json.load(f)
            # 转换为原有的元组格式
            self.chat_history = [
                (item["text"], item["emotion_id"])
                for item in history_data
                if "text" in item and "emotion_id" in item
            ]
            print(f"成功加载{len(self.chat_history)}条历史对话")
        except Exception as e:
            print(f"加载历史对话失败: {e}")


# 全局实例
emotion_analyzer = EmotionAnalyzer()


# 对外接口
def get_emotion_from_text(text: str) -> int:
    """对外接口：从文本获取情绪编号（结合历史对话）"""
    return emotion_analyzer.analyze_emotion(text)


def get_emotion_name(emotion_id: int) -> str:
    """根据情绪编号获取情绪名称"""
    return EMOTION_MAPPING.get(emotion_id, "未知情绪")


# 新增对外接口：历史对话管理
def add_chat_history(text: str, emotion_id: int) -> None:
    """外部添加历史对话"""
    emotion_analyzer.add_to_history(text, emotion_id)


def clear_chat_history() -> None:
    """外部清空历史对话"""
    emotion_analyzer.clear_history()


def get_chat_history() -> List[tuple[str, int]]:
    """外部获取历史对话"""
    return emotion_analyzer.get_history()