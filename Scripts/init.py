import subprocess
import sys
import os
import json
from utils import get_project_root


def run_command(cmd, cwd=None, shell=True):
    try:
        result = subprocess.run(cmd, cwd=cwd, shell=shell, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def check_node():
    success, stdout, stderr = run_command("node --version")
    if success:
        version = stdout.strip()
        print(f"✓ Node.js: {version}")
        return True
    print("✗ Node.js 未安装或不在 PATH 中")
    print("  请安装 Node.js 18+：https://nodejs.org/")
    return False


def check_pnpm():
    success, stdout, stderr = run_command("pnpm --version")
    if success:
        version = stdout.strip()
        print(f"✓ pnpm: {version}")
        return True
    print("✗ pnpm 未安装")
    print("  安装命令: npm install -g pnpm")
    return False


def install_requirements():
    project_root = get_project_root()
    requirements_file = os.path.join(project_root, 'require.txt')
    
    if not os.path.exists(requirements_file):
        print("✗ 未找到 require.txt 文件")
        return False
    
    try:
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', '-r', requirements_file])
        print("✓ 成功安装所有 Python 依赖")
        return True
    except subprocess.CalledProcessError:
        print("✗ 安装 Python 依赖失败")
        return False


def install_understand_anything():
    project_root = get_project_root()
    understand_dir = os.path.join(project_root, '.understand-anything')
    
    if os.path.exists(understand_dir):
        print(f"⚠️ Understand-Anything 已存在于: {understand_dir}")
        return True
    
    print("\n📥 克隆 Understand-Anything 仓库...")
    
    success, stdout, stderr = run_command(
        "git clone https://github.com/Egonex-AI/Understand-Anything.git .understand-anything",
        cwd=project_root
    )
    
    if not success:
        print(f"✗ 克隆仓库失败: {stderr}")
        return False
    
    print("✓ 仓库克隆成功")
    
    print("\n📦 安装 Understand-Anything 依赖...")
    
    success, stdout, stderr = run_command(
        "pnpm install",
        cwd=understand_dir
    )
    
    if success:
        print("✓ 依赖安装成功")
        return True
    else:
        print(f"✗ 依赖安装失败: {stderr}")
        return False


def create_config():
    project_root = get_project_root()
    understand_dir = os.path.join(project_root, '.understand-anything')
    config_dir = os.path.join(understand_dir, 'config')
    
    os.makedirs(config_dir, exist_ok=True)
    
    config = {
        "language": "zh",
        "projectRoot": project_root,
        "outputDir": os.path.join(project_root, 'graph-out')
    }
    
    config_path = os.path.join(config_dir, 'config.json')
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(config, f, indent=2, ensure_ascii=False)
    
    print(f"✓ 配置文件已创建: {config_path}")
    return True


def install_markitdown():
    print("\n📦 安装 Markitdown...")
    
    success, stdout, stderr = run_command("pnpm add -g markitdown")
    
    if success:
        print("✓ Markitdown 安装成功")
        return True
    else:
        print(f"⚠️ pnpm 安装失败，尝试使用 npm...")
        
        success, stdout, stderr = run_command("npm install -g markitdown")
        
        if success:
            print("✓ Markitdown 安装成功")
            return True
        else:
            print(f"✗ Markitdown 安装失败: {stderr}")
            return False


def run():
    print("🚀 开始初始化 work-graph 项目...")
    
    print("\n1. 检查 Node.js 环境...")
    if not check_node():
        print("\n❌ 请先安装 Node.js 18+")
        return False
    
    print("\n2. 检查 pnpm 环境...")
    if not check_pnpm():
        print("\n❌ 请先安装 pnpm")
        return False
    
    print("\n3. 安装 Python 依赖...")
    install_requirements()
    
    print("\n4. 安装 Markitdown...")
    install_markitdown()
    
    print("\n5. 安装 Understand-Anything...")
    if not install_understand_anything():
        print("\n❌ Understand-Anything 安装失败")
        return False
    
    print("\n6. 创建配置文件...")
    create_config()
    
    print("\n✅ 项目初始化完成！")
    print("\n可用命令:")
    print("  work-graph read {文件名} -type {文件类型}   # 读取文件")
    print("  work-graph read -mail [-list|id|subject|latest]  # 读取邮箱")
    print("  work-graph chat -type {文件类型}              # 聊天")
    print("  work-graph build                              # 构建知识图谱")
    print("  work-graph query \"提问内容\"                  # 查询图谱")
    print("  work-graph help                               # 帮助")
    
    return True


if __name__ == '__main__':
    run()