"""
企业级安全系统
提供身份认证、授权、加密、审计等全方位安全保障
"""

import os
import jwt
import bcrypt
import secrets
import hashlib
import asyncio
import re
from typing import Dict, List, Optional, Any, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import json
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
import pyotp
import aiohttp
from sqlalchemy import Column, String, Boolean, DateTime, Integer, Text

from ..common.logger import get_logger
from ..common.config import get_settings
from ..models import db_manager, Base
from ..services.redis_client import get_redis_client

logger = get_logger(__name__)
settings = get_settings()

# ============================================
# 安全配置
# ============================================

class SecurityLevel(Enum):
    """安全级别"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

class AuthMethod(Enum):
    """认证方法"""
    PASSWORD = "password"
    TOKEN = "token"
    OAUTH = "oauth"
    SAML = "saml"
    MFA = "mfa"
    BIOMETRIC = "biometric"

class Permission(Enum):
    """权限类型"""
    READ = "read"
    WRITE = "write"
    EXECUTE = "execute"
    DELETE = "delete"
    ADMIN = "admin"

@dataclass
class SecurityConfig:
    """安全配置"""
    jwt_secret: str = field(default_factory=lambda: os.getenv("JWT_SECRET", secrets.token_urlsafe(32)))
    jwt_algorithm: str = "HS256"
    jwt_expiry_hours: int = 24
    password_min_length: int = 12
    password_require_special: bool = True
    password_require_numbers: bool = True
    password_require_uppercase: bool = True
    max_login_attempts: int = 5
    lockout_duration_minutes: int = 30
    session_timeout_minutes: int = 60
    enable_mfa: bool = True
    enable_rate_limiting: bool = True
    rate_limit_requests: int = 100
    rate_limit_window_seconds: int = 60
    encryption_key: str = field(default_factory=lambda: Fernet.generate_key().decode())
    audit_enabled: bool = True
    sensitive_data_patterns: List[str] = field(default_factory=lambda: [
        r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',  # Email
        r'\b\d{3}-\d{2}-\d{4}\b',  # SSN
        r'\b\d{16}\b',  # Credit card
        r'api[_-]?key.*?[\'"]([^\'"]+)[\'"]',  # API keys
        r'password.*?[\'"]([^\'"]+)[\'"]',  # Passwords
    ])

# ============================================
# 数据库模型
# ============================================

class User(Base):
    """用户模型"""
    __tablename__ = 'security_users'

    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    mfa_secret = Column(String(255))
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime)
    failed_attempts = Column(Integer, default=0)
    locked_until = Column(DateTime)
    permissions = Column(Text)  # JSON array

class Session(Base):
    """会话模型"""
    __tablename__ = 'security_sessions'

    id = Column(String(64), primary_key=True)
    user_id = Column(Integer, nullable=False, index=True)
    token = Column(String(512), nullable=False)
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)
    last_activity = Column(DateTime, default=datetime.utcnow)
    is_valid = Column(Boolean, default=True)

class AuditLog(Base):
    """审计日志模型"""
    __tablename__ = 'security_audit_logs'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource = Column(String(255))
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    status = Column(String(20))  # success, failure
    details = Column(Text)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

class SecurityIncident(Base):
    """安全事件模型"""
    __tablename__ = 'security_incidents'

    id = Column(Integer, primary_key=True)
    type = Column(String(50), nullable=False, index=True)
    severity = Column(String(20), nullable=False)
    source_ip = Column(String(45))
    user_id = Column(Integer)
    description = Column(Text)
    details = Column(Text)
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime)
    resolution_notes = Column(Text)

# ============================================
# 密码管理器
# ============================================

class PasswordManager:
    """密码管理器"""

    def __init__(self, config: SecurityConfig):
        self.config = config

    def hash_password(self, password: str) -> str:
        """哈希密码"""
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')

    def verify_password(self, password: str, hashed: str) -> bool:
        """验证密码"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))

    def validate_password_strength(self, password: str) -> Tuple[bool, List[str]]:
        """验证密码强度"""
        errors = []

        if len(password) < self.config.password_min_length:
            errors.append(f"Password must be at least {self.config.password_min_length} characters")

        if self.config.password_require_uppercase and not re.search(r'[A-Z]', password):
            errors.append("Password must contain at least one uppercase letter")

        if self.config.password_require_numbers and not re.search(r'\d', password):
            errors.append("Password must contain at least one number")

        if self.config.password_require_special and not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            errors.append("Password must contain at least one special character")

        # 检查常见弱密码
        weak_passwords = ["password", "123456", "qwerty", "admin", "letmein"]
        if password.lower() in weak_passwords:
            errors.append("Password is too common")

        return len(errors) == 0, errors

    def generate_secure_password(self, length: int = 16) -> str:
        """生成安全密码"""
        import string
        characters = string.ascii_letters + string.digits + "!@#$%^&*()_+-=[]{}|;:,.<>?"
        password = ''.join(secrets.choice(characters) for _ in range(length))
        return password

