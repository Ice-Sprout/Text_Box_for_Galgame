# api.py
import requests
import json
import os
import time
import random
import re
from typing import Literal, Optional, List, Dict, Tuple
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
EMOTION_COUNT = 15  # 默认情绪总数
DEFAULT_EMOTION = 1  # 默认情绪（开心）

# 默认情绪映射（作为后备）
DEFAULT_EMOTION_MAPPING = {
    1: ["平静"],
    2: ["开心"],
    3: ["惊讶"],
    4: ["气恼"],
    5: ["看乐子", "开玩笑"],
    6: ["伤心"],
    7: ["尴尬"],
    8: ["慌乱"],
    9: ["卖萌"],
    10: ["认真"],
    11: ["疲劳", "鄙夷"],
    12: ["疑惑"],
    13: ["悲伤"],
    14: ["哭泣"],
    15: ["愤怒"]
}

# 历史对话配置
MAX_HISTORY_COUNT = 10  # 最大保存历史对话条数（避免Prompt过长）
# 历史对话持久化文件 - 优先放到 resource/ 下，便于随 release 一起分发并保持可编辑。
HISTORY_FILE = _resource_path("chat_history.json")

# ========== 从info.json读取API配置 ==========
def load_api_config() -> Dict:
    """从info.json加载API配置和情绪映射"""
    default_config = {
        "enable_api": False,
        "api_key": "",
        "characters": {},
        "emotion_mappings": {},  # 新增：存储所有角色的情绪映射
        "font_configs": {},      # 新增：字体配置
        "background_configs": {} # 新增：背景配置
    }
    
    # 尝试从info.json读取API配置
    info_json_path = _resource_path("info.json")
    try:
        if os.path.exists(info_json_path):
            with open(info_json_path, "r", encoding="utf-8") as f:
                info_data = json.load(f)
            
            result = {
                "enable_api": False,
                "api_key": "",
                "characters": {},
                "emotion_mappings": {},
                "font_configs": {},
                "background_configs": {}
            }
            
            # 检查是否有api_config部分
            if "api_config" in info_data:
                api_config = info_data["api_config"]
                result["enable_api"] = api_config.get("enable_api", False)
                result["api_key"] = api_config.get("api_key", "")
            
            # 加载角色和情绪映射
            if "characters" in info_data:
                result["characters"] = info_data["characters"]
                
                # 提取所有角色的情绪映射
                for char_name, char_config in info_data["characters"].items():
                    if "emotion_mapping" in char_config:
                        result["emotion_mappings"][char_name] = char_config["emotion_mapping"]
            
            # 加载字体配置
            if "font_configs" in info_data:
                result["font_configs"] = info_data["font_configs"]
            
            # 加载背景配置
            if "background_configs" in info_data:
                result["background_configs"] = info_data["background_configs"]
            
            # 加载默认背景
            if "DEFAULT_BACKGROUND" in info_data:
                result["default_background"] = info_data["DEFAULT_BACKGROUND"]
            
            return result
    except Exception as e:
        print(f"读取info.json配置失败: {e}")
    
    return default_config

# 全局API配置
API_CONFIG = load_api_config()
ENABLE_API = API_CONFIG.get("enable_api", False)
API_KEY = API_CONFIG.get("api_key", "")

# 新增：全局情绪映射
GLOBAL_EMOTION_MAPPINGS = API_CONFIG.get("emotion_mappings", {})
CHARACTERS_CONFIG = API_CONFIG.get("characters", {})
FONT_CONFIGS = API_CONFIG.get("font_configs", {})
BACKGROUND_CONFIGS = API_CONFIG.get("background_configs", {})
DEFAULT_BACKGROUND = API_CONFIG.get("default_background", "hoshishiro")

# 打印API配置状态
if ENABLE_API and API_KEY:
    print(f"API配置已启用，已加载API Key")
    print(f"已加载 {len(GLOBAL_EMOTION_MAPPINGS)} 个角色的情绪映射")
    print(f"已加载 {len(CHARACTERS_CONFIG)} 个角色配置")
elif ENABLE_API and not API_KEY:
    print("警告：API已启用但API Key为空，请在info.json中配置api_key")
else:
    print("API配置未启用")


