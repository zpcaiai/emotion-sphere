"""
Security and Privacy Module
包含数据加密、GDPR合规、内容安全等功能
"""

import os
import re
import bleach
from typing import Optional
from datetime import datetime, timedelta
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64

# ── 数据加密 ───────────────────────────────────────────────────

class DataEncryption:
    """敏感数据加密/解密"""
    
    def __init__(self):
        # 从环境变量获取密钥或使用默认（生产环境必须使用强密钥）
        key = os.getenv('ENCRYPTION_KEY')
        if not key:
            # 开发环境：生成临时密钥
            key = Fernet.generate_key().decode()
            print('[security] Warning: Using temporary encryption key')
        
        self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
    
    def encrypt(self, plaintext: str) -> str:
        """加密字符串"""
        if not plaintext:
            return ""
        return self.cipher.encrypt(plaintext.encode()).decode()
    
    def decrypt(self, ciphertext: str) -> str:
        """解密字符串"""
        if not ciphertext:
            return ""
        try:
            return self.cipher.decrypt(ciphertext.encode()).decode()
        except Exception as e:
            print(f'[security] Decryption failed: {e}')
            return ""
    
    def encrypt_dict(self, data: dict) -> dict:
        """递归加密字典中的敏感字段"""
        sensitive_fields = ['content', 'diary', 'note', 'personal', 'private']
        result = {}
        for key, value in data.items():
            if any(field in key.lower() for field in sensitive_fields) and isinstance(value, str):
                result[key] = self.encrypt(value)
            elif isinstance(value, dict):
                result[key] = self.encrypt_dict(value)
            else:
                result[key] = value
        return result
    
    def decrypt_dict(self, data: dict) -> dict:
        """递归解密字典中的敏感字段"""
        result = {}
        for key, value in data.items():
            if isinstance(value, str) and value.startswith('gAAAA'):  # Fernet加密标记
                result[key] = self.decrypt(value)
            elif isinstance(value, dict):
                result[key] = self.decrypt_dict(value)
            else:
                result[key] = value
        return result

# 全局加密实例
encryption = DataEncryption()

# ── 内容安全 ───────────────────────────────────────────────────

