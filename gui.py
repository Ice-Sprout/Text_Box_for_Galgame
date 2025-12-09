import tkinter as tk
from tkinter import ttk, messagebox
import json
import os
import sys
import threading
import time
import keyboard
import pyperclip
import io
import win32clipboard
import win32gui
import win32process
import psutil
from PIL import Image as PILImage, ImageTk
import pystray

# resource path handling (兼容打包后的 resource 目录) - 更宽松的查找顺序，便于把 info.py 放在 exe 同目录的 resource/
exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else None
script_dir = os.path.dirname(os.path.abspath(__file__))
# 候选位置（优先级）：1) exe 的目录下的 resource（适用于 onedir），2) 启动路径(sys.argv[0]) 的 resource（便于 onefile 外部资源），3) 脚本目录下的 resource（开发环境）
candidates = []
if exe_dir:
    candidates.append(os.path.join(exe_dir, 'resource'))
try:
    argv_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    if argv_dir:
        candidates.append(os.path.join(argv_dir, 'resource'))
except Exception:
    pass
candidates.append(os.path.join(script_dir, 'resource'))

resource_dir = None
for c in candidates:
    if os.path.isdir(c):
        resource_dir = c
        if resource_dir not in sys.path:
            sys.path.insert(0, resource_dir)
        break
# 回退到脚本目录下的 resource 路径（即使不存在也保持变量可用）
if resource_dir is None:
    resource_dir = os.path.join(script_dir, 'resource')


# Load info from JSON first; fallback to info.py; final fallback to minimal defaults
def _find_info_json_path():
    # try resource_dir first, then script_dir/resource, then PyInstaller _MEIPASS
    candidates = []
    if resource_dir:
        candidates.append(os.path.join(resource_dir, 'info.json'))
    candidates.append(os.path.join(script_dir, 'resource', 'info.json'))
    try:
        meipass = sys._MEIPASS
        candidates.append(os.path.join(meipass, 'resource', 'info.json'))
    except Exception:
        pass
    for p in candidates:
        if p and os.path.exists(p):
            return p
    return None


# 1. 修改 _load_info 函数，确保正确加载 emotion_count
def _load_info():
    # try JSON
    jpath = _find_info_json_path()
    if jpath:
        try:
            with open(jpath, 'r', encoding='utf-8') as jf:
                data = json.load(jf)
            bg = data.get('background_configs', {})
            default_bg = data.get('DEFAULT_BACKGROUND') or data.get('DEFAULT_BACKGROUND', None)
            chars = data.get('characters', {})
            texts = data.get('text_configs_dict', {})

            # convert list coords to tuples where appropriate
            for k, v in list(bg.items()):
                if isinstance(v.get('text_box_topleft'), list):
                    v['text_box_topleft'] = tuple(v['text_box_topleft'])
                if isinstance(v.get('text_box_bottomright'), list):
                    v['text_box_bottomright'] = tuple(v['text_box_bottomright'])
            for role, cfgs in (texts or {}).items():
                for cfg in cfgs:
                    if 'position' in cfg and isinstance(cfg['position'], list):
                        cfg['position'] = tuple(cfg['position'])
                    # Normalize font_color to tuple for consistency
                    if 'font_color' in cfg and isinstance(cfg['font_color'], list):
                        cfg['font_color'] = tuple(cfg['font_color'])

            return bg, chars, texts, default_bg
        except Exception as e:
            print(f"加载 resource/info.json 失败: {e}")

    # final fallback minimal
    return {"默认背景": {}}, {"默认角色": {"emotion_count": 15}}, {}, "默认背景"

# 在_load_info函数后面，添加辅助函数
def get_character_display_names():
    """获取角色显示名列表和映射关系"""
    display_names = []
    folder_to_display = {}
    display_to_folder = {}
    
    for folder_name, config in characters.items():
        # 从配置中获取显示名，如果没有则使用文件夹名
        display_name = config.get("display_name", folder_name)
        display_names.append(display_name)
        folder_to_display[folder_name] = display_name
        display_to_folder[display_name] = folder_name
    
    return display_names, folder_to_display, display_to_folder

# 2. 添加获取角色表情数量的辅助函数
def get_character_emotion_count(character_name):
    """获取指定角色的表情数量"""
    if character_name in characters:
        return characters[character_name].get("emotion_count", 15)
    return 15  # 默认值

background_configs, characters, text_configs_dict, DEFAULT_BACKGROUND = _load_info()

# Import other modules (api, text_to_image, latex). Keep fallbacks for unavailable packages.
try:
    from api import get_emotion_from_text, get_emotion_name, DEFAULT_EMOTION
except Exception:
    DEFAULT_EMOTION = 1
    def get_emotion_from_text(*a, **k): return 1
    def get_emotion_name(*a, **k): return "默认"

