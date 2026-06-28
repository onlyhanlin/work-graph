# work-graph

使用知识图谱管理日常工作的工具，支持多种文档格式的读取、转换和知识图谱生成与查询。

## 功能特点

- 📄 **多格式文档支持**: PDF, DOC, DOCX, PPT, PPTX, Excel, HTML, MD, TXT
- 🖼️ **图片文字识别**: 支持 PNG, JPG, JPEG, BMP 格式的 OCR 识别
- 💬 **聊天内容保存**: 支持与 AI 聊天内容的保存和转换
- 🧠 **知识图谱构建**: 使用 Understand-Anything 生成知识图谱，支持模板驱动按文档类型差异化提取实体和关系
- 🔍 **智能查询**: 基于语义理解的知识图谱查询
- 📊 **文件分类**: 根据文件类型进行分类管理

## 项目结构

```
work-graph/
├── doc/              # 存放生成的markdown文档
├── Scripts/          # 项目脚本文件
├── templates/        # 提取模板（按文档类型定义实体/关系规则）
├── graph-out/        # 存放生成的知识图谱
├── SKILL.md          # 项目技能说明
├── README.md         # 项目说明文档
└── require.txt       # 依赖文件
```

## 安装与初始化

```bash
# 克隆或下载项目后
cd work-graph
python Scripts/work_graph.py init
```

## 命令使用

### 1. 初始化项目

```bash
work-graph init
```

### 2. 读取文件

```bash
# 读取PDF文档
work-graph read ./report.pdf -type report

# 读取Word文档
work-graph read ./document.docx -type document

# 读取图片（自动OCR识别）
work-graph read ./image.png -type image

# 读取HTML文件
work-graph read ./page.html -type web
```

### 3. 聊天保存

```bash
work-graph chat -type meeting
```

### 4. 构建知识图谱

```bash
work-graph build
```

- 使用 Understand-Anything 扫描文档并提取 Markdown 标题结构
- 根据文档类型自动加载 `templates/` 下的对应模板，按模板规则提取 domain 实体和关系
- 模板不存在时使用 `document.md` 兜底
- 用户可直接编辑模板 Markdown 文件调整提取行为

### 5. 查询知识图谱

```bash
work-graph query "今天的会议内容是什么？"
work-graph query "项目进度如何？"
work-graph query "报告中的关键结论有哪些？"
```

### 6. 显示帮助

```bash
work-graph help
```

## 文件类型

转换后的 markdown 文件会根据 `-type` 参数保存到 `doc/{file_type}/` 目录下：

- `email`: 邮件文档
- `report`: 报告文档
- `meeting`: 会议记录
- `image`: 图片文件
- `document`: 通用文档
- `web`: 网页内容

## 技术栈

- **Python**: 核心开发语言
- **Markitdown**: 文档格式转换
- **RapidOCR**: 图片文字识别
- **Understand-Anything**: 知识图谱生成
- **PyMuPDF**: PDF文档读取
- **python-docx**: Word文档读取
- **python-pptx**: PowerPoint读取
- **openpyxl**: Excel读取
- **BeautifulSoup**: HTML解析

## 依赖安装

```bash
pip install -r require.txt
```

## 模板系统

`templates/` 目录下的 Markdown 文件定义了每种文档类型的提取规则：

| 模板文件 | 适用类型 | 提取内容 |
|---------|---------|---------|
| `mail.md` | email, mail | 发件人/收件人/日期 + sent/received/dated 关系 |
| `report.md` | report, 报告 | 人员/日期/参考链接 + mentions/cites 关系 |
| `document.md` | * (兜底) | 概念关键词 + mentions 关系 |

模板支持正则匹配、关键词频率提取、捕获组命名、分裂字符、日期归一化等特性。直接编辑 `.md` 文件即可定制提取行为。

## 注意事项

1. 每个转换后的 markdown 文档都包含元数据，记录了原始文件来源和转换时间
2. 图片文件会先使用 OCR 识别文字，再转换为 markdown
3. 知识图谱构建使用 Understand-Anything 作为核心引擎，模板提供差异化提取
4. 确保在运行 `work-graph build` 之前至少有一个文档已转换

## License

MIT