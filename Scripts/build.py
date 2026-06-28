import os
import subprocess
import shutil
import json
import re
from datetime import datetime

from utils import get_project_root, get_doc_dir, get_graph_out_dir, graph_exists, ensure_dir_exists


# ============================================================
#  模板引擎 — 解析和执行 templates/ 下的提取规则
# ============================================================

def get_templates_dir():
    """返回 templates/ 目录的绝对路径"""
    return os.path.join(get_project_root(), 'templates')


def load_template(file_type):
    """
    加载指定 file_type 的模板文件。
    查找顺序: templates/{file_type}.md → templates/document.md（兜底）
    返回模板内容字符串，找不到返回 None。
    """
    templates_dir = get_templates_dir()

    # 精确匹配
    exact_path = os.path.join(templates_dir, f'{file_type}.md')
    if os.path.exists(exact_path):
        with open(exact_path, 'r', encoding='utf-8') as f:
            return f.read()

    # 兜底
    fallback_path = os.path.join(templates_dir, 'document.md')
    if os.path.exists(fallback_path):
        print(f"  ⚠️ 未找到 '{file_type}' 模板，使用 document.md 兜底")
        with open(fallback_path, 'r', encoding='utf-8') as f:
            return f.read()

    return None


def parse_yaml_metadata(content):
    """
    解析 Markdown 文件的 YAML front matter。
    返回 dict，若不存在则返回 {}。
    """
    if not content.startswith('---'):
        return {}
    end_idx = content.find('---', 3)
    if end_idx == -1:
        return {}
    yaml_block = content[3:end_idx].strip()
    metadata = {}
    for line in yaml_block.split('\n'):
        line = line.strip()
        if ':' in line:
            key, _, val = line.partition(':')
            metadata[key.strip()] = val.strip()
    return metadata


def _get_mail_subject(content):
    """从邮件 markdown 中提取主题行"""
    m = re.search(r'^主题:\s*(.+)$', content, re.MULTILINE)
    return m.group(1).strip() if m else ''


def _normalize_date(date_str):
    """
    尝试将各种日期格式归一化为 YYYY-MM-DD。
    支持: 'Thu, 25 Jun 2026 04:09:00 -0700', '2026-06-28', '2026年6月28日' 等
    """
    if not date_str:
        return date_str
    # 已是 YYYY-MM-DD
    if re.match(r'^\d{4}-\d{2}-\d{2}$', date_str.strip()):
        return date_str.strip()
    # 中文格式: 2026年6月28日
    m = re.match(r'(\d{4})\s*年\s*(\d{1,2})\s*月\s*(\d{1,2})\s*日', date_str)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    # 中文格式: 2026-06-28
    m = re.match(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_str)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    # RFC 2822: Thu, 25 Jun 2026 04:09:00 -0700
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(date_str)
        return dt.strftime('%Y-%m-%d')
    except Exception:
        pass
    # 尝试简单正则提取
    m = re.search(r'(\d{4})-(\d{1,2})-(\d{1,2})', date_str)
    if m:
        return f"{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}"
    # 返回原值
    return date_str.strip()


def _get_content_body(content, file_type):
    """
    获取文档正文（去掉 YAML front matter，对邮件再去掉邮件头）。
    """
    # 去掉 YAML front matter
    if content.startswith('---'):
        end_idx = content.find('---', 3)
        if end_idx != -1:
            content = content[end_idx + 3:]

    # 邮件：去掉邮件头行（主题/发件人/收件人/日期）和分隔符 ---
    if file_type in ('mail', 'email'):
        lines = content.split('\n')
        result = []
        in_body = False
        for line in lines:
            stripped = line.strip()
            if in_body:
                result.append(line)
            elif stripped == '---':
                in_body = True
            elif not re.match(r'^(主题|发件人|收件人|日期)[：:]', stripped):
                # 可能是空行或正文开始
                if stripped:
                    in_body = True
                    result.append(line)
        return '\n'.join(result)

    return content.strip()