try:
    from text_to_image import generate_image, pre_generate_character_images, get_pregen_folder, delate
except Exception:
    def generate_image(*a, **k): return b"", {}
    def pre_generate_character_images(*a, **k): return True
    def get_pregen_folder(): return "./pregen"
    def delate(*a, **k): pass

try:
    from latex import convert_latex_in_text
except Exception:
    def convert_latex_in_text(text): return text

# 配置文件位置：优先 resource/gui_config.json，其次脚本同目录 gui_config.json
exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else None
script_dir = os.path.dirname(os.path.abspath(__file__))
resource_candidate = os.path.join(exe_dir, 'resource', 'gui_config.json') if exe_dir else os.path.join(script_dir, 'resource', 'gui_config.json')
if os.path.exists(os.path.dirname(resource_candidate)) or os.path.isdir(os.path.join(script_dir, 'resource')):
    CONFIG_FILE = resource_candidate
else:
    CONFIG_FILE = os.path.join(script_dir, 'gui_config.json')

# 背景图片（优先 resource/guibg.png）
bg_candidate = os.path.join(resource_dir, 'guibg.png') if resource_dir else ''
BACKGROUND_IMAGE_PATH = bg_candidate if bg_candidate and os.path.exists(bg_candidate) else ''

# 在ImageGeneratorGUI类的__init__方法中，添加映射属性
class ImageGeneratorGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("星白对话框")
        self.root.geometry("960x540")  # 调整为背景图片尺寸
        self.root.resizable(False, False)  # 禁止调整窗口大小，以匹配背景图片
        self.root.withdraw()

        # 获取角色显示名映射
        self.display_names, self.folder_to_display, self.display_to_folder = get_character_display_names()
        
        self.config = self.load_config()
        
        # state
        self.is_running = False
        self.tray_icon = None
        self.tray_thread = None
        self.hotkey_thread = None
        self.bg_image = None
        self.bg_photo = None
        self.hidden_to_tray = False
        self._last_hide_time = 0
        self.text_ids = []  # 存储Canvas文本对象的ID，便于管理

        # UI init
        self.init_background()
        self.init_style()
        self.create_widgets()

        # bindings
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.root.bind('<Unmap>', self.hide_to_tray)

        # tray & hotkey
        self.init_tray()
        self.start_hotkey_listener()
        print(f"程序已后台运行，全局热键：{self.config['global_hotkey']}")

    def load_config(self):
        default_config = {
            "global_hotkey": "ctrl+tab",
            # 注意：这里保存的是文件夹名，但显示时会转换为显示名
            "current_character": list(characters.keys())[0] if characters else "默认角色",
            "current_background": DEFAULT_BACKGROUND,
            "expression": None,
            "latex_enabled": False,
            "delay": 0.1,
            "compression_ratio": 100,  # 压缩比例，100表示不压缩
            "auto_paste": True,
            "auto_send": True,
            "block_hotkey": False,
            "select_all_hotkey": "ctrl+a",
            "cut_hotkey": "ctrl+x",
            "paste_hotkey": "ctrl+v",
            "send_hotkey": "enter",
            "hotkey": "enter",
            "window_whitelist": ["TIM.exe","WeChat.exe","Weixin.exe","WeChatApp.exe","QQ.exe"],
            "enable_whitelist": True
        }
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    # 处理旧配置的兼容性
                    if "reduce_image" in loaded and "compression_ratio" not in loaded:
                        # 将旧的布尔值转换为压缩比例
                        loaded["compression_ratio"] = 100 if loaded["reduce_image"] else 30
                        del loaded["reduce_image"]
                    
                    for k, v in default_config.items():
                        if k not in loaded:
                            loaded[k] = v
                    return loaded
            except Exception as e:
                print(f"加载配置失败: {e}，使用默认配置")
        return default_config

    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
            print("配置已保存")
        except Exception as e:
            print(f"保存配置失败: {e}")

    def init_background(self):
        # 创建Canvas作为背景
        self.canvas = tk.Canvas(self.root, width=960, height=540, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)
        try:
            if not BACKGROUND_IMAGE_PATH:
                raise FileNotFoundError("背景图片未找到")
            self.bg_image = PILImage.open(BACKGROUND_IMAGE_PATH)
            self.bg_photo = ImageTk.PhotoImage(self.bg_image)
            # 在Canvas上绘制背景图片
            self.bg_image_id = self.canvas.create_image(0, 0, image=self.bg_photo, anchor=tk.NW, tags='__bg_img')
        except Exception as e:
            print(f"加载背景失败: {e}")
            self.canvas.configure(bg="#0F0A27")

    def init_style(self):
        style = ttk.Style(self.root)
        self.root.option_add("*Font", "微软雅黑 9")
        style.theme_use("clam")
        
        # 修改样式以使用透明或半透明背景
        style.configure("Transparent.TFrame", background="", borderwidth=0)
        
        # 按钮样式 - 使用半透明或与背景协调的颜色
        style.configure("Custom.TButton", font=("微软雅黑", 10, "bold"), 
                        background="#5D3FD3", foreground="#EDE5F4", 
                        padding=8, relief=tk.RIDGE, borderwidth=2)
        style.map("Custom.TButton", 
                  background=[("active", "#8566DB"), ("disabled", "#6F4F9B")])
        
        # 输入框样式 - 使用半透明背景
        style.configure("Custom.TEntry", font=("微软雅黑", 10), padding=6, 
                        fieldbackground="white", foreground="black", 
                        borderwidth=2, relief=tk.RIDGE)
        
        # Combobox样式
        style.configure("Custom.TCombobox", font=("微软雅黑", 10), padding=6,
                        fieldbackground="white", background="white",
                        foreground="black", borderwidth=2, relief=tk.RIDGE)
        style.map("Custom.TCombobox",
                  fieldbackground=[("readonly", "white"), ("!readonly", "white")],
                  background=[("readonly", "white"), ("!readonly", "white")],
                  foreground=[("disabled", "#7299EC"), ("!disabled", "black")])

    def create_text_with_outline(self, text, x, y, font_size=10, bold=True, fill="white", outline="black"):
        """使用Canvas的create_text方法创建带有描边的文本"""
        if bold:
            font_config = ("微软雅黑", font_size, "bold")
        else:
            font_config = ("微软雅黑", font_size)
        
        # 创建描边效果：黑色文字作为底层
        for dx, dy in [(1, 1), (1, -1), (-1, 1), (-1, -1), (0, 1), (0, -1), (1, 0), (-1, 0)]:
            text_id = self.canvas.create_text(x + dx, y + dy, text=text, 
                                             font=font_config, fill=outline,
                                             anchor=tk.W)
            self.text_ids.append(text_id)
        
        # 创建白色文字作为顶层
        main_text_id = self.canvas.create_text(x, y, text=text, 
                                              font=font_config, fill=fill,
                                              anchor=tk.W)
        self.text_ids.append(main_text_id)
        
        return main_text_id

    def create_checkbutton_with_outline(self, text, x, y, variable, font_size=10, bold=False):
        """创建带有描边文本的复选框"""
        # 首先创建复选框
        cb = tk.Checkbutton(self.canvas, variable=variable, bg="#D1D0D2", 
                           activebackground="#BAACCC", selectcolor="#ACA1BA",
                           highlightthickness=0, bd=0)
        cb.place(x=x, y=y-5)
        
        # 然后创建复选框的文本标签（带描边）
        text_x = x + 25  # 复选框宽度约20像素 + 5像素间距
        text_y = y + 5   # 向下移动3像素
        self.create_text_with_outline(text, text_x, text_y, font_size=font_size, bold=bold)
        
        return cb

    def update_compression_label(self, value):
        """更新压缩比例标签"""
        ratio = int(value)
        if ratio == 100:
            label_text = "100 (不压缩)"
        elif ratio >= 80:
            label_text = f"{ratio} (轻微压缩)"
        elif ratio >= 60:
            label_text = f"{ratio} (中等压缩)"
        elif ratio >= 40:
            label_text = f"{ratio} (较强压缩)"
        elif ratio >= 20:
            label_text = f"{ratio} (强力压缩)"
        else:
            label_text = f"{ratio} (最大压缩)"
        
        self.compression_label_var.set(label_text)

    # 修改update_expression_options方法
    def update_expression_options(self, event=None):
        """当角色改变时更新表情下拉框的选项"""
        # 获取当前选择的显示名
        current_display = self.character_var.get()
        
        # 将显示名转换为文件夹名
        current_folder = self.display_to_folder.get(current_display, current_display)
        
        emotion_count = get_character_emotion_count(current_folder)
        
        # 更新表情选项
        expression_values = ["自动", "随机"] + [str(i) for i in range(1, emotion_count + 1)]
        
        # 更新表情下拉框的值
        if hasattr(self, 'expression_cb'):
            current_value = self.expression_var.get()
            self.expression_cb['values'] = expression_values
            
            # 如果当前值不在新列表中，重置为"自动"
            if current_value not in expression_values and current_value != "自动" and current_value != "随机":
                self.expression_var.set("自动")

    # 修改create_widgets方法中的角色选择部分
    def create_widgets(self):
        # 直接在Canvas上创建控件，不使用Frame容器
        # 控件位置可以根据背景图片设计进行手动调整
        
        # 第一列控件 (左侧)
        left_start_x = 150  # 向右移动20像素
        left_start_y = 90
        row_height = 40
        
        # 程序运行/关闭快捷键
        self.create_text_with_outline("程序运行/关闭快捷键：", 
                                      left_start_x, left_start_y)
        self.global_hotkey_var = tk.StringVar(value=self.config["global_hotkey"])
        ttk.Entry(self.canvas, textvariable=self.global_hotkey_var, style="Custom.TEntry", width=20).place(
            x=left_start_x + 170, y=left_start_y - 3)
        
        # 角色选择 - 使用显示名而不是文件夹名
        self.create_text_with_outline("角色：", 
                                      left_start_x, left_start_y + row_height)
        
        # 从配置中获取当前角色的文件夹名，然后转换为显示名
        current_folder = self.config["current_character"]
        current_display = self.folder_to_display.get(current_folder, current_folder)
        
        self.character_var = tk.StringVar(value=current_display)
        
        # 使用显示名列表作为下拉框的选项
        character_cb = ttk.Combobox(self.canvas, textvariable=self.character_var,
                     values=self.display_names if self.display_names else ["默认角色"], 
                     state="readonly", style="Custom.TCombobox", width=18)
        character_cb.place(x=left_start_x + 170, y=left_start_y + row_height - 3)
        
        # 背景选择
        self.create_text_with_outline("背景：", 
                                      left_start_x, left_start_y + 2 * row_height)
        self.background_var = tk.StringVar(value=self.config["current_background"])
        background_cb = ttk.Combobox(self.canvas, textvariable=self.background_var,
                     values=list(background_configs.keys()) if background_configs else ["默认背景"], 
                     state="readonly", style="Custom.TCombobox", width=18)
        background_cb.place(x=left_start_x + 170, y=left_start_y + 2 * row_height - 3)
        
        # 表情选择 - 修改为动态获取表情数量
        self.create_text_with_outline("表情：", 
                                    left_start_x, left_start_y + 3 * row_height)
        
        # 处理表情设置的初始值
        exp_config = self.config.get("expression")
        if exp_config is None:
            exp_str = "自动"
        elif exp_config == "random":
            exp_str = "随机"
        else:
            exp_str = str(exp_config)
        
        self.expression_var = tk.StringVar(value=exp_str)
        
        # 获取当前角色的表情数量（使用文件夹名）
        current_folder = self.config['current_character']
        emotion_count = get_character_emotion_count(current_folder)
        
        # 创建表情选项：自动 + 随机 + 1到emotion_count的数字
        expression_values = ["自动", "随机"] + [str(i) for i in range(1, emotion_count + 1)]
        
        self.expression_cb = ttk.Combobox(self.canvas, textvariable=self.expression_var,
                    values=expression_values, state="readonly",
                    style="Custom.TCombobox", width=18)
        self.expression_cb.place(x=left_start_x + 170, y=left_start_y + 3 * row_height - 3)
        
        # 为角色选择绑定事件，当角色改变时更新表情选项
        character_cb.bind("<<ComboboxSelected>>", self.update_expression_options)
        
        # LaTeX转换 - 使用新的带描边的复选框
        self.latex_var = tk.BooleanVar(value=self.config.get("latex_enabled", False))
        self.latex_cb = self.create_checkbutton_with_outline("启用LaTeX转换", 
                                      left_start_x, left_start_y + 4 * row_height,
                                      self.latex_var)
        
        # DELAY值
        self.create_text_with_outline("DELAY值：", 
                                      left_start_x, left_start_y + 5 * row_height)
        self.delay_var = tk.StringVar(value=str(self.config.get("delay", 0.1)))
        ttk.Entry(self.canvas, textvariable=self.delay_var, style="Custom.TEntry", width=10).place(
            x=left_start_x + 170, y=left_start_y + 5 * row_height - 3)
        
        # 压缩比例滑块
        self.create_text_with_outline("压缩质量：", 
                                      left_start_x, left_start_y + 6 * row_height)

        # 创建压缩比例标签
        self.compression_label_var = tk.StringVar(value="100 (不压缩)")
        self.compression_label = tk.Label(self.canvas, textvariable=self.compression_label_var,
                                         font=("微软雅黑", 9), bg="#D1D0D2", fg="black",
                                         relief=tk.FLAT)
        self.compression_label.place(x=left_start_x + 120, y=left_start_y + 6 * row_height)

        # 创建滑块
        self.compression_ratio = tk.IntVar(value=self.config.get("compression_ratio", 100))
        self.compression_slider = tk.Scale(self.canvas, from_=10, to=100, 
                                           variable=self.compression_ratio,
                                           orient=tk.HORIZONTAL,
                                           length=180,
                                           showvalue=False,
                                           bg="#D1D0D2",
                                           highlightthickness=0,
                                           troughcolor="#5D3FD3",
                                           sliderrelief=tk.RAISED,
                                           command=self.update_compression_label)
        self.compression_slider.place(x=left_start_x + 120, y=left_start_y + 6 * row_height + 20)
        
        # 初始化压缩比例标签
        self.update_compression_label(self.compression_ratio.get())
        
        # 自动粘贴生成的图片 - 移动到左侧
        self.auto_paste_var = tk.BooleanVar(value=self.config.get("auto_paste", True))
        self.auto_paste_cb = self.create_checkbutton_with_outline("自动粘贴生成的图片", 
                                      left_start_x, left_start_y + 7 * row_height,
                                      self.auto_paste_var)
        
        # 第二列控件 (右侧)
        right_start_x = 540
        right_start_y = 90
        
        # 生成图片后自动发送 - 使用新的带描边的复选框
        self.auto_send_var = tk.BooleanVar(value=self.config.get("auto_send", True))
        self.auto_send_cb = self.create_checkbutton_with_outline("生成图片后自动发送", 
                                      right_start_x, right_start_y,
                                      self.auto_send_var)
        
        # 阻塞按键 - 使用新的带描边的复选框
        self.block_hotkey_var = tk.BooleanVar(value=self.config.get("block_hotkey", False))
        self.block_hotkey_cb = self.create_checkbutton_with_outline("阻塞按键", 
                                      right_start_x, right_start_y + row_height,
                                      self.block_hotkey_var)
        
        # 启用窗口白名单 - 使用新的带描边的复选框
        self.whitelist_var = tk.BooleanVar(value=self.config.get("enable_whitelist", True))
        self.whitelist_cb = self.create_checkbutton_with_outline("启用窗口白名单", 
                                      right_start_x, right_start_y + 2 * row_height,
                                      self.whitelist_var)
        
        # 全选快捷键
        self.create_text_with_outline("全选快捷键：", 
                                      right_start_x, right_start_y + 3 * row_height)
        self.select_all_var = tk.StringVar(value=self.config.get("select_all_hotkey", "ctrl+a"))
        ttk.Entry(self.canvas, textvariable=self.select_all_var, style="Custom.TEntry", width=10).place(
            x=right_start_x + 120, y=right_start_y + 3 * row_height - 3)
        
        # 剪切快捷键
        self.create_text_with_outline("剪切快捷键：", 
                                      right_start_x, right_start_y + 4 * row_height)
        self.cut_var = tk.StringVar(value=self.config.get("cut_hotkey", "ctrl+x"))
        ttk.Entry(self.canvas, textvariable=self.cut_var, style="Custom.TEntry", width=10).place(
            x=right_start_x + 120, y=right_start_y + 4 * row_height - 3)
        
        # 粘贴快捷键
        self.create_text_with_outline("粘贴快捷键：", 
                                      right_start_x, right_start_y + 5 * row_height)
        self.paste_var = tk.StringVar(value=self.config.get("paste_hotkey", "ctrl+v"))
        ttk.Entry(self.canvas, textvariable=self.paste_var, style="Custom.TEntry", width=10).place(
            x=right_start_x + 120, y=right_start_y + 5 * row_height - 3)
        
        # 发送消息快捷键
        self.create_text_with_outline("发送消息快捷键：", 
                                      right_start_x, right_start_y + 6 * row_height)
        self.send_var = tk.StringVar(value=self.config.get("send_hotkey", "enter"))
        ttk.Entry(self.canvas, textvariable=self.send_var, style="Custom.TEntry", width=10).place(
            x=right_start_x + 120, y=right_start_y + 6 * row_height - 3)
        
        # 生成热键
        self.create_text_with_outline("生成热键：", 
                                      right_start_x, right_start_y + 7 * row_height)
        self.hotkey_var = tk.StringVar(value=self.config.get("hotkey", "enter"))
        ttk.Entry(self.canvas, textvariable=self.hotkey_var, style="Custom.TEntry", width=10).place(
            x=right_start_x + 120, y=right_start_y + 7 * row_height - 3)
        
        # 按钮区域 (放在底部中央)
        button_start_x =120
        button_y = 420
        
        ttk.Button(self.canvas, text="进行预生成", command=self.pre_generate, 
                style="Custom.TButton", width=12).place(x=button_start_x, y=button_y)
        ttk.Button(self.canvas, text="清除预生成图片", command=self.clear_pregen, 
                style="Custom.TButton", width=14).place(x=button_start_x + 123, y=button_y)
        ttk.Button(self.canvas, text="删除当前角色预生成", command=self.delete_current_pregen, 
                style="Custom.TButton", width=18).place(x=button_start_x + 265, y=button_y)
        ttk.Button(self.canvas, text="保存设置", command=self.save_settings, 
                style="Custom.TButton", width=10).place(x=button_start_x + 440, y=button_y)
        ttk.Button(self.canvas, text="退出程序", command=self.quit_program, 
                style="Custom.TButton", width=10).place(x=button_start_x + 550, y=button_y)
        
        # 状态标签 (放在底部) - 使用自定义的带描边文本
        self.status_var = tk.StringVar(value=f"窗口已恢复 | 按{self.config['global_hotkey']}启动/停止功能")
        
        # 为状态标签也创建描边效果
        status_x = 350
        status_y = button_y + 50  # 保持相对位置
        
        # 使用Label来显示状态，但给它一个半透明背景
        self.status_label = tk.Label(self.canvas, textvariable=self.status_var, 
                                    font=("微软雅黑", 10, "bold"), 
                                    bg="#2A1B3D", fg="white",
                                    borderwidth=1, relief=tk.FLAT)
        self.status_label.place(x=status_x, y=status_y)
        
        # 强制刷新窗口以确保所有控件显示
        self.root.update_idletasks()

    def init_tray(self):
        try:
            # 优先使用 resource/logo.png 作为托盘与窗口图标
            logo_path = os.path.join(resource_dir, 'logo.png') if resource_dir else ''
            pil_icon = None
            if logo_path and os.path.exists(logo_path):
                try:
                    pil_icon = PILImage.open(logo_path).convert('RGBA')
                except Exception as e:
                    print(f"加载 logo 失败: {e}")
                    pil_icon = None

            # 准备 pystray icon（16x16）
            if pil_icon is not None:
                tray_img = pil_icon.resize((16, 16), PILImage.Resampling.LANCZOS)
            else:
                tray_img = PILImage.new('RGBA', (16, 16), color=(93, 63, 211, 255))

            menu = pystray.Menu(pystray.MenuItem('显示窗口', self.show_window), pystray.MenuItem('退出程序', self.quit_program))
            self.tray_icon = pystray.Icon('图片生成器', tray_img, '图片生成器', menu)
            self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            self.tray_thread.start()

            # 设置 Tk 窗口图标（任务栏/窗口），保存引用防止被垃圾回收
            try:
                if pil_icon is not None:
                    tk_img = ImageTk.PhotoImage(pil_icon.resize((32, 32), PILImage.Resampling.LANCZOS))
                    # 保持引用
                    self._tk_icon = tk_img
                    try:
                        # True 表示设为所有图标（有时 False 也可）
                        self.root.iconphoto(True, tk_img)
                    except Exception:
                        # 兼容性回退
                        try:
                            self.root.iconphoto(False, tk_img)
                        except Exception:
                            pass
            except Exception as e:
                print(f"设置窗口图标失败: {e}")

        except Exception as e:
            print(f"托盘初始化失败: {e}")
            # 出错时恢复窗口显示，避免应用无界面
            try:
                self.root.deiconify()
            except Exception:
                pass

    def hide_to_tray(self, event=None):
        try:
            now = time.time()
            if self.hidden_to_tray and (now - getattr(self, '_last_hide_time', 0) < 0.5):
                return
            if getattr(self, 'root', None) is None:
                return
            self.root.withdraw()
            self.hidden_to_tray = True
            self._last_hide_time = now
            if getattr(self, 'status_var', None) is not None:
                self.status_var.set(f"程序已最小化到系统托盘 | 按{self.config['global_hotkey']}启动/停止")
            print("窗口已隐藏到托盘")
        except Exception:
            pass

    def show_window(self, icon=None, item=None):
        self.root.deiconify()
        self.root.lift()
        self.hidden_to_tray = False
        self.status_var.set(f"窗口已恢复 | 按{self.config['global_hotkey']}启动/停止功能")
        print("窗口已恢复")

    def quit_program(self, icon=None, item=None):
        try:
            if self.is_running:
                self.stop_running()
            keyboard.unhook_all()
            if self.tray_icon:
                try:
                    self.tray_icon.stop()
                except Exception:
                    pass
            try:
                # 清理Canvas上的文本对象
                for text_id in self.text_ids:
                    try:
                        self.canvas.delete(text_id)
                    except Exception:
                        pass
                self.root.destroy()
            except Exception:
                pass
            sys.exit(0)
        except Exception as e:
            print(f"退出失败: {e}")
            sys.exit(1)

    def start_hotkey_listener(self):
        try:
            keyboard.unhook_all()
            keyboard.add_hotkey(self.config['global_hotkey'], self.toggle_running)
            print(f"热键监听启动: {self.config['global_hotkey']}")
        except Exception as e:
            print(f"热键启动失败: {e}")
            if getattr(self, 'status_var', None) is not None:
                self.status_var.set(f"热键错误: {str(e)[:20]}")

    def toggle_running(self):
        if self.is_running:
            self.stop_running()
            self.status_var.set(f"功能已停止 | 按{self.config['global_hotkey']}重新启动")
        else:
            self.start_running()
            self.status_var.set(f"功能已启动 | 按{self.config['global_hotkey']}停止")

    def start_running(self):
        try:
            self.save_settings()
            self.is_running = True
            keyboard.add_hotkey(self.config['hotkey'], self.generate_image_handler, suppress=self.config.get('block_hotkey', False))
        except Exception as e:
            print(f"启动失败: {e}")
            self.status_var.set(f"启动失败: {str(e)[:20]}")

    def stop_running(self):
        try:
            keyboard.remove_hotkey(self.config['hotkey'])
            self.is_running = False
        except Exception as e:
            print(f"停止失败: {e}")

    def get_window_exe_name(self):
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            return os.path.basename(psutil.Process(pid).exe())
        except Exception as e:
            print(f"获取窗口名失败: {e}")
            return None

    def copy_png_bytes_to_clipboard(self, png_bytes: bytes):
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            png_format = win32clipboard.RegisterClipboardFormat("PNG")
            win32clipboard.SetClipboardData(png_format, png_bytes)
            image = PILImage.open(io.BytesIO(png_bytes)).convert("RGB")
            with io.BytesIO() as output:
                image.save(output, "BMP")
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, output.getvalue()[14:])
            win32clipboard.CloseClipboard()
        except Exception as e:
            print(f"剪贴板错误: {e}")
            try:
                win32clipboard.CloseClipboard()
            except Exception:
                pass

    def generate_image_handler(self):
        if self.config.get('enable_whitelist'):
            current = self.get_window_exe_name()
            if current not in self.config.get('window_whitelist', []):
                print("窗口不在白名单，跳过")
                keyboard.send(self.config['hotkey'])
                return
        threading.Thread(target=self._generate_image_thread, daemon=True).start()

    # 修改_generate_image_thread方法，确保使用文件夹名
    def _generate_image_thread(self):
        try:
            # 获取当前角色的表情数量（使用文件夹名）
            current_folder = self.config['current_character']
            emotion_count = get_character_emotion_count(current_folder)
            
            # 处理随机表情
            expression = self.config.get('expression')
            if expression == "random":
                # 生成1到emotion_count之间的随机数
                import random
                expression = random.randint(1, emotion_count)
                print(f"使用随机表情: {expression} (1-{emotion_count})")
            
            text = self.cut_all_and_get_text()
            
            # 获取压缩比例，100表示不压缩，小于100表示进行压缩
            compression_ratio = self.config.get('compression_ratio', 100)
            
            png_bytes, _ = generate_image(text=text,
                                        character_name=current_folder,  # 使用文件夹名
                                        background_name=self.config['current_background'],
                                        expression=expression,  # 这里已经是数字或None
                                        latex_insert=self.config.get('latex_enabled', False),
                                        compression_ratio=compression_ratio)  # 传递压缩比例
            
            self.copy_png_bytes_to_clipboard(png_bytes)
            if self.config.get('auto_paste'):
                keyboard.send(self.config.get('paste_hotkey', 'ctrl+v'))
                if self.config.get('auto_send'):
                    time.sleep(0.3)
                    keyboard.send(self.config.get('send_hotkey', 'enter'))
            if getattr(self, 'status_var', None) is not None:
                self.status_var.set(f"生成完成: {text[:20]}...")
        except Exception as e:
            print(f"生成失败: {e}")
            if getattr(self, 'status_var', None) is not None:
                self.status_var.set(f"生成失败: {str(e)[:20]}")

    def cut_all_and_get_text(self):
        old = pyperclip.paste()
        pyperclip.copy("")
        keyboard.send(self.config.get('select_all_hotkey', 'ctrl+a'))
        keyboard.send(self.config.get('cut_hotkey', 'ctrl+x'))
        time.sleep(self.config.get('delay', 0.1))
        new = pyperclip.paste()
        if self.config.get('latex_enabled') and new.strip():
            new = convert_latex_in_text(new)
            pyperclip.copy(new)
        return new

    # 修改pre_generate方法
    def pre_generate(self):
        # 获取显示名并转换为文件夹名
        display_name = self.character_var.get()
        folder_name = self.display_to_folder.get(display_name, display_name)
        
        bg = self.background_var.get()
        if not folder_name or not bg:
            self.status_var.set("预生成失败：请选择角色和背景")
            return
        self.status_var.set(f"正在预生成 {display_name} - {bg} 的图片...")
        self.root.update()
        try:
            ok = pre_generate_character_images(folder_name, bg)
            self.status_var.set(f"预生成{'完成' if ok else '已存在，跳过'}: {display_name} - {bg}")
        except Exception as e:
            print(f"预生成失败: {e}")
            self.status_var.set(f"预生成失败: {str(e)[:30]}")

    def clear_pregen(self):
        if messagebox.askyesno("确认", "确定清除所有预生成图片？"):
            try:
                delate(get_pregen_folder())
                self.status_var.set("预生成图片已清除")
            except Exception as e:
                messagebox.showerror("错误", f"清除失败: {e}")
                self.status_var.set(f"清除失败: {str(e)[:30]}")

    def delete_current_pregen(self):
        """删除当前选中角色和背景的预生成图片"""
        # 获取当前选中的角色和背景
        display_name = self.character_var.get()
        
        # 将显示名转换为文件夹名
        current_display = self.character_var.get()
        current_folder = self.display_to_folder.get(current_display, current_display)
        
        bg = self.background_var.get()
        
        if not current_folder or not bg:
            messagebox.showerror("错误", "请先选择角色和背景")
            return
        
        # 确认对话框
        if not messagebox.askyesno("确认", 
                               f"确定要删除 {display_name} 在背景 {bg} 下的预生成图片吗？"):
            return
        
        try:
            # 获取预生成文件夹路径
            pregen_folder = get_pregen_folder()
            if not os.path.exists(pregen_folder):
                messagebox.showinfo("提示", "预生成文件夹不存在，无需删除")
                return
            
            # 删除匹配的文件
            deleted_count = 0
            pattern = f"{current_folder}_{bg}_*.jpg"
            
            for filename in os.listdir(pregen_folder):
                if filename.lower().endswith('.jpg') and filename.startswith(f"{current_folder}_{bg}_"):
                    file_path = os.path.join(pregen_folder, filename)
                    try:
                        os.remove(file_path)
                        deleted_count += 1
                    except Exception as e:
                        print(f"删除文件 {filename} 失败: {e}")
            
            if deleted_count > 0:
                self.status_var.set(f"已删除 {deleted_count} 个 {display_name} - {bg} 的预生成图片")
                messagebox.showinfo("成功", f"已删除 {deleted_count} 个 {display_name} 在背景 {bg} 下的预生成图片")
            else:
                self.status_var.set(f"未找到 {display_name} - {bg} 的预生成图片")
                messagebox.showinfo("提示", f"未找到 {display_name} 在背景 {bg} 下的预生成图片")
                
        except Exception as e:
            messagebox.showerror("错误", f"删除预生成图片失败: {e}")
            self.status_var.set(f"删除失败: {str(e)[:30]}")

    # 修改save_settings方法中的角色处理部分
    def save_settings(self):
        try:
            self.config['global_hotkey'] = self.global_hotkey_var.get()
            
            # 将显示名转换为文件夹名保存
            current_display = self.character_var.get()
            current_folder = self.display_to_folder.get(current_display, current_display)
            self.config['current_character'] = current_folder
            
            self.config['current_background'] = self.background_var.get()
            
            # 处理表情设置
            exp_str = self.expression_var.get()
            if exp_str == '自动':
                self.config['expression'] = None
            elif exp_str == '随机':
                self.config['expression'] = "random"  # 使用特殊值表示随机
            else:
                try:
                    self.config['expression'] = int(exp_str)
                except ValueError:
                    self.config['expression'] = None
            
            self.config['latex_enabled'] = bool(self.latex_var.get())
            self.config['delay'] = float(self.delay_var.get())
            self.config['compression_ratio'] = int(self.compression_ratio.get())  # 保存压缩比例
            self.config['auto_paste'] = bool(self.auto_paste_var.get())
            self.config['auto_send'] = bool(self.auto_send_var.get())
            self.config['block_hotkey'] = bool(self.block_hotkey_var.get())
            self.config['enable_whitelist'] = bool(self.whitelist_var.get())
            self.config['select_all_hotkey'] = self.select_all_var.get()
            self.config['cut_hotkey'] = self.cut_var.get()
            self.config['paste_hotkey'] = self.paste_var.get()
            self.config['send_hotkey'] = self.send_var.get()
            self.config['hotkey'] = self.hotkey_var.get()
            
            self.save_config()
            # 重启热键监听
            if self.is_running:
                self.stop_running()
            self.start_hotkey_listener()
            self.status_var.set(f"设置已保存并应用 | 按{self.config['global_hotkey']}启动/停止功能")
            
        except Exception as e:
            messagebox.showerror("错误", f"保存设置失败: {e}")
            self.status_var.set(f"保存失败: {str(e)[:20]}")


def main():
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)
        except Exception:
            pass
    root = tk.Tk()
    app = ImageGeneratorGUI(root)
    root.mainloop()


if __name__ == '__main__':
    main()