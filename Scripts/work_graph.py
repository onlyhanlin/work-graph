import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


def show_help():
    help_text = """
work-graph - 使用知识图谱管理日常工作的工具

用法:
    work-graph <命令> [参数]

命令:
    init                    初始化项目，安装依赖
    read <文件路径> -type <文件类型>    读取文件并转换为markdown
    read -mail [-list <数量>] [-id <邮件ID>] [-subject <主题>] [-latest <数量>]   读取邮箱邮件
    chat -type <文件类型>              与AI聊天并保存内容
    build                   构建知识图谱（全量/增量）
    query "<提问内容>"       查询知识图谱
    help                    显示帮助信息

邮件读取选项:
    -list <数量>            列出最近N封邮件（默认10封）
    -id <邮件ID>            根据Message-ID读取指定邮件
    -subject <主题>         根据主题关键词搜索邮件
    -latest <数量>          读取最近N封邮件并保存（默认1封）

示例:
    work-graph init
    work-graph read ./report.pdf -type report      # 读取PDF
    work-graph read ./document.docx -type document # 读取Word
    work-graph read ./slides.pptx -type meeting    # 读取PPT
    work-graph read ./data.xlsx -type report       # 读取Excel
    work-graph read ./page.html -type web          # 读取HTML
    work-graph read ./notes.md -type document      # 读取Markdown
    work-graph read ./image.png -type image        # 读取图片(OCR)
    work-graph read ./mail.eml -type mail          # 读取邮件文件
    work-graph read -mail -list 10                 # 列出最近10封邮件
    work-graph read -mail -latest 5                # 读取最近5封邮件
    work-graph read -mail -id "<message-id>"       # 根据ID读取邮件
    work-graph read -mail -subject "项目报告"       # 搜索主题包含"项目报告"的邮件
    work-graph chat -type meeting
    work-graph build
    work-graph query "今天的会议内容是什么？"

邮箱配置:
    - 设置 mail_config.json 文件或环境变量
    - 环境变量: MAIL_SERVER, MAIL_EMAIL, MAIL_PASSWORD
    - 支持邮箱: Outlook, Gmail, Yahoo, QQ, 163, 126 及自定义IMAP服务器

支持的文件格式:
    PDF      - .pdf
    Word     - .doc, .docx
    PPT      - .ppt, .pptx
    Excel    - .xls, .xlsx
    HTML     - .html, .htm
    Markdown - .md
    纯文本   - .txt
    图片     - .png, .jpg, .jpeg, .bmp
    邮件     - .eml

文件类型说明:
    - 用于将转换后的markdown文件分类保存到doc目录下的对应文件夹
    - 例如: email, report, meeting, image, document等

项目结构:
    work-graph/
    ├── doc/              # 存放生成的markdown文档
    ├── Scripts/          # 项目脚本文件
    ├── templates/        # 提取模板
    ├── graph-out/        # 存放生成的知识图谱
    ├── SKILL.md          # 项目技能说明
    ├── README.md         # 项目说明文档
    └── require.txt       # 依赖文件
"""
    print(help_text)


def parse_args():
    if len(sys.argv) < 2:
        show_help()
        sys.exit(1)
    
    command = sys.argv[1]
    
    if command == 'init':
        from init import run as init_run
        init_run()
    
    elif command == 'read':
        if len(sys.argv) < 3:
            print("用法: work-graph read <文件路径> -type <文件类型>")
            print("用法: work-graph read -mail [-list <数量>] [-id <邮件ID>] [-subject <主题>] [-latest <数量>]")
            sys.exit(1)
        
        if sys.argv[2] == '-mail':
            from mail import run as mail_run
            mail_args = sys.argv[3:]
            mail_run(mail_args)
        else:
            if len(sys.argv) < 5 or '-type' not in sys.argv:
                print("用法: work-graph read <文件路径> -type <文件类型>")
                sys.exit(1)
            
            file_path = sys.argv[2]
            type_index = sys.argv.index('-type')
            if type_index + 1 >= len(sys.argv):
                print("用法: work-graph read <文件路径> -type <文件类型>")
                sys.exit(1)
            
            file_type = sys.argv[type_index + 1]
            
            from read import run as read_run
            read_run(file_path, file_type)
    
    elif command == 'chat':
        if len(sys.argv) < 4 or '-type' not in sys.argv:
            print("用法: work-graph chat -type <文件类型>")
            sys.exit(1)
        
        type_index = sys.argv.index('-type')
        if type_index + 1 >= len(sys.argv):
            print("用法: work-graph chat -type <文件类型>")
            sys.exit(1)
        
        file_type = sys.argv[type_index + 1]
        
        from chat import run as chat_run
        chat_run(file_type)
    
    elif command == 'build':
        from build import run as build_run
        build_run()
    
    elif command == 'query' or command == 'search':
        if len(sys.argv) < 3:
            print(f'用法: work-graph {command} "提问内容"')
            sys.exit(1)

        query_text = ' '.join(sys.argv[2:])
        query_text = query_text.strip().strip('"').strip("'")

        from utils import get_graph_out_dir
        graph_path = os.path.join(get_graph_out_dir(), 'knowledge-graph.json')

        if not os.path.exists(graph_path):
            print("✗ 知识图谱不存在，请先运行: work-graph build")
            sys.exit(1)

        import json
        try:
            with open(graph_path, 'r', encoding='utf-8') as f:
                graph = json.load(f)
            stats = f"{len(graph.get('nodes', []))} 节点, {len(graph.get('edges', []))} 条边"
        except Exception:
            stats = "未知"

        print(f"📊 知识图谱: {stats}")
        print(f"📁 图谱位置: {graph_path}")
        print(f"❓ 用户问题: {query_text}")
        print()
        print("请使用 UA understand-chat 方法回答:")
        print("  1. grep knowledge-graph.json 搜索匹配的 node (name/summary/tags/type)")
        print("  2. 对匹配节点，grep edges 找 1-hop 子图 (上游/下游)")
        print("  3. 基于子图结构化回答 — 引用具体文档名、人员、日期、关系")
    
    elif command == 'help':
        show_help()
    
    else:
        print(f"未知命令: {command}")
        show_help()
        sys.exit(1)


if __name__ == '__main__':
    parse_args()