# ============================================
# 令牌管理器
# ============================================

class TokenManager:
    """令牌管理器"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.redis_client = get_redis_client()

    def generate_token(self, user_id: int, **claims) -> str:
        """生成JWT令牌"""
        payload = {
            "user_id": user_id,
            "exp": datetime.utcnow() + timedelta(hours=self.config.jwt_expiry_hours),
            "iat": datetime.utcnow(),
            "jti": secrets.token_urlsafe(16),
            **claims
        }

        token = jwt.encode(
            payload,
            self.config.jwt_secret,
            algorithm=self.config.jwt_algorithm
        )

        return token

    def verify_token(self, token: str) -> Optional[Dict]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(
                token,
                self.config.jwt_secret,
                algorithms=[self.config.jwt_algorithm]
            )

            # 检查是否被撤销
            if asyncio.run(self.is_token_revoked(payload.get("jti"))):
                return None

            return payload

        except jwt.ExpiredSignatureError:
            logger.warning("Token expired")
            return None
        except jwt.InvalidTokenError as e:
            logger.warning(f"Invalid token: {e}")
            return None

    async def revoke_token(self, jti: str):
        """撤销令牌"""
        await self.redis_client.setex(
            f"revoked_token:{jti}",
            self.config.jwt_expiry_hours * 3600,
            "1"
        )

    async def is_token_revoked(self, jti: str) -> bool:
        """检查令牌是否被撤销"""
        return await self.redis_client.exists(f"revoked_token:{jti}")

    def generate_refresh_token(self) -> str:
        """生成刷新令牌"""
        return secrets.token_urlsafe(32)

    def generate_api_key(self, user_id: int) -> str:
        """生成API密钥"""
        prefix = "sk"
        random_part = secrets.token_urlsafe(32)
        checksum = hashlib.sha256(f"{user_id}{random_part}".encode()).hexdigest()[:8]
        return f"{prefix}_{random_part}_{checksum}"

# ============================================
# 多因素认证
# ============================================

class MFAManager:
    """多因素认证管理器"""

    def generate_secret(self) -> str:
        """生成MFA密钥"""
        return pyotp.random_base32()

    def generate_qr_code(self, username: str, secret: str) -> str:
        """生成二维码URL"""
        provisioning_uri = pyotp.totp.TOTP(secret).provisioning_uri(
            name=username,
            issuer_name="Evolution System"
        )
        return provisioning_uri

    def verify_totp(self, secret: str, token: str, window: int = 1) -> bool:
        """验证TOTP令牌"""
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=window)

    def generate_backup_codes(self, count: int = 10) -> List[str]:
        """生成备份码"""
        return [secrets.token_hex(4) for _ in range(count)]

# ============================================
# 加密管理器
# ============================================

class EncryptionManager:
    """加密管理器"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.fernet = Fernet(config.encryption_key.encode() if isinstance(config.encryption_key, str) else config.encryption_key)

    def encrypt(self, data: str) -> str:
        """加密数据"""
        return self.fernet.encrypt(data.encode()).decode()

    def decrypt(self, encrypted_data: str) -> str:
        """解密数据"""
        return self.fernet.decrypt(encrypted_data.encode()).decode()

    def encrypt_file(self, file_path: str, output_path: str):
        """加密文件"""
        with open(file_path, 'rb') as f:
            data = f.read()

        encrypted = self.fernet.encrypt(data)

        with open(output_path, 'wb') as f:
            f.write(encrypted)

    def decrypt_file(self, encrypted_path: str, output_path: str):
        """解密文件"""
        with open(encrypted_path, 'rb') as f:
            encrypted = f.read()

        decrypted = self.fernet.decrypt(encrypted)

        with open(output_path, 'wb') as f:
            f.write(decrypted)

    def hash_data(self, data: str) -> str:
        """哈希数据"""
        return hashlib.sha256(data.encode()).hexdigest()

    def generate_encryption_key(self, password: str, salt: bytes = None) -> bytes:
        """从密码生成加密密钥"""
        if salt is None:
            salt = os.urandom(16)

        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
            backend=default_backend()
        )

        key = base64.urlsafe_b64encode(kdf.derive(password.encode()))
        return key

