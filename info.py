# info.py

# 背景图片配置字典
background_configs = {
    "hoshishiro": {
        "name": "hoshishiro",
        "num_bg": 8,
        "text_box_topleft": [728, 355],
        "text_box_bottomright": [2339, 800]
    }
    # 可以在这里添加其他背景配置
}

# 默认背景配置
DEFAULT_BACKGROUND = "hoshishiro"


# 角色配置字典
characters = {
    "karuha":  {"emotion_count": 15, "font": "font3.ttf","drawy":-100,  "drawx":-450},     #狩叶 1500*1200（700*700=0*0）
    "noir":    {"emotion_count": 15, "font": "font3.ttf","drawy":-200  ,"drawx":-450},     #诺瓦 1500*1200
    "neri":    {"emotion_count": 15, "font": "font3.ttf","drawy":-200 , "drawx":-450},     #音理 1500*1200
    "jibie":   {"emotion_count": 15, "font": "font3.ttf","drawy":-200 , "drawx":0},     #野鸟
    "hanae":   {"emotion_count": 15, "font": "font3.ttf","drawy":-200,  "drawx": 0},    #花江
    "mashiro": {"emotion_count": 15, "font": "font3.ttf","drawy":-200,  "drawx":-450},    #真白  1500*1200
    "suzuran": {"emotion_count": 12, "font": "font3.ttf","drawy":-20,   "drawx":300}    #铃兰

}

# 角色文字配置字典 - 每个角色对应4个文字配置
text_configs_dict = {
    "karuha": [  # 狩叶
        {"text": "狩", "position": (759, 63), "font_color": (251, 114, 74), "font_size": 196},
        {"text": "叶", "position": (948, 175), "font_color": (255, 255, 255), "font_size": 92},
        {"text": "", "position": (0, 0), "font_color": (255, 255, 255), "font_size": 1}
    ],
    "noir": [  # 诺瓦
        {"text": "诺", "position": (759, 63), "font_color": (170, 170, 200), "font_size": 196},
        {"text": "瓦", "position": (948, 175), "font_color": (255, 255, 255), "font_size": 92},
        {"text": "", "position": (0, 0), "font_color": (255, 255, 255), "font_size": 1}
    ],
    "neri": [  # 音理
        {"text": "音", "position": (759, 63), "font_color": (255, 0, 0), "font_size": 196},
        {"text": "理", "position": (948, 175), "font_color": (255, 255, 255), "font_size": 92},
        {"text": "", "position": (0, 0), "font_color": (255, 255, 255), "font_size": 1}
    ],
    "jibie": [  # 野鸟
        {"text": "野", "position": (759, 63), "font_color": (255, 255, 0), "font_size": 196},
        {"text": "鸟", "position": (948, 175), "font_color": (255, 255, 255), "font_size": 92},
        {"text": "", "position": (0, 0), "font_color": (255, 255, 255), "font_size": 1}
    ],
    "hanae": [  # 花江
        {"text": "野", "position": (759, 63), "font_color": (128, 0, 128), "font_size": 196},
        {"text": "鸟", "position": (948, 175), "font_color": (255, 255, 255), "font_size": 92},
        {"text": "", "position": (0, 0), "font_color": (255, 255, 255), "font_size": 1}
    ],
    "mashiro": [  #真白
        {"text": "真", "position": (759, 63), "font_color": (255, 255, 255), "font_size": 196},
        {"text": "白", "position": (948, 175), "font_color": (255, 255, 255), "font_size": 92},
        {"text": "", "position": (0, 0), "font_color": (255, 255, 255), "font_size": 1}
    ],
    "suzuran": [  #铃兰
        {"text": "铃", "position": (759, 63), "font_color": (215, 215, 10), "font_size": 196},
        {"text": "兰", "position": (948, 175), "font_color": (255, 255, 255), "font_size": 92},
        {"text": "", "position": (0, 0), "font_color": (255, 255, 255), "font_size": 1}
    ]
}