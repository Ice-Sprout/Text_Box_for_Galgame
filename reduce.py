# reduce.py

import io
from PIL import Image

def compress_image(image_bytes, target_size_kb=100, quality=85, max_iterations=5):
    """
    压缩图片到指定大小，保持尺寸不变
    
    参数:
    - image_bytes: 原始图片字节流
    - target_size_kb: 目标大小(KB)
    - quality: 初始质量(0-100)
    - max_iterations: 最大迭代次数
    
    返回:
    - compressed_bytes: 压缩后的图片字节流
    - original_size_kb: 原始大小(KB)
    - compressed_size_kb: 压缩后大小(KB)
    """
    
    # 打开图片并转换为RGB（去除透明通道）
    image = Image.open(io.BytesIO(image_bytes))
    if image.mode in ('RGBA', 'LA'):
        # 创建白色背景
        background = Image.new('RGB', image.size, (255, 255, 255))
        # 如果图片有透明通道，合并到白色背景上
        if image.mode == 'RGBA':
            background.paste(image, mask=image.split()[-1])
        else:
            background.paste(image)
        image = background
    else:
        image = image.convert('RGB')
    
    original_size_kb = len(image_bytes) / 1024
    
    # 如果已经小于目标大小，直接返回
    if original_size_kb <= target_size_kb:
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=quality, optimize=True)
        compressed_bytes = output.getvalue()
        return compressed_bytes, original_size_kb, len(compressed_bytes) / 1024
    
    # 迭代压缩直到达到目标大小或最大迭代次数
    current_quality = quality
    compressed_bytes = None
    
    for iteration in range(max_iterations):
        output = io.BytesIO()
        image.save(output, format='JPEG', quality=current_quality, optimize=True)
        current_size_kb = len(output.getvalue()) / 1024
        
        print(f"压缩迭代 {iteration + 1}: 质量={current_quality}, 大小={current_size_kb:.1f}KB")
        
        if current_size_kb <= target_size_kb:
            compressed_bytes = output.getvalue()
            break
        
        # 如果还是太大，降低质量继续压缩
        current_quality = max(10, current_quality - 15)  # 每次降低15质量，最小10
        
        if iteration == max_iterations - 1:
            # 最后一次迭代，使用当前结果
            compressed_bytes = output.getvalue()
    
    compressed_size_kb = len(compressed_bytes) / 1024
    
    print(f"压缩完成: {original_size_kb:.1f}KB -> {compressed_size_kb:.1f}KB")
    
    return compressed_bytes, original_size_kb, compressed_size_kb

def compress_image_simple(image_bytes, quality=75):
    """
    简单压缩图片，不进行迭代
    
    参数:
    - image_bytes: 原始图片字节流
    - quality: 压缩质量(0-100)，100表示不压缩
    
    返回:
    - compressed_bytes: 压缩后的图片字节流
    """
    # 如果质量为100，直接返回原图（不压缩）
    if quality >= 100:
        print(f"不压缩: 质量为{quality}%")
        return image_bytes
    
    # 打开图片并转换为RGB（去除透明通道）
    image = Image.open(io.BytesIO(image_bytes))
    if image.mode in ('RGBA', 'LA'):
        # 创建白色背景
        background = Image.new('RGB', image.size, (255, 255, 255))
        # 如果图片有透明通道，合并到白色背景上
        if image.mode == 'RGBA':
            background.paste(image, mask=image.split()[-1])
        else:
            background.paste(image)
        image = background
    else:
        image = image.convert('RGB')
    
    output = io.BytesIO()
    image.save(output, format='JPEG', quality=quality, optimize=True)
    
    original_size_kb = len(image_bytes) / 1024
    compressed_size_kb = len(output.getvalue()) / 1024
    
    # 计算压缩率
    if original_size_kb > 0:
        compression_rate = (compressed_size_kb / original_size_kb) * 100
    else:
        compression_rate = 0
    
    print(f"压缩: {original_size_kb:.1f}KB -> {compressed_size_kb:.1f}KB (质量={quality}, 压缩率={compression_rate:.1f}%)")
    
    return output.getvalue()