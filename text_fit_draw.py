from io import BytesIO
from typing import Tuple, Union, Literal
from PIL import Image, ImageDraw, ImageFont
import os
import re
import sys

Align = Literal["left", "center", "right"]
VAlign = Literal["top", "middle", "bottom"]

# ===== PyInstaller 资源路径处理函数 =====

def get_resource_path(relative_path):
    """获取资源文件的绝对路径，兼容开发环境和打包后的环境"""
    try:
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

try:
    from pilmoji import Pilmoji
    PILMOJI_AVAILABLE = True
except ImportError:
    PILMOJI_AVAILABLE = False
    print("警告: pilmoji未安装，emoji将以黑白显示。安装方法: pip install pilmoji")

IMAGE_SETTINGS = {
    "max_width": 1200,
    "max_height": 800,
    "quality": 65,
    "resize_ratio": 0.7
}

def compress_image(image: Image.Image) -> Image.Image:
    """压缩图像大小"""
    width, height = image.size
    new_width = int(width * IMAGE_SETTINGS["resize_ratio"])
    new_height = int(height * IMAGE_SETTINGS["resize_ratio"])
    
    # 限制最大尺寸
    if new_width > IMAGE_SETTINGS["max_width"]:
        ratio = IMAGE_SETTINGS["max_width"] / new_width
        new_width, new_height = IMAGE_SETTINGS["max_width"], int(new_height * ratio)
    
    if new_height > IMAGE_SETTINGS["max_height"]:
        ratio = IMAGE_SETTINGS["max_height"] / new_height
        new_height, new_width = IMAGE_SETTINGS["max_height"], int(new_width * ratio)
    
    return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

def is_emoji(char: str) -> bool:
    """判断字符是否为emoji"""
    code = ord(char)
    # Emoji常见Unicode范围
    return (
        0x1F300 <= code <= 0x1F9FF or  # 常见表情符号
        0x2600 <= code <= 0x27BF or    # 杂项符号
        0x1F000 <= code <= 0x1F02F or  # 麻将牌等
        0xFE00 <= code <= 0xFE0F or    # 变体选择器
        0x1F200 <= code <= 0x1F251 or  # 方框符号
        0x1F600 <= code <= 0x1F64F or  # 表情符号
        0x1FA00 <= code <= 0x1FA6F or  # 扩展表情
        0x2700 <= code <= 0x27BF       # 装饰符号
    )

def is_chinese_char(char: str) -> bool:
    """判断字符是否为中文字符"""
    code = ord(char)
    return (
        0x4E00 <= code <= 0x9FFF or    # 基本汉字
        0x3400 <= code <= 0x4DBF or    # 扩展A
        0x20000 <= code <= 0x2A6DF or  # 扩展B
        0x2A700 <= code <= 0x2B73F or  # 扩展C
        0x2B740 <= code <= 0x2B81F or  # 扩展D
        0x2B820 <= code <= 0x2CEAF or  # 扩展E
        0x2CEB0 <= code <= 0x2EBEF or  # 扩展F
        0x30000 <= code <= 0x3134F or  # 扩展G
        0xF900 <= code <= 0xFAFF or    # 兼容汉字
        0x2F800 <= code <= 0x2FA1F    # 兼容扩展
    )

def is_fullwidth_char(char: str) -> bool:
    """判断字符是否为全角字符（包括中文、全角符号等）"""
    code = ord(char)
    return (
        is_chinese_char(char) or        # 中文字符
        0x3000 <= code <= 0x303F or    # 中日韩符号和标点
        0xFF00 <= code <= 0xFFEF or    # 全角形式
        0xFE10 <= code <= 0xFE1F or    # 竖排形式
        0xFE30 <= code <= 0xFE4F       # CJK兼容形式
    )