class EmotionAnalyzer:
    def __init__(self, api_key: str = ""):
        self.api_key = api_key or API_KEY
        self.enable_api = ENABLE_API
        self.base_url = "https://api.deepseek.com/v1/chat/completions"
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 新增：存储所有角色的情绪映射
        self.role_emotion_mappings = GLOBAL_EMOTION_MAPPINGS.copy()
        
        # 新增：角色配置
        self.characters_config = CHARACTERS_CONFIG.copy()
        
        # 新增：当前角色（用于情绪分析）
        self.current_role = None
        
        # 新增：字体配置
        self.font_configs = FONT_CONFIGS.copy()
        
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
        
        # 新增：历史对话存储（格式：[("用户文本1", 情绪编号1, 角色1), ("用户文本2", 情绪编号2, 角色2), ...]）
        self.chat_history: List[Tuple[str, int, Optional[str]]] = []
        
        # 初始化时加载持久化的历史对话
        self.load_history_from_file()

    def __del__(self):
        """析构函数，关闭会话池"""
        if hasattr(self, 'session'):
            self.session.close()

    def analyze_emotion(self, text: str, role: Optional[str] = None) -> int:
        """
        分析文本情绪（结合历史对话），返回图片编号
        分析后自动将当前文本和情绪加入历史对话
        
        Args:
            text: 待分析的文本
            role: 角色名称，用于获取对应的情绪映射
        """
        if not text or not text.strip():
            emotion_id = 1  # 默认返回图片编号1
            self.add_to_history(text, emotion_id, role)
            return emotion_id
        
        # 如果API未启用，使用默认情绪
        if not self.enable_api or not self.api_key:
            print("API未启用或无API Key，使用默认情绪")
            emotion_id = 1  # 默认返回图片编号1
            self.add_to_history(text, emotion_id, role)
            return emotion_id

        try:
            # 设置当前角色
            self.current_role = role
            
            # 构建带历史上下文的Prompt
            prompt = self._build_emotion_prompt(text, role)
            response = self._call_deepseek_api(prompt)
            emotion_id = self._parse_emotion_response(response, role)
            
            # 新增：将当前文本和情绪加入历史对话
            self.add_to_history(text, emotion_id, role)
            
            # 保存历史对话到文件（可选）
            self.save_history_to_file()
            
            return emotion_id

        except Exception as e:
            print(f"情绪分析失败: {e}，使用默认情绪")
            emotion_id = 1  # 默认返回图片编号1
            self.add_to_history(text, emotion_id, role)
            return emotion_id

    def _build_emotion_prompt(self, text: str, role: Optional[str] = None) -> str:
        """构建带历史对话上下文的情绪分析Prompt"""
        # 拼接历史对话字符串
        history_str = ""
        if self.chat_history:
            history_str = "【历史对话上下文】\n"
            for idx, (history_text, history_emotion, history_role) in enumerate(self.chat_history[:-1]):  # 排除当前文本（还未分析）
                # 获取情绪名称（如果有角色特定的映射）
                emotion_name = self._get_emotion_name_by_id(history_emotion, history_role)
                history_str += f"{idx + 1}. 文本：{history_text} → 情绪：{emotion_name}（图片{history_emotion}）\n"
            history_str += "\n"

        # 根据角色获取情绪映射
        if role and role in self.role_emotion_mappings:
            # 使用角色特定的情绪映射
            emotion_mapping = self.role_emotion_mappings[role]
            emotion_list_str = self._format_emotion_mapping_for_prompt(emotion_mapping)
            emotion_instruction = "请从以下情绪映射中选择最匹配的情绪，返回对应的图片编号："
        else:
            # 使用默认情绪映射（如果角色没有配置）
            emotion_list_str = self._get_default_emotion_list()
            emotion_instruction = "请从以下情绪列表中选择最匹配的情绪，返回对应的编号："

        # 核心Prompt：结合历史上下文分析当前文本情绪
        prompt = f"""请结合【历史对话上下文】和【当前文本】，分析用户情绪变化，选择最匹配的图片编号。

{emotion_instruction}

{emotion_list_str}

关键分析原则：
- 当前文本判断权重占比0.8，历史占比0.2
- 避免惯性思维，每次都要重新评估文本情绪
- 只返回数字，不要其他内容
- 如果同一个情绪对应多个图片编号，请随机选择一个返回
- 如果无法匹配任何情绪，请返回1

【历史文本】{history_str}
【当前文本】：{text}
【图片编号】："""
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

    def _parse_emotion_response(self, response_text: str, role: Optional[str] = None) -> int:
        """解析API返回的情绪编号，考虑角色特定的映射和随机选择"""
        # 提取数字
        numbers = re.findall(r'\d+', response_text)
        
        if not numbers:
            return 1  # 默认返回图片编号1
        
        requested_id = int(numbers[0])
        
        # 如果有角色映射，处理随机选择
        if role and role in self.role_emotion_mappings:
            emotion_mapping = self.role_emotion_mappings[role]
            emotion_id_str = str(requested_id)
            
            # 检查请求的编号是否在映射中
            if emotion_id_str in emotion_mapping:
                # 获取这个编号对应的情绪名称
                target_emotions = emotion_mapping[emotion_id_str]
                
                # 如果同一个情绪对应多个图片编号，随机选择一个
                if target_emotions:
                    # 找到所有包含这些情绪名称的图片编号
                    all_ids_for_emotion = []
                    for img_id, emotions in emotion_mapping.items():
                        # 检查是否有重叠的情绪名称
                        if any(emotion in target_emotions for emotion in emotions):
                            all_ids_for_emotion.append(int(img_id))
                    
                    # 如果有多个选择，随机选择一个
                    if len(all_ids_for_emotion) > 1:
                        selected_id = random.choice(all_ids_for_emotion)
                        print(f"情绪'{target_emotions[0]}'对应多个图片编号({all_ids_for_emotion})，随机选择: {selected_id}")
                        return selected_id
                    elif all_ids_for_emotion:
                        # 只有一个选择，返回它
                        return all_ids_for_emotion[0]
            
            # 不在映射中，返回默认
            return 1
        else:
            # 没有角色映射，使用默认验证
            if 1 <= requested_id <= EMOTION_COUNT:
                return requested_id
            else:
                return 1

    # ========== 新增：辅助方法 ==========
    
    def _format_emotion_mapping_for_prompt(self, emotion_mapping: dict) -> str:
        """格式化情绪映射为易读的字符串用于Prompt"""
        lines = []
        
        # 按照图片编号排序
        sorted_items = sorted(emotion_mapping.items(), key=lambda x: int(x[0]))
        
        for img_id, emotion_names in sorted_items:
            # 将情绪名称列表转换为字符串，如 "开心/快乐/高兴"
            emotion_str = "/".join(emotion_names)
            lines.append(f"{img_id}-{emotion_str}")
        
        return "\n".join(lines)
    
    def _get_default_emotion_list(self) -> str:
        """获取默认的情绪列表（用于没有配置情绪映射的角色）"""
        lines = []
        for emotion_id, emotion_names in DEFAULT_EMOTION_MAPPING.items():
            emotion_str = "/".join(emotion_names)
            lines.append(f"{emotion_id}-{emotion_str}")
        
        return "\n".join(lines)
    
    def _get_emotion_name_by_id(self, emotion_id: int, role: Optional[str] = None) -> str:
        """根据情绪ID和角色获取情绪名称"""
        if role and role in self.role_emotion_mappings:
            emotion_mapping = self.role_emotion_mappings[role]
            emotion_id_str = str(emotion_id)
            
            if emotion_id_str in emotion_mapping:
                emotion_names = emotion_mapping[emotion_id_str]
                # 返回第一个情绪名称
                return emotion_names[0] if emotion_names else "未知情绪"
        
        # 如果没有角色映射或找不到，使用默认映射
        for default_id, emotion_names in DEFAULT_EMOTION_MAPPING.items():
            if default_id == emotion_id:
                return emotion_names[0] if emotion_names else "未知情绪"
        
        return "未知情绪"
    
    # ========== 新增：角色配置相关方法 ==========
    
    def get_character_config(self, role: str) -> Optional[Dict]:
        """获取角色配置"""
        return self.characters_config.get(role)
    
    def get_character_emotion_count(self, role: str) -> int:
        """获取角色的表情数量"""
        if role in self.characters_config:
            return self.characters_config[role].get("emotion_count", 0)
        return 0
    
    def get_character_emotion_mapping(self, role: str) -> Optional[Dict]:
        """获取角色的情绪映射"""
        return self.role_emotion_mappings.get(role)
    
    def get_available_roles(self) -> List[str]:
        """获取所有配置了情绪映射的角色"""
        return list(self.role_emotion_mappings.keys())
    
    def get_role_display_name(self, role: str) -> str:
        """获取角色的显示名称"""
        if role in self.characters_config:
            return self.characters_config[role].get("display_name", role)
        return role
    
    # ========== 新增：字体配置相关方法 ==========
    
    def get_font_configs(self) -> Dict:
        """获取字体配置"""
        return self.font_configs.copy()
    
    def get_global_chinese_font(self) -> str:
        """获取全局中文字体"""
        if "global" in self.font_configs:
            return self.font_configs["global"].get("chinese_font", "font3.ttf")
        return "font3.ttf"
    
    def get_global_english_math_font(self) -> str:
        """获取全局英文/数学字体"""
        if "global" in self.font_configs:
            return self.font_configs["global"].get("english_math_font", "cambria.ttc")
        return "cambria.ttc"
    
    def get_character_dialog_font(self, role: str) -> str:
        """获取角色的对话框字体"""
        if role in self.characters_config:
            return self.characters_config[role].get("dialog_font", "font3.ttf")
        return "font3.ttf"
    
    # ========== 新增：背景配置相关方法 ==========
    
    def get_background_configs(self) -> Dict:
        """获取背景配置"""
        return BACKGROUND_CONFIGS.copy()
    
    def get_default_background(self) -> str:
        """获取默认背景"""
        return DEFAULT_BACKGROUND
    
    def get_background_count(self, bg_name: str) -> int:
        """获取背景图片数量"""
        if bg_name in BACKGROUND_CONFIGS:
            return BACKGROUND_CONFIGS[bg_name].get("num_bg", 0)
        return 0

    # ========== 新增：历史对话管理方法 ==========
    
    def add_to_history(self, text: str, emotion_id: int, role: Optional[str] = None) -> None:
        """添加对话到历史，自动限制最大条数"""
        self.chat_history.append((text.strip(), emotion_id, role))
        # 超过最大条数时，删除最早的对话
        if len(self.chat_history) > MAX_HISTORY_COUNT:
            self.chat_history.pop(0)

    def clear_history(self) -> None:
        """清空历史对话"""
        self.chat_history = []
        self.save_history_to_file()  # 同步清空文件
        print("历史对话已清空")

    def get_history(self) -> List[Tuple[str, int, Optional[str]]]:
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
                    "emotion_name": self._get_emotion_name_by_id(emotion_id, role),
                    "role": role,
                    "timestamp": time.time()  # 记录时间戳
                }
                for text, emotion_id, role in self.chat_history
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
                (item["text"], item["emotion_id"], item.get("role"))
                for item in history_data
                if "text" in item and "emotion_id" in item
            ]
            print(f"成功加载{len(self.chat_history)}条历史对话")
        except Exception as e:
            print(f"加载历史对话失败: {e}")

    # ========== 新增：重新加载配置 ==========
    
    def reload_config(self) -> None:
        """重新加载所有配置"""
        global API_CONFIG, ENABLE_API, API_KEY, GLOBAL_EMOTION_MAPPINGS, CHARACTERS_CONFIG, FONT_CONFIGS, BACKGROUND_CONFIGS, DEFAULT_BACKGROUND
        
        API_CONFIG = load_api_config()
        ENABLE_API = API_CONFIG.get("enable_api", False)
        API_KEY = API_CONFIG.get("api_key", "")
        GLOBAL_EMOTION_MAPPINGS = API_CONFIG.get("emotion_mappings", {})
        CHARACTERS_CONFIG = API_CONFIG.get("characters", {})
        FONT_CONFIGS = API_CONFIG.get("font_configs", {})
        BACKGROUND_CONFIGS = API_CONFIG.get("background_configs", {})
        DEFAULT_BACKGROUND = API_CONFIG.get("default_background", "hoshishiro")
        
        # 更新实例变量
        self.enable_api = ENABLE_API
        self.api_key = API_KEY
        self.role_emotion_mappings = GLOBAL_EMOTION_MAPPINGS.copy()
        self.characters_config = CHARACTERS_CONFIG.copy()
        self.font_configs = FONT_CONFIGS.copy()
        
        print(f"配置已重新加载，已加载 {len(self.role_emotion_mappings)} 个角色的情绪映射")


