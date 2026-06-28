# report 提取规则

## 适用类型
report, 报告

## 实体规则

### entity:person:相关人员
pattern: 相关人员[：:]\s*(.+?)(?:[。.]|$)
groups: names
id_template: person:{names}
name_template: {names}
type: person
split: 、

### entity:date:报告日期
pattern: 日期[：:]\s*(.+?)(?:[。.]|$)
groups: date_raw
id_template: date:{date_raw}
name_template: {date_raw}
type: date

### entity:reference:参考链接
pattern: 参考链接[：:]\s*(https?://[^\s。，、]+)
groups: url
id_template: reference:{url}
name_template: {url}
type: reference

### entity:concept:正文概念
source: body
method: keyword_freq
type: concept
count: 10

## 关系规则

### relation:报告提及概念
source: document:{file_path}
target: concept:{keyword}
type: mentions
weight: 0.5

### relation:报告提及人员
source: document:{file_path}
target: person:{names}
type: mentions
weight: 0.7

### relation:报告引用链接
source: document:{file_path}
target: reference:{url}
type: cites
weight: 1.0

### relation:报告日期
source: document:{file_path}
target: date:{date_raw}
type: dated
weight: 1.0
