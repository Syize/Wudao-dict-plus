"""
命令行界面绘制模块

使用rich库提供美观的终端输出，包括颜色、样式和格式化功能。
"""
from typing import Literal

from rich.console import Console
from rich.table import Table
from rich.text import Text

from .core import ENWord


class CommandDraw:
    """命令行绘制器类，用于格式化和显示词典查询结果"""
    
    def __init__(self):
        """初始化rich控制台对象"""
        self.console = Console()

    def draw_text_old(self, word: ENWord, conf):
        # 1. 单词标题
        self.console.print(word['word'], style="bold red")

        # 2. 发音
        if word.get('pronunciation'):
            pronunciation_text = Text()
            _template = "{TYPE} {PRON}   "
            _key_map: dict[Literal["uk", "usa", "other"], str] = {
                "uk": "英",
                "usa": "美",
                "other": "英/美"
            }

            for _key in _key_map.keys():
                if word['pronunciation'][_key]:
                    pronunciation_text.append(_template.format(TYPE=_key, PRON=word['pronunciation'][_key]))

            if len(pronunciation_text) == 0:
                pronunciation_text.append("暂无音标数据", style="cyan")

            self.console.print(pronunciation_text)

        # 3. 释义
        table = Table(show_header=False, box=None)
        for paraphrase in word.get('paraphrase', []):
            self.console.print(paraphrase)

        # === 词频 & 词性 ===
        rank_pattern = Text()
        if word.get('rank'):
            rank_pattern.append(f"{word['rank']}  ", style="red")
        if word.get('pattern'):
            rank_pattern.append(word['pattern'].strip(), style="red")
        if len(rank_pattern):
            self.console.print(rank_pattern)

        # === 例句 ===
        if not conf.get('short', False) and word.get('sentence'):
            self.console.print("")  # 空行分隔
            self.console.print("[bold yellow]例句[/bold yellow]\n")

            collins_format = len(word['sentence'][0]) != 2 if word['sentence'] else False

            # 用 Table 美化例句显示
            for i, sentence in enumerate(word['sentence'], 1):
                table = Table(show_header=False, box=None, padding=(0, 1))
                table.add_column("标题", style="green", width=15, no_wrap=True)
                table.add_column("内容", style="white", overflow="fold")

                if collins_format:
                    # 处理Collins词典格式
                    if len(sentence) != 3 or not sentence[1] or not sentence[2]:
                        continue

                    title = f"{i}. [{sentence[1]}]"
                    main_sentence = Text(sentence[0], style="white")

                    # 拼接翻译部分
                    translations = []
                    for example in sentence[2]:
                        translations.append(f"[yellow]{example[0]} {example[1]}[/yellow]", )
                    translation_block = "\n".join(translations)

                    table.add_row(title, Text.assemble(main_sentence, "\n", translation_block))
                    self.console.print(table)

                else:
                    # 处理21世纪词典格式
                    if len(sentence) != 2:
                        continue

                    title = f"{i}."
                    content = Text()
                    content.append(sentence[0], style="white")
                    content.append("\n")
                    content.append(sentence[1], style="yellow")

                    table.add_row(title, content)
                    self.console.print(table)

    def draw_text(self, word, conf):
        """
        绘制英文单词查询结果
        
        Args:
            word (dict): 单词信息字典
            conf (dict): 配置信息字典，包含short等设置
        """
        # 显示单词（红色粗体）
        self.console.print(word['word'], style="bold red")
        
        # 显示发音（青色）
        if word['pronunciation']:
            pronunciation_text = Text()
            if 'uk' in word['pronunciation'] and word['pronunciation']['uk']:
                pronunciation_text.append(f"英 {word['pronunciation']['uk']}", style="cyan")
                pronunciation_text.append("  ")
            if 'usa' in word['pronunciation'] and word['pronunciation']['usa']:
                pronunciation_text.append(f"美 {word['pronunciation']['usa']}", style="cyan")
            if 'other' in word['pronunciation'] and word['pronunciation']['other']:
                pronunciation_text.append(f"英/美 {word['pronunciation']['other']}", style="cyan")
            if len(pronunciation_text) == 0:
                pronunciation_text.append("暂无音标数据", style="cyan")
            self.console.print(pronunciation_text)
        
        # 显示释义（默认白色）
        for paraphrase in word['paraphrase']:
            self.console.print(paraphrase)
        
        # 显示词频和格式信息（红色）
        rank_pattern = Text()
        if word['rank']:
            rank_pattern.append(f"{word['rank']}  ", style="red")
        if word['pattern']:
            rank_pattern.append(word['pattern'].strip(), style="red")
        if rank_pattern:
            self.console.print(rank_pattern)
        
        # 根据配置决定是否显示例句
        if not conf.get('short', False) and word['sentence']:
            self.console.print("")  # 空行分隔
            
            # 判断例句格式类型
            collins_format = len(word['sentence'][0]) != 2 if word['sentence'] else False
            
            # 显示例句
            for i, sentence in enumerate(word['sentence'], 1):
                if collins_format:
                    # 处理Collins词典格式
                    if len(sentence) != 3 or not sentence[1] or not sentence[2]:
                        continue
                    
                    # 创建例句面板
                    example_text = Text()
                    if sentence[1].startswith('['):
                        example_text.append(f"{i}. [{sentence[1]}] ", style="green")
                    else:
                        example_text.append(f"{i}. [{sentence[1]}] ", style="green")
                    example_text.append(sentence[0])
                    
                    self.console.print(example_text)
                    
                    # 显示例句翻译
                    for example in sentence[2]:
                        translation_text = Text("  例: ", style="green")
                        translation_text.append(f"{example[0]} {example[1]}", style="yellow")
                        self.console.print(translation_text)
                else:
                    # 处理21世纪词典格式
                    if len(sentence) != 2:
                        continue
                    
                    example_text = Text()
                    example_text.append(f"{i}. [例] ", style="green")
                    example_text.append(sentence[0])
                    example_text.append("  ")
                    example_text.append(sentence[1], style="yellow")
                    self.console.print(example_text)
    
    def draw_zh_text(self, word, conf):
        """
        绘制中文单词查询结果
        
        Args:
            word (dict): 单词信息字典
            conf (dict): 配置信息字典，包含short等设置
        """
        # 显示单词（红色粗体）
        self.console.print(word['word'], style="bold red")
        
        # 显示发音（青色）
        if word['pronunciation']:
            self.console.print(word['pronunciation'], style="cyan")
        
        # 显示释义（默认白色）
        if word['paraphrase']:
            for paraphrase in word['paraphrase']:
                # 替换分隔符为逗号
                formatted_paraphrase = paraphrase.replace('  ;  ', ', ')
                self.console.print(formatted_paraphrase)
        
        # 根据配置决定是否显示详细信息
        if not conf.get('short', False):
            # 显示详细描述
            if word.get("desc"):
                self.console.print("")  # 空行分隔
                for i, desc in enumerate(word['desc'], 1):
                    if not desc:
                        continue
                    
                    # 显示子标题（绿色）
                    subtitle = desc[0].replace(';', ',')
                    self.console.print(f"{i}. {subtitle}", style="green")
                    
                    # 显示子项示例
                    if len(desc) == 2:
                        for j, example in enumerate(desc[1]):
                            if j % 2 == 0:
                                # 原文（黄色）
                                example_text = example.strip().replace(';', '')
                                self.console.print(f"    {example_text}    ", style="yellow", end="")
                            else:
                                # 译文（默认白色）
                                self.console.print(example)
            
            # 显示例句
            if word.get('sentence'):
                self.console.print("\n例句:", style="bold red")
                for i, sentence in enumerate(word['sentence'], 1):
                    if len(sentence) == 2:
                        self.console.print("")  # 空行分隔
                        example_text = Text()
                        example_text.append(f"{i}. {sentence[0]}", style="yellow")
                        example_text.append(f"    {sentence[1]}")
                        self.console.print(example_text)
                        
                        
__all__ = ["CommandDraw"]
