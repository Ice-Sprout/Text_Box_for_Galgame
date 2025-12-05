# 星白对话框

一个将文本转换为类似星白对话框风格图片的程序。

> 本项目灵感来源于 [manosaba_text_box](https://github.com/oplivilqo/manosaba_text_box)，代码基于 [Text_box-of-mahoushoujo_no_majosaiban-NEO](https://github.com/morpheus315/Text_box-of-mahoushoujo_no_majosaiban-NEO) 的二次编辑版本，并使用了deepseek与ChatGPT辅助编写代码。表情部分与图像功能debug源自"morymofy"，latex支持、首版api支持、图片压缩功能与字体的修改源自"Ice-Sprout"。首次发布版由"morymofy"为api部分提供了历史对话支持，并优化了api提供逻辑，增加了自动下载环境与运行主函数的bat文件。

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
- 使用api功能时请将你的api密钥按api.example.txt的示例创建api.txt文件放在resource文件夹中。

## 🔧 环境配置

- python 用的3.14，但是3.10之后应该也可以跑
- pip install pywin32
- pip install pillow
- pip install keyboard
- pip install pyperclip
- pip install psutil
- pip install emoji==1.7.0
- pip install pilmoji
- pip install requests
- pip install unicodeit
- pip install logging

## 📋 版本更新记录

- 1.1 适配了全部角色
- 1.2 搭载了AI  API KEY调用
- 1.3 适配了4名角色
- 1.4 增加了历史对话学习，可以保存10条历史记录并且通过历史对话分析情感，增加准确度
- 1.5 添加了gui功能，对预生成进行了优化，能够处理不同尺寸背景并赋予透明框方便查看白色文本。修正了requirements和env.bat，对不必要的文件进行了删减。
- 1.6 美化了gui，解决了由于历史对话导致一直输出气愤情绪的bug，gui现在可以自动隐藏到系统托盘
- 1.7 精简并稳定了gui程序，增加了托盘/窗口图标，直接以背景图片作为了背景，但暂不支持放大/缩小；优化了api程序：增加基于会话的情绪分析器、历史对话持久化；整合资源文件到resource文件夹并更改资源查找逻辑方便打包。
  
- ![ScreenShot_2025-11-30_234709_718.png](https://raw.gitcode.com/user-images/assets/8557755/9a94bc7b-2db5-491d-93b4-56814eafc643/ScreenShot_2025-11-30_234709_718.png 'ScreenShot_2025-11-30_234709_718.png')

![微信图片_20251129213206_298_286.png](https://raw.gitcode.com/user-images/assets/8557755/9025117b-6620-4d03-bdb8-d60a098874c5/微信图片_20251129213206_298_286.png '微信图片_20251129213206_298_286.png')
