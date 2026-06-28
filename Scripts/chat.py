import sys
from utils import (
    create_markdown_with_metadata, 
    create_temp_file, 
    delete_temp_file, 
    run_markitdown
)


def get_chat_input():
    print("请输入聊天内容（输入空行结束）:")
    lines = []
    while True:
        try:
            line = input()
            if line.strip() == "":
                break
            lines.append(line)
        except EOFError:
            break
    return '\n'.join(lines)


def run(file_type):
    print(f"💬 开始聊天（文件类型: {file_type}）")
    
    chat_text = get_chat_input()
    
    if not chat_text.strip():
        print("✗ 聊天内容为空")
        return False
    
    temp_txt_path = create_temp_file(chat_text, suffix='.txt')
    
    temp_md_path = create_temp_file("", suffix='.md')
    
    if run_markitdown(temp_txt_path, temp_md_path):
        with open(temp_md_path, 'r', encoding='utf-8') as f:
            md_content = f.read()
        
        md_path = create_markdown_with_metadata(md_content, "chat_input", file_type)
        
        delete_temp_file(temp_txt_path)
        delete_temp_file(temp_md_path)
        
        print(f"✅ 聊天内容已保存到: {md_path}")
        return md_path
    else:
        md_path = create_markdown_with_metadata(chat_text, "chat_input", file_type)
        
        delete_temp_file(temp_txt_path)
        delete_temp_file(temp_md_path)
        
        print(f"⚠️ markitdown转换失败，已直接保存聊天内容到: {md_path}")
        return md_path


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python chat.py {文件类型}")
        sys.exit(1)
    
    file_type = sys.argv[1]
    run(file_type)