def parse_template(template_content):
    """
    解析模板 Markdown 为结构化规则。

    模板结构:
      ## 适用类型
      mail, email
      ## 实体规则
      ### entity:type:name
      key: value
      ## 关系规则
      ### relation:name
      key: value

    返回: {
      'file_types': ['mail', 'email'],
      'entity_rules': [{name, type, pattern, groups, id_template, name_template, split, source, method, count}, ...],
      'relation_rules': [{name, source_tpl, target_tpl, type, weight}, ...]
    }
    """
    result = {
        'file_types': [],
        'entity_rules': [],
        'relation_rules': []
    }

    # 按 ## 分段
    sections = re.split(r'\n## ', template_content)
    current_section = None

    for section in sections:
        section = section.strip()
        if not section:
            continue

        # 确定段类型
        if section.startswith('适用类型'):
            # 取第一行非空内容，按逗号分割
            lines = section.split('\n')[1:]  # 跳过标题行
            types = []
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    types.extend([t.strip() for t in line.split(',') if t.strip()])
            result['file_types'] = types
            current_section = None

        elif section.startswith('实体规则'):
            current_section = 'entity'
            # 同一次迭代中解析本段内的实体规则子段
            # section 内容: "实体规则\n\n### entity:..."
            for sub in re.split(r'\n### ', section)[1:]:  # 跳过 "实体规则" 标题行
                sub = sub.strip()
                if not sub:
                    continue
                # 解析 entity:type:name
                header = sub.split('\n')[0]
                prefix = 'entity:'
                if header.startswith(prefix):
                    parts = header[len(prefix):].split(':', 1)
                    entity_type = parts[0].strip() if len(parts) >= 1 else 'concept'
                    entity_name = parts[1].strip() if len(parts) >= 2 else ''
                else:
                    entity_type = 'concept'
                    entity_name = ''

                rule = {'name': entity_name, 'type': entity_type}
                for line in sub.split('\n')[1:]:
                    line = line.strip()
                    if ':' in line and not line.startswith('#'):
                        key, _, val = line.partition(':')
                        key, val = key.strip(), val.strip()
                        if key == 'pattern':
                            rule['pattern'] = val
                        elif key == 'groups':
                            rule['groups'] = [g.strip() for g in val.split(',')]
                        elif key == 'id_template':
                            rule['id_template'] = val
                        elif key == 'name_template':
                            rule['name_template'] = val
                        elif key == 'split':
                            rule['split'] = val
                        elif key == 'source':
                            rule['source'] = val
                        elif key == 'method':
                            rule['method'] = val
                        elif key == 'count':
                            try:
                                rule['count'] = int(val)
                            except ValueError:
                                rule['count'] = 5
                result['entity_rules'].append(rule)

        elif section.startswith('关系规则'):
            current_section = 'relation'
            # 同一次迭代中解析本段内的关系规则子段
            for sub in re.split(r'\n### ', section)[1:]:
                sub = sub.strip()
                if not sub:
                    continue
                header = sub.split('\n')[0]
                prefix = 'relation:'
                rel_name = header[len(prefix):].strip() if header.startswith(prefix) else ''

                rule = {'name': rel_name}
                for line in sub.split('\n')[1:]:
                    line = line.strip()
                    if ':' in line and not line.startswith('#'):
                        key, _, val = line.partition(':')
                        key, val = key.strip(), val.strip()
                        if key == 'source':
                            rule['source_tpl'] = val
                        elif key == 'source_entity':
                            rule['source_entity'] = val
                        elif key == 'target':
                            rule['target_tpl'] = val
                        elif key == 'target_entity':
                            rule['target_entity'] = val
                        elif key == 'type':
                            rule['type'] = val
                        elif key == 'weight':
                            try:
                                rule['weight'] = float(val)
                            except ValueError:
                                rule['weight'] = 0.5
                result['relation_rules'].append(rule)

    return result


def _resolve_template(tpl, values):
    """将模板字符串中的 {var} 替换为 values 中的值。
    支持单复数回退：{name} 在 values 中找不到时尝试 {names}，反之亦然。
    """
    def replacer(m):
        key = m.group(1)
        if key in values:
            return str(values[key])
        # 单复数回退
        if key.endswith('s'):
            singular = key[:-1]
            if singular in values:
                return str(values[singular])
        else:
            plural = key + 's'
            if plural in values:
                return str(values[plural])
        return m.group(0)
    return re.sub(r'\{(\w+)\}', replacer, tpl)


