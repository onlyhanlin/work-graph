# Work-Graph 技能说明

## 项目概述

work-graph 是一个使用知识图谱管理日常工作的工具，支持多种文档格式的读取、转换和知识图谱生成。

## 核心技能

### 1. 文档读取与转换
- **支持格式**: PDF, DOC, DOCX, PPT, PPTX, Excel, HTML, MD, TXT, PNG, JPG, JPEG, BMP
- **图片处理**: 使用 RapidOCR 提取图片文字
- **格式转换**: 使用 Markitdown 将文档转换为 Markdown 格式
- **文件分类**: 根据文件类型保存到对应目录

### 2. 聊天内容保存
- 支持用户与 AI 聊天内容的保存
- 自动转换为 Markdown 格式
- 根据类型分类存储

### 3. 知识图谱构建
- 使用 Understand-Anything（UA）作为图谱引擎：扫描文档 → 提取结构 → 构建知识图谱
- **模板驱动提取**：`templates/` 目录下每个文档类型对应一个 Markdown 模板文件，定义该类型要提取的实体和关系
  - `mail.md` — 邮件：发件人/收件人/日期 + sent/received/dated 关系
  - `report.md` — 报告：人员/日期/参考链接 + mentions/cites 关系
  - `document.md` — 通用兜底：概念关键词 + mentions 关系
- **UA 负责**：文件扫描、批次计算、Markdown 标题结构提取（sections）、图谱验证和持久化
- **模板负责**：按文档类型差异化提取 domain 实体（person/date/reference/concept）和关系
- 模板不存在时使用 `document.md` 兜底
- 图谱保存到 `graph-out/` 目录

### 4. 知识图谱查询
- 使用 UA understand-chat 方法查询知识图谱
- `work-graph query "问题"` 运行后输出图谱位置和问题上下文
- AI 接管查询，按以下步骤执行：
  1. grep `graph-out/knowledge-graph.json` 搜索匹配的 node（name/summary/tags/type）
  2. 对匹配的节点 ID，grep edges 找 1-hop 子图（上游/下游）
  3. 基于子图结构化回答——引用具体文档名、人员、日期、关系

## 命令列表

| 命令 | 功能 | 示例 |
|------|------|------|
| `work-graph init` | 初始化项目 | `work-graph init` |
| `work-graph read <文件> -type <类型>` | 读取文件并转换 | `work-graph read report.pdf -type report` |
| `work-graph chat -type <类型>` | 聊天并保存 | `work-graph chat -type meeting` |
| `work-graph build` | 构建知识图谱 | `work-graph build` |
| `work-graph query "<问题>"` | 查询图谱 | `work-graph query "项目进度如何？"` |
| `work-graph help` | 显示帮助 | `work-graph help` |

## 文件类型分类

- `email`: 邮件文档
- `report`: 报告文档
- `meeting`: 会议记录
- `image`: 图片文件
- `document`: 通用文档
- `other`: 其他类型

## 项目结构

```
work-graph/
├── doc/              # 生成的markdown文档
│   ├── email/        # 邮件类型
│   ├── report/       # 报告类型
│   └── ...           # 其他类型
├── Scripts/          # Python脚本
│   ├── utils.py      # 工具函数
│   ├── init.py       # 初始化模块
│   ├── read.py       # 文件读取模块
│   ├── chat.py       # 聊天模块
│   ├── build.py      # 图谱构建模块
│   └── work_graph.py # 主入口（含 query 命令）
├── templates/        # 提取模板（按文档类型定义实体/关系规则）
│   ├── mail.md       # 邮件模板
│   ├── report.md     # 报告模板
│   └── document.md   # 通用模板（兜底）
├── graph-out/        # 知识图谱输出
├── SKILL.md          # 技能说明
├── README.md         # 项目说明
└── require.txt       # 依赖文件
```

## 模板系统

`templates/` 目录存放 Markdown 格式的提取模板。每个模板定义一种文档类型应当提取的实体和关系：

- **实体规则**：正则匹配（如邮件头发件人/收件人）或关键词频率提取（正文概念词）
- **关系规则**：定义实体之间的连接（如 `person → sent → document`）
- **支持特性**：捕获组命名、id/name 模板变量、分裂字符、单复数回退、日期归一化
- **编辑方式**：直接编辑 `.md` 文件即可调整提取行为，无需改代码

## 依赖组件

1. **Markitdown**: 文档格式转换
2. **RapidOCR**: 图片文字识别
3. **Understand-Anything**: 知识图谱生成
4. **PyMuPDF**: PDF读取
5. **python-docx**: Word文档读取
6. **python-pptx**: PowerPoint读取
7. **openpyxl**: Excel读取
8. **BeautifulSoup**: HTML解析