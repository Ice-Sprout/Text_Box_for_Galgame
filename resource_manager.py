import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import os
import shutil
from PIL import Image
import json

class ResourceManager:
    def __init__(self, root):
        self.root = root
        self.root.title("资源管理器 - 图片生成器")
        self.root.geometry("900x700")
        
        # 基础路径
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.background_dir = os.path.join(self.base_dir, "background")
        self.character_dir = os.path.join(self.base_dir, "character")
        
        # 创建必要的目录
        os.makedirs(self.background_dir, exist_ok=True)
        os.makedirs(self.character_dir, exist_ok=True)
        
        # 当前选中的角色
        self.current_character = None
        
        self.create_widgets()
        self.refresh_lists()
    
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
        title_label = ttk.Label(main_frame, text="资源管理器", font=("Arial", 16, "bold"))
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
        
        # 配置生成选项卡
        config_frame = ttk.Frame(notebook, padding="10")
        notebook.add(config_frame, text="配置生成")
        
        # 设置选项卡的网格权重
        bg_frame.columnconfigure(1, weight=1)
        bg_frame.rowconfigure(1, weight=1)
        char_frame.columnconfigure(1, weight=1)
        char_frame.rowconfigure(1, weight=1)
        config_frame.columnconfigure(1, weight=1)
        
        # 初始化各个选项卡
        self.setup_background_tab(bg_frame)
        self.setup_character_tab(char_frame)
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
        
        # 背景图片预览
        ttk.Label(parent, text="背景图片预览:").grid(row=4, column=0, sticky=tk.W, pady=5)
        self.bg_preview_text = tk.StringVar(value="选择背景查看图片")
        ttk.Label(parent, textvariable=self.bg_preview_text).grid(row=5, column=0, columnspan=3, pady=5)
        
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
        
        # 角色图片预览
        ttk.Label(parent, text="角色表情预览:").grid(row=5, column=0, sticky=tk.W, pady=5)
        self.char_preview_text = tk.StringVar(value="选择角色查看表情")
        ttk.Label(parent, textvariable=self.char_preview_text).grid(row=6, column=0, columnspan=3, pady=5)
        
        # 绑定列表选择事件
        self.char_listbox.bind('<<ListboxSelect>>', self.on_character_select)
    
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
        ttk.Button(config_button_frame, text="保存到info.py", command=self.save_config_to_file).grid(row=0, column=1, padx=5)
        ttk.Button(config_button_frame, text="设置默认背景", command=self.set_default_background).grid(row=0, column=2, padx=5)
        
        # 默认背景设置
        ttk.Label(parent, text="默认背景:").grid(row=3, column=0, sticky=tk.W, pady=5)
        self.default_bg_var = tk.StringVar()
        self.default_bg_combo = ttk.Combobox(parent, textvariable=self.default_bg_var, state="readonly")
        self.default_bg_combo.grid(row=3, column=1, sticky=(tk.W, tk.E), pady=5, padx=5)
    
    def refresh_lists(self):
        """刷新所有列表"""
        self.refresh_background_list()
        self.refresh_character_list()
        self.refresh_default_background_list()
    
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
                "font": "font3.ttf",
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
        """导入角色表情图片"""
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
            
            for i, file_path in enumerate(files):
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
            
            messagebox.showinfo("成功", f"成功导入 {len(files)} 张表情图片到 '{char_folder_name}'，已转换为PNG格式")
            self.on_character_select(None)  # 刷新预览信息
        except Exception as e:
            messagebox.showerror("错误", f"导入表情图片失败: {e}")
    
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
                "font": "font3.ttf",
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
                "font": "font3.ttf",
                "color": {"r": 255, "g": 255, "b": 255}
            }
        
        # 创建编辑对话框
        edit_dialog = tk.Toplevel(self.root)
        edit_dialog.title(f"编辑角色设置 - {char_folder_name}")
        edit_dialog.geometry("400x300")
        
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
        
        def save_settings():
            try:
                # 更新配置
                config_data["display_name"] = display_name_var.get()
                config_data["drawx"] = int(drawx_var.get())
                config_data["drawy"] = int(drawy_var.get())
                config_data["enlarge"] = float(enlarge_var.get())  # 新增 enlarge
                
                # 保存配置
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(config_data, f, ensure_ascii=False, indent=2)
                
                # 更新显示
                self.char_drawx_label.config(text=drawx_var.get())
                self.char_drawy_label.config(text=drawy_var.get())
                
                messagebox.showinfo("成功", "角色设置已更新")
                edit_dialog.destroy()
                
                # 刷新角色信息显示
                self.on_character_select(None)
                
            except ValueError as e:
                messagebox.showerror("错误", f"输入值错误: {e}")
        
        # 保存按钮位置调整
        ttk.Button(edit_dialog, text="保存设置", command=save_settings).grid(row=4, column=0, columnspan=2, pady=20)
    
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
        """角色选择事件"""
        selected = self.char_listbox.curselection()
        if selected:
            char_folder_name = self.char_listbox.get(selected[0])
            self.current_character = char_folder_name
            char_path = os.path.join(self.character_dir, char_folder_name)
            
            # 统计表情图片数量
            char_images = [f for f in os.listdir(char_path) if f.startswith(char_folder_name) and f.endswith('.png') and os.path.isfile(os.path.join(char_path, f))]
            
            # 读取配置
            config_path = os.path.join(char_path, "config.json")
            if os.path.exists(config_path):
                with open(config_path, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                
                # 显示角色信息
                display_name = config_data.get("display_name", char_folder_name)
                drawx = config_data.get("drawx", 0)
                drawy = config_data.get("drawy", 0)
                enlarge = config_data.get("enlarge", 1.0)  # 获取 enlarge
                color = config_data.get("color", {"r": 255, "g": 255, "b": 255})
                
                # 更新显示
                self.char_drawx_label.config(text=str(drawx))
                self.char_drawy_label.config(text=str(drawy))
                self.char_enlarge_label.config(text=str(enlarge))  # 更新 enlarge 显示
                
                # 颜色显示
                r, g, b = color["r"], color["g"], color["b"]
                color_info = f"RGB({r},{g},{b})"
                color_code = f"#{r:02x}{g:02x}{b:02x}"
                self.char_color_label.config(background=color_code, text=color_info)
                
                self.char_preview_text.set(f"角色: {display_name} ({char_folder_name}), 表情数量: {len(char_images)}")
            else:
                self.char_preview_text.set(f"角色: {char_folder_name}, 表情数量: {len(char_images)}")
                self.char_color_label.config(background="white", text="未设置")
                self.char_drawx_label.config(text="0")
                self.char_drawy_label.config(text="0")
                self.char_enlarge_label.config(text="1.0")  # 默认 enlarge 显示
    
    def generate_config_preview(self):
        """生成配置预览"""
        try:
            config_content = self.generate_info_py_content()
            self.config_text.delete(1.0, tk.END)
            self.config_text.insert(1.0, config_content)
        except Exception as e:
            messagebox.showerror("错误", f"生成配置预览失败: {e}")
    
    def save_config_to_file(self):
        """保存配置到文件"""
        try:
            config_content = self.generate_info_py_content()
            info_py_path = os.path.join(self.base_dir, "info.py")
            
            with open(info_py_path, 'w', encoding='utf-8') as f:
                f.write(config_content)
            
            messagebox.showinfo("成功", "info.py 文件已生成")
        except Exception as e:
            messagebox.showerror("错误", f"保存配置文件失败: {e}")
    
    def set_default_background(self):
        """设置默认背景"""
        default_bg = self.default_bg_var.get()
        if not default_bg:
            messagebox.showerror("错误", "请选择一个默认背景")
            return
        
        messagebox.showinfo("成功", f"已设置默认背景为: {default_bg}")
    
    def generate_info_py_content(self):
        """生成info.py文件内容"""
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
                        
                        display_name = config_data.get("display_name", char_folder_name)
                        drawx = config_data.get("drawx", -450)
                        drawy = config_data.get("drawy", -100)
                        enlarge = config_data.get("enlarge", 1.0)  # 新增 enlarge
                        color = config_data.get("color", {"r": 255, "g": 255, "b": 255})
                        font = config_data.get("font", "font3.ttf")
                    else:
                        # 默认配置
                        display_name = char_folder_name
                        drawx = -450
                        drawy = -100
                        enlarge = 1.0  # 默认 enlarge 为 1.0
                        color = {"r": 255, "g": 255, "b": 255}
                        font = "font3.ttf"
                    
                    # 角色配置 - 添加display_name字段和enlarge字段
                    characters[char_folder_name] = {
                        "display_name": display_name,  # 添加显示名
                        "emotion_count": emotion_count,
                        "font": font,
                        "drawy": drawy,
                        "drawx": drawx,
                        "enlarge": enlarge  # 新增 enlarge 参数
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
                            "position": (759, 73),
                            "font_color": (color["r"], color["g"], color["b"]),
                            "font_size": 186
                        },
                        {
                            "text": second_char,
                            "position": (945, 175),
                            "font_color": (255, 255, 255),
                            "font_size": 92
                        }
                    ]
        
        # 获取默认背景
        default_background = self.default_bg_var.get() if self.default_bg_var.get() else "hoshishiro"
        
        # 格式化输出 - 修复缩进问题
        background_str = self.format_dict(background_configs, indent=4)
        characters_str = self.format_dict(characters, indent=4)
        text_configs_str = self.format_dict(text_configs_dict, indent=4)
        
        # 生成Python文件内容 - 修复缩进问题
        # 使用lstrip()去除每行开头的空白，并确保第一行没有缩进
        content_lines = [
            "# info.py",
            "",
            "# 背景图片配置字典",
            f"background_configs = {background_str}",
            "",
            "# 默认背景配置",
            f'DEFAULT_BACKGROUND = "{default_background}"',
            "",
            "",
            "# 角色配置字典",
            f"characters = {characters_str}",
            "",
            "# 角色文字配置字典 - 每个角色对应文字配置",
            f"text_configs_dict = {text_configs_str}"
        ]
        
        return '\n'.join(content_lines)

    def format_dict(self, data, indent=4):
        """格式化字典为字符串，用于生成Python代码"""
        if not data:
            return "{}"
        
        result = "{\n"
        indent_str = " " * indent
        
        if isinstance(data, dict):
            items = list(data.items())
            for i, (key, value) in enumerate(items):
                result += f'{indent_str}"{key}": '
                
                if isinstance(value, dict):
                    # 递归格式化嵌套字典
                    nested = self.format_dict(value, indent + 4)
                    # 确保嵌套字典正确格式化
                    nested_lines = nested.split('\n')
                    if len(nested_lines) == 1:
                        result += nested
                    else:
                        result += nested
                elif isinstance(value, list):
                    # 格式化列表
                    result += self.format_list(value, indent + 4)
                elif isinstance(value, tuple):
                    # 格式化元组
                    result += str(value)
                elif isinstance(value, str):
                    result += f'"{value}"'
                else:
                    result += str(value)
                
                if i < len(items) - 1:
                    result += ",\n"
                else:
                    result += "\n"
        
        result += " " * (indent - 4) + "}"
        return result

    def format_list(self, data, indent=4):
        """格式化列表为字符串，用于生成Python代码"""
        if not data:
            return "[]"
        
        result = "[\n"
        indent_str = " " * indent
        
        for i, item in enumerate(data):
            result += indent_str
            
            if isinstance(item, dict):
                # 格式化字典
                result += self.format_dict(item, indent + 4)
            elif isinstance(item, list):
                # 递归格式化嵌套列表
                result += self.format_list(item, indent + 4)
            elif isinstance(item, tuple):
                # 格式化元组
                result += str(item)
            elif isinstance(item, str):
                result += f'"{item}"'
            else:
                result += str(item)
            
            if i < len(data) - 1:
                result += ",\n"
            else:
                result += "\n"
        
        result += " " * (indent - 4) + "]"
        return result

def main():
    root = tk.Tk()
    app = ResourceManager(root)
    root.mainloop()

if __name__ == "__main__":
    main()