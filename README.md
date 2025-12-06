# 星白对话框

一个将文本转换为类似星白对话框风格图片的程序。

> 本项目灵感来源于 [manosaba_text_box](https://github.com/oplivilqo/manosaba_text_box)，代码基于 [Text_box-of-mahoushoujo_no_majosaiban-NEO](https://github.com/morpheus315/Text_box-of-mahoushoujo_no_majosaiban-NEO) 的二次编辑版本，并使用了deepseek与ChatGPT辅助编写代码。

## ✨ 功能特色

- **🎨 Galgame风格对话生成**：将普通文本转换为具有星白对话框风格的对话图片
- **😊 多角色与多表情支持**：支持为不同角色配置多种表情，丰富对话表现
- **⌨️ 热键实时处理**：通过热键快速触发文本处理和图片生成
- **🔣 LaTeX公式支持**：支持在文本中嵌入简单的LaTeX公式
- **📝 自动文本适配与格式化**：文本自动适应对话框并进行美观排版
- **🖥️ 双界面可选**：提供图形用户界面(GUI)和命令行界面供用户选择

## 注意事项

- 每一个角色使用前需要点击预生成按钮，等待生成完毕后可以使用，若提前按enter会导致bug，需要清空图片重新预生成
- 切换角色或者更改快捷键后，点击保存设置才能生效
- info.json由于涉及apikey未给出，首次使用请先运行resource_manager.py并生成一下配置文件。
- main.py在2.0版本未进行对应更新，不一定可用。

## 🔧 环境配置

- python 3.14/3.12.12经测试可行。
- pip install pywin32
- pip install pillow
- pip install keyboard
- pip install pyperclip
- pip install psutil
- pip install emoji==1.7.0
- pip install pilmoji
- pip install requests
- pip install unicodeit

## 📋 版本更新记录

### v2.0 (当前版本)

- **资源管理系统重构**：
  - 更改图片合成中对头像的处理逻辑，优化资源使用
  - 新增资源管理GUI：`resource_manager.py`，提供可视化资源管理
  - 资源信息文件从Python文件改为JSON格式，提升可维护性
- **表情系统增强**：
  - 增加随机表情选项，支持自动随机选择表情
  - 实现API中自适应情绪种类，不再限定15种表情（测试中）
- **字体与资源自定义**：
  - 字体文件的导入和更换集成到资源管理GUI中
  - 支持导入GUI背景图片和程序图标
- **用户体验优化**：
  - 新增清除单个角色背景预生成图片功能
  - 图片压缩功能支持分辨率设置
  - 优化GUI布局和操作流程

### v1.7

- 精简并稳定GUI程序，增加系统托盘/窗口图标
- 直接使用背景图片作为对话框背景（暂不支持缩放）
- 优化API程序：增加基于会话的情绪分析器、历史对话持久化
- 整合资源文件到`resource`文件夹，优化资源查找逻辑
- 发布首个pre-release版本

### v1.6

- 美化GUI界面，支持自动隐藏到系统托盘
- 修复历史对话导致情绪输出异常的bug
- 优化GUI程序稳定性和用户体验

### v1.5

- 新增GUI图形用户界面，支持预生成功能优化
- 适配不同尺寸背景图片，添加透明框方便查看白色文本
- 修正环境配置文件`requirements.txt`和`env.bat`
- 精简项目文件结构，删除不必要的文件

### v1.4

- 新增历史对话学习功能，保存10条历史记录
- 通过历史对话分析情感，提升情绪识别准确度
- 优化API调用逻辑和情感分析算法

### v1.3

- 适配4名角色，扩展角色支持范围
- 优化角色切换和表情管理逻辑

### v1.2

- 集成AI API KEY调用功能
- 支持通过API进行智能对话和情绪分析

### v1.1

- 初始版本
- 适配全部基础角色，实现核心对话框生成功能
  
- ![星白对话框 2025_12_6 20_44_18.png](https://raw.githubusercontent.com/Ice-Sprout/assets/main/%E6%98%9F%E7%99%BD%E5%AF%B9%E8%AF%9D%E6%A1%86%202025_12_6%2020_44_18.png)

![微信图片_20251129213206_298_286.png](https://raw.gitcode.com/user-images/assets/8557755/9025117b-6620-4d03-bdb8-d60a098874c5/微信图片_20251129213206_298_286.png '微信图片_20251129213206_298_286.png')
