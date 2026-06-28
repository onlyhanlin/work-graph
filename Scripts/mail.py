import os
import sys
import imaplib
import email
from email.header import decode_header
from email.utils import parseaddr
from datetime import datetime
from utils import create_markdown_with_metadata, get_project_root, ensure_dir_exists


IMAP_SERVERS = {
    'outlook': 'outlook.office365.com',
    'gmail': 'imap.gmail.com',
    'yahoo': 'imap.mail.yahoo.com',
    'qq': 'imap.qq.com',
    '163': 'imap.163.com',
    '126': 'imap.126.com'
}


def load_mail_config():
    config_path = os.path.join(get_project_root(), 'mail_config.json')
    
    if os.path.exists(config_path):
        import json
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    return {
        'server': os.environ.get('MAIL_SERVER', ''),
        'email': os.environ.get('MAIL_EMAIL', ''),
        'password': os.environ.get('MAIL_PASSWORD', '')
    }


def get_imap_server(mail_address):
    domain = mail_address.split('@')[-1].lower()
    
    domain_mapping = {
        'outlook.com': 'outlook',
        'hotmail.com': 'outlook',
        'live.com': 'outlook',
        'gmail.com': 'gmail',
        'yahoo.com': 'yahoo',
        'qq.com': 'qq',
        '163.com': '163',
        '126.com': '126'
    }
    
    provider = domain_mapping.get(domain)
    
    if provider:
        return IMAP_SERVERS[provider]
    
    return None


def decode_str(header_value):
    if header_value is None:
        return ""
    
    decoded_parts = decode_header(header_value)
    result = []
    
    for part, encoding in decoded_parts:
        if isinstance(part, bytes):
            if encoding:
                try:
                    result.append(part.decode(encoding))
                except:
                    result.append(part.decode('utf-8', errors='ignore'))
            else:
                result.append(part.decode('utf-8', errors='ignore'))
        else:
            result.append(str(part))
    
    return ''.join(result)


def get_email_body(msg):
    body = ""
    
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition"))
            
            if "attachment" in content_disposition:
                continue
            
            try:
                payload = part.get_payload(decode=True)
                if payload:
                    charset = part.get_content_charset() or 'utf-8'
                    try:
                        text = payload.decode(charset, errors='ignore')
                    except:
                        text = payload.decode('utf-8', errors='ignore')
                    
                    if content_type == 'text/html':
                        from bs4 import BeautifulSoup
                        soup = BeautifulSoup(text, 'lxml')
                        body += soup.get_text(separator='\n') + '\n'
                    elif content_type == 'text/plain':
                        body += text + '\n'
            except:
                continue
    else:
        content_type = msg.get_content_type()
        try:
            payload = msg.get_payload(decode=True)
            if payload:
                charset = msg.get_content_charset() or 'utf-8'
                try:
                    text = payload.decode(charset, errors='ignore')
                except:
                    text = payload.decode('utf-8', errors='ignore')
                
                if content_type == 'text/html':
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(text, 'lxml')
                    body = soup.get_text(separator='\n')
                else:
                    body = text
        except:
            body = msg.get_payload()
    
    return body


def extract_email_info(msg):
    subject = decode_str(msg.get('Subject', ''))
    from_addr = decode_str(msg.get('From', ''))
    to_addr = decode_str(msg.get('To', ''))
    date_str = msg.get('Date', '')
    
    try:
        date_tuple = email.utils.parsedate(date_str)
        if date_tuple:
            date = datetime(*date_tuple[:6])
            formatted_date = date.strftime('%Y-%m-%d %H:%M:%S')
        else:
            formatted_date = date_str
    except:
        formatted_date = date_str
    
    message_id = msg.get('Message-ID', '')
    
    return {
        'subject': subject,
        'from': from_addr,
        'to': to_addr,
        'date': formatted_date,
        'message_id': message_id
    }


def connect_mailbox(server, email_addr, password):
    try:
        mail = imaplib.IMAP4_SSL(server)
        mail.login(email_addr, password)
        return mail
    except imaplib.IMAP4.error as e:
        print(f"✗ 邮箱连接失败: {e}")
        return None
    except Exception as e:
        print(f"✗ 连接错误: {e}")
        return None


def search_email_by_id(mail, message_id):
    mail.select('INBOX')
    
    status, messages = mail.search(None, 'ALL')
    
    if status != 'OK':
        return None
    
    email_ids = messages[0].split()
    
    for email_id in email_ids:
        status, msg_data = mail.fetch(email_id, '(RFC822)')
        
        if status != 'OK':
            continue
        
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                
                if msg.get('Message-ID') == message_id:
                    return msg, email_id
    
    return None


def search_email_by_subject(mail, subject_keyword, reverse=True):
    mail.select('INBOX')
    
    status, messages = mail.search(None, 'ALL')
    
    if status != 'OK':
        return []
    
    email_ids = messages[0].split()
    
    if reverse:
        email_ids = list(reversed(email_ids))
    
    results = []
    
    for email_id in email_ids:
        status, msg_data = mail.fetch(email_id, '(RFC822)')
        
        if status != 'OK':
            continue
        
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                msg_subject = decode_str(msg.get('Subject', ''))
                
                if subject_keyword.lower() in msg_subject.lower():
                    results.append((msg, email_id))
    
    return results


