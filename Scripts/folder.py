"""
folder.py — 批量读取目录下所有文档

遍历目录，自动识别文件类型（按扩展名），逐个调用 read.py 转换。
"""

import os
import sys

# 扩展名 → file_type 映射
EXT_TO_TYPE = {
    '.pdf': 'report',
    '.doc': 'document',
    '.docx': 'document',
    '.ppt': 'meeting',
    '.pptx': 'meeting',
    '.xls': 'report',
    '.xlsx': 'report',
    '.html': 'web',
    '.htm': 'web',
    '.md': 'document',
    '.txt': 'document',
    '.eml': 'mail',
    '.png': 'image',
    '.jpg': 'image',
    '.jpeg': 'image',
    '.bmp': 'image',
}

# 图片扩展名（走 OCR 流程）
IMAGE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.bmp'}


def detect_file_type(file_path):
    """根据扩展名自动确定文件类型，无法识别返回 None"""
    ext = os.path.splitext(file_path)[1].lower()
    return EXT_TO_TYPE.get(ext)


def scan_directory(dir_path):
    """递归扫描目录，返回 (file_path, file_type) 列表"""
    results = []
    if not os.path.isdir(dir_path):
        print(f"✗ 目录不存在: {dir_path}")
        return results

    for root, dirs, files in os.walk(dir_path):
        # 跳过隐藏目录
        dirs[:] = [d for d in dirs if not d.startswith('.')]
        for filename in files:
            file_path = os.path.join(root, filename)
            file_type = detect_file_type(file_path)
            if file_type:
                results.append((file_path, file_type))

    return results


def run(dir_path):
    """扫描目录，逐个转换所有支持的文件"""
    files = scan_directory(dir_path)

    if not files:
        print(f"⚠️ 目录中未找到可识别的文件: {dir_path}")
        return False

    print(f"📂 找到 {len(files)} 个文件\n")

    from read import run as read_run

    success_count = 0
    fail_count = 0

    for i, (file_path, file_type) in enumerate(files, 1):
        ext = os.path.splitext(file_path)[1].lower()
        print(f"[{i}/{len(files)}] {os.path.basename(file_path)} ({ext} → {file_type})")
        result = read_run(file_path, file_type)
        if result:
            success_count += 1
        else:
            fail_count += 1
        print()

    print(f"✅ 完成: {success_count} 成功, {fail_count} 失败, 共 {len(files)} 个文件")
    return success_count > 0


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python folder.py <目录路径>")
        sys.exit(1)
    run(sys.argv[1])
