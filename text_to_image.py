import os
import random
from PIL import Image, ImageDraw, ImageFont
import io
import sys
import win32clipboard
from info import background_configs, characters, text_configs_dict, DEFAULT_BACKGROUND
from api import get_emotion_from_text, get_emotion_name, DEFAULT_EMOTION
from text_fit_draw import draw_text_auto
from image_fit_paste import paste_image_auto
from reduce import compress_image_simple

def get_resource_path(relative_path):
    """获取资源文件的绝对路径，兼容开发环境和打包后的环境"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)


def get_clipboard_image():
    """从剪贴板获取图片，返回PIL.Image对象（无图片则返回None）"""
    image = None
    # 标记剪贴板是否被当前函数打开
    clipboard_opened = False
    try:
        # 尝试打开剪贴板
        win32clipboard.OpenClipboard()
        clipboard_opened = True

        # 检查剪贴板是否有位图数据
        if not win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_DIB):
            # 也可检查CF_BITMAP格式，提高兼容性
            if not win32clipboard.IsClipboardFormatAvailable(win32clipboard.CF_BITMAP):
                return None

        # 读取剪贴板中的图片数据（优先CF_DIB，兼容CF_BITMAP）
        try:
            dib_data = win32clipboard.GetClipboardData(win32clipboard.CF_DIB)
        except:
            dib_data = win32clipboard.GetClipboardData(win32clipboard.CF_BITMAP)

        # 转换为PIL.Image对象
        image = Image.open(io.BytesIO(dib_data)).convert("RGBA")
    except Exception as e:
        print(f"获取剪贴板图片失败: {e}")
    finally:
        # 仅当当前函数成功打开剪贴板时，才执行关闭操作
        if clipboard_opened:
            try:
                win32clipboard.CloseClipboard()
            except Exception as e:
                print(f"关闭剪贴板失败: {e}")
    return image

def get_pregen_folder():
    """获取预生成图片文件夹路径"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    pregen_folder = os.path.join(base_dir, 'galframeforchat')
    os.makedirs(pregen_folder, exist_ok=True)
    return pregen_folder

def check_pregen_images_exist(character_name, background_name=DEFAULT_BACKGROUND):
    """检查预生成图片是否已存在且完整"""
    pregen_folder = get_pregen_folder()
    character_config = characters.get(character_name)
    background_config = background_configs.get(background_name)
    if not character_config or not background_config:
        return False
    emotion_count = character_config["emotion_count"]
    num_bg = background_config["num_bg"]
    total_images = emotion_count * num_bg
    for img_num in range(1, total_images + 1):
        expected_file = os.path.join(pregen_folder, f"{character_name}_{background_name}_{img_num}.jpg")
        if not os.path.exists(expected_file):
            return False
    return True

