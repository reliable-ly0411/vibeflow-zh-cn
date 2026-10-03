# VibeFlow Studio 简体中文汉化源码

为 **VibeFlow Studio 0.10.0 Windows x64 / ParaView 5.11** 提供中文及中文（英文）双语界面。仓库只发布翻译词表、补丁生成器、安装器、兼容性哈希和测试，不包含应用程序、DLL、原版网页、第三方完整源码、授权文件或个人配置。

这是非官方社区补丁。请自行准备合法获得的、与 `compatibility.json` 中 SHA-256 完全一致的原版安装。即使版本号相同，文件哈希不一致也会拒绝应用。

## 覆盖范围

第二版补丁包含：

- 1,823 处原生 Qt 文字引用，涉及 1,221 个不同原文。
- 17 处数据源／过滤器菜单分类。
- 104 份内嵌 XML 中 2,163 处名称、参数和简短说明。
- 60 处智能体对话、终端、几何查看器网页界面替换。
- 常用控件采用简短中文，专业数据源／过滤器名称保留中文（英文）。

计数不代表全软件覆盖率。仍可能存在未翻译的第三方插件、长篇帮助和外部程序输出。品牌、命令、路径、字典键、变量及用户已有对象名保留原文。

## 环境

- 独立安装的 **Python 3.10–3.12**，不要使用 VibeFlow 自带 Python 执行安装器。
- **Node.js 18 或更新版本**，只用于构建时检查网页脚本语法。
- `requirements.txt` 中的 Python 依赖。
- 原版软件的安装目录，且有修改权限。安装前关闭 VibeFlow 及其自带工具。

以下以 Windows PowerShell 和 `D:\Programs\VibeFlowStudio` 为例。下载本仓库 ZIP 并解压，或：

```powershell
git clone https://github.com/reliable-ly0411/vibeflow-zh-cn.git
cd vibeflow-zh-cn
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

## 检查、构建和安装

```powershell
.\.venv\Scripts\python.exe patch.py check --app "D:\Programs\VibeFlowStudio"
.\.venv\Scripts\python.exe patch.py build --app "D:\Programs\VibeFlowStudio"
.\.venv\Scripts\python.exe patch.py install --app "D:\Programs\VibeFlowStudio"
.\.venv\Scripts\python.exe patch.py verify --app "D:\Programs\VibeFlowStudio"
```

`build` 将原版文件复制到本仓库的 `originals/`，输出到 `work/`，**不会修改软件安装目录**。全部 15 个输出必须与已测试第二版的哈希一致，才可安装。不要使用 Python `-O` 模式运行构建脚本。

`install` 先核对全部原版与补丁哈希，再备份和原子替换；出错会尝试恢复本次事务。重复安装只校验，不重复打补丁。安装后使用原桌面图标启动。

如有额外的渲染兼容镜像，在 `check` 和首次 `install` 时传入镜像根目录：

```powershell
.\.venv\Scripts\python.exe patch.py check --app "D:\Programs\VibeFlowStudio" --mirror "D:\vibeworking\VibeFlow-render\software"
.\.venv\Scripts\python.exe patch.py install --app "D:\Programs\VibeFlowStudio" --mirror "D:\vibeworking\VibeFlow-render\software"
```

这会同步六组二进制硬链接，总计 21 个目标路径。镜像需要已存在，且 `resources`、`share`、`bin\Lib` 已指向主安装的相应目录；工具不会创建渲染配置或修改启动器。没有此镜像就省略 `--mirror`。

如果已安装此前的本地第一版／第二版，请先用对应旧安装器恢复原版，再使用本仓库工具。不要把已打补丁的文件作为原版输入，也不要在原有已安装环境上直接重复迁移安装器。

## 校验与卸载

```powershell
.\.venv\Scripts\python.exe patch.py verify --app "D:\Programs\VibeFlowStudio"
.\.venv\Scripts\python.exe patch.py uninstall --app "D:\Programs\VibeFlowStudio"
```

安装记录与备份位于软件根目录 `.vfzh/`。卸载按记录恢复原版字节，保留备份和个人设置。镜像路径会自动从安装记录读取。

如文件被软件更新或后续修改，校验和卸载会停止，不覆盖未知内容。中断后的恢复方式、旧版迁移见 [恢复说明](docs/RECOVERY.md)。

## 测试与已知限制

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

有受支持原版文件后，还可运行完整集成测试。参数为包含本补丁 15 个原版文件的平铺目录，例如完成构建后的 `originals`：

```powershell
.\.venv\Scripts\python.exe tests/integration.py originals
```

集成测试仅在临时安装副本上运行，覆盖完整构建、预期哈希、安装、重复安装、校验、字节级恢复、设置保留和备份保留。运行时会更新仓库内的 `originals/`、`work/`。

第二版组件已在 Windows 实际安装并通过后台 `Sphere`、`Clip(Plane)`、`Contour`、`Calculator` 和状态保存测试。原生组件加载和 1,823 处字符串解码通过。**尚未完成所有界面的目视排版、脚本录制和完整求解流程验收**，不能将后台测试视为全功能保证。详见 [验证记录](docs/VALIDATION.md)。

## 维护与许可

翻译词表在 `translations.tsv`、`translations-extra.json`、`vtk-label-translations.tsv`；构建原理见 [技术说明](docs/ARCHITECTURE.md)。兼容清单必须与实际软件文件一致，软件升级后不能简单删除哈希检查继续使用。

本仓库原创工具及翻译贡献按 [MIT License](LICENSE) 发布，软件名称、原文及第三方组件权利仍归各自权利人，见 [NOTICE](NOTICE)。生成文件仅用于本机安装，不随本仓库分发。
