# 无道词典增强版

![Python Version from PEP 621 TOML](https://img.shields.io/python/required-version-toml?tomlFilePath=https%3A%2F%2Fraw.githubusercontent.com%2FSyize%2FWudao-dict-plus%2Frefs%2Fheads%2Fmaster%2Fpyproject.toml) ![plat](https://img.shields.io/badge/platform-Linux/MacOS-blue.svg?style=plastic)

---

本项目基于[无道词典](https://github.com/ChestnutHeng/Wudao-dict)，对其原有功能进行了修复、优化和增强。

## 有什么变化？

以下是无道词典增强版与原无道词典功能的简要对比。

|       功能       |         无道词典增强版          |            无道词典             |
| :--------------: | :-----------------------------: | :-----------------------------: |
|    Python版本    |      3.8+，使用更新的语法       |     理论上支持Python3全版本     |
|     离线词典     |              支持               |              支持               |
|   离线词典形式   |          sqlite3数据库          |           自定义词表            |
|   词典服务进程   |             启动快              |             启动慢              |
| 词典服务进程实现 |      Python实现，随机端口       |     依赖shell脚本，固定端口     |
|     安装方法     | 打包上传pypi，<br />支持pip安装 | git克隆仓库，<br />运行安装脚本 |
|     在线词典     | 支持 (见[支持的在线词典](#支持的在线词典)) |             已失效              |
|      生词本      |            暂不支持             |              支持               |
|     自动补全     |            暂不支持             |              支持               |
|     词条上报     |         已移除相关功能          |             已失效              |

## 截图

英汉：

![En_Zh Demo](./img/wudao_en.png)

汉英:

![Zh_En Demo](./img/wudao_zh.png)

## 功能特性

1. 继承自原[无道词典](https://github.com/ChestnutHeng/Wudao-dict)的离线词典数据库。
2. 支持在线查询，并使用在线释义更新离线数据库。

## 支持的在线词典

目前仅支持[有道词典](https://dict.youdao.com/)。


## 如何安装？

```bash
pip install wudao-dict-plus
```


## 使用说明

运行`wd -h`查看使用说明。


```
$ wd -h
usage: wd [-h] [-c | -i | -k] [-s | -l] [-o] [--online {yes,no}] [--short {yes,no}] [-u {yes,no}] [word [word ...]]

无道词典增强版 - 一个简洁优雅的命令行词典

positional arguments:
  word                  要查询的单词或短语

optional arguments:
  -h, --help            show this help message and exit
  -c, --config          打印全局配置选项
  -i, --interactive     进入交互模式（未经测试，可能会出现未知错误）
  -k, --kill            退出服务进程
  -s, --short-once      仅本次查询启用简明模式
  -l, --long            仅本次查询关闭简明模式
  -o, --online-once     仅本次查询优先获取在线释义
  --online {yes,no}     是否强制优先获取在线释义，全局生效
  --short {yes,no}      是否启用简明模式，全局生效
  -u {yes,no}, --update {yes,no}
                        是否使用在线释义更新离线数据库

支持英汉互查的功能，包含释义、词组、例句等有助于学习的内容。
```

查词时可以直接使用`wd 词语`查汉英词典，或`wd word`查英汉词典(可以自动检测)。

## TODO

- [ ] 完全的跨平台兼容 (目前不支持在 Windows 上使用)
- [ ] 发音功能支持 ([#4](https://github.com/Syize/Wudao-dict-plus/issues/4))

## 致谢

- 感谢原[无道词典](https://github.com/ChestnutHeng/Wudao-dict)项目及其作者对本项目的启发。