def pre_generate_character_images(character_name, background_name=DEFAULT_BACKGROUND):
    """预生成角色所有表情和背景组合的图片"""
    if check_pregen_images_exist(character_name, background_name):
        print(f"{character_name} 在背景 {background_name} 下的预生成图片已存在，跳过生成")
        return False

    pregen_folder = get_pregen_folder()
    character_config = characters.get(character_name)
    background_config = background_configs.get(background_name)

    if not character_config or not background_config:
        raise ValueError(f"角色 '{character_name}' 或背景 '{background_name}' 配置不存在")
    emotion_count = character_config["emotion_count"]
    num_bg = background_config["num_bg"]
    print(f"正在预生成 {character_name} 在背景 {background_name} 下的图片...")

    # 获取角色专属文字配置
    text_configs = text_configs_dict.get(character_name, [])
    
    for i in range(num_bg):
        # 加载背景图片
        background_path = get_resource_path(
            os.path.join("background", background_name, f"c{i+1}.png")
        )
        c_image = Image.open(background_path).convert("RGBA")
        
        # === 处理c图片 - 缩放并裁剪 ===
        # 1. 缩放c图片到宽度2560像素，保持宽高比
        target_width = 2560
        c_width, c_height = c_image.size
        scaling_factor = target_width / c_width
        new_c_height = int(c_height * scaling_factor)
        
        # 缩放c图片
        c_image_resized = c_image.resize((target_width, new_c_height), Image.LANCZOS)
        
        # 2. 从底部裁剪c图片到高度834像素
        if new_c_height >= 834:
            # 如果缩放后高度足够，从底部裁剪834像素
            c_image_cropped = c_image_resized.crop((0, new_c_height - 834, target_width, new_c_height))
        else:
            # 如果缩放后高度不足834像素，创建一个2560×834的透明背景，将c图片放在底部
            print(f"警告: 背景图片 c{i+1}.png 缩放后高度({new_c_height}px)不足834px")
            c_image_cropped = Image.new("RGBA", (target_width, 834), (0, 0, 0, 0))
            c_image_cropped.paste(c_image_resized, (0, 834 - new_c_height))
        
        # 使用处理后的c图片作为基础背景
        background = c_image_cropped
        
        # === 处理d图片 - 缩放并放置在底部 ===
        d_image_path = get_resource_path(
            os.path.join("background", background_name, "d.png")
        )
        if os.path.exists(d_image_path):
            d_image = Image.open(d_image_path).convert("RGBA")
            
            # 1. 缩放d图片到宽度2560像素，保持宽高比
            d_width, d_height = d_image.size
            scaling_factor_d = target_width / d_width
            new_d_height = int(d_height * scaling_factor_d)
            
            # 缩放d图片
            d_image_resized = d_image.resize((target_width, new_d_height), Image.LANCZOS)
            
            # 2. 处理d图片高度
            if new_d_height > 834:
                # 如果d图片高度超过834像素，从底部裁剪834像素
                d_image_final = d_image_resized.crop((0, new_d_height - 834, target_width, new_d_height))
            else:
                # 如果d图片高度不足834像素，直接使用
                d_image_final = d_image_resized
            
            # 3. 将d图片覆盖到背景底部
            # 计算位置：d图片底部与背景底部对齐
            d_y_position = 834 - d_image_final.height
            background.paste(d_image_final, (0, d_y_position), d_image_final)
        
        character_folder = get_resource_path(os.path.join("character", character_name))
        
        for j in range(emotion_count):
            overlay_path = os.path.join(character_folder, f"{character_name}{j+1}.png")
            overlay = Image.open(overlay_path).convert("RGBA")
            
            # ====== 新增：缩放角色表情图片到宽度750像素 ======
            target_char_width = 750  # 目标宽度750像素
            overlay_width, overlay_height = overlay.size
            if overlay_width != target_char_width:
                # 计算缩放比例
                scale_factor = target_char_width / overlay_width
                new_char_height = int(overlay_height * scale_factor)
                # 使用LANCZOS算法高质量缩放
                overlay = overlay.resize((target_char_width, new_char_height), Image.LANCZOS)
            
            result = background.copy()

            # 绘制角色图片 - 使用原有的drawx/drawy值
            result.paste(overlay, (0+characters[character_name]["drawx"], 134+characters[character_name]["drawy"]), overlay)

            # === 在预生成阶段绘制角色专属文字 ===
            if text_configs:
                draw = ImageDraw.Draw(result)
                shadow_offset = (2, 2)
                shadow_color = (0, 0, 0)
                
                for config in text_configs:
                    char_text = config["text"]
                    position = config["position"]
                    font_color = config["font_color"]
                    font_size = config["font_size"]
                
                    # 使用 get_resource_path 获取字体文件路径
                    font_path_char = get_resource_path("font3.ttf")
                    try:
                        char_font = ImageFont.truetype(font_path_char, font_size)
                        shadow_position = (position[0] + shadow_offset[0], position[1] + shadow_offset[1])
                        
                        # 绘制阴影文字
                        draw.text(shadow_position, char_text, fill=shadow_color, font=char_font)
                        # 绘制主文字
                        draw.text(position, char_text, fill=font_color, font=char_font)
                    except Exception as e:
                        print(f"预生成阶段角色文字绘制失败: {e}")
                        continue

            img_num = j * num_bg + i + 1
            save_path = os.path.join(pregen_folder, f"{character_name}_{background_name}_{img_num}.jpg")
            result.convert("RGB").save(save_path, quality=85)   
    print(f"{character_name} 在背景 {background_name} 下的图片预生成完成")
    return True

def get_pregen_image_path(character_name, img_num, background_name=DEFAULT_BACKGROUND):
    """获取预生成图片的路径"""
    pregen_folder = get_pregen_folder()
    return os.path.join(pregen_folder, f"{character_name}_{background_name}_{img_num}.jpg")

