# 流程
# 1 搞蒙版
# 2 截头像
# 3 叠头像
# 4 嵌字
# 5 改分辨率
#1 优化算法 尽量不出现两个重复表情在一块
#2 优化代码 md0.2s的时间太长了
#3 把原代码重做 他def的函数我看不懂 只能打印一次文本吗我靠
#4 增加多种表情包选择
#5 把选择的地方做的更明显一些
#6 加阴影
#7 新增：快捷键切换角色功能
#8 新增：限制生成图片大小功能

print("""角色说明:
1狩叶 2诺瓦 3音理 4野鸟（没做） 5花江（没做） 6真白 


快捷键说明:
Ctrl+i : 切换角色i
Ctrl+0: 显示当前角色
Alt+1-9: 切换表情1-9
Alt+L: 切换LaTeX转换功能
Enter: 生成图片
Tab: 退出程序
Ctrl+Tab: 清除缓存
Ctrl+G和Ctrl+H: 切换自动粘贴/发送功能（TIMemoji替代品）
      
      
程序说明：
初次更换角色后需要等待数秒才能正常使用
如果调用API则延迟1-2s加载，随机模式仅需要半秒
感谢各位的支持

"""
)

import sys
import random
import time
import keyboard
import pyperclip
import io
from PIL import Image,ImageDraw,ImageFont
import win32clipboard
import os
import shutil
import threading
import win32gui
import win32process
import psutil
from api import get_emotion_from_text, get_emotion_name, EMOTION_COUNT, DEFAULT_EMOTION, clear_chat_history, get_chat_history

from latex import convert_latex_in_text, latex_converter
from info import background_configs, characters, text_configs_dict, DEFAULT_BACKGROUND
from text_to_image import generate_image, pre_generate_character_images, get_pregen_folder, check_pregen_images_exist, delate


# 角色配置
current_character_index = 1  # 初始角色为狩叶（索引从0开始）
current_background = DEFAULT_BACKGROUND
num_bg = background_configs[current_background]["num_bg"]
text_box_topleft = background_configs[current_background]["text_box_topleft"]
text_box_bottomright = background_configs[current_background]["text_box_bottomright"]

try:
    from latex import convert_latex_in_text
except ImportError:
    print("警告: latex.py 导入失败，LaTeX 功能不可用")
    # 提供一个空的替代函数
    def convert_latex_in_text(text):
        return text

# ===== PyInstaller 资源路径处理函数 =====
def get_resource_path(relative_path):
    """获取资源文件的绝对路径，兼容开发环境和打包后的环境"""
    try:
        # PyInstaller 创建临时文件夹，路径存储在 _MEIPASS 中
        base_path = sys._MEIPASS
    except AttributeError:
        # 开发环境中使用当前文件所在目录
        base_path = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_path, relative_path)

i = -1
value_1 = -1
expression = None
latex_insert = False  # LaTeX转换功能开关
reduce_image = True  # 图片压缩功能开关

#前台窗口白名单
windowwhitelist=["TIM.exe","WeChat.exe","Weixin.exe","WeChatApp.exe","QQ.exe"]
enablewhitelist=True

# 获取预生成文件夹路径
magic_cut_folder = get_pregen_folder()

# 角色列表（按顺序对应1-13的角色）
character_list = list(characters.keys())

# 获取当前角色信息
def get_current_character():
    character_names = list(characters.keys())
    return character_names[current_character_index-1] if current_character_index-1 < len(character_names) else character_names[0]

def get_current_font():
    current_char = get_current_character()
    return get_resource_path(characters[current_char]["font"])

def get_current_emotion_count():
    current_char = get_current_character()
    return characters[current_char]["emotion_count"]


# 修改预生成图片函数
def generate_and_save_images(character_name):
    pre_generate_character_images(character_name)

def switch_character(new_index):
    global current_character_index
    if 0 <= new_index < len(character_list):
        current_character_index = new_index
        character_name = get_current_character()
        print(f"已切换到角色: {character_name}")

        # 生成并保存图片
        generate_and_save_images(character_name)

        return True
    return False

