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

# resource path handling (兼容打包后的 resource 目录)
exe_dir = os.path.dirname(sys.executable) if getattr(sys, 'frozen', False) else None
resource_dir = os.path.join(exe_dir, 'resource') if exe_dir else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resource')
if os.path.isdir(resource_dir) and resource_dir not in sys.path:
    sys.path.insert(0, resource_dir)

try:
    from info import background_configs, characters, text_configs_dict, DEFAULT_BACKGROUND
    from api import get_emotion_from_text, get_emotion_name, DEFAULT_EMOTION
    from text_to_image import generate_image, pre_generate_character_images, get_pregen_folder, delate
    from latex import convert_latex_in_text
except Exception as e:
    print(f"依赖模块导入失败: {e}，使用最小模拟")
    background_configs = {"默认背景": {}}
    characters = {"默认角色": {}}
    text_configs_dict = {}
    DEFAULT_BACKGROUND = "默认背景"
    DEFAULT_EMOTION = 1
    def get_emotion_from_text(*a, **k): return 1
    def get_emotion_name(*a, **k): return "默认"
    def generate_image(*a, **k): return b"", {}
    def pre_generate_character_images(*a, **k): return True
    def get_pregen_folder(): return "./pregen"
    def delate(*a, **k): pass
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


class ImageGeneratorGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("图片生成器")
        self.root.geometry("960x540")  # 调整为背景图片尺寸
        self.root.resizable(False, False)  # 禁止调整窗口大小，以匹配背景图片
        self.root.withdraw()

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
                    loaded = json.load(f)
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
                  background=[("active", "#4A2CA0"), ("disabled", "#3A2557")])
        
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
                  foreground=[("disabled", "#9A9A9A"), ("!disabled", "black")])

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

    def create_checkbutton_with_outline(self, text, x, y, variable, font_size=9, bold=False):
        """创建带有描边文本的复选框"""
        # 首先创建复选框
        cb = tk.Checkbutton(self.canvas, variable=variable, bg="#2A1B3D", 
                           activebackground="#2A1B3D", selectcolor="#2A1B3D",
                           highlightthickness=0, bd=0)
        cb.place(x=x, y=y)
        
        # 然后创建复选框的文本标签（带描边）
        text_x = x + 25  # 复选框宽度约20像素 + 5像素间距
        text_y = y + 5   # 向下移动3像素
        self.create_text_with_outline(text, text_x, text_y, font_size=font_size, bold=bold)
        
        return cb

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
        
        # 角色选择
        self.create_text_with_outline("角色：", 
                                      left_start_x, left_start_y + row_height)
        self.character_var = tk.StringVar(value=self.config["current_character"])
        character_cb = ttk.Combobox(self.canvas, textvariable=self.character_var,
                     values=list(characters.keys()) if characters else ["默认角色"], 
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
        
        # 表情选择
        self.create_text_with_outline("表情：", 
                                      left_start_x, left_start_y + 3 * row_height)
        self.expression_var = tk.StringVar(value=str(self.config.get("expression") or "自动"))
        expression_cb = ttk.Combobox(self.canvas, textvariable=self.expression_var,
                     values=["自动"] + [str(i) for i in range(1, 16)], state="readonly",
                     style="Custom.TCombobox", width=18)
        expression_cb.place(x=left_start_x + 170, y=left_start_y + 3 * row_height - 3)
        
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
        
        # 图片压缩 - 使用新的带描边的复选框
        self.reduce_var = tk.BooleanVar(value=self.config.get("reduce_image", True))
        self.reduce_cb = self.create_checkbutton_with_outline("启用图片压缩", 
                                      left_start_x, left_start_y + 6 * row_height,
                                      self.reduce_var)
        
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
        button_start_x = 250
        button_y = 420
        
        ttk.Button(self.canvas, text="进行预生成", command=self.pre_generate, 
                  style="Custom.TButton", width=12).place(x=button_start_x, y=button_y)
        ttk.Button(self.canvas, text="清除预生成图片", command=self.clear_pregen, 
                  style="Custom.TButton", width=14).place(x=button_start_x + 130, y=button_y)
        ttk.Button(self.canvas, text="保存设置", command=self.save_settings, 
                  style="Custom.TButton", width=10).place(x=button_start_x + 260, y=button_y)
        ttk.Button(self.canvas, text="退出程序", command=self.quit_program, 
                  style="Custom.TButton", width=10).place(x=button_start_x + 370, y=button_y)
        
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

    def _generate_image_thread(self):
        try:
            text = self.cut_all_and_get_text()
            png_bytes, _ = generate_image(text=text,
                                         character_name=self.config['current_character'],
                                         background_name=self.config['current_background'],
                                         expression=self.config.get('expression'),
                                         latex_insert=self.config.get('latex_enabled', False),
                                         reduce=self.config.get('reduce_image', True))
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

    def pre_generate(self):
        char = self.character_var.get()
        bg = self.background_var.get()
        if not char or not bg:
            self.status_var.set("预生成失败：请选择角色和背景")
            return
        self.status_var.set(f"正在预生成 {char} - {bg} 的图片...")
        self.root.update()
        try:
            ok = pre_generate_character_images(char, bg)
            self.status_var.set(f"预生成{'完成' if ok else '已存在，跳过'}: {char} - {bg}")
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

    def save_settings(self):
        try:
            self.config['global_hotkey'] = self.global_hotkey_var.get()
            self.config['current_character'] = self.character_var.get()
            self.config['current_background'] = self.background_var.get()
            try:
                self.config['expression'] = int(self.expression_var.get()) if self.expression_var.get() != '自动' else None
            except Exception:
                self.config['expression'] = None
            self.config['latex_enabled'] = bool(self.latex_var.get())
            self.config['delay'] = float(self.delay_var.get())
            self.config['reduce_image'] = bool(self.reduce_var.get())
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