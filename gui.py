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
from PIL import Image

# 导入必要的模块
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from info import background_configs, characters, text_configs_dict, DEFAULT_BACKGROUND
from api import get_emotion_from_text, get_emotion_name, DEFAULT_EMOTION, set_api_key
from text_to_image import generate_image, pre_generate_character_images, get_pregen_folder, delate
from latex import convert_latex_in_text

# 配置文件名
CONFIG_FILE = "gui_config.json"

class ImageGeneratorGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("图片生成器")
        self.root.geometry("600x750")  # 增加高度以容纳API Key输入框
        
        # 初始化变量
        self.character_display_names = {}
        self.character_folder_names = {}
        self.config = self.load_config()
        self.is_running = False
        self.hotkey_thread = None
        
        # 在load_config之后建立角色映射
        self.setup_character_mappings()
        
        # 创建界面
        self.create_widgets()
        
        # 绑定关闭事件
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        # 启动热键监听
        self.start_hotkey_listener()
    
    def setup_character_mappings(self):
        """设置角色名称映射"""
        for folder_name, char_info in characters.items():
            display_name = char_info.get("display_name", folder_name)
            self.character_display_names[folder_name] = display_name
            self.character_folder_names[display_name] = folder_name
    
    def get_character_display_names(self):
        """获取角色显示名列表"""
        return sorted(self.character_display_names.values())
    
    def get_folder_name_by_display_name(self, display_name):
        """根据显示名获取文件夹名"""
        return self.character_folder_names.get(display_name, display_name)
    
    def get_display_name_by_folder_name(self, folder_name):
        """根据文件夹名获取显示名"""
        return self.character_display_names.get(folder_name, folder_name)
    
    def load_config(self):
        """加载配置文件"""
        default_config = {
            "global_hotkey": "alt+shift+a",
            "current_character": list(characters.keys())[0] if characters else "default",
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
            "enable_whitelist": True,
            "api_key": ""  # 添加API Key配置
        }
        
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                    
                    # 直接返回加载的配置，不需要在此时转换角色名
                    for key, value in default_config.items():
                        if key not in loaded_config:
                            loaded_config[key] = value
                    return loaded_config
            except Exception as e:
                print(f"加载配置文件失败: {e}")
                return default_config
        else:
            return default_config
    
    def save_config(self):
        """保存配置文件"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, ensure_ascii=False, indent=2)
        except Exception as e:
            messagebox.showerror("错误", f"保存配置文件失败: {e}")
    
    def create_widgets(self):
        """创建界面控件"""
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重，使界面可缩放
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="图片生成器", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 20))
        
        # 运行状态
        self.running_var = tk.StringVar(value="程序未运行")
        running_label = ttk.Label(main_frame, textvariable=self.running_var, foreground="red")
        running_label.grid(row=1, column=0, columnspan=2, pady=(0, 10))
        
        row = 2
        
        # API Key设置
        ttk.Label(main_frame, text="DeepSeek API Key:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.api_key_var = tk.StringVar(value=self.config["api_key"])
        
        # 创建带边框的Frame来包裹Entry
        self.api_key_frame = ttk.Frame(main_frame)  # 保存为实例变量
        self.api_key_frame.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        
        self.api_key_entry = ttk.Entry(self.api_key_frame, textvariable=self.api_key_var, show="*", width=30)
        self.api_key_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 显示/隐藏API Key的按钮
        self.api_key_visible = False
        self.api_key_toggle_btn = ttk.Button(self.api_key_frame, text="👁", width=2, 
                                           command=self.toggle_api_key_visibility)
        self.api_key_toggle_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        row += 1
        
        # 分隔线
        separator = ttk.Separator(main_frame, orient='horizontal')
        separator.grid(row=row, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=10)
        row += 1
        
        # 全局热键设置
        ttk.Label(main_frame, text="全局热键:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.global_hotkey_var = tk.StringVar(value=self.config["global_hotkey"])
        global_hotkey_entry = ttk.Entry(main_frame, textvariable=self.global_hotkey_var)
        global_hotkey_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # 角色选择 - 使用显示名
        ttk.Label(main_frame, text="角色:").grid(row=row, column=0, sticky=tk.W, pady=5)
        
        # 获取当前角色的显示名
        current_folder = self.config["current_character"]
        current_display = self.get_display_name_by_folder_name(current_folder)
        
        # 获取所有角色的显示名
        character_display_list = self.get_character_display_names()
        
        self.character_var = tk.StringVar(value=current_display)
        character_combo = ttk.Combobox(main_frame, textvariable=self.character_var, 
                                      values=character_display_list, state="readonly")
        character_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # 背景选择
        ttk.Label(main_frame, text="背景:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.background_var = tk.StringVar(value=self.config["current_background"])
        background_combo = ttk.Combobox(main_frame, textvariable=self.background_var, 
                                       values=list(background_configs.keys()), state="readonly")
        background_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # 表情选择
        ttk.Label(main_frame, text="表情:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.expression_var = tk.StringVar(value=str(self.config["expression"]) if self.config["expression"] else "自动")
        expression_combo = ttk.Combobox(main_frame, textvariable=self.expression_var, 
                                       values=["自动"] + [str(i) for i in range(1, 16)], state="readonly")
        expression_combo.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # LaTeX开关
        self.latex_var = tk.BooleanVar(value=self.config["latex_enabled"])
        latex_check = ttk.Checkbutton(main_frame, text="启用LaTeX转换", variable=self.latex_var)
        latex_check.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1
        
        # DELAY值
        ttk.Label(main_frame, text="DELAY值:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.delay_var = tk.StringVar(value=str(self.config["delay"]))
        delay_entry = ttk.Entry(main_frame, textvariable=self.delay_var)
        delay_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # 图片压缩开关
        self.reduce_var = tk.BooleanVar(value=self.config["reduce_image"])
        reduce_check = ttk.Checkbutton(main_frame, text="启用图片压缩", variable=self.reduce_var)
        reduce_check.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1
        
        # 自动粘贴开关
        self.auto_paste_var = tk.BooleanVar(value=self.config["auto_paste"])
        auto_paste_check = ttk.Checkbutton(main_frame, text="自动粘贴生成的图片", variable=self.auto_paste_var)
        auto_paste_check.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1
        
        # 自动发送开关
        self.auto_send_var = tk.BooleanVar(value=self.config["auto_send"])
        auto_send_check = ttk.Checkbutton(main_frame, text="生成图片后自动发送", variable=self.auto_send_var)
        auto_send_check.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1
        
        # 阻塞按键开关
        self.block_hotkey_var = tk.BooleanVar(value=self.config["block_hotkey"])
        block_hotkey_check = ttk.Checkbutton(main_frame, text="阻塞按键", variable=self.block_hotkey_var)
        block_hotkey_check.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1
        
        # 窗口白名单开关
        self.whitelist_var = tk.BooleanVar(value=self.config["enable_whitelist"])
        whitelist_check = ttk.Checkbutton(main_frame, text="启用窗口白名单", variable=self.whitelist_var)
        whitelist_check.grid(row=row, column=0, columnspan=2, sticky=tk.W, pady=5)
        row += 1
        
        # 全选快捷键
        ttk.Label(main_frame, text="全选快捷键:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.select_all_var = tk.StringVar(value=self.config["select_all_hotkey"])
        select_all_entry = ttk.Entry(main_frame, textvariable=self.select_all_var)
        select_all_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # 剪切快捷键
        ttk.Label(main_frame, text="剪切快捷键:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.cut_var = tk.StringVar(value=self.config["cut_hotkey"])
        cut_entry = ttk.Entry(main_frame, textvariable=self.cut_var)
        cut_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # 粘贴快捷键
        ttk.Label(main_frame, text="粘贴快捷键:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.paste_var = tk.StringVar(value=self.config["paste_hotkey"])
        paste_entry = ttk.Entry(main_frame, textvariable=self.paste_var)
        paste_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # 发送消息快捷键
        ttk.Label(main_frame, text="发送消息快捷键:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.send_var = tk.StringVar(value=self.config["send_hotkey"])
        send_entry = ttk.Entry(main_frame, textvariable=self.send_var)
        send_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # HOTKEY
        ttk.Label(main_frame, text="生成热键:").grid(row=row, column=0, sticky=tk.W, pady=5)
        self.hotkey_var = tk.StringVar(value=self.config["hotkey"])
        hotkey_entry = ttk.Entry(main_frame, textvariable=self.hotkey_var)
        hotkey_entry.grid(row=row, column=1, sticky=(tk.W, tk.E), pady=5)
        row += 1
        
        # 按钮框架
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)
        
        # 预生成按钮
        pregen_button = ttk.Button(button_frame, text="进行预生成", command=self.pre_generate)
        pregen_button.grid(row=0, column=0, padx=5)
        
        # 清除预生成图片按钮
        clear_button = ttk.Button(button_frame, text="清除预生成图片", command=self.clear_pregen)
        clear_button.grid(row=0, column=1, padx=5)
        
        # 保存按钮
        save_button = ttk.Button(button_frame, text="保存设置", command=self.save_settings)
        save_button.grid(row=0, column=2, padx=5)
        
        # 状态标签
        self.status_var = tk.StringVar(value="就绪")
        status_label = ttk.Label(main_frame, textvariable=self.status_var, foreground="blue")
        status_label.grid(row=row+1, column=0, columnspan=2, pady=10)
    
    def toggle_api_key_visibility(self):
        """切换API Key显示/隐藏"""
        self.api_key_visible = not self.api_key_visible
        
        if self.api_key_visible:
            self.api_key_entry.config(show="")
            self.api_key_toggle_btn.config(text="👁‍🗨")
        else:
            self.api_key_entry.config(show="*")
            self.api_key_toggle_btn.config(text="👁")
    
    def start_hotkey_listener(self):
        """启动热键监听"""
        try:
            # 移除之前的热键
            keyboard.unhook_all()
            
            # 添加全局热键
            global_hotkey = self.config["global_hotkey"]
            keyboard.add_hotkey(global_hotkey, self.toggle_running)
            
            self.is_running = False
            self.running_var.set(f"程序已启动，按 {global_hotkey} 开始运行")
            self.status_var.set("热键监听已启动")
            
        except Exception as e:
            messagebox.showerror("错误", f"启动热键监听失败: {e}")
    
    def toggle_running(self):
        """切换运行状态"""
        if self.is_running:
            self.stop_running()
        else:
            self.start_running()
    
    def start_running(self):
        """开始运行图片生成功能"""
        try:
            # 保存当前设置
            self.save_settings()
            
            # 设置运行状态
            self.is_running = True
            self.running_var.set("程序运行中...")
            
            # 添加生成热键
            hotkey = self.config["hotkey"]
            keyboard.add_hotkey(hotkey, self.generate_image_handler, 
                              suppress=self.config["block_hotkey"])
            
            self.status_var.set("程序运行中，等待热键触发")
            
        except Exception as e:
            messagebox.showerror("错误", f"启动运行失败: {e}")
    
    def stop_running(self):
        """停止运行图片生成功能"""
        try:
            # 移除生成热键
            keyboard.remove_hotkey(self.config["hotkey"])
            
            # 设置运行状态
            self.is_running = False
            self.running_var.set("程序已停止")
            self.status_var.set("程序已停止")
            
        except Exception as e:
            print(f"停止运行失败: {e}")
    
    def get_window_exe_name(self):
        """获取当前窗口的EXE名称"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process = psutil.Process(pid)
            exe_path = process.exe()
            return os.path.basename(exe_path)
        except Exception as e:
            print(f"获取窗口名时发生错误：{e}")
            return None
    
    def copy_png_bytes_to_clipboard(self, png_bytes: bytes):
        """将PNG图片字节流复制到剪贴板"""
        try:
            win32clipboard.OpenClipboard()
            win32clipboard.EmptyClipboard()
            
            # 直接设置PNG格式到剪贴板
            png_format = win32clipboard.RegisterClipboardFormat("PNG")
            win32clipboard.SetClipboardData(png_format, png_bytes)
            
            # 同时设置DIB格式作为后备，确保兼容性
            image = Image.open(io.BytesIO(png_bytes))
            with io.BytesIO() as output:
                image.convert("RGB").save(output, "BMP")
                bmp_data = output.getvalue()[14:]
                win32clipboard.SetClipboardData(win32clipboard.CF_DIB, bmp_data)
                
            win32clipboard.CloseClipboard()
            
        except Exception as e:
            print(f"剪贴板传输失败: {e}")
            try:
                win32clipboard.CloseClipboard()
            except:
                pass
    
    def generate_image_handler(self):
        """处理图片生成"""
        # 检查窗口白名单
        if self.config["enable_whitelist"]:
            current_window = self.get_window_exe_name()
            if current_window not in self.config["window_whitelist"]:
                print("当前窗口不在白名单内")
                keyboard.send(self.config["hotkey"])
                return
        
        # 在新线程中执行图片生成
        threading.Thread(target=self._generate_image_thread, daemon=True).start()
    
    def _generate_image_thread(self):
        """在新线程中生成图片"""
        try:
            text = self.cut_all_and_get_text()
            
            print(f"获取到的文本: {text}")
            
            # 生成图片 - 使用文件夹名
            character_folder = self.config["current_character"]
            background_name = self.config["current_background"]
            expression = self.config["expression"]
            
            png_bytes, info_dict = generate_image(
                text=text,
                character_name=character_folder,  # 这里传入的是文件夹名
                background_name=background_name,
                emotion_id=None,
                expression=expression,
                latex_insert=self.config["latex_enabled"],
                reduce=self.config["reduce_image"]
            )
            
            # 复制到剪贴板
            self.copy_png_bytes_to_clipboard(png_bytes)
            
            # 自动粘贴和发送
            if self.config["auto_paste"]:
                keyboard.send(self.config["paste_hotkey"])
                if self.config["auto_send"]:
                    time.sleep(0.3)
                    keyboard.send(self.config["send_hotkey"])
            
            print(f"图片生成完成: {info_dict}")
            self.status_var.set("图片生成完成")
            
        except Exception as e:
            print(f"图片生成失败: {e}")
            self.status_var.set("图片生成失败")
    
    def cut_all_and_get_text(self):
        """模拟 Ctrl+A / Ctrl+X 剪切全部文本，并返回剪切得到的内容"""
        # 备份原剪贴板
        old_clip = pyperclip.paste()
        # 清空剪贴板，防止读到旧数据
        pyperclip.copy("")

        # 发送 Ctrl+A 和 Ctrl+X
        keyboard.send(self.config["select_all_hotkey"])
        keyboard.send(self.config["cut_hotkey"])
        time.sleep(self.config["delay"])

        # 获取剪切后的内容
        new_clip = pyperclip.paste()

        # ===== 仅当有文本时，才调用LaTeX转换 =====
        if self.config["latex_enabled"] and new_clip.strip() != "":
            converted_text = convert_latex_in_text(new_clip)
            if converted_text != new_clip:
                print(f"LaTeX转换: {new_clip} -> {converted_text}")
                new_clip = converted_text
                pyperclip.copy(new_clip)

        return new_clip
    
    def pre_generate(self):
        """执行预生成"""
        character_display = self.character_var.get()
        background = self.background_var.get()
        
        if not character_display or not background:
            messagebox.showerror("错误", "请先选择角色和背景")
            return
        
        # 将显示名转换为文件夹名
        character_folder = self.get_folder_name_by_display_name(character_display)
        
        self.status_var.set(f"正在预生成 {character_display} 在 {background} 背景下的图片...")
        self.root.update()
        
        try:
            success = pre_generate_character_images(character_folder, background)
            if success:
                self.status_var.set(f"{character_display} 在 {background} 背景下的图片预生成完成")
            else:
                self.status_var.set(f"{character_display} 在 {background} 背景下的图片已存在，跳过生成")
        except Exception as e:
            messagebox.showerror("错误", f"预生成失败: {e}")
            self.status_var.set("预生成失败")
    
    def clear_pregen(self):
        """清除预生成图片"""
        result = messagebox.askyesno("确认", "确定要清除所有预生成图片吗？")
        if result:
            try:
                pregen_folder = get_pregen_folder()
                delate(pregen_folder)
                self.status_var.set("预生成图片已清除")
            except Exception as e:
                messagebox.showerror("错误", f"清除失败: {e}")
                self.status_var.set("清除失败")
    
    def save_settings(self):
        """保存设置"""
        try:
            # 更新配置字典
            self.config["global_hotkey"] = self.global_hotkey_var.get()
            
            # 将显示名转换为文件夹名存储
            character_display = self.character_var.get()
            character_folder = self.get_folder_name_by_display_name(character_display)
            self.config["current_character"] = character_folder
            
            self.config["current_background"] = self.background_var.get()
            
            # 保存API Key
            self.config["api_key"] = self.api_key_var.get()
            
            # 设置API Key
            set_api_key(self.config["api_key"])
            
            expression = self.expression_var.get()
            self.config["expression"] = int(expression) if expression != "自动" else None
            
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
            
            # 保存到文件
            self.save_config()
            
            # 重新启动热键监听
            if self.is_running:
                self.stop_running()
            self.start_hotkey_listener()
            
            self.status_var.set("设置已保存并应用")
            
        except ValueError as e:
            messagebox.showerror("错误", f"输入值无效: {e}")
        except Exception as e:
            messagebox.showerror("错误", f"保存设置失败: {e}")
    
    def on_closing(self):
        """关闭窗口时的处理"""
        # 停止运行
        if self.is_running:
            self.stop_running()
        
        # 移除所有热键
        keyboard.unhook_all()
        
        # 自动保存设置
        self.save_settings()
        
        self.root.destroy()

def main():
    root = tk.Tk()
    app = ImageGeneratorGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main()