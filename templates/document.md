# document 提取规则（兜底）

## 适用类型
*

## 实体规则

### entity:concept:正文概念
source: body
method: keyword_freq
type: concept
count: 10

## 关系规则

### relation:文档提及概念
source: document:{file_path}
target: concept:{keyword}
type: mentions
weight: 0.5
