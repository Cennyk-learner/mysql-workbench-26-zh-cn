# MySQL Workbench 8.0.47 简体中文补丁

适用于 Apple 芯片 Mac 上的 **MySQL Workbench 8.0.47 CE ARM64**。本补丁翻译菜单和常用工作界面，并将自绘侧边栏的字体改为系统苹方，解决中文显示成方框的问题。

## 汉化范围

| 区域 | 已覆盖的内容 |
| --- | --- |
| 菜单栏 | 242 处菜单标题及对应的辅助功能名称 |
| 管理侧边栏 | 管理、实例、性能分组，以及服务器状态、客户端连接、用户与权限、导入导出等入口 |
| SQL 编辑器 | 管理与架构标签、会话与对象面板、语法帮助、代码片段、行数限制及常用工具提示 |
| 执行结果区 | 执行输出、文本输出、时间、操作、响应和耗时标题 |
| Python 管理插件 | 410 个可匹配的常用界面词条，应用于标签、按钮、表头等显示接口 |
| 字体 | 自绘侧边栏使用系统 `PingFang SC`，覆盖中文分组和入口文字 |

“410 个词条”指词典中可匹配的文本数量，实际出现的词条取决于打开的页面。部分高级页面、弹窗、编辑器内置功能和帮助文档仍有英文。已经保存的查询标签名称可能继续显示为 `Query 1`，新建查询标签会使用中文。

## 兼容要求

| 项目 | 要求 |
| --- | --- |
| Workbench | Oracle 官方 **8.0.47 CE，build 5817297，macOS ARM64** |
| Mac | Apple 芯片，已在 macOS 26.4.1 上验证 |
| Python | 原生 ARM64 Python **3.9 或更新版本** |
| 系统工具 | `codesign`、`ps` 及 LaunchServices，安装器会调用这些 macOS 工具 |

安装器按 SHA-256 校验六个原版资源，并检查原版主程序的 Oracle 签名标识。其他 Workbench 版本、Intel 安装包和已被修改的资源会被拒绝。