# ============================================
# 访问控制管理器
# ============================================

class AccessControlManager:
    """访问控制管理器"""

    def __init__(self):
        self.roles = {
            "admin": [Permission.READ, Permission.WRITE, Permission.EXECUTE, Permission.DELETE, Permission.ADMIN],
            "developer": [Permission.READ, Permission.WRITE, Permission.EXECUTE],
            "viewer": [Permission.READ]
        }
        self.redis_client = get_redis_client()

    def check_permission(self, user_id: int, resource: str, permission: Permission) -> bool:
        """检查权限"""
        user_permissions = self.get_user_permissions(user_id)
        return permission in user_permissions

    def get_user_permissions(self, user_id: int) -> List[Permission]:
        """获取用户权限"""
        with db_manager.get_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if user and user.permissions:
                permissions = json.loads(user.permissions)
                return [Permission(p) for p in permissions]
            return []

    def grant_permission(self, user_id: int, permission: Permission):
        """授予权限"""
        with db_manager.get_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if user:
                current_permissions = json.loads(user.permissions) if user.permissions else []
                if permission.value not in current_permissions:
                    current_permissions.append(permission.value)
                    user.permissions = json.dumps(current_permissions)
                    session.commit()

    def revoke_permission(self, user_id: int, permission: Permission):
        """撤销权限"""
        with db_manager.get_session() as session:
            user = session.query(User).filter_by(id=user_id).first()
            if user and user.permissions:
                current_permissions = json.loads(user.permissions)
                if permission.value in current_permissions:
                    current_permissions.remove(permission.value)
                    user.permissions = json.dumps(current_permissions)
                    session.commit()

    async def check_rate_limit(self, user_id: int, action: str) -> bool:
        """检查速率限制"""
        key = f"rate_limit:{user_id}:{action}"
        current = await self.redis_client.incr(key)

        if current == 1:
            await self.redis_client.expire(key, 60)  # 60秒窗口

        return current <= 100  # 每分钟100次

# ============================================
# 审计管理器
# ============================================

