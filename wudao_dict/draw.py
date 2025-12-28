"""
命令行界面绘制模块

使用rich库提供美观的终端输出，包括颜色、样式和格式化功能。
"""
from typing import Literal

from rich.console import Console
from rich.table import Table
from rich.text import Text

from .core import CollinsSentenceUnit, ENWord, SentenceUnit, ZHWord


class CommandDraw:
    """命令行绘制器类，用于格式化和显示词典查询结果"""
    
    def __init__(self):
        """初始化rich控制台对象"""
        self.console = Console()

    def draw_text(self, word: ENWord, short=False):
        # 1. 单词标题
        self.console.print(word['word'], style="bold red")

        # 2. 发音
        pronunciation_text = Text()
        _template = "{TYPE} {PRON} "
        _key_map: dict[Literal["uk", "usa", "other"], str] = {
            "uk": "英",
            "usa": "美",
            "other": "英/美"
        }

        for _key in _key_map.keys():
            if word['pronunciation'][_key]:
                pronunciation_text.append(f"{_key_map[_key]} ")
                pronunciation_text.append(f"{word['pronunciation'][_key]} ", style="cyan")

        if len(pronunciation_text) == 0:
            pronunciation_text.append("暂无音标数据", style="cyan")

        self.console.print(pronunciation_text)

        # 3. 释义
        table = Table(show_header=False, padding=(0, 1, 0, 0), box=None)
        table.add_column("category", no_wrap=True)
        table.add_column("means", overflow="fold")
        paraphrase = word["paraphrase"]

        for _category in paraphrase.keys():
            for _mean in paraphrase[_category]:
                table.add_row(_category, _mean)

        self.console.print(table)

        # === 词频 & 词性 ===
        rank_pattern = Text()
        if word.get('rank'):
            rank_pattern.append(f"{word['rank']}  ", style="red")
        if word.get('pattern'):
            rank_pattern.append(word['pattern'].strip(), style="red")
        if len(rank_pattern):
            self.console.print(rank_pattern)

        # === 例句 ===
        if not short:
            sentence = word["sentence"]
            collins_format = sentence["is_collins"]

            table = Table(show_header=True, padding=(0, 1, 0, 0), box=None)
            table.add_column("例句", header_style="red", no_wrap=True)
            table.add_column("", header_style="white", overflow="fold")
            has_sentence = False
            
            if collins_format:

                sentences_group_list: list[CollinsSentenceUnit] = sentence["sentences"]

                for index, _group in enumerate(sentences_group_list):
                    has_sentence = True
                    _mean = _group["mean"]
                    _category = _group["category"]
                    _sentences = _group["sentences"]

                    output_title = Text()
                    output_title.append(f"{index + 1}. [{_category}]", style="green")

                    output_sentence = Text()
                    output_sentence.append(_mean, style="white")

                    table.add_row(output_title, output_sentence)

                    if len(_sentences) > 0:
                        _subtable = Table(show_header=False, padding=(1, 1, 0, 0), box=None)
                        _subtable.add_column("例", style="green", no_wrap=True)
                        _subtable.add_column("句", style="yellow", overflow="fold")

                        for _sentence in _sentences:
                            _subtable.add_row("例:", f"{_sentence['en']}\n{_sentence['zh']}")

                        table.add_row("", _subtable)

                    table.add_row("", "")

            else:
                sentences_group_list: list[SentenceUnit] = sentence["sentences"]

                for index, _group in enumerate(sentences_group_list):
                    has_sentence = True
                    output_title = Text()
                    output_title.append(f"{index}.", style="green")

                    output_sentence = Text()
                    output_sentence.append(_group["en"], style="yellow")
                    output_sentence.append(" ")
                    output_sentence.append(_group["zh"], style="yellow")

                    table.add_row(output_title, output_sentence)

            if has_sentence:
                self.console.print("")  # 空行分隔
                self.console.print(table)

    def draw_zh_text(self, word: ZHWord, short=False):
        """
        绘制中文单词查询结果

        Args:
            word (dict): 单词信息字典
            conf (dict): 配置信息字典，包含short等设置
        """
        # 显示单词（红色粗体）
        self.console.print(word['word'], style="bold red")

        # 显示发音（青色）
        pronunciation = Text(word['pronunciation'], style="cyan")
        self.console.print(pronunciation)

        # 显示释义（默认白色）
        paraphrase = word['paraphrase']

        if len(paraphrase) != 0:
            table = Table(show_header=False, padding=(0, 1, 0, 0), box=None)
            table.add_column("paraphrase", no_wrap=True)
            table.add_column("words")

            for _paraphrase in paraphrase.keys():
                # 替换分隔符为逗号
                en_words = word['paraphrase'][_paraphrase]
                en_words = [x.replace(' ; ', ', ') for x in en_words]
                en_words = ", ".join(en_words)
                table.add_row(_paraphrase, en_words)

            self.console.print(table)

        # 根据配置决定是否显示详细信息
        if short:
            return

        # 显示详细描述
        desc_list = word['desc']

        if len(desc_list) != 0:
            self.console.print("")

            table = Table(show_header=True, box=None, padding=(0, 1, 0, 0))
            table.add_column("释义", no_wrap=True, header_style="red", style="green")
            table.add_column("", overflow="fold")

            for i, desc in enumerate(word['desc'], 1):
                table.add_row(f"{i}.", Text(desc["desc"], style="green"))

                # 显示子项示例
                if len(desc["desc_sentences"]) != 0:
                    _subtable = Table(show_header=False, box=None, padding=(0, 1, 0, 0))
                    _subtable.add_column("en", style="yellow", no_wrap=True)
                    _subtable.add_column("zh", no_wrap=True, style="white")

                    for _sentence in desc["desc_sentences"]:
                        _subtable.add_row(_sentence["en"], _sentence["zh"])

                    table.add_row("", _subtable)

                table.add_row("", "")

            self.console.print(table)

        # 显示例句
        if len(word["sentence"]) != 0:
            self.console.print("")

            table = Table(show_header=True, box=None, padding=(0, 1, 0, 0))
            table.add_column("例句", header_style="red", no_wrap=True, style="green")
            table.add_column("", style="yellow", overflow="fold")
            table.add_column("", style="white", overflow="fold")

            for i, sentence in enumerate(word['sentence'], 1):
                table.add_row(f"{i}.", sentence["en"], sentence["zh"])

            self.console.print(table)
                        
                        
__all__ = ["CommandDraw"]