def apply_template_engine(template_content, file_content, file_path, file_type):
    """
    模板执行引擎：加载模板 → 解析规则 → 应用实体规则 → 应用关系规则 → 返回 {nodes, edges}。

    返回: {'nodes': [...], 'edges': [...]}
    """
    rules = parse_template(template_content)
    entity_rules = rules['entity_rules']
    relation_rules = rules['relation_rules']

    nodes = []
    edges = []
    entity_map = {}  # entity_type → list of {id, name, type, ...}

    # 准备数据源
    subject_text = _get_mail_subject(file_content) if file_type in ('mail', 'email') else ''
    body_text = _get_content_body(file_content, file_type)

    # ── 1. 执行实体规则 ──
    for rule in entity_rules:
        entity_type = rule.get('type', 'concept')
        method = rule.get('method', '')

        if method == 'keyword_freq':
            # 关键词频率提取
            source = rule.get('source', 'body')
            count = rule.get('count', 5)
            if source == 'subject':
                keywords = extract_keywords(subject_text, count)
            else:
                keywords = extract_keywords(body_text, count)

            for kw in keywords:
                kw_id = f"{entity_type}:{kw}"
                nodes.append({
                    'id': kw_id,
                    'type': entity_type,
                    'name': kw,
                    'summary': f"关键词: {kw}",
                    'description': '',
                    'tags': [],
                    'complexity': 'simple'
                })
                if entity_type not in entity_map:
                    entity_map[entity_type] = []
                entity_map[entity_type].append({
                    'id': kw_id, 'name': kw, 'keyword': kw,
                    '_rule_name': rule.get('name', '')
                })

        elif rule.get('pattern'):
            # 正则匹配提取
            pattern = rule['pattern']
            group_names = rule.get('groups', [])
            id_tpl = rule.get('id_template', f"{entity_type}:{{0}}")
            name_tpl = rule.get('name_template', '{0}')
            split_char = rule.get('split', '')

            for m in re.finditer(pattern, file_content, re.MULTILINE):
                groups = m.groups()
                if not groups:
                    continue

                # 构建 values dict
                values = {}
                for i, g in enumerate(group_names):
                    if i < len(groups):
                        values[g] = groups[i].strip() if groups[i] else ''
                # 也按索引放入
                for i, g in enumerate(groups):
                    values[str(i)] = g.strip() if g else ''

                # 对可分裂字段处理（如"张三，李四"）
                if split_char and group_names:
                    first_key = group_names[0]
                    first_val = values.get(first_key, '')
                    parts = [p.strip() for p in first_val.split(split_char) if p.strip()]
                else:
                    parts = [values.get(group_names[0], '')] if group_names else []

                for part in parts:
                    item_values = dict(values)
                    if split_char and group_names:
                        item_values[group_names[0]] = part

                    entity_id = _resolve_template(id_tpl, item_values)
                    entity_name = _resolve_template(name_tpl, item_values)

                    # 日期类型自动归一化
                    if entity_type == 'date':
                        entity_id = f"date:{_normalize_date(item_values.get(group_names[0], ''))}"
                        entity_name = _normalize_date(item_values.get(group_names[0], ''))

                    nodes.append({
                        'id': entity_id,
                        'type': entity_type,
                        'name': entity_name,
                        'summary': f"{rule.get('name', entity_type)}: {entity_name}",
                        'description': '',
                        'tags': [],
                        'complexity': 'simple'
                    })
                    if entity_type not in entity_map:
                        entity_map[entity_type] = []
                    item_values['id'] = entity_id
                    item_values['name'] = entity_name
                    item_values['_rule_name'] = rule.get('name', '')
                    entity_map[entity_type].append(item_values)

    # ── 2. 执行关系规则 ──
    for rule in relation_rules:
        source_tpl = rule.get('source_tpl', '')
        target_tpl = rule.get('target_tpl', '')
        edge_type = rule.get('type', 'related')
        weight = rule.get('weight', 0.5)

        # 解析 source/target 模板中的类型引用
        # 例如 source: "person:{email}" → source_type: person, 需要遍历 person 实体
        # 例如 source: "document:{file_path}" → 直接替换

        def resolve_side(tpl, file_path, entity_map, entity_filter=None):
            """解析模板一侧，返回实体 id 列表。entity_filter 限定只取指定规则名的实体。"""
            if '{file_path}' in tpl:
                return [tpl.replace('{file_path}', file_path)]

            m = re.match(r'^(\w+):\{(\w+)\}$', tpl)
            if m:
                ref_type = m.group(1)
                ref_var = m.group(2)
                if ref_type in entity_map:
                    candidates = entity_map[ref_type]
                    if entity_filter:
                        candidates = [e for e in candidates if e.get('_rule_name') == entity_filter]
                    return [entry['id'] for entry in candidates if ref_var in entry]

            return []

        source_filter = rule.get('source_entity', None)
        target_filter = rule.get('target_entity', None)
        source_ids = resolve_side(source_tpl, file_path, entity_map, source_filter)
        target_ids = resolve_side(target_tpl, file_path, entity_map, target_filter)

        for src in source_ids:
            for tgt in target_ids:
                if src and tgt:
                    edges.append({
                        'source': src,
                        'target': tgt,
                        'type': edge_type,
                        'direction': 'forward',
                        'weight': weight
                    })

    return {'nodes': nodes, 'edges': edges}