# 全局实例
emotion_analyzer = EmotionAnalyzer()


# 对外接口
def get_emotion_from_text(text: str, role: Optional[str] = None) -> int:
    """对外接口：从文本获取情绪编号（结合历史对话）"""
    return emotion_analyzer.analyze_emotion(text, role)


def get_emotion_name(emotion_id: int, role: Optional[str] = None) -> str:
    """根据情绪编号和角色获取情绪名称"""
    return emotion_analyzer._get_emotion_name_by_id(emotion_id, role)


# 新增对外接口：情绪映射管理
def get_role_emotion_mapping(role: str) -> Optional[dict]:
    """获取指定角色的情绪映射"""
    return emotion_analyzer.get_character_emotion_mapping(role)


def get_available_roles() -> List[str]:
    """获取所有配置了情绪映射的角色"""
    return emotion_analyzer.get_available_roles()


def get_character_config(role: str) -> Optional[dict]:
    """获取角色配置"""
    return emotion_analyzer.get_character_config(role)


def get_character_display_name(role: str) -> str:
    """获取角色的显示名称"""
    return emotion_analyzer.get_role_display_name(role)


def get_character_emotion_count(role: str) -> int:
    """获取角色的表情数量"""
    return emotion_analyzer.get_character_emotion_count(role)