class ContentSecurity:
    """内容安全与输入验证"""
    
    # 允许的HTML标签（用于富文本）
    ALLOWED_TAGS = ['b', 'i', 'em', 'strong', 'p', 'br', 'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'blockquote']
    ALLOWED_ATTRIBUTES = {}
    
    # 敏感信息模式
    SENSITIVE_PATTERNS = [
        (r'\b\d{16,19}\b', '[CREDIT_CARD]'),  # 信用卡号
        (r'\b\d{3}-\d{2}-\d{4}\b', '[SSN]'),    # 社保号
        (r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[EMAIL]'),  # 邮箱（可选脱敏）
    ]
    
    @classmethod
    def sanitize_html(cls, text: str) -> str:
        """清理HTML内容，防止XSS"""
        if not text:
            return ""
        return bleach.clean(
            text,
            tags=cls.ALLOWED_TAGS,
            attributes=cls.ALLOWED_ATTRIBUTES,
            strip=True
        )
    
    @classmethod
    def sanitize_input(cls, text: str, max_length: int = 10000) -> str:
        """通用输入清理"""
        if not text:
            return ""
        
        # 限制长度
        text = text[:max_length]
        
        # 移除 null 字节
        text = text.replace('\x00', '')
        
        # 基础XSS防护
        text = bleach.clean(text, tags=[], strip=True)
        
        return text.strip()
    
    @classmethod
    def detect_sensitive_info(cls, text: str) -> list:
        """检测敏感信息"""
        findings = []
        for pattern, label in cls.SENSITIVE_PATTERNS:
            matches = re.finditer(pattern, text)
            for match in matches:
                findings.append({
                    'type': label,
                    'position': (match.start(), match.end()),
                    'preview': text[max(0, match.start()-5):min(len(text), match.end()+5)]
                })
        return findings
    
    @classmethod
    def mask_sensitive_info(cls, text: str) -> str:
        """脱敏敏感信息"""
        for pattern, label in cls.SENSITIVE_PATTERNS:
            text = re.sub(pattern, label, text)
        return text

# ── GDPR 合规 ──────────────────────────────────────────────────

class GDPRCompliance:
    """GDPR 数据保护合规支持"""
    
    @staticmethod
    def anonymize_user_data(user_data: dict) -> dict:
        """匿名化用户数据（保留统计价值，移除个人标识）"""
        anonymized = user_data.copy()
        
        # 移除直接标识符
        for field in ['email', 'nickname', 'openid', 'unionid', 'phone']:
            if field in anonymized:
                anonymized[field] = f'[ANONYMIZED_{field.upper()}]'
        
        # 哈希化ID
        if 'id' in anonymized:
            anonymized['id'] = f'hash_{hash(str(anonymized["id"]))}'
        
        return anonymized
    
    @staticmethod
    def should_anonymize(user_data: dict) -> bool:
        """判断是否应该匿名化（根据删除请求日期）"""
        deletion_requested_at = user_data.get('deletion_requested_at')
        if not deletion_requested_at:
            return False
        
        # 请求删除后30天执行匿名化
        grace_period = timedelta(days=30)
        return datetime.now() - deletion_requested_at > grace_period
    
    @staticmethod
    def get_data_retention_date(created_at: datetime, data_type: str = 'default') -> datetime:
        """计算数据保留截止日期"""
        retention_periods = {
            'emotion_log': timedelta(days=365 * 2),      # 2年
            'psychology_analysis': timedelta(days=365 * 3),  # 3年
            'personal_note': timedelta(days=365),        # 1年
            'audit_log': timedelta(days=365),            # 1年
            'default': timedelta(days=365 * 2),          # 2年
        }
        
        period = retention_periods.get(data_type, retention_periods['default'])
        return created_at + period

# ── 隐私保护工具函数 ──────────────────────────────────────────

def encrypt_sensitive_field(value: str) -> str:
    """加密敏感字段的便捷函数"""
    return encryption.encrypt(value)

def decrypt_sensitive_field(value: str) -> str:
    """解密敏感字段的便捷函数"""
    return encryption.decrypt(value)

def sanitize_user_input(text: str, max_length: int = 10000) -> str:
    """用户输入清理的便捷函数"""
    return ContentSecurity.sanitize_input(text, max_length)

def mask_pii(text: str) -> str:
    """PII脱敏的便捷函数"""
    return ContentSecurity.mask_sensitive_info(text)

# ── 安全配置检查 ───────────────────────────────────────────────

def check_security_configuration():
    """检查安全配置是否到位"""
    issues = []
    
    # 检查加密密钥
    if not os.getenv('ENCRYPTION_KEY'):
        issues.append('ENCRYPTION_KEY not set - using temporary key')
    
    # 检查数据库URL
    if not os.getenv('DATABASE_URL'):
        issues.append('DATABASE_URL not set')
    
    # 检查JWT密钥
    if not os.getenv('JWT_SECRET'):
        issues.append('JWT_SECRET not set - using default (security risk)')
    
    # 检查环境
    env = os.getenv('ENVIRONMENT', 'development')
    if env == 'production':
        # 生产环境额外检查
        if not os.getenv('HTTPS_ONLY'):
            issues.append('HTTPS_ONLY not enforced in production')
    
    return issues

if __name__ == '__main__':
    # 测试加密功能
    test = DataEncryption()
    original = "测试敏感数据"
    encrypted = test.encrypt(original)
    decrypted = test.decrypt(encrypted)
    print(f'Original: {original}')
    print(f'Encrypted: {encrypted}')
    print(f'Decrypted: {decrypted}')
    assert original == decrypted, 'Encryption/Decryption failed'
    print('Security module test passed')
