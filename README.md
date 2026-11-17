# MySQL Workbench 26 简体中文补丁

给 Apple 芯片 Mac 上的 MySQL Workbench **26.10.0** 加上简体中文菜单和常用界面翻译。安装后，在访达打开「MySQL Workbench 中文版」即可使用。中文版和 Oracle 原版可以同时保留。

目前覆盖 macOS 菜单栏及 **293 个前端词条**，包括首页、连接列表、新建连接、测试连接、SQL 脚本与笔记本、架构浏览和查询结果。部分高级页面、编辑器内置菜单、数据库报错和帮助文档仍显示英文。

## 支持的版本

| 项目 | 要求 |
| --- | --- |
| MySQL Workbench | Oracle 官方 **26.10.0 macOS ARM64** 版 |
| Mac | Apple 芯片，已在 macOS 26.4.1 上验证 |
| Node.js | macOS ARM64 版，已用 26.5.0 验证 |

此补丁按具体版本校验资源。旧版 Workbench 8.0、Intel Mac、Windows 和 Linux 不适用。

## 安装

1. 下载 `mysql-workbench-26.10.0-macos-arm64.dmg`，把 **MySQL Workbench.app** 拖入「应用程序」。当前下载页显示其他版本时，请在归档页选 **26.10.0** 和 **macOS (ARM, 64-bit)**。 [Oracle 下载页](https://dev.mysql.com/downloads/workbench/?os=6) · [Oracle 版本归档](https://downloads.mysql.com/archives/workbench/)
2. 安装 ARM64 版 Node.js，在终端用 `node -v` 确认可运行。 [Node.js 下载](https://nodejs.org/zh-cn/download)
3. 在本仓库的 **Code → Download ZIP** 下载并解压补丁，进入解压后的目录。也可以用 Git 下载。

   ```sh
   git clone https://github.com/Cennyk-learner/mysql-workbench-26-zh-cn.git
   cd mysql-workbench-26-zh-cn
   ```

4. 在补丁目录执行以下命令。第一条检查版本和词条定位，第二条创建中文版。

   ```sh
   node --expose-internals install.cjs --check
   node --expose-internals install.cjs
   ```

5. 在访达按 `⌘⇧G`，输入 `~/Applications`，打开 **MySQL Workbench 中文版.app**。

中文版使用独立的连接和偏好设置，可在首页用原来的主机、端口和用户名重新添加数据库连接。安装脚本会验证原版的 Oracle 签名，在本机创建并签名中文版副本。仓库仅提供安装脚本和翻译词条，原版安装包请从 Oracle 获取。

## 常见问题

- **提示资源与已验证版本不一致**。确认下载的是官方 26.10.0 ARM64 安装包。原版放在其他位置时，传入 `--source "/完整路径/MySQL Workbench.app"`。
- **提示找不到 Acorn 或内部模块**。确认命令带有 `--expose-internals`。如果当前 Node.js 构建无法加载其内置解析器，可使用已验证的原生 ARM64 Node.js 26.5.0。
- **想试新译文或重新安装**。用 `--dest "$HOME/Applications/MySQL Workbench 中文测试版.app"` 指定一个尚未存在的目标。安装脚本会拒绝覆盖同名应用。
- **想恢复原版界面**。直接打开 Oracle 原版。卸载中文版时，把中文版应用拖入废纸篓。

## 反馈和改译

欢迎在 [Issues](https://github.com/Cennyk-learner/mysql-workbench-26-zh-cn/issues) 提交漏译、误译和安装问题。请附上 Workbench 版本、macOS 版本、界面位置和英文原文。分享截图或日志前请遮盖连接地址和账号信息。

翻译集中在 [界面词条.tsv](界面词条.tsv)，每行用一个制表符分隔英文原文与中文译文。修改后可先运行 `--check`，再安装到测试路径确认显示效果。

本项目为社区汉化补丁。MySQL Workbench 由 Oracle 开发和维护。
