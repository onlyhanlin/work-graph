# mail 提取规则

## 适用类型
mail, email

## 实体规则

### entity:person:发件人
pattern: ^发件人:\s*(.+?)\s*<(.+?)>$
groups: name, email
id_template: person:{email}
name_template: {name}
type: person

### entity:person:收件人
pattern: ^收件人:\s*(.+)$
groups: email
id_template: person:{email}
name_template: {email}
type: person

### entity:date:邮件日期
pattern: ^日期:\s*(.+)$
groups: date_raw
id_template: date:{date_raw}
name_template: {date_raw}
type: date

### entity:concept:主题概念
source: subject
method: keyword_freq
type: concept
count: 5

### entity:concept:正文概念
source: body
method: keyword_freq
type: concept
count: 8

## 关系规则

### relation:发件人发送
source_entity: 发件人
source: person:{email}
target: document:{file_path}
type: sent
weight: 1.0

### relation:邮件接收
source: document:{file_path}
target_entity: 收件人
target: person:{email}
type: received
weight: 1.0

### relation:邮件日期
source: document:{file_path}
target: date:{date_raw}
type: dated
weight: 1.0

### relation:主题提及概念
source: document:{file_path}
target: concept:{keyword}
type: mentions
weight: 0.5

### relation:正文提及概念
source: document:{file_path}
target: concept:{keyword}
type: mentions
weight: 0.3