def is_math_symbol(char: str) -> bool:
    """判断字符是否为数学符号"""
    code = ord(char)
    return (
        0x2070 <= code <= 0x209C or    # 上标和下标
        0x2200 <= code <= 0x22FF or    # 数学运算符
        0x2A00 <= code <= 0x2AFF or    # 补充数学运算符
        0x1D400 <= code <= 0x1D7FF or  # 数学字母数字符号
        0x2100 <= code <= 0x214F or    # 类字母符号
        0x2190 <= code <= 0x21FF       # 箭头符号
    )

def get_char_font(char: str, chinese_font: ImageFont.FreeTypeFont, math_font: ImageFont.FreeTypeFont) -> ImageFont.FreeTypeFont:
    """根据字符类型选择合适的字体"""
    if is_fullwidth_char(char):
        return chinese_font
    elif is_math_symbol(char):
        return math_font
    else:
        # 对于英文字母、数字和半角符号，使用数学字体
        return math_font

def draw_text_auto(
    image_source: Union[str, Image.Image],
    top_left: Tuple[int, int],
    bottom_right: Tuple[int, int],
    text: str,
    color: Tuple[int, int, int] = (0, 0, 0),
    max_font_height: int | None = None,
    font_path: str | None = None,
    align: Align = "center",
    valign: VAlign = "middle",
    line_spacing: float = 0.15,
    bracket_color: Tuple[int, int, int] = (137,177,251),  # 中括号及内部内容颜色
    image_overlay: Union[str, Image.Image,None]=None,
    role_name: str = "unknown",  # 添加角色名称参数
    text_configs_dict: dict = None,  # 添加文字配置字典参数
) -> bytes:
    """
    在指定矩形内自适应字号绘制文本；
    中括号及括号内文字使用 bracket_color。
    支持彩色emoji表情显示。
    使用混合字体：中文使用原字体，英文和数学符号使用Cambria字体。
    """
    
    # --- 文本为空时直接返回图片，绕开所有文本/LaTeX逻辑 ---
    if not text.strip():
        if isinstance(image_source, Image.Image):
            img = image_source.copy()
        else:
            img = Image.open(image_source).convert("RGBA")
        # 绘制角色专属文字（保留原有功能）
        if text_configs_dict and role_name in text_configs_dict:
            regular_draw = ImageDraw.Draw(img)
            shadow_offset = (2, 2)
            shadow_color = (0, 0, 0)
            for config in text_configs_dict[role_name]:
                char_text = config["text"]
                position = config["position"]
                font_color = config["font_color"]
                font_size = config["font_size"]
                font_path_char = get_resource_path("font3.ttf")
                try:
                    char_font = ImageFont.truetype(font_path_char, font_size)
                    regular_draw.text((position[0]+shadow_offset[0], position[1]+shadow_offset[1]), char_text, fill=shadow_color, font=char_font)
                    regular_draw.text(position, char_text, fill=font_color, font=char_font)
                except Exception as e:
                    print(f"角色文字绘制失败: {e}")
                    continue
        # 压缩并返回
        img = compress_image(img)
        buf = BytesIO()
        img.save(buf, format="png")
        return buf.getvalue()

    # --- 原有逻辑保持不变 ---
    if isinstance(image_source, Image.Image):
        img = image_source.copy()
    else:
        img = Image.open(image_source).convert("RGBA")
    
    # 创建Pilmoji对象用于彩色emoji
    if PILMOJI_AVAILABLE:
        pilmoji = Pilmoji(img)
        draw = pilmoji  # 使用pilmoji替代draw
    else:
        draw = ImageDraw.Draw(img)

    if image_overlay is not None:
        if isinstance(image_overlay, Image.Image):
            img_overlay = image_overlay.copy()
        else:
            img_overlay = Image.open(image_overlay).convert("RGBA") if os.path.isfile(image_overlay) else None

    x1, y1 = top_left
    x2, y2 = bottom_right
    if not (x2 > x1 and y2 > y1):
        raise ValueError("无效的文字区域。")
    region_w, region_h = x2 - x1, y2 - y1

    # --- 2. 字体加载 ---
    def _load_fonts(size: int) -> tuple[ImageFont.FreeTypeFont, ImageFont.FreeTypeFont]:
        """加载中文字体和数学字体"""
        # 加载中文字体
        if font_path and os.path.exists(font_path):
            chinese_font = ImageFont.truetype(font_path, size=size)
        else:
            try:
                chinese_font = ImageFont.truetype("DejaVuSans.ttf", size=size)
            except Exception:
                chinese_font = ImageFont.load_default()
        
        # 加载数学字体 (Cambria)
        math_font_path = get_resource_path("cambria.ttc")
        if os.path.exists(math_font_path):
            try:
                math_font = ImageFont.truetype(math_font_path, size=size)
            except Exception:
                math_font = chinese_font  # 回退到中文字体
        else:
            math_font = chinese_font  # 回退到中文字体
        
        return chinese_font, math_font

    # --- 3. 文本包行 (使用混合字体计算宽度) ---
    def wrap_lines(txt: str, chinese_font: ImageFont.FreeTypeFont, math_font: ImageFont.FreeTypeFont, max_w: int) -> list[str]:
        lines: list[str] = []
        
        for para in txt.splitlines() or [""]:
            has_space = (" " in para)
            units = para.split(" ") if has_space else list(para)
            buf = ""

            def unit_join(a: str, b: str) -> str:
                if not a:
                    return b
                return (a + " " + b) if has_space else (a + b)

            def get_text_width(text: str) -> int:
                """使用混合字体计算文本宽度"""
                total_width = 0
                for char in text:
                    char_font = get_char_font(char, chinese_font, math_font)
                    if PILMOJI_AVAILABLE:
                        width = pilmoji.getsize(char, font=char_font)[0]
                    else:
                        temp_draw = ImageDraw.Draw(img)
                        width = temp_draw.textlength(char, font=char_font)
                    total_width += width
                return total_width

            for u in units:
                trial = unit_join(buf, u)
                w = get_text_width(trial)
                
                if w <= max_w:
                    buf = trial
                else:
                    if buf:
                        lines.append(buf)
                    if has_space and len(u) > 1:
                        tmp = ""
                        for ch in u:
                            tmp_w = get_text_width(tmp + ch)
                            if tmp_w <= max_w:
                                tmp += ch
                            else:
                                if tmp:
                                    lines.append(tmp)
                                tmp = ch
                        buf = tmp
                    else:
                        u_w = get_text_width(u)
                        if u_w <= max_w:
                            buf = u
                        else:
                            lines.append(u)
                            buf = ""
            if buf != "":
                lines.append(buf)
            if para == "" and (not lines or lines[-1] != ""):
                lines.append("")
        return lines

    # --- 4. 测量 ---
    def measure_block(lines: list[str], chinese_font: ImageFont.FreeTypeFont, math_font: ImageFont.FreeTypeFont) -> tuple[int, int, int]:
        ascent, descent = chinese_font.getmetrics()
        line_h = int((ascent + descent) * (1 + line_spacing))
        max_w = 0
        
        def get_text_width(text: str) -> int:
            """使用混合字体计算文本宽度"""
            total_width = 0
            for char in text:
                char_font = get_char_font(char, chinese_font, math_font)
                if PILMOJI_AVAILABLE:
                    width = pilmoji.getsize(char, font=char_font)[0]
                else:
                    temp_draw = ImageDraw.Draw(img)
                    width = temp_draw.textlength(char, font=char_font)
                total_width += width
            return total_width
        
        for ln in lines:
            w = get_text_width(ln)
            max_w = max(max_w, int(w))
        total_h = max(line_h * max(1, len(lines)), 1)
        return max_w, total_h, line_h

    # --- 5. 搜索最大字号 ---
    hi = min(region_h, max_font_height) if max_font_height else region_h
    lo, best_size, best_lines, best_line_h, best_block_h = 1, 0, [], 0, 0

    while lo <= hi:
        mid = (lo + hi) // 2
        chinese_font, math_font = _load_fonts(mid)
        lines = wrap_lines(text, chinese_font, math_font, region_w)
        w, h, lh = measure_block(lines, chinese_font, math_font)
        if w <= region_w and h <= region_h:
            best_size, best_lines, best_line_h, best_block_h = mid, lines, lh, h
            lo = mid + 1
        else:
            hi = mid - 1

    if best_size == 0:
        chinese_font, math_font = _load_fonts(1)
        best_lines = wrap_lines(text, chinese_font, math_font, region_w)
        _, best_block_h, best_line_h = 0, 1, 1
        best_size = 1
    else:
        chinese_font, math_font = _load_fonts(best_size)

    # --- 6. 解析着色片段 ---
    def parse_color_segments(s: str, in_bracket: bool) -> Tuple[list[tuple[str, Tuple[int, int, int]]], bool]:
        segs: list[tuple[str, Tuple[int, int, int]]] = []
        buf = ""
        for ch in s:
            if ch == "[" or ch == "【":
                if buf:
                    segs.append((buf, bracket_color if in_bracket else color))
                    buf = ""
                segs.append((ch, bracket_color))
                in_bracket = True
            elif ch == "]" or ch == "】":
                if buf:
                    segs.append((buf, bracket_color))
                    buf = ""
                segs.append((ch, bracket_color))
                in_bracket = False
            else:
                buf += ch
        if buf:
            segs.append((buf, bracket_color if in_bracket else color))
        return segs, in_bracket

    # --- 7. 垂直对齐 ---
    if valign == "top":
        y_start = y1
    elif valign == "middle":
        y_start = y1 + (region_h - best_block_h) // 2
    else:
        y_start = y2 - best_block_h

    # --- 8. 绘制 (支持混合字体和彩色emoji) ---
    y = y_start
    in_bracket = False
    
    for ln in best_lines:
        # 计算行宽（使用混合字体）
        def get_line_width(text: str) -> int:
            total_width = 0
            for char in text:
                char_font = get_char_font(char, chinese_font, math_font)
                if PILMOJI_AVAILABLE:
                    width = pilmoji.getsize(char, font=char_font)[0]
                else:
                    temp_draw = ImageDraw.Draw(img)
                    width = temp_draw.textlength(char, font=char_font)
                total_width += width
            return total_width
        
        line_w = get_line_width(ln)
        
        if align == "left":
            x = x1
        elif align == "center":
            x = x1 + (region_w - line_w) // 2
        else:
            x = x2 - line_w
        
        segments, in_bracket = parse_color_segments(ln, in_bracket)
        
        for seg_text, seg_color in segments:
            if seg_text:
                # 按字符绘制，每个字符使用合适的字体
                for char in seg_text:
                    char_font = get_char_font(char, chinese_font, math_font)
                    
                    if PILMOJI_AVAILABLE:
                        # 使用pilmoji绘制彩色emoji
                        # 先绘制阴影
                        pilmoji.text((x+4, y+4), char, font=char_font, fill=(0,0,0), emoji_position_offset=(0, 0))
                        # 绘制主文字
                        pilmoji.text((x, y), char, font=char_font, fill=seg_color, emoji_position_offset=(0, 0))
                        char_width = pilmoji.getsize(char, font=char_font)[0]
                    else:
                        # 回退到普通绘制
                        temp_draw = ImageDraw.Draw(img)
                        temp_draw.text((x+4, y+4), char, font=char_font, fill=(0,0,0))
                        temp_draw.text((x, y), char, font=char_font, fill=seg_color)
                        char_width = int(temp_draw.textlength(char, font=char_font))
                    
                    x += char_width
        
        y += best_line_h
        if y - y_start > region_h:
            break

    # 覆盖置顶图层（如果有）
    if image_overlay is not None and img_overlay is not None:
        img.paste(img_overlay, (0, 0), img_overlay)
    elif image_overlay is not None and img_overlay is None:
        print("Warning: overlay image is not exist.")


    
    img = compress_image(img)
    
    # --- 9. 输出 PNG ---
    buf = BytesIO()
    img.save(buf, format="png")
    return buf.getvalue()