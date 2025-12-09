# resource_manager.py
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import os
import sys
import shutil
from PIL import Image
import json

# 统一资源路径解析：优先 exe 同目录的 resource/，回退脚本目录，再次回退 _MEIPASS
def get_resource_base_dir():
    exe_dir = None
    try:
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
    except Exception:
        exe_dir = None

    if exe_dir:
        resource_dir = os.path.join(exe_dir, 'resource')
        if os.path.isdir(resource_dir):
            return resource_dir

    script_dir = os.path.dirname(os.path.abspath(__file__))
    resource_dir_script = os.path.join(script_dir, 'resource')
    if os.path.isdir(resource_dir_script):
        return resource_dir_script

    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        resource_dir_meipass = os.path.join(meipass, 'resource')
        if os.path.isdir(resource_dir_meipass):
            return resource_dir_meipass

    # 默认回退到脚本目录下的 resource（若不存在，后续会创建）
    return resource_dir_script

class ResourceManager:
    def __init__(self, root):
        self.root = root
        self.root.title("资源管理器")
        self.root.geometry("900x700")
        
        # 基础路径 - 指向 resource 文件夹（打包优先 exe 同目录）
        self.resource_dir = get_resource_base_dir()
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        
        # 背景和角色目录
        self.background_dir = os.path.join(self.resource_dir, "background")
        self.character_dir = os.path.join(self.resource_dir, "character")
        
        # 新增：字体目录
        self.fonts_dir = os.path.join(self.resource_dir, "fonts")
        
        # GUI背景和图标路径
        self.gui_bg_path = os.path.join(self.resource_dir, "guibg.png")
        self.logo_png_path = os.path.join(self.resource_dir, "logo.png")
        
        # 字体配置变量
        self.chinese_font_var = tk.StringVar(value="font3.ttf")  # 全局中文字体
        self.english_math_font_var = tk.StringVar(value="cambria.ttc")  # 全局英文/数学字体
        
        # 角色字体变量（在角色选择时动态设置）
        self.character_dialog_font_var = tk.StringVar(value="")
        self.character_name_font_var = tk.StringVar(value="")
        
        # 创建必要的目录
        os.makedirs(self.resource_dir, exist_ok=True)
        os.makedirs(self.background_dir, exist_ok=True)
        os.makedirs(self.character_dir, exist_ok=True)
        os.makedirs(self.fonts_dir, exist_ok=True)  # 新增
        
        # 当前选中的角色
        self.current_character = None

            # 当前角色的表情映射
        self.current_emotion_mapping = {}

        self.create_widgets()
        self.refresh_lists()
        self.load_font_config()  # 新增：加载已有字体配置
    
    def create_widgets(self):
        # 创建主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # 配置网格权重
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # 标题
        title_label = ttk.Label(main_frame, text="资源管理器 (资源目录: resource/)", font=("Arial", 16, "bold"))
        title_label.grid(row=0, column=0, columnspan=4, pady=(0, 20))
        
        # 创建选项卡
        notebook = ttk.Notebook(main_frame)
        notebook.grid(row=1, column=0, columnspan=4, sticky=(tk.W, tk.E, tk.N, tk.S), pady=10)
        
        # 背景管理选项卡
        bg_frame = ttk.Frame(notebook, padding="10")
        notebook.add(bg_frame, text="背景管理")
        
        # 角色管理选项卡
        char_frame = ttk.Frame(notebook, padding="10")
        notebook.add(char_frame, text="角色管理")
        
        # 新增：字体管理选项卡
        font_frame = ttk.Frame(notebook, padding="10")
        notebook.add(font_frame, text="字体管理")
        
        # 配置生成选项卡
        config_frame = ttk.Frame(notebook, padding="10")
        notebook.add(config_frame, text="配置生成")
        
        # 设置选项卡的网格权重
        bg_frame.columnconfigure(1, weight=1)
        bg_frame.rowconfigure(1, weight=1)
        char_frame.columnconfigure(1, weight=1)
        char_frame.rowconfigure(1, weight=1)
        font_frame.columnconfigure(1, weight=1)
        font_frame.rowconfigure(1, weight=1)
        config_frame.columnconfigure(1, weight=1)
        
        # 初始化各个选项卡
        self.setup_background_tab(bg_frame)
        self.setup_character_tab(char_frame)
        self.setup_font_tab(font_frame)  # 新增
        self.setup_config_tab(config_frame)
    
    def setup_background_tab(self, parent):
        """设置背景管理选项卡"""
        # 创建新背景
        ttk.Label(parent, text="创建新背景:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.new_bg_name = tk.StringVar()
        ttk.Entry(parent, textvariable=self.new_bg_name, width=20).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        ttk.Button(parent, text="创建背景文件夹", command=self.create_background_folder).grid(row=0, column=2, pady=5)
        
        # 背景列表
        ttk.Label(parent, text="现有背景:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.bg_listbox = tk.Listbox(parent, height=10)
        self.bg_listbox.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # 背景操作按钮
        bg_button_frame = ttk.Frame(parent)
        bg_button_frame.grid(row=3, column=0, columnspan=3, pady=10)
        
        ttk.Button(bg_button_frame, text="导入背景图片", command=self.import_background_images).grid(row=0, column=0, padx=5)
        ttk.Button(bg_button_frame, text="导入透明框(d.png)", command=self.import_d_image).grid(row=0, column=1, padx=5)
        ttk.Button(bg_button_frame, text="删除背景", command=self.delete_background).grid(row=0, column=2, padx=5)
        ttk.Button(bg_button_frame, text="刷新列表", command=self.refresh_background_list).grid(row=0, column=3, padx=5)
        
        # 添加分隔线
        separator = ttk.Separator(parent, orient='horizontal')
        separator.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # GUI背景和图标管理
        ttk.Label(parent, text="全局资源:", font=("Arial", 10, "bold")).grid(row=5, column=0, sticky=tk.W, pady=5)
        
        # GUI背景导入
        gui_bg_frame = ttk.Frame(parent)
        gui_bg_frame.grid(row=6, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(gui_bg_frame, text="GUI背景:").grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Button(gui_bg_frame, text="导入GUI背景", command=self.import_gui_background).grid(row=0, column=1, padx=5)
        self.gui_bg_status = ttk.Label(gui_bg_frame, text="未设置", foreground="gray")
        self.gui_bg_status.grid(row=0, column=2, padx=5)
        
        # 图标导入
        logo_frame = ttk.Frame(parent)
        logo_frame.grid(row=7, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        ttk.Label(logo_frame, text="应用程序图标:").grid(row=0, column=0, sticky=tk.W, padx=5)
        ttk.Button(logo_frame, text="导入图标", command=self.import_logo).grid(row=0, column=1, padx=5)
        self.logo_status = ttk.Label(logo_frame, text="未设置", foreground="gray")
        self.logo_status.grid(row=0, column=2, padx=5)
        
        # 更新状态显示
        self.update_gui_resource_status()
        
        # 背景图片预览
        ttk.Label(parent, text="背景图片预览:").grid(row=8, column=0, sticky=tk.W, pady=5)
        self.bg_preview_text = tk.StringVar(value="选择背景查看图片")
        ttk.Label(parent, textvariable=self.bg_preview_text).grid(row=9, column=0, columnspan=3, pady=5)
        
        # 绑定列表选择事件
        self.bg_listbox.bind('<<ListboxSelect>>', self.on_background_select)
    
    def setup_character_tab(self, parent):
        """设置角色管理选项卡"""
        # 创建新角色部分
        create_frame = ttk.LabelFrame(parent, text="创建新角色", padding="10")
        create_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # 英文文件夹名
        ttk.Label(create_frame, text="英文文件夹名:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.new_char_folder_name = tk.StringVar()
        ttk.Entry(create_frame, textvariable=self.new_char_folder_name, width=20).grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        # 角色显示名
        ttk.Label(create_frame, text="角色显示名:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.new_char_display_name = tk.StringVar()
        ttk.Entry(create_frame, textvariable=self.new_char_display_name, width=20).grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        # drawx 和 drawy 设置
        ttk.Label(create_frame, text="drawx:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.new_char_drawx = tk.StringVar(value="0")
        ttk.Entry(create_frame, textvariable=self.new_char_drawx, width=10).grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)
        
        ttk.Label(create_frame, text="drawy:").grid(row=2, column=2, sticky=tk.W, pady=5)
        self.new_char_drawy = tk.StringVar(value="0")
        ttk.Entry(create_frame, textvariable=self.new_char_drawy, width=10).grid(row=2, column=3, sticky=tk.W, pady=5, padx=5)
        
        # enlarge 设置
        ttk.Label(create_frame, text="enlarge:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.new_char_enlarge = tk.StringVar(value="1.0")
        ttk.Entry(create_frame, textvariable=self.new_char_enlarge, width=10).grid(row=3, column=1, sticky=tk.W, pady=5, padx=5)
        
        # 创建按钮 - 注意行号修正
        ttk.Button(create_frame, text="创建角色文件夹", command=self.create_character_folder).grid(row=4, column=0, columnspan=4, pady=10)
        
        # 角色列表
        ttk.Label(parent, text="现有角色:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.char_listbox = tk.Listbox(parent, height=10)
        self.char_listbox.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # 角色操作按钮
        char_button_frame = ttk.Frame(parent)
        char_button_frame.grid(row=3, column=0, columnspan=3, pady=10)
        
        ttk.Button(char_button_frame, text="导入表情图片", command=self.import_character_images).grid(row=0, column=0, padx=5)
        ttk.Button(char_button_frame, text="设置角色颜色", command=self.set_character_color).grid(row=0, column=1, padx=5)
        ttk.Button(char_button_frame, text="修改角色设置", command=self.edit_character_settings).grid(row=0, column=2, padx=5)
        ttk.Button(char_button_frame, text="删除角色", command=self.delete_character).grid(row=0, column=3, padx=5)
        ttk.Button(char_button_frame, text="刷新列表", command=self.refresh_character_list).grid(row=0, column=4, padx=5)
        
        # 角色设置显示 - 改为实例变量
        self.settings_frame = ttk.LabelFrame(parent, text="角色设置", padding="10")
        self.settings_frame.grid(row=4, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=10)
        
        # 角色颜色显示
        ttk.Label(self.settings_frame, text="角色颜色:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.char_color_label = ttk.Label(self.settings_frame, text="未设置", background="white", width=15)
        self.char_color_label.grid(row=0, column=1, sticky=tk.W, pady=5, padx=5)

        # 在角色操作按钮区域添加编辑情绪映射按钮
        char_button_frame = ttk.Frame(parent)
        char_button_frame.grid(row=3, column=0, columnspan=3, pady=10)
        
        ttk.Button(char_button_frame, text="导入表情图片", command=self.import_character_images).grid(row=0, column=0, padx=5)
        ttk.Button(char_button_frame, text="设置角色颜色", command=self.set_character_color).grid(row=0, column=1, padx=5)
        ttk.Button(char_button_frame, text="修改角色设置", command=self.edit_character_settings).grid(row=0, column=2, padx=5)
        ttk.Button(char_button_frame, text="编辑情绪映射", command=self.edit_emotion_mapping).grid(row=0, column=3, padx=5)  # 新增按钮
        ttk.Button(char_button_frame, text="删除角色", command=self.delete_character).grid(row=0, column=4, padx=5)
        ttk.Button(char_button_frame, text="刷新列表", command=self.refresh_character_list).grid(row=0, column=5, padx=5)
            
        # drawx 和 drawy 显示
        ttk.Label(self.settings_frame, text="drawx:").grid(row=1, column=0, sticky=tk.W, pady=5)
        self.char_drawx_label = ttk.Label(self.settings_frame, text="0")
        self.char_drawx_label.grid(row=1, column=1, sticky=tk.W, pady=5, padx=5)
        
        ttk.Label(self.settings_frame, text="drawy:").grid(row=1, column=2, sticky=tk.W, pady=5)
        self.char_drawy_label = ttk.Label(self.settings_frame, text="0")
        self.char_drawy_label.grid(row=1, column=3, sticky=tk.W, pady=5, padx=5)

        # enlarge 显示（新增）
        ttk.Label(self.settings_frame, text="enlarge:").grid(row=2, column=0, sticky=tk.W, pady=5)
        self.char_enlarge_label = ttk.Label(self.settings_frame, text="1.0")
        self.char_enlarge_label.grid(row=2, column=1, sticky=tk.W, pady=5, padx=5)
        
        # 对话框字体设置（新增）
        ttk.Label(self.settings_frame, text="对话框字体:").grid(row=3, column=0, sticky=tk.W, pady=5)
        
        # 角色对话框字体选择和显示
        dialog_font_frame = ttk.Frame(self.settings_frame)
        dialog_font_frame.grid(row=3, column=1, columnspan=3, sticky=(tk.W, tk.E), pady=5)
        
        # 这里不需要初始化Entry，我们会在on_character_select中动态设置
        self.char_dialog_font_entry = ttk.Entry(dialog_font_frame, textvariable=self.character_dialog_font_var, 
                                               width=20, state="normal")
        self.char_dialog_font_entry.grid(row=0, column=0, padx=(0, 5), sticky=(tk.W, tk.E))
        
        ttk.Button(dialog_font_frame, text="选择字体", 
                  command=self.select_character_dialog_font).grid(row=0, column=1, padx=5)
        # 名字字体控件
        ttk.Label(self.settings_frame, text="名字字体:").grid(row=3, column=2, sticky=tk.W, pady=5)
        name_font_frame = ttk.Frame(self.settings_frame)
        name_font_frame.grid(row=3, column=3, sticky=(tk.W, tk.E), pady=5)
        self.char_name_font_entry = ttk.Entry(name_font_frame, textvariable=self.character_name_font_var, width=20, state="normal")
        self.char_name_font_entry.grid(row=0, column=0, padx=(0, 5), sticky=(tk.W, tk.E))
        ttk.Button(name_font_frame, text="选择字体", command=self.select_character_name_font).grid(row=0, column=1, padx=5)
        
        # 添加保存字体设置的按钮到角色设置部分
        # 将保存按钮放低一行，避免遮挡名字字体的输入框
        ttk.Button(self.settings_frame, text="保存字体设置", 
              command=self.save_character_font_setting).grid(row=5, column=0, columnspan=4, pady=10)
        
        # 角色图片预览
        ttk.Label(parent, text="角色表情预览:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.char_preview_text = tk.StringVar(value="选择角色查看表情")
        ttk.Label(parent, textvariable=self.char_preview_text).grid(row=6, column=0, columnspan=3, pady=5)
        
        # 绑定列表选择事件
        self.char_listbox.bind('<<ListboxSelect>>', self.on_character_select)
    
    def setup_font_tab(self, parent):
        """设置字体管理选项卡"""
        # ===== 1. 全局字体设置 =====
        global_frame = ttk.LabelFrame(parent, text="全局字体设置", padding="10")
        global_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 15))
        global_frame.columnconfigure(1, weight=1)
        
        # 1.1 全局中文字体（用于中文和中文符号）
        ttk.Label(global_frame, text="全局中文字体:").grid(row=0, column=0, sticky=tk.W, pady=5, padx=5)
        
        chinese_font_frame = ttk.Frame(global_frame)
        chinese_font_frame.grid(row=0, column=1, sticky=(tk.W, tk.E), pady=5)
        
        self.chinese_font_entry = ttk.Entry(chinese_font_frame, textvariable=self.chinese_font_var, width=30)
        self.chinese_font_entry.grid(row=0, column=0, padx=(0, 5), sticky=(tk.W, tk.E))
        
        ttk.Button(chinese_font_frame, text="选择字体文件", 
                  command=lambda: self.select_font_file(self.chinese_font_var, "中文字体")).grid(row=0, column=1, padx=5)
        
        # 1.2 全局英文/数学字体
        ttk.Label(global_frame, text="全局英文/数学字体:").grid(row=1, column=0, sticky=tk.W, pady=5, padx=5)
        
        english_font_frame = ttk.Frame(global_frame)
        english_font_frame.grid(row=1, column=1, sticky=(tk.W, tk.E), pady=5)
        
        self.english_font_entry = ttk.Entry(english_font_frame, textvariable=self.english_math_font_var, width=30)
        self.english_font_entry.grid(row=0, column=0, padx=(0, 5), sticky=(tk.W, tk.E))
        
        ttk.Button(english_font_frame, text="选择字体文件", 
                  command=lambda: self.select_font_file(self.english_math_font_var, "英文/数学字体")).grid(row=0, column=1, padx=5)
        
        # 字体说明
        ttk.Label(global_frame, text="说明:", font=("Arial", 9, "bold")).grid(row=2, column=0, sticky=tk.W, pady=(10, 0), padx=5)
        
        info_text = """1. 中文字体：用于显示中文和全角符号
2. 英文/数学字体：用于显示英文、数字和数学符号
3. 支持字体格式：.ttf, .ttc, .otf, .woff, .woff2
4. 优先使用角色设置中的中文字体，角色设置中为空时使用此处的中文字体"""
        
        ttk.Label(global_frame, text=info_text, justify=tk.LEFT, wraplength=500).grid(
            row=3, column=0, columnspan=2, sticky=tk.W, pady=5, padx=5)
        
        # ===== 2. 字体文件列表 =====
        list_frame = ttk.LabelFrame(parent, text="已安装的字体文件", padding="10")
        list_frame.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 15))
        list_frame.columnconfigure(0, weight=1)
        list_frame.rowconfigure(0, weight=1)
        
        # 创建字体列表和滚动条
        self.font_listbox = tk.Listbox(list_frame, height=8)
        self.font_listbox.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.font_listbox.yview)
        scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.font_listbox.config(yscrollcommand=scrollbar.set)
        
        # 字体文件操作按钮
        font_button_frame = ttk.Frame(parent)
        font_button_frame.grid(row=2, column=0, columnspan=2, pady=5)
        
        ttk.Button(font_button_frame, text="刷新字体列表", 
                  command=self.refresh_font_list).grid(row=0, column=0, padx=5)
        ttk.Button(font_button_frame, text="删除选中字体", 
                  command=self.delete_selected_font).grid(row=0, column=1, padx=5)
        ttk.Button(font_button_frame, text="打开字体文件夹", 
              command=self.open_fonts_folder).grid(row=0, column=2, padx=5)
        ttk.Button(font_button_frame, text="导入字体文件", 
              command=self.import_font_file).grid(row=0, column=3, padx=5)
        
        # 初始化字体列表
        self.refresh_font_list()
        
        # 绑定列表选择事件
        self.font_listbox.bind('<<ListboxSelect>>', self.on_font_select)
    
    def setup_config_tab(self, parent):
        """设置配置生成选项卡"""
        # 配置预览
        ttk.Label(parent, text="配置文件预览:").grid(row=0, column=0, sticky=tk.W, pady=5)
        self.config_text = tk.Text(parent, height=20, width=80)
        self.config_text.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=5)
        
        # 配置操作按钮
        config_button_frame = ttk.Frame(parent)
        config_button_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        ttk.Button(config_button_frame, text="生成配置预览", command=self.generate_config_preview).grid(row=0, column=0, padx=5)
        ttk.Button(config_button_frame, text="保存到info.json", command=self.save_config_to_file).grid(row=0, column=1, padx=5)
        ttk.Button(config_button_frame, text="设置默认背景", command=self.set_default_background).grid(row=0, column=2, padx=5)
        
        # 默认背景设置
        ttk.Label(parent, text="默认背景:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.default_bg_var = tk.StringVar()
        self.default_bg_combo = ttk.Combobox(parent, textvariable=self.default_bg_var, state="readonly")
        self.default_bg_combo.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        # API 设置部分
        # API 启用开关
        self.api_enable_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(parent, text="启用API", variable=self.api_enable_var).grid(row=4, column=0, sticky=tk.W, pady=5)
        
        # API Key 输入
        ttk.Label(parent, text="API Key:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.api_key_var = tk.StringVar()
        ttk.Entry(parent, textvariable=self.api_key_var, width=50, show="*").grid(row=5, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
        
        # 加载现有的API配置（如果有）
        self.load_api_config()
    
    def select_font_file(self, font_var, font_type):
        """选择字体文件（仅从 resource/fonts 选择，不导入）"""
        file_path = filedialog.askopenfilename(
            title=f"选择{font_type}文件",
            initialdir=self.fonts_dir,
            filetypes=[
                ("字体文件", "*.ttf *.ttc *.otf *.woff *.woff2"),
                ("TrueType字体", "*.ttf"),
                ("TrueType集合", "*.ttc"),
                ("OpenType字体", "*.otf"),
                ("网页字体", "*.woff *.woff2"),
                ("所有文件", "*.*")
            ]
        )
        if not file_path:
            return
        try:
            # 只允许选择 resource/fonts 下的文件
            if not os.path.commonpath([self.fonts_dir, file_path]).startswith(self.fonts_dir):
                messagebox.showerror("错误", "请选择 resource/fonts 目录中的字体文件。\n如需导入新字体，请使用“导入字体文件”按钮。")
                return
            filename = os.path.basename(file_path)
            font_var.set(filename)
        except Exception as e:
            messagebox.showerror("错误", f"选择字体失败: {e}")

    def import_font_file(self):
        """导入字体文件到 resource/fonts（与选择分离）"""
        file_path = filedialog.askopenfilename(
            title="导入字体文件",
            filetypes=[
                ("字体文件", "*.ttf *.ttc *.otf *.woff *.woff2"),
                ("所有文件", "*.*")
            ]
        )
        if not file_path:
            return
        try:
            if not self.validate_font_file(file_path):
                messagebox.showerror("错误", "选择的文件不是有效的字体文件，或文件已损坏。")
                return
            filename = os.path.basename(file_path)
            dest_path = os.path.join(self.fonts_dir, filename)
            if os.path.exists(dest_path):
                if not messagebox.askyesno("确认", f"字体文件 '{filename}' 已存在，是否覆盖？"):
                    return
            shutil.copy2(file_path, dest_path)
            messagebox.showinfo("成功", f"字体文件已导入: {filename}")
            self.refresh_font_list()
        except Exception as e:
            messagebox.showerror("错误", f"导入字体文件失败: {e}")
    
    def validate_font_file(self, font_path):
        """验证字体文件是否有效"""
        try:
            from PIL import ImageFont
            
            # 尝试加载字体（不显示实际大小）
            test_font = ImageFont.truetype(font_path, 10)
            return True
        except Exception as e:
            print(f"字体验证失败: {e}")
            return False
    
    def refresh_font_list(self):
        """刷新字体文件列表"""
        self.font_listbox.delete(0, tk.END)
        
        if os.path.exists(self.fonts_dir):
            # 支持的字体文件扩展名
            font_extensions = ['.ttf', '.ttc', '.otf', '.woff', '.woff2']
            
            for filename in os.listdir(self.fonts_dir):
                file_path = os.path.join(self.fonts_dir, filename)
                if os.path.isfile(file_path):
                    ext = os.path.splitext(filename)[1].lower()
                    if ext in font_extensions:
                        self.font_listbox.insert(tk.END, filename)
    
    def delete_selected_font(self):
        """删除选中的字体文件"""
        selected = self.font_listbox.curselection()
        if not selected:
            messagebox.showerror("错误", "请先选择一个字体文件")
            return
        
        font_filename = self.font_listbox.get(selected[0])
        
        # 检查是否正在被使用
        if self.is_font_in_use(font_filename):
            messagebox.showerror("错误", 
                f"字体文件 '{font_filename}' 正在被使用，无法删除。\n"
                f"请先修改全局字体设置或角色字体设置。")
            return
        
        if messagebox.askyesno("确认", f"确定要删除字体文件 '{font_filename}' 吗？"):
            try:
                font_path = os.path.join(self.fonts_dir, font_filename)
                os.remove(font_path)
                messagebox.showinfo("成功", f"字体文件 '{font_filename}' 已删除")
                self.refresh_font_list()
            except Exception as e:
                messagebox.showerror("错误", f"删除字体文件失败: {e}")
    
    def is_font_in_use(self, font_filename):
        """检查字体文件是否正在被使用"""
        # 检查全局字体设置
        if (self.chinese_font_var.get() == font_filename or 
            self.english_math_font_var.get() == font_filename):
            return True
        
        # 检查所有角色的对话框字体设置
        for char_folder_name in os.listdir(self.character_dir):
            char_path = os.path.join(self.character_dir, char_folder_name)
            config_path = os.path.join(char_path, "config.json")
            
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        config_data = json.load(f)
                    
                    if config_data.get("dialog_font") == font_filename or config_data.get("name_font") == font_filename:
                        return True
                except Exception:
                    continue
        
        return False
    
    def open_fonts_folder(self):
        """打开字体文件夹"""
        if os.path.exists(self.fonts_dir):
            os.startfile(self.fonts_dir)
        else:
            messagebox.showerror("错误", "字体文件夹不存在")
    
    def on_font_select(self, event):
        """字体选择事件"""
        selected = self.font_listbox.curselection()
        if selected:
            font_filename = self.font_listbox.get(selected[0])
            
            # 可以在这里添加字体信息显示
            font_path = os.path.join(self.fonts_dir, font_filename)
            font_size = os.path.getsize(font_path)
            
            # 格式化文件大小
            if font_size < 1024:
                size_str = f"{font_size} B"
            elif font_size < 1024 * 1024:
                size_str = f"{font_size/1024:.1f} KB"
            else:
                size_str = f"{font_size/(1024*1024):.1f} MB"
            
            # 显示字体信息（可以添加一个状态标签）
            print(f"选中字体: {font_filename} ({size_str})")
    
    def select_character_dialog_font(self):
        """选择角色对话框字体（仅从 resource/fonts 选择，不导入）"""
        if not self.current_character:
            messagebox.showerror("错误", "请先选择一个角色")
            return
        
        file_path = filedialog.askopenfilename(
            title=f"为 {self.current_character} 选择对话框字体",
            initialdir=self.fonts_dir,
            filetypes=[
                ("字体文件", "*.ttf *.ttc *.otf *.woff *.woff2"),
                ("所有文件", "*.*")
            ]
        )
        
        if not file_path:
            return
        
        try:
            # 仅允许选择 resource/fonts 下的文件
            if not os.path.commonpath([self.fonts_dir, file_path]).startswith(self.fonts_dir):
                messagebox.showerror("错误", "请选择 resource/fonts 目录中的字体文件。\n如需导入新字体，请在字体管理页使用“导入字体文件”。")
                return
            filename = os.path.basename(file_path)
            self.character_dialog_font_var.set(filename)
            messagebox.showinfo("成功", f"已为 {self.current_character} 设置对话框字体: {filename}")
            
        except Exception as e:
            messagebox.showerror("错误", f"设置角色对话框字体失败: {e}")

    def select_character_name_font(self):
        """选择角色名字字体（仅从 resource/fonts 选择，不导入）"""
        if not self.current_character:
            messagebox.showerror("错误", "请先选择一个角色")
            return
        file_path = filedialog.askopenfilename(
            title=f"为 {self.current_character} 选择名字字体",
            initialdir=self.fonts_dir,
            filetypes=[
                ("字体文件", "*.ttf *.ttc *.otf *.woff *.woff2"),
                ("所有文件", "*.*")
            ]
        )
        if not file_path:
            return
        try:
            if not os.path.commonpath([self.fonts_dir, file_path]).startswith(self.fonts_dir):
                messagebox.showerror("错误", "请选择 resource/fonts 目录中的字体文件。\n如需导入新字体，请在字体管理页使用“导入字体文件”。")
                return
            filename = os.path.basename(file_path)
            self.character_name_font_var.set(filename)
            messagebox.showinfo("成功", f"已为 {self.current_character} 设置名字字体: {filename}")
        except Exception as e:
            messagebox.showerror("错误", f"设置角色名字字体失败: {e}")
    
    def save_character_font_setting(self):
        """保存角色字体设置"""
        if not self.current_character:
            messagebox.showerror("错误", "请先选择一个角色")
            return
        
        char_folder_name = self.current_character
        char_path = os.path.join(self.character_dir, char_folder_name)
        config_path = os.path.join(char_path, "config.json")
        
        try:
            # 读取现有配置
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            else:
                config_data = {
                    "folder_name": char_folder_name,
                    "display_name": char_folder_name,
                    "drawx": -450,
                    "drawy": -100,
                    "enlarge": 1.0,
                    "font": "",
                    "dialog_font": "",  # 默认空
                    "name_font": "",    # 默认空
                    "color": {"r": 255, "g": 255, "b": 255}
                }
            
            # 更新对话框字体与名字字体
            config_data["dialog_font"] = self.character_dialog_font_var.get()
            config_data["name_font"] = self.character_name_font_var.get()
            
            # 保存配置
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("成功", f"已保存 {char_folder_name} 的对话框字体设置")
            
        except Exception as e:
            messagebox.showerror("错误", f"保存角色字体设置失败: {e}")
    
    def load_font_config(self):
        """加载已有的字体配置"""
        info_json_path = os.path.join(self.resource_dir, "info.json")
        
        if not os.path.exists(info_json_path):
            return
        
        try:
            with open(info_json_path, 'r', encoding='utf-8') as f:
                info_data = json.load(f)
            
            # 加载字体配置
            if "font_configs" in info_data:
                font_configs = info_data["font_configs"]
                
                # 加载全局字体
                if "global" in font_configs:
                    global_fonts = font_configs["global"]
                    self.chinese_font_var.set(global_fonts.get("chinese_font", ""))
                    self.english_math_font_var.set(global_fonts.get("english_math_font", ""))
                
                # 角色字体配置会在选择角色时加载
                
        except Exception as e:
            print(f"加载字体配置失败: {e}")
    
    def update_gui_resource_status(self):
        """更新GUI资源状态显示"""
        # 检查GUI背景是否存在
        if os.path.exists(self.gui_bg_path):
            self.gui_bg_status.config(text="已设置", foreground="green")
        else:
            self.gui_bg_status.config(text="未设置", foreground="gray")
        
        # 检查图标是否存在（只检查PNG）
        if os.path.exists(self.logo_png_path):
            self.logo_status.config(text="已设置", foreground="green")  # 移除了ICO的显示
        else:
            self.logo_status.config(text="未设置", foreground="gray")
    
    def import_gui_background(self):
        """导入GUI背景图片并自动重命名为guibg.png"""
        file_path = filedialog.askopenfilename(
            title="选择GUI背景图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp")]
        )
        
        if not file_path:
            return
        
        try:
            # 打开图片
            with Image.open(file_path) as img:
                # 转换为RGBA模式（保持透明度）
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # 保存为PNG格式，命名为guibg.png
                img.save(self.gui_bg_path, 'PNG')
            
            self.update_gui_resource_status()
            messagebox.showinfo("成功", f"GUI背景图片已导入并保存为: guibg.png")
            
        except Exception as e:
            messagebox.showerror("错误", f"导入GUI背景图片失败: {e}")
    
    def import_logo(self):
        """导入图标并保存为PNG格式"""
        file_path = filedialog.askopenfilename(
            title="选择图标图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp *.ico")]
        )
        
        if not file_path:
            return
        
        try:
            # 打开图片
            with Image.open(file_path) as img:
                # 转换为RGBA模式（保持透明度）
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # 保存为PNG格式，命名为logo.png
                img.save(self.logo_png_path, 'PNG')
            
            self.update_gui_resource_status()
            messagebox.showinfo("成功", f"图标已导入并保存为: logo.png")
            
        except Exception as e:
            messagebox.showerror("错误", f"导入图标失败: {e}")
    
    def refresh_lists(self):
        """刷新所有列表"""
        self.refresh_background_list()
        self.refresh_character_list()
        self.refresh_default_background_list()
        self.refresh_font_list()  # 新增
        self.update_gui_resource_status()
    
    def refresh_background_list(self):
        """刷新背景列表"""
        self.bg_listbox.delete(0, tk.END)
        if os.path.exists(self.background_dir):
            for item in os.listdir(self.background_dir):
                if os.path.isdir(os.path.join(self.background_dir, item)):
                    self.bg_listbox.insert(tk.END, item)
    
    def refresh_character_list(self):
        """刷新角色列表"""
        self.char_listbox.delete(0, tk.END)
        if os.path.exists(self.character_dir):
            for item in os.listdir(self.character_dir):
                if os.path.isdir(os.path.join(self.character_dir, item)):
                    self.char_listbox.insert(tk.END, item)
    
    def refresh_default_background_list(self):
        """刷新默认背景下拉列表"""
        backgrounds = []
        if os.path.exists(self.background_dir):
            for item in os.listdir(self.background_dir):
                if os.path.isdir(os.path.join(self.background_dir, item)):
                    backgrounds.append(item)
        self.default_bg_combo['values'] = backgrounds
        if backgrounds:
            self.default_bg_var.set(backgrounds[0])
    
    def create_background_folder(self):
        """创建背景文件夹"""
        bg_name = self.new_bg_name.get().strip()
        if not bg_name:
            messagebox.showerror("错误", "请输入背景名称")
            return
        
        bg_path = os.path.join(self.background_dir, bg_name)
        if os.path.exists(bg_path):
            messagebox.showerror("错误", f"背景 '{bg_name}' 已存在")
            return
        
        try:
            os.makedirs(bg_path)
            messagebox.showinfo("成功", f"背景文件夹 '{bg_name}' 创建成功")
            self.new_bg_name.set("")
            self.refresh_background_list()
            self.refresh_default_background_list()
        except Exception as e:
            messagebox.showerror("错误", f"创建背景文件夹失败: {e}")
    
    def create_character_folder(self):
        """创建角色文件夹"""
        folder_name = self.new_char_folder_name.get().strip()
        display_name = self.new_char_display_name.get().strip()
        
        if not folder_name or not display_name:
            messagebox.showerror("错误", "请输入英文文件夹名和角色显示名")
            return
        
        char_path = os.path.join(self.character_dir, folder_name)
        if os.path.exists(char_path):
            messagebox.showerror("错误", f"角色文件夹 '{folder_name}' 已存在")
            return
        
        try:
            # 获取 drawx 和 drawy
            drawx = int(self.new_char_drawx.get())
            drawy = int(self.new_char_drawy.get())
            
            # 获取 enlarge 参数
            enlarge_value = self.new_char_enlarge.get().strip()
            enlarge = float(enlarge_value) if enlarge_value else 1.0
            
            os.makedirs(char_path)
            
            # 创建角色配置文件
            config_path = os.path.join(char_path, "config.json")
            config_data = {
                "folder_name": folder_name,
                "display_name": display_name,
                "drawx": drawx,
                "drawy": drawy,
                "enlarge": enlarge,  # 新增 enlarge 参数
                    "font": "",
                    "dialog_font": "",  # 新增对话框字体
                "color": {"r": 255, "g": 255, "b": 255}  # 默认白色
            }
            
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("成功", f"角色文件夹 '{folder_name}' 创建成功")
            
            # 清空输入框
            self.new_char_folder_name.set("")
            self.new_char_display_name.set("")
            self.new_char_drawx.set("0")
            self.new_char_drawy.set("0")
            self.new_char_enlarge.set("1.0")  # 重置 enlarge 输入框
            
            self.refresh_character_list()
            
        except ValueError as e:
            messagebox.showerror("错误", f"输入值错误: {e}")
        except Exception as e:
            messagebox.showerror("错误", f"创建角色文件夹失败: {e}")
    
    def import_background_images(self):
        """导入背景图片并自动转换为PNG格式"""
        selected = self.bg_listbox.curselection()
        if not selected:
            messagebox.showerror("错误", "请先选择一个背景")
            return
        
        bg_name = self.bg_listbox.get(selected[0])
        bg_path = os.path.join(self.background_dir, bg_name)
        
        files = filedialog.askopenfilenames(
            title="选择背景图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp")]
        )
        
        if not files:
            return
        
        try:
            # 获取已存在的背景图片数量
            existing_files = [f for f in os.listdir(bg_path) if f.startswith('c') and f.endswith('.png')]
            existing_nums = []
            for f in existing_files:
                try:
                    num = int(f[1:-4])  # 移除'c'和'.png'
                    existing_nums.append(num)
                except:
                    pass
            
            start_num = max(existing_nums) + 1 if existing_nums else 1
            
            for i, file_path in enumerate(files):
                # 打开图片
                with Image.open(file_path) as img:
                    # 转换为RGBA模式（保持透明度）
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    
                    # 生成新文件名：c1.png, c2.png, ...
                    new_name = f"c{start_num + i}.png"
                    new_path = os.path.join(bg_path, new_name)
                    
                    # 保存为PNG格式
                    img.save(new_path, 'PNG')
            
            messagebox.showinfo("成功", f"成功导入 {len(files)} 张背景图片到 '{bg_name}'，已转换为PNG格式")
            self.on_background_select(None)  # 刷新预览信息
        except Exception as e:
            messagebox.showerror("错误", f"导入背景图片失败: {e}")
    
    def import_d_image(self):
        """导入透明框图片并自动转换为PNG格式"""
        selected = self.bg_listbox.curselection()
        if not selected:
            messagebox.showerror("错误", "请先选择一个背景")
            return
        
        bg_name = self.bg_listbox.get(selected[0])
        bg_path = os.path.join(self.background_dir, bg_name)
        
        file_path = filedialog.askopenfilename(
            title="选择透明框图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp")]
        )
        
        if not file_path:
            return
        
        try:
            # 打开图片
            with Image.open(file_path) as img:
                # 转换为RGBA模式（保持透明度）
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                
                # 重命名为 d.png
                new_path = os.path.join(bg_path, "d.png")
                
                # 保存为PNG格式
                img.save(new_path, 'PNG')
            
            messagebox.showinfo("成功", f"成功导入透明框图片到 '{bg_name}'，已转换为PNG格式")
            self.on_background_select(None)  # 刷新预览信息
        except Exception as e:
            messagebox.showerror("错误", f"导入透明框图片失败: {e}")
    
    def import_character_images(self):
        """导入角色表情图片（修改版，添加情绪名称捕获）"""
        selected = self.char_listbox.curselection()
        if not selected:
            messagebox.showerror("错误", "请先选择一个角色")
            return
        
        char_folder_name = self.char_listbox.get(selected[0])
        char_path = os.path.join(self.character_dir, char_folder_name)
        
        files = filedialog.askopenfilenames(
            title="选择角色表情图片",
            filetypes=[("图片文件", "*.png *.jpg *.jpeg *.bmp *.gif *.tiff *.webp")]
        )
        
        if not files:
            return
        
        try:
            # 获取已存在的表情图片数量
            existing_files = [f for f in os.listdir(char_path) 
                            if f.startswith(char_folder_name) and f.endswith('.png')]
            existing_nums = []
            for f in existing_files:
                try:
                    # 提取数字部分
                    prefix_len = len(char_folder_name)
                    num = int(f[prefix_len:-4])  # 移除角色文件夹名和'.png'
                    existing_nums.append(num)
                except:
                    pass
            
            start_num = max(existing_nums) + 1 if existing_nums else 1
            
            # 新增：导入每张图片时提示输入情绪名称
            imported_emotions = {}  # 存储图片编号到情绪名称的映射
            
            for i, file_path in enumerate(files):
                # 获取原始文件名（不带扩展名）
                original_name = os.path.splitext(os.path.basename(file_path))[0]
                
                # 弹出对话框让用户确认/修改情绪名称
                emotion_name = self.prompt_for_emotion_name(
                    original_name, 
                    char_folder_name, 
                    start_num + i
                )
                
                if emotion_name:  # 如果用户提供了情绪名称
                    # 记录情绪映射
                    img_num = start_num + i
                    imported_emotions[str(img_num)] = [emotion_name.strip()]
                
                # 打开图片
                with Image.open(file_path) as img:
                    # 转换为RGBA模式（保持透明度）
                    if img.mode != 'RGBA':
                        img = img.convert('RGBA')
                    
                    # 重命名为 角色文件夹名1.png, 角色文件夹名2.png, ...
                    new_name = f"{char_folder_name}{start_num + i}.png"
                    new_path = os.path.join(char_path, new_name)
                    
                    # 保存为PNG格式
                    img.save(new_path, 'PNG')
            
            # 更新角色的情绪映射配置文件
            if imported_emotions:
                self.update_character_emotion_mapping(char_folder_name, imported_emotions)
            
            messagebox.showinfo("成功", f"成功导入 {len(files)} 张表情图片到 '{char_folder_name}'，已转换为PNG格式")
            self.on_character_select(None)  # 刷新预览信息
            
        except Exception as e:
            messagebox.showerror("错误", f"导入表情图片失败: {e}")

    def prompt_for_emotion_name(self, original_name, char_name, img_number):
        """弹出对话框让用户输入情绪名称"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"输入情绪名称 - {char_name} 图片{img_number}")
        dialog.geometry("400x200")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # 提示信息
        ttk.Label(dialog, text=f"原始文件名: {original_name}", font=("Arial", 10)).pack(pady=(20, 5))
        ttk.Label(dialog, text="请输入这张图片代表的情绪名称:", font=("Arial", 10)).pack(pady=5)
        
        # 输入框（默认使用原始文件名）
        emotion_var = tk.StringVar(value=original_name)
        entry = ttk.Entry(dialog, textvariable=emotion_var, width=30)
        entry.pack(pady=10)
        entry.focus_set()
        entry.select_range(0, tk.END)
        
        result = {"value": None}
        
        def on_ok():
            result["value"] = emotion_var.get()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        # 按钮
        button_frame = ttk.Frame(dialog)
        button_frame.pack(pady=20)
        
        ttk.Button(button_frame, text="确定", command=on_ok).pack(side=tk.LEFT, padx=10)
        ttk.Button(button_frame, text="取消", command=on_cancel).pack(side=tk.LEFT, padx=10)
        
        # 绑定回车键
        dialog.bind('<Return>', lambda e: on_ok())
        dialog.bind('<Escape>', lambda e: on_cancel())
        
        # 等待对话框关闭
        self.root.wait_window(dialog)
        
        return result["value"]
    
    def update_character_emotion_mapping(self, char_folder_name, new_mapping):
        """更新角色的情绪映射配置"""
        char_path = os.path.join(self.character_dir, char_folder_name)
        config_path = os.path.join(char_path, "config.json")
        
        try:
            # 读取现有配置
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            else:
                config_data = {
                    "folder_name": char_folder_name,
                    "display_name": char_folder_name,
                    "drawx": -450,
                    "drawy": -100,
                    "enlarge": 1.0,
                    "font": "font3.ttf",
                    "dialog_font": "font3.ttf",
                    "color": {"r": 255, "g": 255, "b": 255}
                }
            
            # 更新或添加情绪映射
            if "emotion_mapping" in config_data:
                # 合并现有映射
                for img_num, emotions in new_mapping.items():
                    if img_num in config_data["emotion_mapping"]:
                        # 合并情绪列表，避免重复
                        existing_emotions = config_data["emotion_mapping"][img_num]
                        for emotion in emotions:
                            if emotion not in existing_emotions:
                                existing_emotions.append(emotion)
                    else:
                        config_data["emotion_mapping"][img_num] = emotions
            else:
                # 创建新的映射
                config_data["emotion_mapping"] = new_mapping
            
            # 保存配置
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
        except Exception as e:
            print(f"更新情绪映射失败: {e}")

    def load_character_emotion_mapping(self, char_folder_name):
        """加载角色的情绪映射"""
        char_path = os.path.join(self.character_dir, char_folder_name)
        config_path = os.path.join(char_path, "config.json")
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                if "emotion_mapping" in config_data:
                    emotion_mapping = config_data["emotion_mapping"]
                    # 确保情绪映射中的值是列表格式
                    for img_num, emotions in emotion_mapping.items():
                        if isinstance(emotions, str):
                            # 如果是字符串，转换为列表
                            emotion_mapping[img_num] = [emotions]
                        elif isinstance(emotions, list):
                            # 确保列表中的每个元素都是字符串
                            emotion_mapping[img_num] = [str(e) for e in emotions]
                    return emotion_mapping
            except Exception as e:
                print(f"加载情绪映射失败: {e}")
        
        return {}

    def set_character_color(self):
        """设置角色颜色"""
        if not self.current_character:
            messagebox.showerror("错误", "请先选择一个角色")
            return
        
        char_folder_name = self.current_character
        char_path = os.path.join(self.character_dir, char_folder_name)
        
        # 读取现有配置
        config_path = os.path.join(char_path, "config.json")
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except:
            # 如果配置文件不存在，创建默认配置
            config_data = {
                "folder_name": char_folder_name, 
                "display_name": char_folder_name,
                "drawx": -450,
                "drawy": -100,
                "enlarge": 1.0,  # 默认值
                "font": "font3.ttf",
                "dialog_font": "font3.ttf",  # 新增默认值
                "color": {"r": 255, "g": 255, "b": 255}
            }
        
        # 打开颜色选择器
        color_tuple = colorchooser.askcolor(title=f"选择 {char_folder_name} 的角色颜色")
        if color_tuple[1]:  # color_tuple[1]是十六进制颜色代码
            color_code = color_tuple[1]
            
            # 将十六进制颜色转换为RGB
            r = int(color_code[1:3], 16)
            g = int(color_code[3:5], 16)
            b = int(color_code[5:7], 16)
            
            # 更新配置中的color字段
            config_data["color"] = {"r": r, "g": g, "b": b}
            
            # 保存更新后的配置
            try:
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
                
                # 更新显示
                self.char_color_label.config(background=color_code, text=f"RGB({r},{g},{b})")
                messagebox.showinfo("成功", f"已设置 {char_folder_name} 的角色颜色为 RGB({r},{g},{b})")
                
                # 刷新角色信息显示
                self.on_character_select(None)
            except Exception as e:
                messagebox.showerror("错误", f"保存颜色配置失败: {e}")
    
    def edit_character_settings(self):
        """编辑角色设置"""
        if not self.current_character:
            messagebox.showerror("错误", "请先选择一个角色")
            return
        
        char_folder_name = self.current_character
        char_path = os.path.join(self.character_dir, char_folder_name)
        
        # 读取现有配置
        config_path = os.path.join(char_path, "config.json")
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
        except:
            config_data = {
                "folder_name": char_folder_name, 
                "display_name": char_folder_name,
                "drawx": -450,
                "drawy": -100,
                "enlarge": 1.0,
                "font": "font3.ttf",
                "dialog_font": "font3.ttf",  # 新增默认值
                "color": {"r": 255, "g": 255, "b": 255}
            }
        
        # 创建编辑对话框
        edit_dialog = tk.Toplevel(self.root)
        edit_dialog.title(f"编辑角色设置 - {char_folder_name}")
        edit_dialog.geometry("400x400")  # 增加高度以容纳新字段
        
        # 角色显示名
        ttk.Label(edit_dialog, text="角色显示名:").grid(row=0, column=0, sticky=tk.W, pady=10, padx=10)
        display_name_var = tk.StringVar(value=config_data.get("display_name", char_folder_name))
        ttk.Entry(edit_dialog, textvariable=display_name_var, width=20).grid(row=0, column=1, pady=10, padx=10)
        
        # drawx 设置
        ttk.Label(edit_dialog, text="drawx:").grid(row=1, column=0, sticky=tk.W, pady=10, padx=10)
        drawx_var = tk.StringVar(value=str(config_data.get("drawx", -450)))
        ttk.Entry(edit_dialog, textvariable=drawx_var, width=10).grid(row=1, column=1, sticky=tk.W, pady=10, padx=10)
        
        # drawy 设置
        ttk.Label(edit_dialog, text="drawy:").grid(row=2, column=0, sticky=tk.W, pady=10, padx=10)
        drawy_var = tk.StringVar(value=str(config_data.get("drawy", -100)))
        ttk.Entry(edit_dialog, textvariable=drawy_var, width=10).grid(row=2, column=1, sticky=tk.W, pady=10, padx=10)
            
        # enlarge 设置
        ttk.Label(edit_dialog, text="enlarge:").grid(row=3, column=0, sticky=tk.W, pady=10, padx=10)
        enlarge_var = tk.StringVar(value=str(config_data.get("enlarge", 1.0)))
        ttk.Entry(edit_dialog, textvariable=enlarge_var, width=10).grid(row=3, column=1, sticky=tk.W, pady=10, padx=10)
        
        # 对话框字体设置（新增）
        ttk.Label(edit_dialog, text="对话框字体:").grid(row=4, column=0, sticky=tk.W, pady=10, padx=10)
        dialog_font_var = tk.StringVar(value=config_data.get("dialog_font", ""))
        
        dialog_font_frame = ttk.Frame(edit_dialog)
        dialog_font_frame.grid(row=4, column=1, sticky=(tk.W, tk.E), pady=10, padx=10)
        
        dialog_font_entry = ttk.Entry(dialog_font_frame, textvariable=dialog_font_var, width=15)
        dialog_font_entry.grid(row=0, column=0, padx=(0, 5))
        
        def select_dialog_font():
            file_path = filedialog.askopenfilename(
                title="选择对话框字体",
                initialdir=self.fonts_dir,
                filetypes=[("字体文件", "*.ttf *.ttc *.otf *.woff *.woff2")]
            )
            if file_path:
                try:
                    if not os.path.commonpath([self.fonts_dir, file_path]).startswith(self.fonts_dir):
                        messagebox.showerror("错误", "请选择 resource/fonts 目录中的字体文件。\n如需导入新字体，请在字体管理页使用“导入字体文件”。")
                        return
                    filename = os.path.basename(file_path)
                    dialog_font_var.set(filename)
                except Exception as e:
                    messagebox.showerror("错误", f"选择字体失败: {e}")
        
        ttk.Button(dialog_font_frame, text="选择", command=select_dialog_font).grid(row=0, column=1)

        # 名字字体设置
        ttk.Label(edit_dialog, text="名字字体:").grid(row=5, column=0, sticky=tk.W, pady=10, padx=10)
        name_font_var = tk.StringVar(value=config_data.get("name_font", ""))
        name_font_frame = ttk.Frame(edit_dialog)
        name_font_frame.grid(row=5, column=1, sticky=(tk.W, tk.E), pady=10, padx=10)
        name_font_entry = ttk.Entry(name_font_frame, textvariable=name_font_var, width=15)
        name_font_entry.grid(row=0, column=0, padx=(0, 5))
        def select_name_font():
            file_path = filedialog.askopenfilename(
                title="选择名字字体",
                initialdir=self.fonts_dir,
                filetypes=[("字体文件", "*.ttf *.ttc *.otf *.woff *.woff2")]
            )
            if file_path:
                try:
                    if not os.path.commonpath([self.fonts_dir, file_path]).startswith(self.fonts_dir):
                        messagebox.showerror("错误", "请选择 resource/fonts 目录中的字体文件。\n如需导入新字体，请在字体管理页使用“导入字体文件”。")
                        return
                    filename = os.path.basename(file_path)
                    name_font_var.set(filename)
                except Exception as e:
                    messagebox.showerror("错误", f"选择字体失败: {e}")
        ttk.Button(name_font_frame, text="选择", command=select_name_font).grid(row=0, column=1)
        
        def save_settings():
            try:
                # 更新配置
                config_data["display_name"] = display_name_var.get()
                config_data["drawx"] = int(drawx_var.get())
                config_data["drawy"] = int(drawy_var.get())
                config_data["enlarge"] = float(enlarge_var.get())
                config_data["dialog_font"] = dialog_font_var.get()
                config_data["name_font"] = name_font_var.get()
                
                # 保存配置
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
                
                # 更新显示
                self.char_drawx_label.config(text=drawx_var.get())
                self.char_drawy_label.config(text=drawy_var.get())
                self.char_enlarge_label.config(text=enlarge_var.get())
                self.character_dialog_font_var.set(dialog_font_var.get())  # 更新字体显示
                
                messagebox.showinfo("成功", "角色设置已更新")
                edit_dialog.destroy()
                
                # 刷新角色信息显示
                self.on_character_select(None)
                
            except ValueError as e:
                messagebox.showerror("错误", f"输入值错误: {e}")
        
        # 保存按钮位置调整
        ttk.Button(edit_dialog, text="保存设置", command=save_settings).grid(row=6, column=0, columnspan=2, pady=20)
    
    def edit_emotion_mapping(self):
        """编辑角色的情绪映射"""
        if not self.current_character:
            messagebox.showerror("错误", "请先选择一个角色")
            return
        
        char_folder_name = self.current_character
        char_path = os.path.join(self.character_dir, char_folder_name)
        
        # 获取现有情绪映射
        emotion_mapping = self.load_character_emotion_mapping(char_folder_name)
        
        # 创建编辑对话框
        edit_dialog = tk.Toplevel(self.root)
        edit_dialog.title(f"编辑情绪映射 - {char_folder_name}")
        edit_dialog.geometry("600x600")  # 增加高度到600
        
        # 配置对话框网格权重
        edit_dialog.columnconfigure(0, weight=1)
        edit_dialog.rowconfigure(0, weight=0)  # 说明文字行（不扩展）
        edit_dialog.rowconfigure(1, weight=1)  # 文本编辑框行（扩展）
        edit_dialog.rowconfigure(2, weight=0)  # 按钮行（不扩展）
        
        # 说明文字
        info_text = """格式说明：
    每行格式为：图片编号-情绪名称1,情绪名称2,...
    示例：
    1-开心,快乐,高兴
    2-悲伤,伤心
    3-惊讶,吃惊
    4-生气,愤怒

    注意：
    1. 图片编号对应角色文件夹中的图片编号
    2. 同一情绪可以有多个图片编号
    3. 一行可以有多个情绪名称，用逗号分隔"""
        
        info_label = ttk.Label(edit_dialog, text=info_text, justify=tk.LEFT, wraplength=550)
        info_label.grid(row=0, column=0, sticky=tk.W, padx=10, pady=10)
        
        # 创建文本编辑框框架
        text_frame = ttk.Frame(edit_dialog)
        text_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        
        text_widget = tk.Text(text_frame, wrap=tk.WORD)
        text_widget.grid(row=0, column=0, sticky="nsew")
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(text_frame, orient=tk.VERTICAL, command=text_widget.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        text_widget.config(yscrollcommand=scrollbar.set)
        
        # 将现有映射格式化为文本并显示
        mapping_text = self.format_emotion_mapping_to_text(emotion_mapping)
        text_widget.insert("1.0", mapping_text)
        
        def save_mapping():
            """保存情绪映射"""
            new_text = text_widget.get("1.0", tk.END).strip()
            
            try:
                # 解析文本为映射字典
                new_mapping = self.parse_emotion_mapping_from_text(new_text)
                
                # 验证映射
                if not self.validate_emotion_mapping(new_mapping, char_folder_name):
                    messagebox.showerror("错误", "情绪映射验证失败，请检查格式和图片编号")
                    return
                
                # 保存到配置文件
                if self.save_emotion_mapping_to_config(char_folder_name, new_mapping):
                    messagebox.showinfo("成功", "情绪映射已保存")
                    edit_dialog.destroy()
                    
                    # 刷新角色信息
                    self.on_character_select(None)
                else:
                    messagebox.showerror("错误", "保存失败")
                    
            except Exception as e:
                messagebox.showerror("错误", f"保存失败: {e}")
        
        def load_default():
            """加载默认情绪映射"""
            default_mapping = self.generate_default_emotion_mapping(char_folder_name)
            text_widget.delete("1.0", tk.END)
            default_text = self.format_emotion_mapping_to_text(default_mapping)
            text_widget.insert("1.0", default_text)
        
        # 按钮区域
        button_frame = ttk.Frame(edit_dialog)
        button_frame.grid(row=2, column=0, pady=(0, 10))
        
        ttk.Button(button_frame, text="保存", command=save_mapping).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="加载默认", command=load_default).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="取消", command=edit_dialog.destroy).pack(side=tk.LEFT, padx=5)

    def format_emotion_mapping_to_text(self, emotion_mapping):
        """将情绪映射字典格式化为文本"""
        lines = []
        if not emotion_mapping:
            return ""
        
        # 按照图片编号排序
        sorted_nums = sorted(emotion_mapping.keys(), key=lambda x: int(x))
        
        for img_num in sorted_nums:
            emotions = emotion_mapping[img_num]
            # 确保 emotions 是列表且所有元素都是字符串
            if isinstance(emotions, str):
                emotions = [emotions]
            elif not isinstance(emotions, list):
                emotions = []
            
            # 转换所有情绪名称为字符串
            emotions = [str(e) for e in emotions]
            
            # 过滤空字符串
            emotions = [e for e in emotions if e]
            
            if emotions:
                emotions_str = ",".join(emotions)
                lines.append(f"{img_num}-{emotions_str}")
        
        return "\n".join(lines)

    def parse_emotion_mapping_from_text(self, text):
        """将文本解析为情绪映射字典"""
        emotion_mapping = {}
        
        if not text:
            return emotion_mapping
        
        lines = text.strip().split('\n')
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            
            # 分割图片编号和情绪列表
            if '-' in line:
                parts = line.split('-', 1)
                if len(parts) == 2:
                    img_num_part, emotions_part = parts
                    img_num = img_num_part.strip()
                    
                    if not img_num:
                        continue
                    
                    # 分割情绪名称
                    emotions = []
                    for e in emotions_part.split(','):
                        e = e.strip()
                        if e:  # 确保不是空字符串
                            emotions.append(str(e))
                    
                    if emotions:
                        emotion_mapping[img_num] = emotions
        
        return emotion_mapping

    def validate_emotion_mapping(self, emotion_mapping, char_folder_name):
        """验证情绪映射的有效性"""
        char_path = os.path.join(self.character_dir, char_folder_name)
        
        # 检查图片编号是否有效（对应存在的图片）
        for img_num in emotion_mapping.keys():
            try:
                # 检查图片是否存在
                img_name = f"{char_folder_name}{img_num}.png"
                img_path = os.path.join(char_path, img_name)
                
                if not os.path.exists(img_path):
                    # 图片不存在，但可以允许这种情况（用户可能稍后添加图片）
                    print(f"警告: 图片 {img_name} 不存在")
            except ValueError:
                return False  # 图片编号不是有效的数字
        
        return True

    def generate_default_emotion_mapping(self, char_folder_name):
        """生成默认的情绪映射（基于默认的15种情绪）"""
        default_emotions = {
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
        
        # 只包含角色实际拥有的表情图片
        char_path = os.path.join(self.character_dir, char_folder_name)
        actual_images = []
        
        if os.path.exists(char_path):
            for f in os.listdir(char_path):
                if f.startswith(char_folder_name) and f.endswith('.png'):
                    try:
                        # 提取数字部分
                        prefix_len = len(char_folder_name)
                        img_num = int(f[prefix_len:-4])
                        actual_images.append(img_num)
                    except:
                        pass
        
        # 过滤只保留实际存在的图片编号
        filtered_mapping = {}
        for img_num in actual_images:
            if img_num in default_emotions:
                # 确保情绪名称是字符串
                emotions = [str(e) for e in default_emotions[img_num]]
                filtered_mapping[str(img_num)] = emotions
        
        return filtered_mapping

    def save_emotion_mapping_to_config(self, char_folder_name, emotion_mapping):
        """将情绪映射保存到角色的配置文件中"""
        char_path = os.path.join(self.character_dir, char_folder_name)
        config_path = os.path.join(char_path, "config.json")
        
        try:
            # 读取现有配置
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
            else:
                config_data = {
                    "folder_name": char_folder_name,
                    "display_name": char_folder_name,
                    "drawx": -450,
                    "drawy": -100,
                    "enlarge": 1.0,
                    "font": "font3.ttf",
                    "dialog_font": "font3.ttf",
                    "color": {"r": 255, "g": 255, "b": 255}
                }
            
            # 清理情绪映射数据，确保格式正确
            cleaned_mapping = {}
            for img_num, emotions in emotion_mapping.items():
                if isinstance(emotions, list):
                    cleaned_mapping[img_num] = [str(e) for e in emotions if e]
                elif isinstance(emotions, str):
                    cleaned_mapping[img_num] = [str(emotions)]
                else:
                    cleaned_mapping[img_num] = []
            
            # 更新情绪映射
            config_data["emotion_mapping"] = cleaned_mapping
            
            # 保存配置
            with open(config_path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, ensure_ascii=False, indent=2)
            
            # 更新当前映射
            self.current_emotion_mapping = cleaned_mapping
            
            return True
            
        except Exception as e:
            print(f"保存情绪映射失败: {e}")
            return False
    
    def delete_background(self):
        """删除背景"""
        selected = self.bg_listbox.curselection()
        if not selected:
            messagebox.showerror("错误", "请先选择一个背景")
            return
        
        bg_name = self.bg_listbox.get(selected[0])
        
        if messagebox.askyesno("确认", f"确定要删除背景 '{bg_name}' 吗？此操作不可恢复！"):
            try:
                bg_path = os.path.join(self.background_dir, bg_name)
                shutil.rmtree(bg_path)
                messagebox.showinfo("成功", f"背景 '{bg_name}' 已删除")
                self.refresh_background_list()
                self.refresh_default_background_list()
            except Exception as e:
                messagebox.showerror("错误", f"删除背景失败: {e}")
    
    def delete_character(self):
        """删除角色"""
        selected = self.char_listbox.curselection()
        if not selected:
            messagebox.showerror("错误", "请先选择一个角色")
            return
        
        char_folder_name = self.char_listbox.get(selected[0])
        
        if messagebox.askyesno("确认", f"确定要删除角色 '{char_folder_name}' 吗？此操作不可恢复！"):
            try:
                char_path = os.path.join(self.character_dir, char_folder_name)
                shutil.rmtree(char_path)
                messagebox.showinfo("成功", f"角色 '{char_folder_name}' 已删除")
                self.refresh_character_list()
                self.current_character = None
            except Exception as e:
                messagebox.showerror("错误", f"删除角色失败: {e}")
    
    def on_background_select(self, event):
        """背景选择事件"""
        selected = self.bg_listbox.curselection()
        if selected:
            bg_name = self.bg_listbox.get(selected[0])
            bg_path = os.path.join(self.background_dir, bg_name)
            
            # 统计背景图片数量
            bg_images = [f for f in os.listdir(bg_path) if f.startswith('c') and f.endswith('.png') and os.path.isfile(os.path.join(bg_path, f))]
            has_d = os.path.exists(os.path.join(bg_path, "d.png"))
            
            self.bg_preview_text.set(f"背景: {bg_name}, 图片数量: {len(bg_images)}, 透明框: {'有' if has_d else '无'}")
    
    def on_character_select(self, event):
        """角色选择事件（修改版，加载情绪映射）"""
        selected = self.char_listbox.curselection()
        if selected:
            char_folder_name = self.char_listbox.get(selected[0])
            self.current_character = char_folder_name
            char_path = os.path.join(self.character_dir, char_folder_name)
            
            # 统计表情图片数量
            char_images = [f for f in os.listdir(char_path) 
                        if f.startswith(char_folder_name) and f.endswith('.png') 
                        and os.path.isfile(os.path.join(char_path, f))]
            
            # 读取配置
            config_path = os.path.join(char_path, "config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 显示角色信息
                display_name = config_data.get("display_name", char_folder_name)
                drawx = config_data.get("drawx", 0)
                drawy = config_data.get("drawy", 0)
                enlarge = config_data.get("enlarge", 1.0)
                color = config_data.get("color", {"r": 255, "g": 255, "b": 255})
                
                # 加载角色对话框/名字字体
                dialog_font = config_data.get("dialog_font", "")
                name_font = config_data.get("name_font", "")
                self.character_dialog_font_var.set(dialog_font)
                self.character_name_font_var.set(name_font)
                
                # 新增：加载情绪映射
                emotion_mapping = config_data.get("emotion_mapping", {})
                self.current_emotion_mapping = emotion_mapping
                
                # 更新显示
                self.char_drawx_label.config(text=str(drawx))
                self.char_drawy_label.config(text=str(drawy))
                self.char_enlarge_label.config(text=str(enlarge))
                
                # 颜色显示
                r, g, b = color["r"], color["g"], color["b"]
                color_info = f"RGB({r},{g},{b})"
                color_code = f"#{r:02x}{g:02x}{b:02x}"
                self.char_color_label.config(background=color_code, text=color_info)
                
                # 显示情绪映射信息
                emotion_count = len(emotion_mapping)
                mapping_info = f"，已配置情绪: {emotion_count}个" if emotion_count > 0 else "，未配置情绪映射"
                self.char_preview_text.set(f"角色: {display_name} ({char_folder_name}), 表情数量: {len(char_images)}{mapping_info}")
            else:
                self.char_preview_text.set(f"角色: {char_folder_name}, 表情数量: {len(char_images)}")
                self.char_color_label.config(background="white", text="未设置")
                self.char_drawx_label.config(text="0")
                self.char_drawy_label.config(text="0")
                self.char_enlarge_label.config(text="1.0")
                self.character_dialog_font_var.set("")
                self.character_name_font_var.set("")
                self.current_emotion_mapping = {}
    
    def generate_config_preview(self):
        """生成配置预览"""
        try:
            config_content = self.generate_info_json_content()
            self.config_text.delete(1.0, tk.END)
            self.config_text.insert(1.0, json.dumps(config_content, ensure_ascii=False, indent=2))
        except Exception as e:
            messagebox.showerror("错误", f"生成配置预览失败: {e}")
    
    def save_config_to_file(self):
        """保存配置到文件"""
        try:
            config_content = self.generate_info_json_content()
            info_json_path = os.path.join(self.resource_dir, "info.json")
            
            with open(info_json_path, 'w', encoding='utf-8') as f:
                json.dump(config_content, f, ensure_ascii=False, indent=2)
            
            messagebox.showinfo("成功", f"info.json 文件已生成到: {info_json_path}")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置文件失败: {e}")
    
    def set_default_background(self):
        """设置默认背景"""
        default_bg = self.default_bg_var.get()
        if not default_bg:
            messagebox.showerror("错误", "请选择一个默认背景")
            return
        
        messagebox.showinfo("成功", f"已设置默认背景为: {default_bg} (将在生成配置文件时生效)")

    def load_api_config(self):
        """从现有的info.json加载API配置"""
        info_json_path = os.path.join(self.resource_dir, "info.json")
        try:
            if os.path.exists(info_json_path):
                with open(info_json_path, 'r', encoding='utf-8') as f:
                    info_data = json.load(f)
                
                # 检查是否有api_config部分
                if "api_config" in info_data:
                    api_config = info_data["api_config"]
                    self.api_enable_var.set(api_config.get("enable_api", False))
                    self.api_key_var.set(api_config.get("api_key", ""))
                    print("已加载API配置")
        except Exception as e:
            print(f"加载API配置失败: {e}")  

    def generate_info_json_content(self):
        """生成info.json文件内容（修改版，包含情绪映射）"""
        # 收集背景配置
        background_configs = {}
        if os.path.exists(self.background_dir):
            for bg_name in os.listdir(self.background_dir):
                bg_path = os.path.join(self.background_dir, bg_name)
                if os.path.isdir(bg_path):
                    # 统计背景图片数量
                    bg_images = [f for f in os.listdir(bg_path) if f.startswith('c') and f.endswith('.png') and os.path.isfile(os.path.join(bg_path, f))]
                    num_bg = len(bg_images)
                    
                    background_configs[bg_name] = {
                        "name": bg_name,
                        "num_bg": num_bg,
                        "text_box_topleft": [728, 355],
                        "text_box_bottomright": [2339, 800]
                    }
        
        # 收集角色配置
        characters = {}
        text_configs_dict = {}
        
        if os.path.exists(self.character_dir):
            for char_folder_name in os.listdir(self.character_dir):
                char_path = os.path.join(self.character_dir, char_folder_name)
                if os.path.isdir(char_path):
                    # 统计表情图片数量
                    char_images = [f for f in os.listdir(char_path) if f.startswith(char_folder_name) and f.endswith('.png') and os.path.isfile(os.path.join(char_path, f))]
                    emotion_count = len(char_images)
                    
                    # 读取角色配置
                    config_path = os.path.join(char_path, "config.json")
                    if os.path.exists(config_path):
                        with open(config_path, 'r', encoding='utf-8') as f:
                            config_data = json.load(f)
                        
                        # 从config.json中获取显示名
                        display_name = config_data.get("display_name", char_folder_name)
                        drawx = config_data.get("drawx", -450)
                        drawy = config_data.get("drawy", -100)
                        enlarge = config_data.get("enlarge", 1.0)
                        color = config_data.get("color", {"r": 255, "g": 255, "b": 255})
                        font = config_data.get("font", "")
                        dialog_font = config_data.get("dialog_font", "")
                        
                        # 新增：获取情绪映射
                        emotion_mapping = config_data.get("emotion_mapping", {})
                        
                        # 确保情绪映射的格式正确
                        if emotion_mapping:
                            cleaned_mapping = {}
                            for img_num, emotions in emotion_mapping.items():
                                if isinstance(emotions, list):
                                    cleaned_mapping[img_num] = [str(e) for e in emotions]
                                elif isinstance(emotions, str):
                                    cleaned_mapping[img_num] = [str(emotions)]
                                else:
                                    cleaned_mapping[img_num] = []
                            emotion_mapping = cleaned_mapping
                    else:
                        # 默认配置
                        display_name = char_folder_name
                        drawx = -450
                        drawy = -100
                        enlarge = 1.0
                        color = {"r": 255, "g": 255, "b": 255}
                        font = ""
                        dialog_font = ""
                        emotion_mapping = {}  # 默认空映射
                    
                    # 角色配置 - 包含情绪映射
                    characters[char_folder_name] = {
                        "display_name": display_name,
                        "emotion_count": emotion_count,
                        "font": font,
                        "dialog_font": dialog_font,
                        "drawy": drawy,
                        "drawx": drawx,
                        "enlarge": enlarge,
                        "emotion_mapping": emotion_mapping  # 新增：情绪映射
                    }
                    
                    # 生成文字配置
                    if len(display_name) >= 1:
                        first_char = display_name[0]
                        second_char = display_name[1:] if len(display_name) > 1 else ""
                    else:
                        first_char = display_name
                        second_char = ""
                    
                    text_configs_dict[char_folder_name] = [
                        {
                            "text": first_char,
                            "position": [759, 73],  # 注意：JSON中需要列表格式
                            "font_color": [color["r"], color["g"], color["b"]],  # 列表格式
                            "font_size": 186
                        },
                        {
                            "text": second_char,
                            "position": [945, 175],  # 列表格式
                            "font_color": [255, 255, 255],  # 列表格式
                            "font_size": 92
                        }
                    ]
        
        # 获取默认背景
        default_background = self.default_bg_var.get() if self.default_bg_var.get() else "hoshishiro"
        
        # 构建字体配置
        font_configs = {
            "global": {
                "chinese_font": self.chinese_font_var.get(),
                "english_math_font": self.english_math_font_var.get()
            },
            "characters": {}
        }
        
        # 收集角色字体配置
        if os.path.exists(self.character_dir):
            for char_folder_name in os.listdir(self.character_dir):
                char_path = os.path.join(self.character_dir, char_folder_name)
                if os.path.isdir(char_path):
                    config_path = os.path.join(char_path, "config.json")
                    if os.path.exists(config_path):
                        with open(config_path, 'r', encoding='utf-8') as f:
                            config_data = json.load(f)
                        
                        # 获取角色对话框/名字字体
                        dialog_font = config_data.get("dialog_font", "")
                        name_font = config_data.get("name_font", "")
                        font_configs["characters"][char_folder_name] = {
                            "dialog_font": dialog_font,
                            "name_font": name_font  # 角色名字字体
                        }
        
        # API配置
        api_config = {
            "enable_api": self.api_enable_var.get(),
            "api_key": self.api_key_var.get()
        }
        
        # 构建完整的JSON结构
        info_json_content = {
            "background_configs": background_configs,
            "DEFAULT_BACKGROUND": default_background,
            "characters": characters,
            "text_configs_dict": text_configs_dict,
            "font_configs": font_configs,
            "api_config": api_config
        }
        
        return info_json_content


def main():
    root = tk.Tk()
    app = ResourceManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()