class AuditManager:
    """审计管理器"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.redis_client = get_redis_client()

    async def log_action(
        self,
        user_id: int,
        action: str,
        resource: Optional[str] = None,
        status: str = "success",
        details: Optional[Dict] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ):
        """记录审计日志"""
        if not self.config.audit_enabled:
            return

        try:
            with db_manager.get_session() as session:
                audit_log = AuditLog(
                    user_id=user_id,
                    action=action,
                    resource=resource,
                    status=status,
                    details=json.dumps(details) if details else None,
                    ip_address=ip_address,
                    user_agent=user_agent
                )
                session.add(audit_log)
                session.commit()

            # 实时通知
            await self._send_audit_notification(audit_log)

        except Exception as e:
            logger.error(f"Failed to log audit: {e}")

    async def _send_audit_notification(self, audit_log: AuditLog):
        """发送审计通知"""
        notification = {
            "type": "audit",
            "action": audit_log.action,
            "user_id": audit_log.user_id,
            "timestamp": audit_log.timestamp.isoformat()
        }

        await self.redis_client.publish(
            "security:audit",
            json.dumps(notification)
        )

    def get_audit_logs(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """获取审计日志"""
        with db_manager.get_session() as session:
            query = session.query(AuditLog)

            if user_id:
                query = query.filter(AuditLog.user_id == user_id)
            if action:
                query = query.filter(AuditLog.action == action)
            if start_date:
                query = query.filter(AuditLog.timestamp >= start_date)
            if end_date:
                query = query.filter(AuditLog.timestamp <= end_date)

            logs = query.order_by(AuditLog.timestamp.desc()).limit(limit).all()

            return [
                {
                    "id": log.id,
                    "user_id": log.user_id,
                    "action": log.action,
                    "resource": log.resource,
                    "status": log.status,
                    "details": json.loads(log.details) if log.details else None,
                    "timestamp": log.timestamp.isoformat()
                }
                for log in logs
            ]

# ============================================
# 威胁检测器
# ============================================

class ThreatDetector:
    """威胁检测器"""

    def __init__(self):
        self.patterns = {
            "sql_injection": [
                r"(\bunion\b.*\bselect\b|\bselect\b.*\bfrom\b.*\bwhere\b)",
                r"(\bdrop\b|\bdelete\b|\btruncate\b).*\btable\b",
                r"(\bor\b|\band\b)\s*\d+\s*=\s*\d+",
                r"['\"]\s*;\s*(drop|delete|truncate|update|insert)"
            ],
            "xss": [
                r"<script[^>]*>.*?</script>",
                r"javascript:",
                r"on\w+\s*=",
                r"<iframe[^>]*>",
                r"<object[^>]*>"
            ],
            "path_traversal": [
                r"\.\.[\\/]",
                r"\.\.%2[fF]",
                r"%2e%2e[\\/]"
            ],
            "command_injection": [
                r";\s*(ls|cat|wget|curl|bash|sh)\b",
                r"\|\s*(ls|cat|wget|curl|bash|sh)\b",
                r"`[^`]*`",
                r"\$\([^)]*\)"
            ]
        }
        self.redis_client = get_redis_client()

    async def detect_threats(self, input_data: str) -> List[Dict]:
        """检测威胁"""
        threats = []

        for threat_type, patterns in self.patterns.items():
            for pattern in patterns:
                if re.search(pattern, input_data, re.IGNORECASE):
                    threats.append({
                        "type": threat_type,
                        "pattern": pattern,
                        "severity": self._get_threat_severity(threat_type)
                    })

        if threats:
            await self._log_security_incident(threats, input_data)

        return threats

    def _get_threat_severity(self, threat_type: str) -> str:
        """获取威胁严重性"""
        severity_map = {
            "sql_injection": "high",
            "xss": "high",
            "command_injection": "critical",
            "path_traversal": "medium"
        }
        return severity_map.get(threat_type, "low")

    async def _log_security_incident(self, threats: List[Dict], input_data: str):
        """记录安全事件"""
        with db_manager.get_session() as session:
            for threat in threats:
                incident = SecurityIncident(
                    type=threat["type"],
                    severity=threat["severity"],
                    description=f"Detected {threat['type']} attempt",
                    details=json.dumps({
                        "pattern": threat["pattern"],
                        "input": input_data[:500]  # 只保存部分输入
                    })
                )
                session.add(incident)
            session.commit()

    async def check_ip_reputation(self, ip_address: str) -> Dict:
        """检查IP信誉"""
        # 简化实现，实际应该查询威胁情报数据库
        blacklisted_ips = await self._get_blacklisted_ips()

        if ip_address in blacklisted_ips:
            return {
                "reputation": "bad",
                "reason": "IP is blacklisted",
                "threat_level": "high"
            }

        return {
            "reputation": "good",
            "threat_level": "low"
        }

    async def _get_blacklisted_ips(self) -> Set[str]:
        """获取黑名单IP"""
        # 从Redis获取
        blacklist = await self.redis_client.smembers("security:ip_blacklist")
        return set(blacklist) if blacklist else set()

# ============================================
# 数据保护管理器
# ============================================

class DataProtectionManager:
    """数据保护管理器"""

    def __init__(self, config: SecurityConfig):
        self.config = config
        self.encryption_manager = EncryptionManager(config)

    def mask_sensitive_data(self, data: str) -> str:
        """脱敏敏感数据"""
        masked = data

        for pattern in self.config.sensitive_data_patterns:
            matches = re.finditer(pattern, masked, re.IGNORECASE)
            for match in matches:
                sensitive = match.group()
                if len(sensitive) > 4:
                    masked_value = sensitive[:2] + "*" * (len(sensitive) - 4) + sensitive[-2:]
                else:
                    masked_value = "*" * len(sensitive)
                masked = masked.replace(sensitive, masked_value)

        return masked

    def encrypt_field(self, data: str) -> str:
        """加密字段"""
        return self.encryption_manager.encrypt(data)

    def decrypt_field(self, encrypted_data: str) -> str:
        """解密字段"""
        return self.encryption_manager.decrypt(encrypted_data)

    def generate_data_retention_policy(self) -> Dict:
        """生成数据保留策略"""
        return {
            "personal_data": {
                "retention_days": 365,
                "anonymize_after": 180,
                "delete_after": 365
            },
            "audit_logs": {
                "retention_days": 2555,  # 7年
                "archive_after": 365
            },
            "session_data": {
                "retention_days": 30,
                "delete_after": 30
            }
        }

# ============================================
# 企业安全管理器
# ============================================

class EnterpriseSecurityManager:
    """企业安全管理器"""

    def __init__(self, config: Optional[SecurityConfig] = None):
        """初始化安全管理器"""
        self.config = config or SecurityConfig()
        self.password_manager = PasswordManager(self.config)
        self.token_manager = TokenManager(self.config)
        self.mfa_manager = MFAManager()
        self.encryption_manager = EncryptionManager(self.config)
        self.access_control = AccessControlManager()
        self.audit_manager = AuditManager(self.config)
        self.threat_detector = ThreatDetector()
        self.data_protection = DataProtectionManager(self.config)
        self.redis_client = get_redis_client()

    async def authenticate(
        self,
        username: str,
        password: str,
        mfa_token: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None
    ) -> Optional[Dict]:
        """用户认证"""
        try:
            with db_manager.get_session() as session:
                user = session.query(User).filter_by(username=username).first()

                if not user:
                    await self.audit_manager.log_action(
                        user_id=0,
                        action="login_attempt",
                        status="failure",
                        details={"reason": "user_not_found"},
                        ip_address=ip_address
                    )
                    return None

                # 检查账户是否被锁定
                if user.locked_until and user.locked_until > datetime.utcnow():
                    return None

                # 验证密码
                if not self.password_manager.verify_password(password, user.password_hash):
                    user.failed_attempts += 1

                    # 锁定账户
                    if user.failed_attempts >= self.config.max_login_attempts:
                        user.locked_until = datetime.utcnow() + timedelta(
                            minutes=self.config.lockout_duration_minutes
                        )

                    session.commit()

                    await self.audit_manager.log_action(
                        user_id=user.id,
                        action="login_attempt",
                        status="failure",
                        details={"reason": "invalid_password"},
                        ip_address=ip_address
                    )
                    return None

                # 验证MFA
                if self.config.enable_mfa and user.mfa_secret:
                    if not mfa_token or not self.mfa_manager.verify_totp(user.mfa_secret, mfa_token):
                        await self.audit_manager.log_action(
                            user_id=user.id,
                            action="login_attempt",
                            status="failure",
                            details={"reason": "invalid_mfa"},
                            ip_address=ip_address
                        )
                        return None

                # 重置失败尝试
                user.failed_attempts = 0
                user.last_login = datetime.utcnow()
                session.commit()

                # 生成令牌
                token = self.token_manager.generate_token(
                    user_id=user.id,
                    username=user.username,
                    is_admin=user.is_admin
                )

                # 创建会话
                session_id = await self._create_session(
                    user_id=user.id,
                    token=token,
                    ip_address=ip_address,
                    user_agent=user_agent
                )

                await self.audit_manager.log_action(
                    user_id=user.id,
                    action="login",
                    status="success",
                    ip_address=ip_address
                )

                return {
                    "user_id": user.id,
                    "username": user.username,
                    "token": token,
                    "session_id": session_id,
                    "is_admin": user.is_admin
                }

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return None

    async def _create_session(
        self,
        user_id: int,
        token: str,
        ip_address: Optional[str],
        user_agent: Optional[str]
    ) -> str:
        """创建会话"""
        session_id = secrets.token_urlsafe(32)

        with db_manager.get_session() as session:
            new_session = Session(
                id=session_id,
                user_id=user_id,
                token=token,
                ip_address=ip_address,
                user_agent=user_agent,
                expires_at=datetime.utcnow() + timedelta(hours=self.config.jwt_expiry_hours)
            )
            session.add(new_session)
            session.commit()

        # 缓存会话
        await self.redis_client.setex(
            f"session:{session_id}",
            self.config.session_timeout_minutes * 60,
            json.dumps({
                "user_id": user_id,
                "token": token
            })
        )

        return session_id

    async def validate_session(self, session_id: str) -> Optional[Dict]:
        """验证会话"""
        # 先检查缓存
        cached = await self.redis_client.get(f"session:{session_id}")
        if cached:
            return json.loads(cached)

        # 检查数据库
        with db_manager.get_session() as session:
            db_session = session.query(Session).filter_by(
                id=session_id,
                is_valid=True
            ).first()

            if db_session and db_session.expires_at > datetime.utcnow():
                # 更新最后活动时间
                db_session.last_activity = datetime.utcnow()
                session.commit()

                return {
                    "user_id": db_session.user_id,
                    "token": db_session.token
                }

        return None

    async def revoke_session(self, session_id: str):
        """撤销会话"""
        with db_manager.get_session() as session:
            db_session = session.query(Session).filter_by(id=session_id).first()
            if db_session:
                db_session.is_valid = False
                session.commit()

        await self.redis_client.delete(f"session:{session_id}")

    async def perform_security_scan(self, code: str) -> Dict:
        """执行安全扫描"""
        results = {
            "vulnerabilities": [],
            "warnings": [],
            "passed": True
        }

        # 检测威胁
        threats = await self.threat_detector.detect_threats(code)
        if threats:
            results["vulnerabilities"].extend(threats)
            results["passed"] = False

        # 检查硬编码凭据
        credential_patterns = [
            r'password\s*=\s*["\'][^"\']+["\']',
            r'api_key\s*=\s*["\'][^"\']+["\']',
            r'secret\s*=\s*["\'][^"\']+["\']'
        ]

        for pattern in credential_patterns:
            if re.search(pattern, code, re.IGNORECASE):
                results["warnings"].append({
                    "type": "hardcoded_credentials",
                    "message": "Possible hardcoded credentials detected"
                })

        return results

    def get_security_headers(self) -> Dict[str, str]:
        """获取安全头部"""
        return {
            "X-Content-Type-Options": "nosniff",
            "X-Frame-Options": "DENY",
            "X-XSS-Protection": "1; mode=block",
            "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
            "Content-Security-Policy": "default-src 'self'",
            "Referrer-Policy": "strict-origin-when-cross-origin",
            "Permissions-Policy": "geolocation=(), microphone=(), camera=()"
        }

    async def get_security_status(self) -> Dict:
        """获取安全状态"""
        with db_manager.get_session() as session:
            # 统计数据
            total_users = session.query(User).count()
            active_sessions = session.query(Session).filter(
                Session.is_valid == True,
                Session.expires_at > datetime.utcnow()
            ).count()

            recent_incidents = session.query(SecurityIncident).filter(
                SecurityIncident.detected_at > datetime.utcnow() - timedelta(days=1),
                SecurityIncident.resolved == False
            ).count()

            recent_failures = session.query(AuditLog).filter(
                AuditLog.status == "failure",
                AuditLog.timestamp > datetime.utcnow() - timedelta(hours=1)
            ).count()

        return {
            "status": "secure" if recent_incidents == 0 else "warning",
            "total_users": total_users,
            "active_sessions": active_sessions,
            "recent_incidents": recent_incidents,
            "recent_failures": recent_failures,
            "mfa_enabled": self.config.enable_mfa,
            "encryption_enabled": True,
            "audit_enabled": self.config.audit_enabled
        }

# ============================================
# 单例实例
# ============================================

_security_manager_instance: Optional[EnterpriseSecurityManager] = None

def get_security_manager() -> EnterpriseSecurityManager:
    """获取安全管理器单例"""
    global _security_manager_instance
    if _security_manager_instance is None:
        _security_manager_instance = EnterpriseSecurityManager()
    return _security_manager_instance