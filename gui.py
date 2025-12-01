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

# 依赖模块模拟（实际保留原有导入）
try:
    from info import background_configs, characters, text_configs_dict, DEFAULT_BACKGROUND
    from api import get_emotion_from_text, get_emotion_name, DEFAULT_EMOTION
    from text_to_image import generate_image, pre_generate_character_images, get_pregen_folder, delate
    from latex import convert_latex_in_text
except ImportError as e:
    print(f"依赖模块导入失败: {e}，使用模拟数据")
    background_configs = {"默认背景": {}}
    characters = {"默认角色": {}}
    text_configs_dict = {}
    DEFAULT_BACKGROUND = "默认背景"
    DEFAULT_EMOTION = 1
    def get_emotion_from_text(*args): return 1
    def get_emotion_name(*args): return "默认"
    def generate_image(*args, **kwargs): return b"", {}
    def pre_generate_character_images(*args): return True
    def get_pregen_folder(): return "./pregen"
    def delate(*args): pass
    def convert_latex_in_text(text): return text

CONFIG_FILE = "gui_config.json"
BACKGROUND_IMAGE_PATH = r"E:\desketop\stars\star1.6\star-master\background\hoshishiro\e0.png"  # 保持用户指定背景

class ImageGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("图片生成器")
        self.root.geometry("1300x900")
        self.root.minsize(800, 800)
        self.root.withdraw()

        # 初始化变量
        self.config = self.load_config()
        self.is_running = False
        self.hotkey_thread = None
        self.tray_icon = None
        self.tray_thread = None
        self.bg_image = None
        self.bg_photo = None
        self.panel_window = None  # 面板窗口对象

        # 初始化背景和样式
        self.init_background()
        self.init_style()  # 深紫色系样式
        self.create_widgets()  # 不含顶部文字

        # 绑定事件
        self.root.protocol("WM_DELETE_WINDOW", self.hide_to_tray)
        self.root.bind('<Unmap>', self.hide_to_tray)
        self.root.bind('<Configure>', self.on_window_resize)

        # 系统托盘和热键
        self.init_tray()
        self.start_hotkey_listener()
        print(f"程序已后台运行，全局热键：{self.config['global_hotkey']}")

    def init_background(self):
        """加载星空背景图"""
        self.canvas = tk.Canvas(self.root, highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        try:
            if os.path.exists(BACKGROUND_IMAGE_PATH):
                self.bg_image = PILImage.open(BACKGROUND_IMAGE_PATH)
                self.update_background()
            else:
                raise FileNotFoundError(f"背景图片不存在：{BACKGROUND_IMAGE_PATH}")
        except Exception as e:
            print(f"加载背景图片失败: {e}，使用纯色背景")
            self.canvas.configure(bg="#0F0A27")  # 星空色系 fallback

    def update_background(self):
        """窗口缩放时更新背景"""
        if self.bg_image is None:
            return
        win_width = self.root.winfo_width()
        win_height = self.root.winfo_height()
        img = self.bg_image.resize((win_width, win_height), PILImage.Resampling.LANCZOS)
        self.bg_photo = ImageTk.PhotoImage(img)
        self.canvas.create_image(0, 0, image=self.bg_photo, anchor=tk.NW)

    def on_window_resize(self, event):
        if event.widget == self.root and self.bg_image is not None:
            self.update_background()
        # 窗口缩放时同步校准面板位置
        if self.panel_window is not None:
            self.canvas.coords(self.panel_window, event.width // 2, event.height // 2)

    def create_gradient_frame(self, parent, width, height):
        """创建带渐变色边框的容器"""
        # 外层渐变边框容器
        gradient_frame = tk.Frame(parent, width=width, height=height, bd=0)
        gradient_frame.pack_propagate(False)  # 固定尺寸

        # 用Canvas绘制渐变边框
        canvas = tk.Canvas(gradient_frame, width=width, height=height, highlightthickness=0)
        canvas.pack(fill=tk.BOTH, expand=True)

        # 渐变颜色（从深紫到亮紫）
        colors = ["#5D3FD3", "#7B5CF0", "#9D8DF1", "#C9B8FF"]
        border_width = 4  # 边框宽度

        # 绘制四层渐变边框（模拟平滑过渡）
        for i in range(border_width):
            canvas.create_rectangle(
                i, i, width - i, height - i,
                outline=colors[i % len(colors)],  # 循环使用渐变色
                width=1
            )

        # 内部深紫色面板（与原风格统一）
        inner_frame = ttk.Frame(canvas, style="Main.TFrame")
        canvas.create_window(
            border_width, border_width,
            window=inner_frame,
            anchor=tk.NW,
            width=width - 2 * border_width,
            height=height - 2 * border_width
        )

        return gradient_frame, inner_frame

    def init_style(self):
        """深紫色系样式配置（增加边框效果）"""
        style = ttk.Style(self.root)
        self.root.option_add("*Font", "微软雅黑 9")

        style.theme_use("clam")

        # 主面板背景（深紫色）
        style.configure("Main.TFrame",
                        background="#2A1B3D",
                        borderwidth=2,
                        relief=tk.RIDGE)  # 面板边框

        # 按钮样式（模拟渐变边框）
        style.configure("Custom.TButton",
                        font=("微软雅黑", 10, "bold"),
                        background="#5D3FD3",  # 主色
                        foreground="#EDE5F4",
                        padding=8,
                        relief=tk.RIDGE,  # 按钮边框
                        borderwidth=2,
                        focusthickness=2,
                        focuscolor="#9D8DF1")  # 聚焦时亮边
        # 悬停渐变效果
        style.map("Custom.TButton",
                  background=[("active", "#4A2CA0"), ("disabled", "#3A2557")],
                  bordercolor=[("active", "#9D8DF1"), ("!active", "#4A3567")])  # 边框颜色变化

        # 输入框/下拉框（带渐变边框）
        style.configure("Custom.TEntry",
                        font=("微软雅黑", 10),
                        padding=6,
                        fieldbackground="#4A3567",
                        foreground="#EDE5F4",
                        borderwidth=2,
                        relief=tk.RIDGE,  # 输入框边框
                        focusthickness=2,
                        focuscolor="#9D8DF1")  # 聚焦时亮边（模拟渐变）
        style.configure("Custom.TCombobox",
                        font=("微软雅黑", 10),
                        padding=6,
                        fieldbackground="#4A3567",
                        foreground="#EDE5F4",
                        borderwidth=2,
                        relief=tk.RIDGE)
        style.map("Custom.TCombobox",
                  fieldbackground=[("readonly", "#4A3567")],
                  bordercolor=[("focus", "#9D8DF1"), ("!focus", "#4A3567")])

        # 标签文字
        style.configure("Normal.TLabel",
                        font=("微软雅黑", 10),
                        foreground="#EDE5F4",
                        background="#2A1B3D")

        # 复选框
        style.configure("Custom.TCheckbutton",
                        font=("微软雅黑", 9),
                        padding=4,
                        foreground="#EDE5F4",
                        background="#2A1B3D",
                        borderwidth=1,
                        relief=tk.FLAT)
        style.map("Custom.TCheckbutton",
                  foreground=[("active", "#C9B8FF")],
                  background=[("active", "#3A2557")])  # 悬停背景变化

    def load_config(self):
        """加载配置（逻辑不变）"""
        default_config = {
            "global_hotkey": "ctrl+tab",
            "current_character": list(characters.keys())[0] if characters else "默认角色",
            "current_background": DEFAULT_BACKGROUND,
            "expression": None,
            "latex_enabled": False,
            "delay": 0.1,
            "reduce_image": True,
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
                    loaded_config = json.load(f)
                    for key, value in default_config.items():
                        if key not in loaded_config:
                            loaded_config[key] = value
                    return loaded_config
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

    def create_widgets(self):
        """修复面板居中与两列布局显示错误"""
        # 适配两列布局的面板尺寸（宽度足够，高度适配内容）
        panel_total_width = 700
        panel_total_height = 600

        # 创建带渐变边框的容器（初始居中，后续随窗口 resize 动态调整）
        gradient_container, main_frame = self.create_gradient_frame(
            self.root,
            panel_total_width,
            panel_total_height
        )
        # 初始位置设为(0,0)，通过anchor=CENTER和后续事件校准到正中央
        self.panel_window = self.canvas.create_window(
            0, 0,
            window=gradient_container,
            anchor=tk.CENTER
        )

        # 面板内边距（避免内容贴边框）
        main_frame.configure(padding="25")
        # 两列平均分配宽度
        main_frame.columnconfigure(0, weight=1, minsize=300)  # 左列最小宽度
        main_frame.columnconfigure(1, weight=1, minsize=300)  # 右列最小宽度
        row_col0 = 0  # 左列行索引
        row_col1 = 0  # 右列行索引

        # ---------------------- 左列控件（基础设置） ----------------------
        # 1. 程序运行/关闭快捷键
        ttk.Label(main_frame, text="程序运行/关闭快捷键：", style="Normal.TLabel").grid(
            row=row_col0, column=0, sticky=tk.W, pady=6, padx=(5, 10))
        self.global_hotkey_var = tk.StringVar(value=self.config["global_hotkey"])
        ttk.Entry(main_frame, textvariable=self.global_hotkey_var, style="Custom.TEntry").grid(
            row=row_col0, column=0, sticky=tk.E, pady=6, padx=(10, 5))  # 输入框右对齐
        row_col0 += 1

        # 2. 角色选择
        ttk.Label(main_frame, text="角色：", style="Normal.TLabel").grid(
            row=row_col0, column=0, sticky=tk.W, pady=6, padx=(5, 10))
        self.character_var = tk.StringVar(value=self.config["current_character"])
        ttk.Combobox(
            main_frame,
            textvariable=self.character_var,
            values=list(characters.keys()) if characters else ["默认角色"],
            state="readonly",
            style="Custom.TCombobox",
            width=15
        ).grid(row=row_col0, column=0, sticky=tk.E, pady=6, padx=(10, 5))
        row_col0 += 1

        # 3. 背景选择
        ttk.Label(main_frame, text="背景：", style="Normal.TLabel").grid(
            row=row_col0, column=0, sticky=tk.W, pady=6, padx=(5, 10))
        self.background_var = tk.StringVar(value=self.config["current_background"])
        ttk.Combobox(
            main_frame,
            textvariable=self.background_var,
            values=list(background_configs.keys()) if background_configs else ["默认背景"],
            state="readonly",
            style="Custom.TCombobox",
            width=15
        ).grid(row=row_col0, column=0, sticky=tk.E, pady=6, padx=(10, 5))
        row_col0 += 1

        # 4. 表情选择
        ttk.Label(main_frame, text="表情：", style="Normal.TLabel").grid(
            row=row_col0, column=0, sticky=tk.W, pady=6, padx=(5, 10))
        self.expression_var = tk.StringVar(
            value=str(self.config["expression"]) if self.config["expression"] else "自动")
        ttk.Combobox(
            main_frame,
            textvariable=self.expression_var,
            values=["自动"] + [str(i) for i in range(1, 16)],
            state="readonly",
            style="Custom.TCombobox",
            width=15
        ).grid(row=row_col0, column=0, sticky=tk.E, pady=6, padx=(10, 5))
        row_col0 += 1

        # 5. 启用LaTeX转换（复选框）
        self.latex_var = tk.BooleanVar(value=self.config["latex_enabled"])
        ttk.Checkbutton(
            main_frame,
            text="启用LaTeX转换",
            variable=self.latex_var,
            style="Custom.TCheckbutton"
        ).grid(row=row_col0, column=0, sticky=tk.W, pady=6, padx=5)
        row_col0 += 1

        # 6. DELAY值
        ttk.Label(main_frame, text="DELAY值：", style="Normal.TLabel").grid(
            row=row_col0, column=0, sticky=tk.W, pady=6, padx=(5, 10))
        self.delay_var = tk.StringVar(value=str(self.config["delay"]))
        ttk.Entry(
            main_frame,
            textvariable=self.delay_var,
            style="Custom.TEntry",
            width=8
        ).grid(row=row_col0, column=0, sticky=tk.E, pady=6, padx=(10, 5))
        row_col0 += 1

        # 7. 启用图片压缩（复选框）
        self.reduce_var = tk.BooleanVar(value=self.config["reduce_image"])
        ttk.Checkbutton(
            main_frame,
            text="启用图片压缩",
            variable=self.reduce_var,
            style="Custom.TCheckbutton"
        ).grid(row=row_col0, column=0, sticky=tk.W, pady=6, padx=5)
        row_col0 += 1

        # ---------------------- 右列控件（快捷键与功能） ----------------------
        # 1. 自动粘贴生成的图片（复选框）
        self.auto_paste_var = tk.BooleanVar(value=self.config["auto_paste"])
        ttk.Checkbutton(
            main_frame,
            text="自动粘贴生成的图片",
            variable=self.auto_paste_var,
            style="Custom.TCheckbutton"
        ).grid(row=row_col1, column=1, sticky=tk.W, pady=6, padx=5)
        row_col1 += 1

        # 2. 生成图片后自动发送（复选框）
        self.auto_send_var = tk.BooleanVar(value=self.config["auto_send"])
        ttk.Checkbutton(
            main_frame,
            text="生成图片后自动发送",
            variable=self.auto_send_var,
            style="Custom.TCheckbutton"
        ).grid(row=row_col1, column=1, sticky=tk.W, pady=6, padx=5)
        row_col1 += 1

        # 3. 阻塞按键（复选框）
        self.block_hotkey_var = tk.BooleanVar(value=self.config["block_hotkey"])
        ttk.Checkbutton(
            main_frame,
            text="阻塞按键",
            variable=self.block_hotkey_var,
            style="Custom.TCheckbutton"
        ).grid(row=row_col1, column=1, sticky=tk.W, pady=6, padx=5)
        row_col1 += 1

        # 4. 启用窗口白名单（复选框）
        self.whitelist_var = tk.BooleanVar(value=self.config["enable_whitelist"])
        ttk.Checkbutton(
            main_frame,
            text="启用窗口白名单",
            variable=self.whitelist_var,
            style="Custom.TCheckbutton"
        ).grid(row=row_col1, column=1, sticky=tk.W, pady=6, padx=5)
        row_col1 += 1

        # 5. 全选快捷键
        ttk.Label(main_frame, text="全选快捷键：", style="Normal.TLabel").grid(
            row=row_col1, column=1, sticky=tk.W, pady=6, padx=(5, 10))
        self.select_all_var = tk.StringVar(value=self.config["select_all_hotkey"])
        ttk.Entry(
            main_frame,
            textvariable=self.select_all_var,
            style="Custom.TEntry",
            width=8
        ).grid(row=row_col1, column=1, sticky=tk.E, pady=6, padx=(10, 5))
        row_col1 += 1

        # 6. 剪切快捷键
        ttk.Label(main_frame, text="剪切快捷键：", style="Normal.TLabel").grid(
            row=row_col1, column=1, sticky=tk.W, pady=6, padx=(5, 10))
        self.cut_var = tk.StringVar(value=self.config["cut_hotkey"])
        ttk.Entry(
            main_frame,
            textvariable=self.cut_var,
            style="Custom.TEntry",
            width=8
        ).grid(row=row_col1, column=1, sticky=tk.E, pady=6, padx=(10, 5))
        row_col1 += 1

        # 7. 粘贴快捷键
        ttk.Label(main_frame, text="粘贴快捷键：", style="Normal.TLabel").grid(
            row=row_col1, column=1, sticky=tk.W, pady=6, padx=(5, 10))
        self.paste_var = tk.StringVar(value=self.config["paste_hotkey"])
        ttk.Entry(
            main_frame,
            textvariable=self.paste_var,
            style="Custom.TEntry",
            width=8
        ).grid(row=row_col1, column=1, sticky=tk.E, pady=6, padx=(10, 5))
        row_col1 += 1

        # 8. 发送消息快捷键
        ttk.Label(main_frame, text="发送消息快捷键：", style="Normal.TLabel").grid(
            row=row_col1, column=1, sticky=tk.W, pady=6, padx=(5, 10))
        self.send_var = tk.StringVar(value=self.config["send_hotkey"])
        ttk.Entry(
            main_frame,
            textvariable=self.send_var,
            style="Custom.TEntry",
            width=8
        ).grid(row=row_col1, column=1, sticky=tk.E, pady=6, padx=(10, 5))
        row_col1 += 1

        # 9. 生成热键
        ttk.Label(main_frame, text="生成热键：", style="Normal.TLabel").grid(
            row=row_col1, column=1, sticky=tk.W, pady=6, padx=(5, 10))
        self.hotkey_var = tk.StringVar(value=self.config["hotkey"])
        ttk.Entry(
            main_frame,
            textvariable=self.hotkey_var,
            style="Custom.TEntry",
            width=8
        ).grid(row=row_col1, column=1, sticky=tk.E, pady=6, padx=(10, 5))
        row_col1 += 1

        # ---------------------- 底部按钮区域（跨两列） ----------------------
        max_row = max(row_col0, row_col1)  # 确保按钮在最下方
        button_frame = ttk.Frame(main_frame, style="Main.TFrame")
        button_frame.grid(row=max_row, column=0, columnspan=2, pady=15)

        # 按钮布局（增加宽度避免文字截断）
        ttk.Button(
            button_frame,
            text="进行预生成",
            command=self.pre_generate,
            style="Custom.TButton",
            width=12
        ).grid(row=0, column=0, padx=8)

        ttk.Button(
            button_frame,
            text="清除预生成图片",
            command=self.clear_pregen,
            style="Custom.TButton",
            width=14
        ).grid(row=0, column=1, padx=8)

        ttk.Button(
            button_frame,
            text="保存设置",
            command=self.save_settings,
            style="Custom.TButton",
            width=10
        ).grid(row=0, column=2, padx=8)

        ttk.Button(
            button_frame,
            text="退出程序",
            command=self.quit_program,
            style="Custom.TButton",
            width=10
        ).grid(row=0, column=3, padx=8)

        # 底部状态提示（跨两列）
        self.status_var = tk.StringVar(value="窗口已恢复 | 按{}启动/停止功能".format(self.config["global_hotkey"]))
        ttk.Label(
            main_frame,
            textvariable=self.status_var,
            style="Normal.TLabel"
        ).grid(row=max_row + 1, column=0, columnspan=2, pady=10)

        # 强制刷新布局
        main_frame.update_idletasks()

    # 以下为原有功能逻辑（托盘、热键、生成图片等，保持不变）
    def init_tray(self):
        try:
            icon = PILImage.new('RGB', (16, 16), color=(93, 63, 211))  # 紫色托盘图标
            menu = pystray.Menu(
                pystray.MenuItem("显示窗口", self.show_window),
                pystray.MenuItem("退出程序", self.quit_program)
            )
            self.tray_icon = pystray.Icon("图片生成器", icon, "图片生成器", menu)
            self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
            self.tray_thread.start()
            print("系统托盘初始化成功")
        except Exception as e:
            print(f"托盘初始化失败: {e}")
            self.root.deiconify()

    def hide_to_tray(self):
        self.root.withdraw()
        self.status_var.set("程序已最小化到系统托盘 | 按{}启动/停止".format(self.config["global_hotkey"]))
        print("窗口已隐藏到托盘")

    def show_window(self, icon=None, item=None):
        self.root.deiconify()
        self.root.lift()
        self.update_background()
        # 手动校准面板到窗口正中央
        canvas_width = self.canvas.winfo_width()
        canvas_height = self.canvas.winfo_height()
        self.canvas.coords(self.panel_window, canvas_width // 2, canvas_height // 2)
        self.status_var.set("窗口已恢复 | 按{}启动/停止功能".format(self.config["global_hotkey"]))
        print("窗口已恢复")

    def quit_program(self, icon=None, item=None):
        try:
            if self.is_running:
                self.stop_running()
            keyboard.unhook_all()
            if self.tray_icon:
                self.tray_icon.stop()
            self.root.destroy()
            sys.exit(0)
        except Exception as e:
            print(f"退出失败: {e}")
            sys.exit(1)

    def start_hotkey_listener(self):
        try:
            keyboard.unhook_all()
            keyboard.add_hotkey(self.config["global_hotkey"], self.toggle_running)
            print(f"热键监听启动: {self.config['global_hotkey']}")
        except Exception as e:
            print(f"热键启动失败: {e}")
            self.status_var.set(f"热键错误: {str(e)[:20]}")

    def toggle_running(self):
        if self.is_running:
            self.stop_running()
            self.status_var.set("功能已停止 | 按{}重新启动".format(self.config["global_hotkey"]))
        else:
            self.start_running()
            self.status_var.set("功能已启动 | 按{}停止".format(self.config["global_hotkey"]))

    def start_running(self):
        try:
            self.save_settings()
            self.is_running = True
            keyboard.add_hotkey(self.config["hotkey"], self.generate_image_handler, suppress=self.config["block_hotkey"])
        except Exception as e:
            print(f"启动失败: {e}")
            self.status_var.set(f"启动失败: {str(e)[:20]}")

    def stop_running(self):
        try:
            keyboard.remove_hotkey(self.config["hotkey"])
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
            except:
                pass

    def generate_image_handler(self):
        if self.config["enable_whitelist"]:
            current_window = self.get_window_exe_name()
            if current_window not in self.config["window_whitelist"]:
                print("窗口不在白名单，跳过")
                keyboard.send(self.config["hotkey"])
                return
        threading.Thread(target=self._generate_image_thread, daemon=True).start()

    def _generate_image_thread(self):
        try:
            text = self.cut_all_and_get_text()
            png_bytes, _ = generate_image(
                text=text,
                character_name=self.config["current_character"],
                background_name=self.config["current_background"],
                expression=self.config["expression"],
                latex_insert=self.config["latex_enabled"],
                reduce=self.config["reduce_image"]
            )
            self.copy_png_bytes_to_clipboard(png_bytes)
            if self.config["auto_paste"]:
                keyboard.send(self.config["paste_hotkey"])
                if self.config["auto_send"]:
                    time.sleep(0.3)
                    keyboard.send(self.config["send_hotkey"])
            self.status_var.set(f"生成完成: {text[:20]}...")
        except Exception as e:
            print(f"生成失败: {e}")
            self.status_var.set(f"生成失败: {str(e)[:20]}")

    def cut_all_and_get_text(self):
        """剪切文本并转换LaTeX"""
        old_clip = pyperclip.paste()
        pyperclip.copy("")
        keyboard.send(self.config["select_all_hotkey"])
        keyboard.send(self.config["cut_hotkey"])
        time.sleep(self.config["delay"])
        new_clip = pyperclip.paste()
        # LaTeX转换
        if self.config["latex_enabled"] and new_clip.strip() != "":
            new_clip = convert_latex_in_text(new_clip)
            pyperclip.copy(new_clip)
        return new_clip

    def pre_generate(self):
        """预生成图片"""
        character = self.character_var.get()
        background = self.background_var.get()
        if not character or not background:
            print("请选择角色和背景")
            self.status_var.set("预生成失败：请选择角色和背景")
            return
        self.status_var.set(f"正在预生成 {character} - {background} 的图片...")
        self.root.update()
        try:
            success = pre_generate_character_images(character, background)
            self.status_var.set(f"预生成{'完成' if success else '已存在，跳过'}: {character} - {background}")
        except Exception as e:
            print(f"预生成失败: {e}")
            self.status_var.set(f"预生成失败: {str(e)[:30]}")

    def clear_pregen(self):
        """清除预生成图片"""
        if messagebox.askyesno("确认", "确定清除所有预生成图片？"):
            try:
                delate(get_pregen_folder())
                self.status_var.set("预生成图片已清除")
            except Exception as e:
                messagebox.showerror("错误", f"清除失败: {e}")
                self.status_var.set(f"清除失败: {str(e)[:30]}")

    def save_settings(self):
        """保存设置"""
        try:
            self.config["global_hotkey"] = self.global_hotkey_var.get()
            self.config["current_character"] = self.character_var.get()
            self.config["current_background"] = self.background_var.get()
            self.config["expression"] = int(self.expression_var.get()) if self.expression_var.get() != "自动" else None
            self.config["latex_enabled"] = self.latex_var.get()
            self.config["delay"] = float(self.delay_var.get())
            self.config["reduce_image"] = self.reduce_var.get()
            self.config["auto_paste"] = self.auto_paste_var.get()
            self.config["auto_send"] = self.auto_send_var.get()
            self.config["block_hotkey"] = self.block_hotkey_var.get()
            self.config["enable_whitelist"] = self.whitelist_var.get()
            self.config["select_all_hotkey"] = self.select_all_var.get()
            self.config["cut_hotkey"] = self.cut_var.get()
            self.config["paste_hotkey"] = self.paste_var.get()
            self.config["send_hotkey"] = self.send_var.get()
            self.config["hotkey"] = self.hotkey_var.get()
            # 保存配置
            self.save_config()
            # 重启热键监听
            if self.is_running:
                self.stop_running()
            self.start_hotkey_listener()
            self.status_var.set("设置已保存并应用 | 按{}启动/停止功能".format(self.config["global_hotkey"]))
        except ValueError as e:
            messagebox.showerror("错误", f"输入值无效: {e}")
            self.status_var.set(f"保存失败: 输入值无效 - {str(e)[:20]}")
        except Exception as e:
            messagebox.showerror("错误", f"保存设置失败: {e}")
            self.status_var.set(f"保存失败: {str(e)[:20]}")

def main():
    """主函数：隐藏命令行窗口"""
    if sys.platform == "win32":
        import ctypes
        ctypes.windll.user32.ShowWindow(ctypes.windll.kernel32.GetConsoleWindow(), 0)

    root = tk.Tk()
    app = ImageGeneratorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    # 安装依赖（首次运行可取消注释）
    # os.system("pip install pystray pillow keyboard pywin32 psutil")
    main()