def run_command(cmd, cwd=None, shell=True):
    try:
        result = subprocess.run(cmd, cwd=cwd, shell=shell, capture_output=True, text=True)
        return result.returncode == 0, result.stdout, result.stderr
    except Exception as e:
        return False, "", str(e)


def get_understand_dir():
    project_root = get_project_root()
    understand_dir = os.path.join(project_root, '.understand-anything', 'Understand-Anything-main', 'understand-anything-plugin')
    return understand_dir


def get_skill_dir():
    understand_dir = get_understand_dir()
    return os.path.join(understand_dir, 'skills', 'understand')


def check_understand_installed():
    understand_dir = get_understand_dir()
    if not os.path.exists(understand_dir):
        print("✗ Understand-Anything 未安装，请先运行: work-graph init")
        return False
    return True


def extract_keywords(text, max_count=10):
    # 过滤常见的无意义词和 URL 片段
    stop_words = {
        'https', 'http', 'com', 'org', 'net', 'html', 'www', 'gle',
        'the', 'and', 'for', 'that', 'this', 'with', 'from', 'have',
        'are', 'was', 'not', 'but', 'all', 'can', 'has', 'had', 'been',
        'will', 'would', 'could', 'should', 'may', 'also', 'its',
        '关于', '以及', '我们', '他们', '这些', '那些', '一些', '一个',
        '可以', '需要', '已经', '没有', '还是', '不会', '什么', '怎么',
        '如果', '因为', '所以', '但是', '或者', '其中', '这个', '那个',
        '进行', '使用', '通过', '根据', '提供', '包括', '其中',
        '部分中的变更以外', '如果您位于',
    }
    words = re.findall(r'[\u4e00-\u9fff]{2,}|[a-zA-Z]{3,}', text)
    word_counts = {}
    for word in words:
        word_lower = word.lower()
        if len(word_lower) < 2:
            continue
        if word_lower in stop_words:
            continue
        # 过滤纯数字和 URL-like 词
        if re.match(r'^[\d_.-]+$', word_lower):
            continue
        word_counts[word_lower] = word_counts.get(word_lower, 0) + 1
    sorted_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)
    return [word for word, count in sorted_words[:max_count]]