#自动发送/粘贴
AUTO_PASTE_IMAGE=True
AUTO_SEND_IMAGE=True

def switch_auto_paste():
    global AUTO_PASTE_IMAGE,AUTO_SEND_IMAGE
    AUTO_PASTE_IMAGE=not AUTO_PASTE_IMAGE
    if(AUTO_PASTE_IMAGE==False):
        AUTO_SEND_IMAGE=False
    print(f"自动粘贴已切换为: {AUTO_PASTE_IMAGE}")

def switch_auto_send():
    global AUTO_PASTE_IMAGE,AUTO_SEND_IMAGE
    if(AUTO_PASTE_IMAGE==False):
        print("请先开启自动粘贴")
        return
    AUTO_SEND_IMAGE=not AUTO_SEND_IMAGE
    print(f"自动发送已切换为: {AUTO_SEND_IMAGE}")

# 显示当前角色信息
def show_current_character():
    character_name = get_current_character()
    print(f"当前角色: {character_name}")

# 显示当前角色信息
show_current_character()

# 测试：生成当前角色的图片
generate_and_save_images(get_current_character())

def get_expression(i):
    global expression
    character_name = get_current_character()
    # 修改这里：使用 characters 而不是 mahoshojo
    if i <= characters[character_name]["emotion_count"]:
        print(f"已切换至第{i}个表情")
        expression = i

# 获取表情图片名称
def get_random_value(input_text: str = None):
    """
    根据输入文本的情绪分析结果获取对应的表情图片
    如果未提供文本，则使用默认情绪
    """
    global value_1, expression

    character_name = get_current_character()
    emotion_count = get_current_emotion_count()
    total_images = num_bg * emotion_count

    # 如果指定了表情，优先使用指定表情
    if expression:
        i = random.randint((expression-1)*num_bg+1, expression*num_bg)
        value_1 = i
        expression = None
        return f"{character_name} ({i})"

    # 情绪分析
    if input_text:
        emotion_id = get_emotion_from_text(input_text)
        print(f"情绪分析结果: {get_emotion_name(emotion_id)} (编号: {emotion_id})")
    else:
        emotion_id = DEFAULT_EMOTION
        print(f"使用默认情绪: {get_emotion_name(emotion_id)}")

    # 确保情绪编号在有效范围内
    emotion_id = max(1, min(emotion_id, emotion_count))

    # 随机选择该情绪下的一个图片
    i = random.randint((emotion_id-1)*num_bg+1, emotion_id*num_bg)
    value_1 = i

    return f"{character_name} ({i})"

HOTKEY= "enter"

# 全选快捷键, 此按键并不会监听,  而是会作为模拟输入
# 此值为字符串, 代表热键的键名, 格式同 HOTKEY
SELECT_ALL_HOTKEY= "ctrl+a"

# 剪切快捷键, 此按键并不会监听,  而是会作为模拟输入
# 此值为字符串, 代表热键的键名, 格式同 HOTKEY
CUT_HOTKEY= "ctrl+x"

# 黏贴快捷键, 此按键并不会监听,  而是会作为模拟输入
# 此值为字符串, 代表热键的键名, 格式同 HOTKEY
PASTE_HOTKEY= "ctrl+v"

# 发送消息快捷键, 此按键并不会监听,  而是会作为模拟输入
# 此值为字符串, 代表热键的键名, 格式同 HOTKEY
SEND_HOTKEY= "enter"

# 是否阻塞按键, 如果热键设置为阻塞模式, 则按下热键时不会将该按键传递给前台应用
# 如果生成热键和发送热键相同, 则强制阻塞, 防止误触发发送消息
# 此值为布尔值, True 或 False
BLOCK_HOTKEY= False

# 操作的间隔, 如果失效可以适当增大此数值
# 此值为数字, 单位为秒
DELAY= 0.1

