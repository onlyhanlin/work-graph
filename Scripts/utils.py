import os
import sys
import tempfile
import shutil
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOC_DIR = os.path.join(PROJECT_ROOT, 'doc')
GRAPH_OUT_DIR = os.path.join(PROJECT_ROOT, 'graph-out')
SCRIPTS_DIR = os.path.join(PROJECT_ROOT, 'Scripts')


def get_project_root():
    return PROJECT_ROOT


def get_doc_dir():
    return DOC_DIR


def get_graph_out_dir():
    return GRAPH_OUT_DIR


def ensure_dir_exists(dir_path):
    os.makedirs(dir_path, exist_ok=True)


def generate_timestamp():
    return datetime.now().strftime('%Y-%m-%d-%H-%M-%S')


def generate_markdown_filename(original_name, file_type):
    timestamp = generate_timestamp()
    original_basename = os.path.basename(original_name)
    return f"{timestamp}-{original_basename}.md"


def create_markdown_with_metadata(content, original_file_path, file_type):
    ensure_dir_exists(os.path.join(DOC_DIR, file_type))
    
    metadata = f"""---
文件来源: {original_file_path}
文件类型: {file_type}
转换时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
---

"""
    
    full_content = metadata + content
    
    md_filename = generate_markdown_filename(original_file_path, file_type)
    md_path = os.path.join(DOC_DIR, file_type, md_filename)
    
    with open(md_path, 'w', encoding='utf-8') as f:
        f.write(full_content)
    
    return md_path


def get_all_markdown_files():
    md_files = []
    for root, dirs, files in os.walk(DOC_DIR):
        for file in files:
            if file.endswith('.md'):
                md_files.append(os.path.join(root, file))
    return md_files


def graph_exists():
    return os.path.exists(GRAPH_OUT_DIR) and len(os.listdir(GRAPH_OUT_DIR)) > 0


def create_temp_file(content, suffix='.txt'):
    fd, path = tempfile.mkstemp(suffix=suffix, text=True)
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(content)
    return path


def delete_temp_file(file_path):
    if os.path.exists(file_path):
        os.remove(file_path)


def run_markitdown(input_path, output_path):
    import subprocess
    try:
        subprocess.run(['markitdown', input_path, '-o', output_path], 
                      check=True, capture_output=True, text=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"markitdown转换失败: {e.stderr}")
        return False
    except FileNotFoundError:
        print("markitdown未安装或不在PATH中")
        return False