def generate_image(text, character_name, background_name=DEFAULT_BACKGROUND,
                  emotion_id=None, expression=None, latex_insert=False, reduce=True):
    """
    根据文本/图片、角色和背景信息生成图片
    新增：支持剪贴板图片输入，绕开LaTeX转换
    """
    # === 1. 图片输入判定：优先获取剪贴板图片 ===
    content_image = get_clipboard_image()
    is_image_input = content_image is not None and (text.strip() == "" or text is None)

    # === 2. 基础配置获取 ===
    character_config = characters.get(character_name)
    background_config = background_configs.get(background_name) 
    text_configs = text_configs_dict.get(character_name, [])
    if not character_config or not background_config:
        raise ValueError(f"角色 '{character_name}' 或背景 '{background_name}' 配置不存在")

    # === 3. 情绪和表情判定 ===
    if emotion_id is None:
        # 图片输入时使用默认情绪
        emotion_id = DEFAULT_EMOTION if is_image_input else (get_emotion_from_text(text) if text else DEFAULT_EMOTION)
    emotion_name = get_emotion_name(emotion_id)
    num_bg = background_config["num_bg"]
    emotion_count = character_config["emotion_count"]
    if expression:
        img_num = random.randint((expression-1)*num_bg+1, expression*num_bg)
    else:
        emotion_id = max(1, min(emotion_id, emotion_count))
        img_num = random.randint((emotion_id-1)*num_bg+1, emotion_id*num_bg)

    # === 4. 加载基础图片 ===
    base_image_path = get_pregen_image_path(character_name, img_num, background_name)  
    base_image = Image.open(base_image_path).convert("RGBA")
    text_box_topleft = background_config["text_box_topleft"]
    text_box_bottomright = background_config["text_box_bottomright"]
    font_path = get_resource_path(character_config["font"])
    png_bytes = None


    # === 5. 分逻辑处理：图片输入 / 文本输入 ===
    if is_image_input and content_image is not None:
        """图片输入：调用image_fit_paste，绕开LaTeX"""
        print("检测到剪贴板图片输入，绕开LaTeX转换，绘制图片到文本区域")
        try:
            # 调用图片粘贴函数，将剪贴板图片显示在文本区域
            png_bytes = paste_image_auto(
                image_source=base_image,
                top_left=text_box_topleft,
                bottom_right=text_box_bottomright,
                content_image=content_image,
                align="center",       # 图片水平居中
                valign="middle",      # 图片垂直居中
                padding=10,           # 文本区域内边距10px
                allow_upscale=False,  # 不允许放大图片
                keep_alpha=True,      # 保留图片透明通道
                image_overlay=None,
                max_image_size=(background_config.get("max_image_width"), background_config.get("max_image_height")),
                role_name=character_name,
            )
        except Exception as e:
            print(f"图片绘制失败: {e}")
            # 失败时返回基础图片
            with io.BytesIO() as output:
                base_image.convert("RGB").save(output, "PNG")
                png_bytes = output.getvalue()
    else:
        """文本输入：保留原有逻辑，支持LaTeX转换"""
        if text:
            # LaTeX转换：仅文本输入时执行
            if latex_insert:
                try:
                    from latex import convert_latex_in_text
                    text = convert_latex_in_text(text)
                except ImportError:
                    print("警告: LaTeX功能不可用")
            # 调用文字绘制函数
            png_bytes = draw_text_auto(
                image_source=base_image,
                image_overlay=None,
                top_left=text_box_topleft,
                bottom_right=text_box_bottomright,
                text=text,
                align="left",
                valign='top',
                color=(255, 255, 255),
                max_font_height=145,
                font_path=font_path,
                role_name=character_name,
            )
        else:
            # 无文本无图片，返回基础图片
            with io.BytesIO() as output:
                base_image.convert("RGB").save(output, "PNG")
                png_bytes = output.getvalue()

    # === 6. 图片压缩 ===
    if reduce and png_bytes:
        try:
            png_bytes = compress_image_simple(png_bytes, quality=75)
        except Exception as e:
            print(f"图片压缩失败: {e}")

    # === 7. 返回生成信息 ===
    info_dict = {
        "character": character_name,
        "background": background_name,
        "emotion_id": emotion_id,
        "emotion_name": emotion_name,
        "expression_num": 1 + ((img_num - 1) // num_bg),
        "background_num": (img_num - 1) % num_bg + 1,
        "image_num": img_num,
        "compressed": reduce,
        "input_type": "image" if is_image_input else "text"  
    }
    return png_bytes, info_dict

def delate(folder_path):
    """删除预生成文件夹中的所有图片"""
    deleted_count = 0
    for filename in os.listdir(folder_path):
        if filename.lower().endswith('.jpg'):
            os.remove(os.path.join(folder_path, filename))
            deleted_count += 1
    print(f"预生成图片已清除，共删除 {deleted_count} 个文件")
    return deleted_count