# 是否自动黏贴生成的图片(如果为否则保留图片在剪贴板, 可以手动黏贴)
# 此值为布尔值, True 或 False
AUTO_PASTE_IMAGE= True

# 生成图片后是否自动发送(模拟回车键输入), 只有开启自动黏贴才生效
# 此值为布尔值, True 或 False
AUTO_SEND_IMAGE= True

def copy_png_bytes_to_clipboard(png_bytes: bytes):
    """将PNG图片字节流复制到剪贴板，保持压缩"""
    try:
        win32clipboard.OpenClipboard()
        win32clipboard.EmptyClipboard()

        # 直接设置PNG格式到剪贴板
        # 注册PNG格式
        png_format = win32clipboard.RegisterClipboardFormat("PNG")
        win32clipboard.SetClipboardData(png_format, png_bytes)

        # 同时设置DIB格式作为后备，确保兼容性
        image = Image.open(io.BytesIO(png_bytes))
        with io.BytesIO() as output:
            image.convert("RGB").save(output, "BMP")
            bmp_data = output.getvalue()[14:]
            win32clipboard.SetClipboardData(win32clipboard.CF_DIB, bmp_data)

        win32clipboard.CloseClipboard()
        print("图片已以PNG格式传输到剪贴板")

    except Exception as e:
        print(f"剪贴板传输失败: {e}")
        try:
            win32clipboard.CloseClipboard()
        except:
            pass

#判断窗口名
def get_window_exe_name():
    try:
        hwnd=win32gui.GetForegroundWindow()
        _,pid=win32process.GetWindowThreadProcessId(hwnd)
        process=psutil.Process(pid)
        exe_path=process.exe()
        return os.path.basename(exe_path)
    except Exception as e:
        print(f"获取文件名时发生错误：{e}")
        return None

def toggle_latex_insert():
    """切换LaTeX转换功能"""
    global latex_insert
    latex_insert = not latex_insert
    status = "开启" if latex_insert else "关闭"
    print(f"LaTeX公式转换功能已{status}")

# 在 toggle_latex_insert 函数附近添加切换压缩功能的函数
def toggle_reduce_image():
    """切换图片压缩功能"""
    global reduce_image
    reduce_image = not reduce_image
    status = "开启" if reduce_image else "关闭"
    print(f"图片压缩功能已{status}")

#针对latex导致程序崩溃，重写的调用程序
def cut_all_and_get_text() -> str:
    """模拟 Ctrl+A / Ctrl+X 剪切全部文本，并返回剪切得到的内容"""
    # 备份原剪贴板
    old_clip = pyperclip.paste()
    # 清空剪贴板，防止读到旧数据
    pyperclip.copy("")

    # 发送 Ctrl+A 和 Ctrl+X
    keyboard.send(SELECT_ALL_HOTKEY)
    keyboard.send(CUT_HOTKEY)
    time.sleep(DELAY)

    # 获取剪切后的内容
    new_clip = pyperclip.paste()

    # ===== 仅当有文本时，才调用LaTeX转换 =====
    if latex_insert and new_clip.strip() != "":
        converted_text = convert_latex_in_text(new_clip)
        if converted_text != new_clip:
            print(f"LaTeX转换: {new_clip} -> {converted_text}")
            new_clip = converted_text
            pyperclip.copy(new_clip)

    return new_clip

def try_get_image() -> Image.Image | None:
    """
    尝试从剪贴板获取图像，如果没有图像则返回 None。
    仅支持 Windows。
    """
    try:
        win32clipboard.OpenClipboard()
        if win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
            data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
            if data:
                # 将 DIB 数据转换为字节流，供 Pillow 打开
                bmp_data = data
                # DIB 格式缺少 BMP 文件头，需要手动加上
                # BMP 文件头是 14 字节，包含 "BM" 标识和文件大小信息
                header = b'BM' + (len(bmp_data) + 14).to_bytes(4, 'little') + b'\x00\x00\x00\x00\x36\x00\x00\x00'
                image = Image.open(io.BytesIO(header + bmp_data))
                return image
    except Exception as e:
        print("无法从剪贴板获取图像：", e)
    finally:
        try:
            win32clipboard.CloseClipboard()
        except:
            pass
    return None