Workbench 8.0 已停止维护。连接 MySQL 8.4 时可能显示版本兼容性提示，部分管理功能受限。补丁会翻译相关提示，数据库连接能力仍取决于 Workbench 本身。[Oracle 维护说明](https://dev.mysql.com/doc/relnotes/workbench/en/news-26-7-0.html) · [8.0 兼容性说明](https://dev.mysql.com/doc/workbench/en/wb-intro.html)

## 安装方法

1. 从 Oracle 版本归档选择 **8.0.47**、**macOS (ARM, 64-bit)**，下载 `mysql-workbench-community-8.0.47-macos-arm64.dmg`，把 `MySQLWorkbench.app` 拖入「应用程序」。[Oracle 版本归档](https://downloads.mysql.com/archives/workbench/)

2. 确认终端能运行 `python3 --version`。如果系统提示需要命令行开发工具，可先安装。

   ```sh
   xcode-select --install
   ```

3. 在本仓库选择 **Code → Download ZIP** 并解压，进入其中的 `workbench-8.0` 文件夹。也可以用 Git 下载。

   ```sh
   git clone https://github.com/Cennyk-learner/mysql-workbench-26-zh-cn.git
   cd mysql-workbench-26-zh-cn/workbench-8.0
   ```

4. 保存正在编辑的 SQL，并退出 Workbench。先检查补丁能否应用，再创建本地汉化副本。

   ```sh
   python3 install.py --check
   python3 install.py --copy-to "$HOME/Applications/MySQLWorkbench-8.0-zh-CN.app"
   ```

5. 重新打开 Workbench。

   ```sh
   open "$HOME/Applications/MySQLWorkbench-8.0-zh-CN.app"
   ```

中英文副本共用 Workbench 用户配置。请退出一个版本后再打开另一个版本。

如果应用放在其他目录，给检查、安装或恢复命令加上 `--app`。

```sh
python3 install.py --app "$HOME/Applications/MySQLWorkbench.app" --check
python3 install.py --app "$HOME/Applications/MySQLWorkbench.app" --copy-to "$HOME/Applications/MySQLWorkbench-8.0-zh-CN.app"
```

这里的 `--app` 指定官方原版，`--copy-to` 指定尚不存在的汉化应用路径。默认原版路径为 `/Applications/MySQLWorkbench.app`。推荐把汉化副本放在当前用户的 `~/Applications` 中。

## 安装过程与备份

安装器会从已校验的官方原版创建本地副本，复制应用结构时排除原下载文件的扩展属性，然后应用翻译、字体修复和本地签名。这个流程用于避免直接复制已修改应用后出现 macOS“已损坏”提示。

汉化副本内的原版资源会先备份，备份位置会打印在终端，并记录在应用的补丁标记中。默认备份存放在以下目录。

```text
~/Library/Application Support/MySQL/Workbench/zh-cn-backups/
```

Workbench 内置 Python 可能向签名框架写入字节码缓存。安装器会归档额外的缓存，并为应用配置 `PYTHONDONTWRITEBYTECODE=1`，避免这些缓存再次影响资源签名校验。

更新本地签名后，macOS 钥匙串可能再次询问是否允许 Workbench 读取已保存的数据库密码。需要授权时，在系统窗口输入 Mac 登录密码，并按自己的使用需求选择「允许」或「始终允许」。

## 使用英文原版与恢复

安装完成后，可以从“应用程序”打开 Oracle 英文原版。需要把汉化副本也恢复为英文时，先保存 SQL 并退出 Workbench，再执行恢复命令。


```sh
python3 install.py --app "$HOME/Applications/MySQLWorkbench-8.0-zh-CN.app" --restore
```

安装器会校验备份与当前补丁资源，恢复安装前的应用文件和签名。恢复命令需要安装器生成的补丁记录与原版备份。请保留备份目录，恢复后可重新打开 Workbench。

如果补丁安装后又手动修改了应用资源，恢复检查可能会停止。此时请保留备份，并从 Oracle 重新复制同版本的官方应用。

## 常见问题

- **资源与官方安装包不一致**。检查版本、芯片架构与应用路径。已经安装其他汉化包的应用，需要先重新复制官方 8.0.47 ARM64 版。
- **提示先退出 Workbench**。保存 SQL，并用菜单退出应用后重试。
- **macOS 提示“已损坏”**。请取消打开，并从官方原版重新运行上述 `--copy-to` 安装流程。建议在每台 Mac 上各自生成本地汉化副本。
- **侧边栏仍显示方框**。确认运行的是刚打补丁的应用，完全退出后重开。该修复依赖 macOS 系统苹方字体。
- **部分文字仍是英文**。请提交界面位置和英文原文，便于补充词条。已有查询标签的名称会随工作区保存。
- **看到“警告：未受支持”**。这是 Workbench 8.0 对服务器版本的兼容性提示，可以结合实际使用的功能判断。补丁保留了该提示。

## 改译和反馈

翻译集中在 [translations.json](translations.json)。`menus` 按菜单 ID 定位，`ui` 用于 Python 界面标签，`native` 用于已确认的原生显示文本。

原生译文的 UTF-8 字节数受原字符串空间限制，安装器会检查长度，并保持原字符串地址。界面文件的字符串长度与表偏移由安装器更新。修改词条后，先运行 `--check`，再在独立的应用副本上验证。

菜单词条参考了 [pifeifei/mysql-workbench-zh-cn](https://github.com/pifeifei/mysql-workbench-zh-cn)，并补充了 8.0.47 的条目。主界面翻译、安装与恢复脚本、字体修复在本目录维护。MySQL Workbench 由 Oracle 开发。

欢迎通过 [Issues](https://github.com/Cennyk-learner/mysql-workbench-26-zh-cn/issues) 提交反馈，请附上版本、macOS 版本和界面位置。分享截图或日志前，请遮盖连接地址与账号信息。