# 新增对外接口：字体配置
def get_font_configs() -> Dict:
    """获取字体配置"""
    return emotion_analyzer.get_font_configs()


def get_global_chinese_font() -> str:
    """获取全局中文字体"""
    return emotion_analyzer.get_global_chinese_font()


def get_global_english_math_font() -> str:
    """获取全局英文/数学字体"""
    return emotion_analyzer.get_global_english_math_font()


def get_character_dialog_font(role: str) -> str:
    """获取角色的对话框字体"""
    return emotion_analyzer.get_character_dialog_font(role)


# 新增对外接口：背景配置
def get_background_configs() -> Dict:
    """获取背景配置"""
    return emotion_analyzer.get_background_configs()


def get_default_background() -> str:
    """获取默认背景"""
    return emotion_analyzer.get_default_background()


def get_background_count(bg_name: str) -> int:
    """获取背景图片数量"""
    return emotion_analyzer.get_background_count(bg_name)


# 新增对外接口：历史对话管理
def add_chat_history(text: str, emotion_id: int, role: Optional[str] = None) -> None:
    """外部添加历史对话"""
    emotion_analyzer.add_to_history(text, emotion_id, role)


def clear_chat_history() -> None:
    """外部清空历史对话"""
    emotion_analyzer.clear_history()