def perform_keyboard_actions(png_bytes):
    """在主线程中执行所有键盘操作"""
    if png_bytes is None:
        print("Generate image failed!")
        return

    copy_png_bytes_to_clipboard(png_bytes)

    if AUTO_PASTE_IMAGE:
        # 使用 call_later 确保 send 在 keyboard 自己的线程中运行
        keyboard.call_later(lambda: keyboard.send(PASTE_HOTKEY), delay=0.1)

        if AUTO_SEND_IMAGE:
            keyboard.call_later(lambda: keyboard.send(SEND_HOTKEY), delay=0.4) # 增加延迟以确保粘贴完成

# 在 Start() 函数中修改 generate_image 调用，添加 reduce 参数
def Start():
    print("Start generate...")

    # 先获取文本内容
    text = pyperclip.paste()
    print(f"获取到的文本: {text}")

    character_name = get_current_character()

    try:
        # 使用新的text_to_image模块生成图片
        png_bytes, info_dict = generate_image(
            text=text,
            character_name=character_name,
            background_name=DEFAULT_BACKGROUND,
            emotion_id=None,  # 自动分析情绪
            expression=expression,  # 使用全局expression变量
            latex_insert=latex_insert,  # 使用全局latex_insert变量
            reduce=reduce_image  # 使用全局reduce_image变量
        )

        # 打印生成信息
        print(f"角色: {info_dict['character']}, 表情: {info_dict['expression_num']}, "
              f"背景: {info_dict['background_num']}, 情绪: {info_dict['emotion_name']}, "
              f"压缩: {'是' if info_dict.get('compressed', False) else '否'}")

    except Exception as e:
        print(f"生成图片失败: {e}")
        keyboard.call_later(perform_keyboard_actions, args=[None])
        return

    # 后续的键盘操作保持不变...
    keyboard.call_later(perform_keyboard_actions, args=[png_bytes])


def run_start_in_thread():
    if enablewhitelist and get_window_exe_name() not in windowwhitelist:
        print("当前窗口不在白名单内")
        keyboard.send(HOTKEY)
        return
    # 1. 在主线程（keyboard线程）中安全地剪切文本
    text = cut_all_and_get_text()

    # 2. 在后台线程中运行耗时的图像处理
    # 将获取的文本作为参数传递给 Start 函数（需要修改Start函数以接受它）
    # 但为了简化，我们依赖于剪贴板，因为 cut_all_and_get_text 已经更新了它
    threading.Thread(target=Start).start()

keyboard.add_hotkey('alt+l', toggle_latex_insert)
# 在热键绑定部分添加压缩功能切换热键（例如使用 Alt+R）
keyboard.add_hotkey('alt+r', toggle_reduce_image)
# 角色切换快捷键绑定
# 按Ctrl+1 到 Ctrl+9: 切换角色1-9
for i in range(1,9):
    keyboard.add_hotkey(f'ctrl+{i}', lambda idx=i: switch_character(idx))
keyboard.add_hotkey('ctrl+g',switch_auto_paste)
keyboard.add_hotkey('ctrl+h',switch_auto_send)
keyboard.add_hotkey('ctrl+Tab', lambda: delate(magic_cut_folder))

for i in range(1,10):
    keyboard.add_hotkey(f'alt+{i}', lambda idx=i: get_expression(idx))

# 绑定 Ctrl+Alt+H 作为全局热键
ok=keyboard.add_hotkey(HOTKEY,run_start_in_thread, suppress=BLOCK_HOTKEY or HOTKEY==SEND_HOTKEY)

# 绑定Ctrl+0显示当前角色
keyboard.add_hotkey('ctrl+0', show_current_character)

# 保持程序运行
keyboard.wait("Tab")