def run_ua_pipeline(doc_dir, intermediate_dir):
    print("[Phase 1/7] 扫描项目文件...")
    
    skill_dir = get_skill_dir()
    understand_dir = get_understand_dir()
    
    scan_script = os.path.join(skill_dir, 'scan-project.mjs')
    scan_result_file = os.path.join(doc_dir, '.understand-anything', 'intermediate', 'scan-result.json')
    
    success, stdout, stderr = run_command(
        f"node \"{scan_script}\" \"{doc_dir}\" \"{scan_result_file}\"",
        cwd=understand_dir
    )
    if not success:
        print(f"✗ 扫描失败: {stderr[:300]}")
        return False, None
    
    print(f"✓ 扫描完成")
    
    print("[Phase 1.5/7] 计算语义批次...")
    batch_script = os.path.join(skill_dir, 'compute-batches.mjs')
    
    success, stdout, stderr = run_command(
        f"node \"{batch_script}\" \"{doc_dir}\"",
        cwd=understand_dir
    )
    if not success:
        print(f"✗ 批处理计算失败: {stderr[:300]}")
        return False, None
    
    print(f"✓ 批处理计算完成")
    
    batches_file = os.path.join(doc_dir, '.understand-anything', 'intermediate', 'batches.json')
    if not os.path.exists(batches_file):
        print("✗ 批处理结果文件不存在")
        return False, None
    
    try:
        with open(batches_file, 'r', encoding='utf-8') as f:
            batches = json.load(f)
    except Exception as e:
        print(f"✗ 读取批处理结果失败: {e}")
        return False, None
    
    print("[Phase 2/7] 分析文件结构...")
    extract_script = os.path.join(skill_dir, 'extract-structure.mjs')
    
    for i, batch in enumerate(batches.get('batches', [])):
        batch_files = []
        for file_info in batch.get('files', []):
            batch_files.append({
                'path': file_info.get('path', ''),
                'language': file_info.get('language', ''),
                'sizeLines': file_info.get('sizeLines', 0),
                'fileCategory': file_info.get('fileCategory', '')
            })
        
        input_data = {
            "projectRoot": doc_dir,
            "batchFiles": batch_files,
            "batchImportData": batch.get('batchImportData', {})
        }
        
        input_file = os.path.join(intermediate_dir, f'extract-input-{i}.json')
        output_file = os.path.join(intermediate_dir, f'extract-output-{i}.json')
        
        with open(input_file, 'w', encoding='utf-8') as f:
            json.dump(input_data, f)
        
        success, stdout, stderr = run_command(
            f"node \"{extract_script}\" \"{input_file}\" \"{output_file}\"",
            cwd=understand_dir
        )
        
        if success:
            print(f"  ✓ 批次 {i+1} 结构提取完成")
        else:
            print(f"  ⚠️ 批次 {i+1} 结构提取失败: {stderr[:100]}")
    
    print("✓ 分析完成")
    
    return True, batches


def build_graph_from_ua_output(doc_dir, intermediate_dir, batches):
    print("[Phase 3/7] 构建知识图谱（模板驱动 + UA 结构提取）...")

    nodes = []
    edges = []
    node_ids = set()
    edge_keys = set()

    def add_node(node):
        nid = node['id']
        if nid not in node_ids:
            node_ids.add(nid)
            nodes.append(node)

    def add_edge(edge):
        ek = f"{edge['source']}|{edge['type']}|{edge['target']}"
        if ek not in edge_keys:
            edge_keys.add(ek)
            edges.append(edge)

    for batch_index, batch in enumerate(batches.get('batches', [])):
        extract_output_file = os.path.join(intermediate_dir, f'extract-output-{batch_index}.json')

        if os.path.exists(extract_output_file):
            try:
                with open(extract_output_file, 'r', encoding='utf-8') as f:
                    extract_result = json.load(f)
            except Exception:
                extract_result = None
        else:
            extract_result = None

        if extract_result:
            for result in extract_result.get('results', []):
                file_path = result.get('path', '')
                file_id = f"document:{file_path}"

                # ── 读取完整文档内容 ──
                full_path = os.path.join(doc_dir, file_path)
                try:
                    with open(full_path, 'r', encoding='utf-8') as f:
                        full_content = f.read()
                except Exception:
                    full_content = ""

                # ── 解析 YAML 元数据，确定 file_type ──
                metadata = parse_yaml_metadata(full_content)
                file_type = metadata.get('文件类型', 'document')

                # ── 1. 添加 document 节点 ──
                summary_text = full_content[:300].replace('\n', ' ')
                add_node({
                    "id": file_id,
                    "type": "document",
                    "name": os.path.basename(file_path),
                    "filePath": file_path,
                    "summary": summary_text,
                    "description": "",
                    "tags": [],
                    "complexity": "simple"
                })

                # ── 2. 模板驱动提取 domain 实体和关系 ──
                template_content = load_template(file_type)
                if template_content:
                    print(f"  📄 {file_path} → 类型 '{file_type}'，应用模板提取")
                    tmpl_result = apply_template_engine(
                        template_content, full_content, file_path, file_type
                    )
                    for node in tmpl_result.get('nodes', []):
                        add_node(node)
                    for edge in tmpl_result.get('edges', []):
                        add_edge(edge)
                else:
                    print(f"  ⚠️ {file_path} → 无可用模板，跳过模板提取")

                # ── 3. UA 提取的 sections → section 节点 + contains 边 ──
                if result.get('sections'):
                    for section in result['sections']:
                        heading = section.get('heading', '')
                        if heading and len(heading) >= 2:
                            section_id = f"section:{file_path}#{heading}"
                            add_node({
                                "id": section_id,
                                "type": "concept",
                                "name": heading,
                                "summary": f"章节: {heading}",
                                "description": "",
                                "tags": [],
                                "complexity": "simple"
                            })
                            add_edge({
                                "source": file_id,
                                "target": section_id,
                                "type": "contains",
                                "direction": "forward",
                                "weight": 0.7
                            })

    print(f"✓ 构建完成，共 {len(nodes)} 个节点，{len(edges)} 条边")

    return {
        "nodes": nodes,
        "edges": edges,
        "layers": [],
        "tour": []
    }