def get_chat_history() -> List[Tuple[str, int, Optional[str]]]:
    """外部获取历史对话"""
    return emotion_analyzer.get_history()


# 新增对外接口：配置重新加载
def reload_api_config() -> None:
    """重新加载API配置和情绪映射"""
    emotion_analyzer.reload_config()


# 测试函数
def test_emotion_analysis():
    """测试情绪分析功能"""
    print("=== 测试情绪分析 ===")
    
    # 测试默认情绪映射
    test_text = "我今天很开心！"
    emotion_id = get_emotion_from_text(test_text)
    emotion_name = get_emotion_name(emotion_id)
    print(f"默认映射测试: '{test_text}' -> 情绪编号: {emotion_id}, 情绪名称: {emotion_name}")
    
    # 测试角色特定情绪映射
    available_roles = get_available_roles()
    if available_roles:
        test_role = available_roles[0]
        print(f"\n使用角色 '{test_role}' 测试:")
        
        # 获取角色配置
        config = get_character_config(test_role)
        if config:
            display_name = get_character_display_name(test_role)
            emotion_count = get_character_emotion_count(test_role)
            print(f"角色显示名: {display_name}, 表情数量: {emotion_count}")
        
        # 测试情绪分析
        test_text2 = "我有点难过"
        emotion_id2 = get_emotion_from_text(test_text2, test_role)
        emotion_name2 = get_emotion_name(emotion_id2, test_role)
        print(f"角色映射测试: '{test_text2}' -> 情绪编号: {emotion_id2}, 情绪名称: {emotion_name2}")
        
        # 获取情绪映射
        mapping = get_role_emotion_mapping(test_role)
        if mapping:
            print(f"\n角色 '{test_role}' 的情绪映射:")
            for img_id, emotions in mapping.items():
                print(f"  图片{img_id}: {', '.join(emotions)}")
    
    # 测试字体配置
    font_configs = get_font_configs()
    if font_configs:
        print(f"\n字体配置:")
        if "global" in font_configs:
            print(f"  全局中文字体: {font_configs['global'].get('chinese_font', 'font3.ttf')}")
            print(f"  全局英文/数学字体: {font_configs['global'].get('english_math_font', 'cambria.ttc')}")
    
    # 测试背景配置
    bg_configs = get_background_configs()
    if bg_configs:
        print(f"\n背景配置 (共{len(bg_configs)}个):")
        for bg_name, config in list(bg_configs.items())[:3]:  # 只显示前3个
            print(f"  {bg_name}: {config.get('num_bg', 0)}张图片")
    
    print(f"\n默认背景: {get_default_background()}")
    print("=== 测试结束 ===")


if __name__ == "__main__":
    # 运行测试
    test_emotion_analysis()