def get_latest_emails(mail, count=10, reverse=True):
    mail.select('INBOX')
    
    status, messages = mail.search(None, 'ALL')
    
    if status != 'OK':
        return []
    
    email_ids = messages[0].split()
    
    if reverse:
        email_ids = list(reversed(email_ids))
    
    email_ids = email_ids[:count]
    
    results = []
    
    for email_id in email_ids:
        status, msg_data = mail.fetch(email_id, '(RFC822)')
        
        if status != 'OK':
            continue
        
        for response_part in msg_data:
            if isinstance(response_part, tuple):
                msg = email.message_from_bytes(response_part[1])
                results.append((msg, email_id))
    
    return results


def convert_email_to_markdown(msg, mail_source="imap"):
    info = extract_email_info(msg)
    body = get_email_body(msg)
    
    md_content = f"""# {info['subject']}

## 基本信息

- **发件人**: {info['from']}
- **收件人**: {info['to']}
- **日期**: {info['date']}
- **Message-ID**: {info['message_id']}
- **来源**: {mail_source}

## 内容

{body}
"""
    
    return md_content, info


def read_single_email(message_id=None, subject=None, latest=False, count=1):
    config = load_mail_config()
    
    server = config.get('server')
    email_addr = config.get('email')
    password = config.get('password')
    
    if not all([server, email_addr, password]):
        if email_addr and not server:
            server = get_imap_server(email_addr)
        
        if not all([server, email_addr, password]):
            print("✗ 缺少邮箱配置，请设置 mail_config.json 或环境变量")
            print("  环境变量: MAIL_SERVER, MAIL_EMAIL, MAIL_PASSWORD")
            return False
    
    print(f"📬 连接邮箱: {email_addr}")
    
    mail = connect_mailbox(server, email_addr, password)
    
    if not mail:
        return False
    
    try:
        emails = []
        
        if message_id:
            print(f"🔍 搜索邮件 (Message-ID): {message_id}")
            result = search_email_by_id(mail, message_id)
            if result:
                emails = [result]
        
        elif subject:
            print(f"🔍 搜索邮件 (主题): {subject}")
            emails = search_email_by_subject(mail, subject, reverse=True)
        
        elif latest:
            print(f"📥 获取最近 {count} 封邮件")
            emails = get_latest_emails(mail, count, reverse=True)
        
        else:
            print("✗ 请指定邮件搜索条件: -id (邮件ID) 或 -subject (主题)")
            return False
        
        if not emails:
            print("✗ 未找到匹配的邮件")
            return False
        
        for msg, email_id in emails:
            md_content, info = convert_email_to_markdown(msg, f"imap://{email_addr}")
            
            md_path = create_markdown_with_metadata(
                md_content, 
                f"imap://{email_addr}/{info['message_id']}", 
                'email'
            )
            
            print(f"✅ 邮件已保存: {md_path}")
            print(f"   主题: {info['subject']}")
            print(f"   发件人: {info['from']}")
            print(f"   日期: {info['date']}")
        
        return True
    
    finally:
        mail.close()
        mail.logout()


def list_emails(count=10):
    config = load_mail_config()
    
    server = config.get('server')
    email_addr = config.get('email')
    password = config.get('password')
    
    if not all([server, email_addr, password]):
        if email_addr and not server:
            server = get_imap_server(email_addr)
        
        if not all([server, email_addr, password]):
            print("✗ 缺少邮箱配置，请设置 mail_config.json 或环境变量")
            return False
    
    print(f"📬 连接邮箱: {email_addr}")
    
    mail = connect_mailbox(server, email_addr, password)
    
    if not mail:
        return False
    
    try:
        emails = get_latest_emails(mail, count, reverse=True)
        
        print(f"\n📧 最近 {len(emails)} 封邮件:")
        print("-" * 60)
        
        for i, (msg, email_id) in enumerate(emails, 1):
            info = extract_email_info(msg)
            print(f"{i}. {info['subject']}")
            print(f"   发件人: {info['from']}")
            print(f"   日期: {info['date']}")
            print(f"   ID: {info['message_id']}")
            print("-" * 60)
        
        return True
    
    finally:
        mail.close()
        mail.logout()


def run(args):
    if not args:
        print("用法: work-graph read -mail [-list <数量>] [-id <邮件ID>] [-subject <主题>] [-latest <数量>]")
        return False
    
    i = 0
    while i < len(args):
        arg = args[i]
        
        if arg == '-list':
            count = int(args[i + 1]) if i + 1 < len(args) else 10
            return list_emails(count)
        
        elif arg == '-id':
            if i + 1 >= len(args):
                print("✗ 请提供邮件ID")
                return False
            message_id = args[i + 1]
            return read_single_email(message_id=message_id)
        
        elif arg == '-subject':
            if i + 1 >= len(args):
                print("✗ 请提供邮件主题关键词")
                return False
            subject = args[i + 1]
            return read_single_email(subject=subject)
        
        elif arg == '-latest':
            count = int(args[i + 1]) if i + 1 < len(args) else 1
            return read_single_email(latest=True, count=count)
        
        i += 1
    
    print("用法: work-graph read -mail [-list <数量>] [-id <邮件ID>] [-subject <主题>] [-latest <数量>]")
    return False


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print("用法: python mail.py [-list <数量>] [-id <邮件ID>] [-subject <主题>] [-latest <数量>]")
        sys.exit(1)
    
    run(sys.argv[1:])