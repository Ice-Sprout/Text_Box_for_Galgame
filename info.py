# info.py

# 背景图片配置字典
background_configs = {
    "ustc": {
        "name": "ustc",
        "num_bg": 6,
        "text_box_topleft": [
            728,
            355
        ],
        "text_box_bottomright": [
            2339,
            800
        ]
    }
}

# 默认背景配置
DEFAULT_BACKGROUND = "ustc"


# 角色配置字典
characters = {
    "xingling": {
        "display_name": "鹰仓杏铃",
        "emotion_count": 15,
        "font": "font3.ttf",
        "drawy": 0,
        "drawx": 0,
        "enlarge": 1.0
    }
}

# 角色文字配置字典 - 每个角色对应文字配置
text_configs_dict = {
    "xingling": [
        {
            "text": "鹰",
            "position": (759, 73),
            "font_color": (255, 255, 0),
            "font_size": 186
        },
        {
            "text": "仓杏铃",
            "position": (945, 175),
            "font_color": (255, 255, 255),
            "font_size": 92
        }
    ]
}