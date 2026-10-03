# 构建原理

1. `compatibility.json` 固定 15 个原版输入和最终输出的 SHA-256；同版本的未知构建也拒绝处理。
2. `extract_qt_calls.py` 提取明确的 Qt 翻译调用。`build_patch.py` 添加翻译数据段，重定向已识别的 QStringLiteral、QString UTF-8 和 QCoreApplication 翻译文字，保留占位符。
3. `build_web.py` 仅替换指定的界面片段，不替换用户消息、代码或协议字段。
4. `build_xml.py` 更新 EXE 内嵌压缩的菜单 XML，以及 VTK DLL 中分块存储的 ServerManager XML。原地址与分块长度保持不变，重排后重新解析，对比功能属性、默认值和节点顺序。
5. 专业代理名称采用中文（英文）。ParaView 使用显示标签生成 Python 接口，因此从本机原版三份 Python 模块生成兼容版本，将中文标签映射回原 API 名称。仓库不包含这些模块的完整源码；仅包含生成逻辑。17 个可能产生歧义的翻译在标签中保留原文。
6. 通过 PE 结构、字符串指针、占位符、JavaScript 语法和 API 标签映射检查后，再比较最终输出哈希。

`originals/`、`work/` 永不提交。数据源、过滤器、属性的内部名称和算法不翻译。示例工程、显卡配置、启动器、用户凭据均不属于此补丁。

当前只有一个严格固定的 Windows x64 构建受支持。UTF-8 和 LF 输出显式固定，以避免 Windows 默认编码及换行影响生成结果。