def validate_graph(graph):
    print("[Phase 6/7] 验证知识图谱...")
    
    issues = []
    
    if not isinstance(graph.get('nodes'), list):
        issues.append("graph.nodes 不是数组")
        graph['nodes'] = []
    
    if not isinstance(graph.get('edges'), list):
        issues.append("graph.edges 不是数组")
        graph['edges'] = []
    
    node_ids = set()
    for node in graph['nodes']:
        if node.get('id'):
            node_ids.add(node['id'])
    
    for edge in graph['edges']:
        if edge.get('source') not in node_ids:
            issues.append(f"Edge source '{edge['source']}' 不存在")
        if edge.get('target') not in node_ids:
            issues.append(f"Edge target '{edge['target']}' 不存在")
    
    stats = {
        "totalNodes": len(graph['nodes']),
        "totalEdges": len(graph['edges']),
        "nodeTypes": {},
        "edgeTypes": {}
    }
    
    for node in graph['nodes']:
        ntype = node.get('type', 'unknown')
        stats['nodeTypes'][ntype] = stats['nodeTypes'].get(ntype, 0) + 1
    
    for edge in graph['edges']:
        etype = edge.get('type', 'unknown')
        stats['edgeTypes'][etype] = stats['edgeTypes'].get(etype, 0) + 1
    
    if issues:
        print(f"  ⚠️ 发现 {len(issues)} 个问题")
    else:
        print("  ✓ 验证通过")
    
    return True, issues, stats


def phase_save(project_root, doc_dir, graph_out_dir, graph, scan_result=None):
    print("[Phase 7/7] 保存知识图谱...")
    
    graph_out_path = os.path.join(graph_out_dir, 'knowledge-graph.json')
    
    final_graph = {
        "version": "1.0.0",
        "project": {
            "name": "work-graph",
            "languages": [],
            "frameworks": [],
            "description": "知识图谱管理日常工作",
            "analyzedAt": datetime.now().isoformat(),
            "gitCommitHash": ""
        },
        "nodes": graph.get('nodes', []),
        "edges": graph.get('edges', []),
        "layers": graph.get('layers', []),
        "tour": graph.get('tour', [])
    }
    
    with open(graph_out_path, 'w', encoding='utf-8') as f:
        json.dump(final_graph, f, indent=2, ensure_ascii=False)
    
    print(f"✓ 知识图谱已保存到: {graph_out_path}")
    
    return True


def run():
    print("🏗️ 开始构建知识图谱...")
    
    project_root = get_project_root()
    doc_dir = get_doc_dir()
    graph_out_dir = get_graph_out_dir()
    
    if not os.path.exists(doc_dir):
        print("✗ doc目录不存在")
        return False
    
    if not os.listdir(doc_dir):
        print("✗ doc目录为空，请先使用 work-graph read 读取文件")
        return False
    
    if not check_understand_installed():
        return False
    
    intermediate_dir = os.path.join(project_root, '.understand-anything', 'intermediate')
    ensure_dir_exists(intermediate_dir)
    
    temp_scan_dir = os.path.join(doc_dir, '.understand-anything', 'intermediate')
    ensure_dir_exists(temp_scan_dir)
    
    success, batches = run_ua_pipeline(doc_dir, intermediate_dir)
    if not success:
        return False
    
    graph = build_graph_from_ua_output(doc_dir, intermediate_dir, batches)
    
    success, issues, stats = validate_graph(graph)
    if not success:
        return False
    
    success = phase_save(project_root, doc_dir, graph_out_dir, graph)
    if not success:
        return False
    
    print("\n📊 构建完成！")
    print(f"   节点数: {stats['totalNodes']}")
    print(f"   边数: {stats['totalEdges']}")
    print(f"   节点类型: {json.dumps(stats['nodeTypes'], ensure_ascii=False)}")
    print(f"   边类型: {json.dumps(stats['edgeTypes'], ensure_ascii=False)}")
    
    return True


if __name__ == '__main__':
    run()