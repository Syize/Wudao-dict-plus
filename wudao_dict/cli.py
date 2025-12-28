#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
无道词典命令行接口

使用argparse优化的命令行参数解析实现
"""

import argparse
import json
import sys

from rich import print
from rich.table import Table

from .client import WudaoClient
from .core import CONFIG_FILE, load_config, save_config
from .draw import CommandDraw
from .server import WudaoServer
from .utils import is_alphabet


class WudaoCLI:
    """无道词典命令行接口类"""

    def __init__(self):
        """初始化CLI实例"""
        self.painter = CommandDraw()
        self.conf = load_config()
        self.client = WudaoClient()
        self._temp_config = {
            "short": False,
            "online": False
        }

    def run(self, args: argparse.Namespace):
        """
        执行命令

        Args:
            args: argparse解析后的参数对象
        """
        if args.kill:
            self.client.close_server()
            return

        if args.interactive:
            self.interaction_mode()
            return
        
        if args.config:
            self.print_global_config()
            return
        
        if args.daemon:
            self.run_daemon()
            return

        # 处理配置选项
        config_changed = False
        
        if args.short:
            short_mode = True if args.short == "yes" else False
            
            if short_mode:
                print('[red]简明模式已开启！[red]')
                
            else:
                print('[red]完整模式已开启！[red]')
                
            self.conf["short"] = short_mode
            config_changed = True
            
        if args.online:
            online_mode = True if args.online == "yes" else False
            
            if online_mode:
                print("[red]将优先使用在线释义，获取的释义会自动更新到离线数据库中。[red]")
                
            else:
                print("[red]将优先使用本地数据库，其次是在线释义[red]")
            
            self.conf["online"] = online_mode
            config_changed = True
            
        if args.update:
            update_db = True if args.update == "yes" else False
            
            if update_db:
                print("[red]将使用在线释义更新离线数据库[red]")
                
            else:
                print("[red]不使用在线释义更新离线数据库[red]")
                
            self.conf["update_db"] = update_db
            config_changed = True

        if config_changed:
            save_config(self.conf)
            
        # check the one time setting
        if args.short_once:
            self._temp_config["short"] = True
        else:
            self._temp_config["short"] = self.conf["short"]
            
        if args.long:
            self._temp_config["short"] = False
        else:
            self._temp_config["short"] = self.conf["short"]
            
        if args.online_once:
            self._temp_config["online"] = True
        else:
            self._temp_config["online"] = self.conf["online"]
            
        # 执行查询
        if args.word:
            word = ' '.join(args.word)
            self.query(word)

    def query(self, word: str):
        """
        查询单词

        Args:
            word (str): 要查询的单词
            notename (str): 生词本文件名
        """
        word_info = {}
        is_zh = False
        if not is_alphabet(word[0]):
            is_zh = True

        # 1. query on server
        word_info = ""
        server_context = self.client.get_word_info(
            word,
            online=self._temp_config["online"],
            update_db=self.conf["update_db"]
        ).strip()
        
        if server_context:
            word_info = json.loads(server_context)

        # 5. draw
        if word_info:
            if is_zh:
                self.painter.draw_zh_text(word_info, self._temp_config["short"])
            else:
                self.painter.draw_text(word_info, self._temp_config["short"])
        else:
            print('无法查询到相关释义')

    def interaction_mode(self):
        """交互模式"""
        print("[red]无道词典增强版的交互模式未经测试，如果出现异常错误，请将错误信息反馈至:[red]")
        print("[red] https://github.com/Syize/Wudao-dict-plus/issues [red]")
        print('进入交互模式。直接键入词汇查询单词的含义。下面提供了一些设置：')
        print(':help                    本帮助')
        # print(':note [filename]         设置生词本的名称')
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
                    # print(':note [filename]         设置生词本的名称')
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
                
    def print_global_config(self):
        table = Table()
        table.add_column("配置项", no_wrap=True, style="red")
        table.add_column("用途", overflow="fold", style="white")
        table.add_column("值", no_wrap=True, style="green")
        
        table.add_row("online", "是否优先使用在线释义", "启用" if self.conf["online"] else "不启用")
        table.add_row("short", "是否启用简明模式", "启用" if self.conf["short"] else "不启用")
        table.add_row("update_db", "是否使用在线释义更新离线数据库", "启用" if self.conf["update_db"] else "不启用")
        
        print("[boldwhite]无道词典增强版全局配置[boldwhite]")
        print(table)
        print(f"[cyan]配置文件位于：[boldwhite]{CONFIG_FILE}")
        
    def run_daemon(self):
        server = WudaoServer(is_foreground=True)
        print("正在运行无道词典服务")
        try:
            server.run()
            
        except KeyboardInterrupt:
            print("无道词典服务已退出")


def create_parser():
    """
    创建命令行参数解析器

    Returns:
        argparse.ArgumentParser: 参数解析器实例
    """
    parser = argparse.ArgumentParser(
        prog='wd',
        description='无道词典增强版 - 一个简洁优雅的命令行词典',
        epilog='支持英汉互查的功能，包含释义、词组、例句等有助于学习的内容。'
    )

    # 位置参数
    parser.add_argument('word', nargs='*', help='要查询的单词或短语')

    # 选项参数
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-c", "--config", action="store_true", help="打印全局配置选项")
    group.add_argument("-d", "--daemon", action="store_true", help="在前台运行无道词典服务(可用于DEBUG)")
    group.add_argument('-i', '--interactive', action='store_true', help='进入交互模式（未经测试，可能会出现未知错误）')
    group.add_argument('-k', '--kill', action='store_true', help='退出服务进程')
    
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-s", "--short-once", action="store_true", help="仅本次查询启用简明模式")
    group.add_argument("-l", "--long", action="store_true", help="仅本次查询关闭简明模式")
    
    parser.add_argument("-o", "--online-once", action="store_true", help="仅本次查询优先获取在线释义")
    
    parser.add_argument("--online", type=str, choices=["yes", "no"], help="是否强制优先获取在线释义，全局生效")
    parser.add_argument("--short", type=str, choices=["yes", "no"], help="是否启用简明模式，全局生效")
    parser.add_argument("-u", "--update", type=str, choices=["yes", "no"], help="是否使用在线释义更新离线数据库")

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
