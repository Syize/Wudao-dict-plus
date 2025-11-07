#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
无道词典命令行接口

使用argparse优化的命令行参数解析实现
"""

import argparse
import json
import sys
import os

from .core import load_config, save_config
from .client import WudaoClient
from .ui import CommandDraw
from .utils import is_alphabet


class WudaoCLI:
    """无道词典命令行接口类"""
    
    def __init__(self):
        """初始化CLI实例"""
        self.painter = CommandDraw()
        self.conf = load_config()
        self.client = WudaoClient()
        
    def run(self, args):
        """
        执行命令
        
        Args:
            args: argparse解析后的参数对象
        """
        # 处理各种命令选项
        if args.version:
            self.show_version()
            return
            
        if args.kill:
            self.client.close_server()
            return
            
        if args.interactive:
            self.interaction_mode()
            return
            
        # 处理配置选项
        config_changed = False
        if args.short is not None:
            self.conf['short'] = args.short
            config_changed = True
            if args.short:
                print('简明模式已开启！')
            else:
                print('完整模式已开启！')
                
        if config_changed:
            save_config(self.conf)
            
        # 执行查询
        if args.word:
            word = ' '.join(args.word)
            self.query(word)
        elif not any([args.version, args.kill, args.interactive]):
            # 如果没有提供单词且没有其他命令，显示帮助
            self.show_help()
    
    def show_version(self):
        """显示版本信息"""
        print('Wudao-dict, Version \033[31m2.1\033[0m, Nov 27, 2019')
        
    def show_help(self):
        """显示帮助信息"""
        print('Usage: wd [OPTION]... [WORD]')
        print('Youdao is wudao, a powerful dict.')
        print('生词本文件: ' + os.path.abspath('./usr/') + '/notebook.txt')
        print('查询次数: ' + os.path.abspath('./usr/') + '/usr_word.json')
        
    def query(self, word, notename='notebook'):
        """
        查询单词
        
        Args:
            word (str): 要查询的单词
            notename (str): 生词本文件名
        """
        word_info = {}
        is_zh = False
        if word:
            if not is_alphabet(word[0]):
                is_zh = True
                
        # 1. query on server
        word_info = None
        server_context = self.client.get_word_info(word).strip()
        if server_context and server_context != 'None':
            word_info = json.loads(server_context)
            
        # 5. draw
        if word_info:
            if is_zh:
                self.painter.draw_zh_text(word_info, self.conf)
            else:
                self.painter.draw_text(word_info, self.conf)
        else:
            print('Word not exists.')
    
    def interaction_mode(self):
        """交互模式"""
        print('进入交互模式。直接键入词汇查询单词的含义。下面提供了一些设置：')
        print(':help                    本帮助')
        print(':note [filename]         设置生词本的名称')
        print(':long                    切换完整模式(:short切换回去)')
        
        conf = {'save': True, 'short': True, 'notename': 'notebook'}
        while True:
            try:
                inp = input('~ ')
            except EOFError:
                sys.exit(0)
            if inp.startswith(':'):
                if inp == ':quit':
                    print('Bye!')
                    sys.exit(0)
                elif inp == ':short':
                    conf['short'] = True
                    print('简明模式（例句将会被忽略）')
                elif inp == ':long':
                    conf['short'] = False
                    print('完整模式（例句将会被显示）')
                elif inp == ':help':
                    print(':help                    本帮助')
                    print(':quit                    退出')
                    print(':note [filename]         设置生词本的名称')
                    print(':long                    切换完整模式(:short切换回去)')
                elif inp.startswith(':note'):
                    vec = inp.split()
                    if len(vec) == 2 and vec[1]:
                        conf['notename'] = vec[1]
                        print('生词本指定为: ./usr/%s.txt' % (vec[1]))
                    else:
                        print('Bad notebook name!')
                else:
                    print('Bad Command!')
                continue
            if inp.strip():
                self.query(inp.strip(), conf['notename'])


def create_parser():
    """
    创建命令行参数解析器
    
    Returns:
        argparse.ArgumentParser: 参数解析器实例
    """
    parser = argparse.ArgumentParser(
        prog='wd',
        description='无道词典 - 一个简洁优雅的有道词典命令行版本',
        epilog='支持英汉互查的功能，包含释义、词组、例句等有助于学习的内容。'
    )
    
    # 位置参数
    parser.add_argument(
        'word',
        nargs='*',
        help='要查询的单词或短语'
    )
    
    # 选项参数
    parser.add_argument(
        '-k', '--kill',
        action='store_true',
        help='退出服务进程'
    )
    
    parser.add_argument(
        '-s', '--short',
        nargs='?',
        const=True,
        type=lambda x: x.lower() not in ('false', '0', 'no'),
        metavar='BOOLEAN',
        dest='short',
        help='简明/完整模式 (默认: 开启简明模式)'
    )
    
    parser.add_argument(
        '-i', '--interactive',
        action='store_true',
        help='进入交互模式'
    )
    
    parser.add_argument(
        '-n', '--note',
        nargs='?',
        const=True,
        type=lambda x: x.lower() not in ('false', '0', 'no'),
        metavar='BOOLEAN',
        dest='save',
        help='保存/不保存到生词本 (默认: 开启保存)'
    )
    
    parser.add_argument(
        '-v', '--version',
        action='store_true',
        help='显示版本信息'
    )
    
    return parser


def main():
    """主函数"""
    # 创建解析器
    parser = create_parser()
    
    # 解析参数
    args = parser.parse_args(args=None if sys.argv[1:] else ["--help"])
    
    # 创建CLI实例并运行
    cli = WudaoCLI()
    cli.run(args)


if __name__ == '__main__':
    main()
