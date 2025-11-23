"""
智能运维系统
提供自动化运维、健康监控、故障诊断和自愈能力
"""

import os
import sys
import time
import asyncio
import psutil
import docker
import kubernetes
import subprocess
from typing import Dict, List, Optional, Any, Callable, Tuple, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
from collections import defaultdict, deque
import json
import yaml
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import prometheus_client
from prometheus_client import Counter, Gauge, Histogram, Summary
import logging
from logging.handlers import RotatingFileHandler

from ..common.logger import get_logger
from ..common.config import get_settings
from ..models import db_manager, SystemHealth, Incident, MaintenanceTask
from ..services.redis_client import get_redis_client
from ..services.ai_model_manager import get_model_manager, ModelCapability

logger = get_logger(__name__)
settings = get_settings()

# ============================================
# 运维配置
# ============================================

class ServiceStatus(Enum):
    """服务状态"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"

class IncidentSeverity(Enum):
    """事件严重性"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"

class MaintenanceType(Enum):
    """维护类型"""
    BACKUP = "backup"
    UPDATE = "update"
    CLEANUP = "cleanup"
    RESTART = "restart"
    SCALE = "scale"
    ROLLBACK = "rollback"

@dataclass
class OperationsConfig:
    """运维配置"""
    health_check_interval: int = 30  # 秒
    metrics_collection_interval: int = 10
    log_rotation_size_mb: int = 100
    log_retention_days: int = 30
    backup_retention_days: int = 7
    auto_restart_enabled: bool = True
    auto_scale_enabled: bool = True
    max_restart_attempts: int = 3
    alert_email_enabled: bool = True
    alert_slack_enabled: bool = False
    alert_threshold_cpu: float = 80.0
    alert_threshold_memory: float = 85.0
    alert_threshold_disk: float = 90.0
    alert_threshold_response_time: int = 1000  # ms
    maintenance_window_start: str = "02:00"
    maintenance_window_end: str = "05:00"
    docker_enabled: bool = True
    kubernetes_enabled: bool = False

@dataclass
class HealthCheck:
    """健康检查"""
    name: str
    endpoint: str
    method: str = "GET"
    timeout: int = 5
    expected_status: int = 200
    interval: int = 30
    retries: int = 3

@dataclass
class Alert:
    """告警"""
    id: str
    severity: IncidentSeverity
    title: str
    description: str
    service: str
    timestamp: datetime = field(default_factory=datetime.now)
    resolved: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)

# ============================================
# 监控管理器
# ============================================

class MonitoringManager:
    """监控管理器"""

    def __init__(self, config: OperationsConfig):
        self.config = config
        self.metrics = {}
        self.health_checks = {}
        self.service_status = defaultdict(lambda: ServiceStatus.UNKNOWN)

        # Prometheus指标
        self.request_count = Counter('requests_total', 'Total requests', ['method', 'endpoint'])
        self.request_duration = Histogram('request_duration_seconds', 'Request duration', ['method', 'endpoint'])
        self.error_count = Counter('errors_total', 'Total errors', ['type'])
        self.cpu_usage = Gauge('cpu_usage_percent', 'CPU usage percentage')
        self.memory_usage = Gauge('memory_usage_percent', 'Memory usage percentage')
        self.disk_usage = Gauge('disk_usage_percent', 'Disk usage percentage')
        self.active_connections = Gauge('active_connections', 'Active connections')

    async def start_monitoring(self):
        """启动监控"""
        asyncio.create_task(self._collect_metrics())
        asyncio.create_task(self._check_health())

    async def _collect_metrics(self):
        """收集指标"""
        while True:
            try:
                # 系统指标
                cpu_percent = psutil.cpu_percent(interval=1)
                memory_percent = psutil.virtual_memory().percent
                disk_percent = psutil.disk_usage('/').percent

                # 更新Prometheus指标
                self.cpu_usage.set(cpu_percent)
                self.memory_usage.set(memory_percent)
                self.disk_usage.set(disk_percent)

                # 存储指标
                metrics = {
                    "timestamp": datetime.now().isoformat(),
                    "cpu_percent": cpu_percent,
                    "memory_percent": memory_percent,
                    "disk_percent": disk_percent,
                    "network": self._get_network_metrics(),
                    "processes": self._get_process_metrics()
                }

                await self._store_metrics(metrics)

            except Exception as e:
                logger.error(f"Error collecting metrics: {e}")

            await asyncio.sleep(self.config.metrics_collection_interval)

    def _get_network_metrics(self) -> Dict:
        """获取网络指标"""
        net_io = psutil.net_io_counters()
        return {
            "bytes_sent": net_io.bytes_sent,
            "bytes_recv": net_io.bytes_recv,
            "packets_sent": net_io.packets_sent,
            "packets_recv": net_io.packets_recv,
            "errors_in": net_io.errin,
            "errors_out": net_io.errout
        }

    def _get_process_metrics(self) -> List[Dict]:
        """获取进程指标"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                if proc.info['cpu_percent'] > 10 or proc.info['memory_percent'] > 10:
                    processes.append(proc.info)
            except:
                pass
        return processes

    async def _store_metrics(self, metrics: Dict):
        """存储指标"""
        redis_client = get_redis_client()
        await redis_client.zadd(
            "metrics:system",
            {json.dumps(metrics): time.time()}
        )

        # 只保留最近1小时的数据
        cutoff = time.time() - 3600
        await redis_client.zremrangebyscore("metrics:system", 0, cutoff)

    async def _check_health(self):
        """健康检查"""
        while True:
            for name, check in self.health_checks.items():
                status = await self._perform_health_check(check)
                self.service_status[name] = status

            await asyncio.sleep(self.config.health_check_interval)

    async def _perform_health_check(self, check: HealthCheck) -> ServiceStatus:
        """执行健康检查"""
        for attempt in range(check.retries):
            try:
                response = requests.request(
                    check.method,
                    check.endpoint,
                    timeout=check.timeout
                )

                if response.status_code == check.expected_status:
                    return ServiceStatus.HEALTHY

                return ServiceStatus.DEGRADED

            except requests.exceptions.Timeout:
                logger.warning(f"Health check timeout for {check.name}")
            except requests.exceptions.RequestException as e:
                logger.error(f"Health check failed for {check.name}: {e}")

            if attempt < check.retries - 1:
                await asyncio.sleep(2)

        return ServiceStatus.UNHEALTHY

    def register_health_check(self, check: HealthCheck):
        """注册健康检查"""
        self.health_checks[check.name] = check

    def get_service_status(self) -> Dict[str, str]:
        """获取服务状态"""
        return {name: status.value for name, status in self.service_status.items()}

# ============================================
# 告警管理器
# ============================================

class AlertManager:
    """告警管理器"""

    def __init__(self, config: OperationsConfig):
        self.config = config
        self.active_alerts: Dict[str, Alert] = {}
        self.alert_history: deque = deque(maxlen=1000)
        self.redis_client = get_redis_client()

    async def create_alert(
        self,
        severity: IncidentSeverity,
        title: str,
        description: str,
        service: str,
        metadata: Dict = None
    ) -> Alert:
        """创建告警"""
        alert_id = f"alert_{int(time.time() * 1000)}"

        alert = Alert(
            id=alert_id,
            severity=severity,
            title=title,
            description=description,
            service=service,
            metadata=metadata or {}
        )

        self.active_alerts[alert_id] = alert
        self.alert_history.append(alert)

        # 发送通知
        await self._send_notifications(alert)

        # 存储到数据库
        await self._store_alert(alert)

        # 自动修复
        if severity in [IncidentSeverity.CRITICAL, IncidentSeverity.HIGH]:
            asyncio.create_task(self._auto_remediate(alert))

        return alert

    async def _send_notifications(self, alert: Alert):
        """发送通知"""
        # Email通知
        if self.config.alert_email_enabled:
            await self._send_email_alert(alert)

        # Slack通知
        if self.config.alert_slack_enabled:
            await self._send_slack_alert(alert)

        # Redis发布
        await self.redis_client.publish(
            f"alerts:{alert.severity.value}",
            json.dumps({
                "id": alert.id,
                "title": alert.title,
                "description": alert.description,
                "service": alert.service,
                "timestamp": alert.timestamp.isoformat()
            })
        )

    async def _send_email_alert(self, alert: Alert):
        """发送邮件告警"""
        try:
            msg = MIMEMultipart()
            msg['From'] = settings.alert_email_from
            msg['To'] = settings.alert_email_to
            msg['Subject'] = f"[{alert.severity.value.upper()}] {alert.title}"

            body = f"""
            Alert Details:
            --------------
            Service: {alert.service}
            Severity: {alert.severity.value}
            Time: {alert.timestamp}

            Description:
            {alert.description}

            Metadata:
            {json.dumps(alert.metadata, indent=2)}
            """

            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
                server.starttls()
                server.login(settings.smtp_user, settings.smtp_password)
                server.send_message(msg)

        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")

    async def _send_slack_alert(self, alert: Alert):
        """发送Slack告警"""
        try:
            webhook_url = settings.slack_webhook_url

            color_map = {
                IncidentSeverity.CRITICAL: "danger",
                IncidentSeverity.HIGH: "warning",
                IncidentSeverity.MEDIUM: "warning",
                IncidentSeverity.LOW: "good",
                IncidentSeverity.INFO: "#36a64f"
            }

            payload = {
                "attachments": [{
                    "color": color_map.get(alert.severity, "warning"),
                    "title": alert.title,
                    "text": alert.description,
                    "fields": [
                        {"title": "Service", "value": alert.service, "short": True},
                        {"title": "Severity", "value": alert.severity.value, "short": True},
                        {"title": "Time", "value": alert.timestamp.isoformat(), "short": False}
                    ]
                }]
            }

            requests.post(webhook_url, json=payload)

        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")

    async def _store_alert(self, alert: Alert):
        """存储告警"""
        try:
            with db_manager.get_session() as session:
                incident = Incident(
                    severity=alert.severity.value,
                    title=alert.title,
                    description=alert.description,
                    service=alert.service,
                    metadata=json.dumps(alert.metadata)
                )
                session.add(incident)
                session.commit()
        except Exception as e:
            logger.error(f"Failed to store alert: {e}")

    async def _auto_remediate(self, alert: Alert):
        """自动修复"""
        remediation_map = {
            "high_cpu": self._remediate_high_cpu,
            "high_memory": self._remediate_high_memory,
            "service_down": self._remediate_service_down,
            "disk_full": self._remediate_disk_full
        }

        alert_type = alert.metadata.get("type")
        if alert_type in remediation_map:
            await remediation_map[alert_type](alert)

    async def _remediate_high_cpu(self, alert: Alert):
        """修复高CPU"""
        logger.info("Attempting to remediate high CPU usage")
        # 可以实现进程优先级调整、负载均衡等
        pass

    async def _remediate_high_memory(self, alert: Alert):
        """修复高内存"""
        logger.info("Attempting to remediate high memory usage")
        # 可以实现内存清理、进程重启等
        import gc
        gc.collect()

    async def _remediate_service_down(self, alert: Alert):
        """修复服务宕机"""
        service_name = alert.metadata.get("service_name")
        if service_name and self.config.auto_restart_enabled:
            logger.info(f"Attempting to restart service: {service_name}")
            # 实现服务重启逻辑
            pass

    async def _remediate_disk_full(self, alert: Alert):
        """修复磁盘满"""
        logger.info("Attempting to clean up disk space")
        # 实现日志清理、临时文件清理等
        pass

    async def resolve_alert(self, alert_id: str):
        """解决告警"""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            del self.active_alerts[alert_id]

            # 更新数据库
            with db_manager.get_session() as session:
                incident = session.query(Incident).filter_by(id=alert_id).first()
                if incident:
                    incident.resolved = True
                    incident.resolved_at = datetime.now()
                    session.commit()

# ============================================
# 日志管理器
# ============================================

class LogManager:
    """日志管理器"""

    def __init__(self, config: OperationsConfig):
        self.config = config
        self.loggers = {}
        self._setup_loggers()

    def _setup_loggers(self):
        """设置日志记录器"""
        # 应用日志
        app_logger = logging.getLogger("application")
        app_handler = RotatingFileHandler(
            "logs/application.log",
            maxBytes=self.config.log_rotation_size_mb * 1024 * 1024,
            backupCount=10
        )
        app_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        )
        app_logger.addHandler(app_handler)
        self.loggers["application"] = app_logger

        # 错误日志
        error_logger = logging.getLogger("error")
        error_handler = RotatingFileHandler(
            "logs/error.log",
            maxBytes=self.config.log_rotation_size_mb * 1024 * 1024,
            backupCount=10
        )
        error_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s - %(exc_info)s')
        )
        error_logger.addHandler(error_handler)
        self.loggers["error"] = error_logger

        # 访问日志
        access_logger = logging.getLogger("access")
        access_handler = RotatingFileHandler(
            "logs/access.log",
            maxBytes=self.config.log_rotation_size_mb * 1024 * 1024,
            backupCount=10
        )
        access_handler.setFormatter(
            logging.Formatter('%(asctime)s - %(remote_addr)s - %(method)s - %(path)s - %(status)s')
        )
        access_logger.addHandler(access_handler)
        self.loggers["access"] = access_logger

    async def analyze_logs(self, log_type: str = "error", hours: int = 24) -> Dict:
        """分析日志"""
        log_file = f"logs/{log_type}.log"
        if not os.path.exists(log_file):
            return {}

        errors_by_type = defaultdict(int)
        errors_by_time = defaultdict(int)

        with open(log_file, 'r') as f:
            for line in f:
                # 简单的日志分析，实际应该使用更复杂的解析
                if "ERROR" in line:
                    errors_by_type["ERROR"] += 1
                elif "WARNING" in line:
                    errors_by_type["WARNING"] += 1

        return {
            "errors_by_type": dict(errors_by_type),
            "total_errors": sum(errors_by_type.values())
        }

    async def cleanup_old_logs(self):
        """清理旧日志"""
        cutoff_date = datetime.now() - timedelta(days=self.config.log_retention_days)

        for log_file in os.listdir("logs"):
            file_path = os.path.join("logs", log_file)
            if os.path.getmtime(file_path) < cutoff_date.timestamp():
                os.remove(file_path)
                logger.info(f"Removed old log file: {log_file}")

# ============================================
# 备份管理器
# ============================================

class BackupManager:
    """备份管理器"""

    def __init__(self, config: OperationsConfig):
        self.config = config
        self.backup_dir = "/backups"

    async def create_backup(self, backup_type: str = "full") -> Dict:
        """创建备份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"backup_{backup_type}_{timestamp}"
        backup_path = os.path.join(self.backup_dir, backup_name)

        try:
            os.makedirs(backup_path, exist_ok=True)

            # 备份数据库
            await self._backup_database(backup_path)

            # 备份文件
            await self._backup_files(backup_path)

            # 备份配置
            await self._backup_config(backup_path)

            # 创建备份元数据
            metadata = {
                "name": backup_name,
                "type": backup_type,
                "timestamp": timestamp,
                "path": backup_path,
                "size": self._get_dir_size(backup_path)
            }

            # 压缩备份
            archive_path = f"{backup_path}.tar.gz"
            subprocess.run(f"tar -czf {archive_path} {backup_path}", shell=True)

            # 清理原始备份目录
            subprocess.run(f"rm -rf {backup_path}", shell=True)

            metadata["archive_path"] = archive_path
            metadata["archive_size"] = os.path.getsize(archive_path)

            # 保存备份记录
            await self._save_backup_record(metadata)

            return metadata

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            raise

    async def _backup_database(self, backup_path: str):
        """备份数据库"""
        db_backup_path = os.path.join(backup_path, "database.sql")
        subprocess.run(
            f"mysqldump -u {settings.db_user} -p{settings.db_password} {settings.db_name} > {db_backup_path}",
            shell=True,
            check=True
        )

    async def _backup_files(self, backup_path: str):
        """备份文件"""
        files_backup_path = os.path.join(backup_path, "files")
        subprocess.run(
            f"cp -r /app/data {files_backup_path}",
            shell=True,
            check=True
        )

    async def _backup_config(self, backup_path: str):
        """备份配置"""
        config_backup_path = os.path.join(backup_path, "config")
        subprocess.run(
            f"cp -r /app/config {config_backup_path}",
            shell=True,
            check=True
        )

    def _get_dir_size(self, path: str) -> int:
        """获取目录大小"""
        total_size = 0
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                total_size += os.path.getsize(filepath)
        return total_size

    async def _save_backup_record(self, metadata: Dict):
        """保存备份记录"""
        redis_client = get_redis_client()
        await redis_client.zadd(
            "backups:history",
            {json.dumps(metadata): time.time()}
        )

    async def restore_backup(self, backup_name: str) -> Dict:
        """恢复备份"""
        archive_path = os.path.join(self.backup_dir, f"{backup_name}.tar.gz")

        if not os.path.exists(archive_path):
            raise FileNotFoundError(f"Backup not found: {backup_name}")

        try:
            # 解压备份
            temp_path = f"/tmp/{backup_name}"
            subprocess.run(f"tar -xzf {archive_path} -C /tmp/", shell=True, check=True)

            # 恢复数据库
            db_backup = os.path.join(temp_path, "database.sql")
            subprocess.run(
                f"mysql -u {settings.db_user} -p{settings.db_password} {settings.db_name} < {db_backup}",
                shell=True,
                check=True
            )

            # 恢复文件
            subprocess.run(f"cp -r {temp_path}/files/* /app/data/", shell=True, check=True)

            # 恢复配置
            subprocess.run(f"cp -r {temp_path}/config/* /app/config/", shell=True, check=True)

            # 清理临时文件
            subprocess.run(f"rm -rf {temp_path}", shell=True)

            return {"status": "success", "backup_name": backup_name}

        except Exception as e:
            logger.error(f"Restore failed: {e}")
            raise

    async def cleanup_old_backups(self):
        """清理旧备份"""
        cutoff_date = datetime.now() - timedelta(days=self.config.backup_retention_days)

        for backup_file in os.listdir(self.backup_dir):
            if backup_file.endswith(".tar.gz"):
                file_path = os.path.join(self.backup_dir, backup_file)
                if os.path.getmtime(file_path) < cutoff_date.timestamp():
                    os.remove(file_path)
                    logger.info(f"Removed old backup: {backup_file}")

# ============================================
# 容器管理器
# ============================================

class ContainerManager:
    """容器管理器"""

    def __init__(self, config: OperationsConfig):
        self.config = config
        self.docker_client = docker.from_env() if config.docker_enabled else None
        self.k8s_client = None

        if config.kubernetes_enabled:
            kubernetes.config.load_incluster_config()
            self.k8s_client = kubernetes.client.CoreV1Api()

    async def list_containers(self) -> List[Dict]:
        """列出容器"""
        if not self.docker_client:
            return []

        containers = []
        for container in self.docker_client.containers.list(all=True):
            containers.append({
                "id": container.short_id,
                "name": container.name,
                "image": container.image.tags[0] if container.image.tags else "unknown",
                "status": container.status,
                "created": container.attrs['Created'],
                "ports": container.ports
            })

        return containers

    async def restart_container(self, container_name: str):
        """重启容器"""
        if self.docker_client:
            container = self.docker_client.containers.get(container_name)
            container.restart()
            logger.info(f"Restarted container: {container_name}")

    async def scale_service(self, service_name: str, replicas: int):
        """扩缩容服务"""
        if self.k8s_client:
            # Kubernetes扩缩容
            apps_v1 = kubernetes.client.AppsV1Api()
            deployment = apps_v1.read_namespaced_deployment(
                name=service_name,
                namespace="default"
            )
            deployment.spec.replicas = replicas
            apps_v1.patch_namespaced_deployment(
                name=service_name,
                namespace="default",
                body=deployment
            )
            logger.info(f"Scaled {service_name} to {replicas} replicas")

        elif self.docker_client:
            # Docker Swarm扩缩容
            service = self.docker_client.services.get(service_name)
            service.scale(replicas)
            logger.info(f"Scaled {service_name} to {replicas} replicas")

    async def get_container_logs(self, container_name: str, lines: int = 100) -> str:
        """获取容器日志"""
        if self.docker_client:
            container = self.docker_client.containers.get(container_name)
            return container.logs(tail=lines).decode('utf-8')
        return ""

# ============================================
# 智能运维系统
# ============================================

class IntelligentOperationsSystem:
    """智能运维系统"""

    def __init__(self, config: Optional[OperationsConfig] = None):
        """初始化运维系统"""
        self.config = config or OperationsConfig()
        self.monitoring = MonitoringManager(self.config)
        self.alert_manager = AlertManager(self.config)
        self.log_manager = LogManager(self.config)
        self.backup_manager = BackupManager(self.config)
        self.container_manager = ContainerManager(self.config)
        self.model_manager = get_model_manager()
        self.redis_client = get_redis_client()
        self.maintenance_tasks = []

    async def start(self):
        """启动运维系统"""
        logger.info("Starting Intelligent Operations System")

        # 启动监控
        await self.monitoring.start_monitoring()

        # 启动定时任务
        asyncio.create_task(self._schedule_maintenance())

        # 启动健康检查
        self._register_default_health_checks()

        logger.info("Operations system started successfully")

    def _register_default_health_checks(self):
        """注册默认健康检查"""
        default_checks = [
            HealthCheck(
                name="api_server",
                endpoint="http://localhost:8765/health",
                expected_status=200
            ),
            HealthCheck(
                name="database",
                endpoint="http://localhost:3306/health",
                expected_status=200
            ),
            HealthCheck(
                name="redis",
                endpoint="http://localhost:6379/health",
                expected_status=200
            )
        ]

        for check in default_checks:
            self.monitoring.register_health_check(check)

    async def _schedule_maintenance(self):
        """调度维护任务"""
        while True:
            current_time = datetime.now()
            current_hour = current_time.strftime("%H:%M")

            # 检查是否在维护窗口
            if self.config.maintenance_window_start <= current_hour <= self.config.maintenance_window_end:
                await self._perform_maintenance()

            await asyncio.sleep(3600)  # 每小时检查一次

    async def _perform_maintenance(self):
        """执行维护任务"""
        logger.info("Starting maintenance tasks")

        # 清理日志
        await self.log_manager.cleanup_old_logs()

        # 清理备份
        await self.backup_manager.cleanup_old_backups()

        # 创建备份
        if datetime.now().weekday() == 0:  # 周一全量备份
            await self.backup_manager.create_backup("full")
        else:  # 其他时间增量备份
            await self.backup_manager.create_backup("incremental")

        # 优化数据库
        await self._optimize_database()

        logger.info("Maintenance tasks completed")

    async def _optimize_database(self):
        """优化数据库"""
        try:
            with db_manager.get_session() as session:
                # 分析表
                session.execute("ANALYZE TABLE sessions")
                session.execute("ANALYZE TABLE metrics")

                # 优化表
                session.execute("OPTIMIZE TABLE sessions")
                session.execute("OPTIMIZE TABLE metrics")

                session.commit()
        except Exception as e:
            logger.error(f"Database optimization failed: {e}")

    async def diagnose_issue(self, symptoms: Dict) -> Dict:
        """诊断问题"""
        # 使用AI分析问题
        prompt = f"""
        Diagnose the following system issue:

        Symptoms:
        {json.dumps(symptoms, indent=2)}

        Provide:
        1. Root cause analysis
        2. Severity assessment
        3. Recommended solutions
        4. Prevention measures

        Format as JSON.
        """

        response = await self.model_manager.generate(
            prompt=prompt,
            capability=ModelCapability.EXPLANATION
        )

        try:
            diagnosis = json.loads(response.content)
        except:
            diagnosis = {
                "root_cause": "Unknown",
                "severity": "medium",
                "solutions": ["Manual investigation required"],
                "prevention": []
            }

        return diagnosis

    async def auto_scale(self, service: str, metrics: Dict):
        """自动扩缩容"""
        if not self.config.auto_scale_enabled:
            return

        cpu_usage = metrics.get("cpu_percent", 0)
        memory_usage = metrics.get("memory_percent", 0)
        current_replicas = metrics.get("replicas", 1)

        # 扩容条件
        if cpu_usage > 80 or memory_usage > 85:
            new_replicas = min(current_replicas + 1, 10)
            await self.container_manager.scale_service(service, new_replicas)
            logger.info(f"Scaled up {service} to {new_replicas} replicas")

        # 缩容条件
        elif cpu_usage < 30 and memory_usage < 40 and current_replicas > 1:
            new_replicas = max(current_replicas - 1, 1)
            await self.container_manager.scale_service(service, new_replicas)
            logger.info(f"Scaled down {service} to {new_replicas} replicas")

    async def rollback_deployment(self, service: str, version: str):
        """回滚部署"""
        logger.info(f"Rolling back {service} to version {version}")

        # Docker回滚
        if self.config.docker_enabled:
            container = self.docker_client.containers.get(service)
            container.stop()

            # 启动旧版本
            self.docker_client.containers.run(
                f"{service}:{version}",
                name=service,
                detach=True,
                restart_policy={"Name": "always"}
            )

        logger.info(f"Rollback completed for {service}")

    async def get_operations_dashboard(self) -> Dict:
        """获取运维仪表板"""
        system_metrics = await self.analyze_system_performance()
        service_status = self.monitoring.get_service_status()
        active_alerts = len(self.alert_manager.active_alerts)

        redis_client = get_redis_client()
        recent_backups = await redis_client.zrange("backups:history", -5, -1)

        return {
            "system": system_metrics,
            "services": service_status,
            "alerts": {
                "active": active_alerts,
                "recent": list(self.alert_manager.alert_history)[-10:]
            },
            "backups": [json.loads(b) for b in recent_backups],
            "maintenance": {
                "next_window": self.config.maintenance_window_start,
                "auto_scale": self.config.auto_scale_enabled,
                "auto_restart": self.config.auto_restart_enabled
            }
        }

    async def analyze_system_performance(self) -> Dict:
        """分析系统性能"""
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')

        return {
            "cpu": {
                "usage": cpu_percent,
                "cores": psutil.cpu_count()
            },
            "memory": {
                "usage": memory.percent,
                "available_gb": memory.available / 1024 / 1024 / 1024
            },
            "disk": {
                "usage": disk.percent,
                "free_gb": disk.free / 1024 / 1024 / 1024
            },
            "uptime": datetime.now() - datetime.fromtimestamp(psutil.boot_time())
        }

# ============================================
# 单例实例
# ============================================

_operations_instance: Optional[IntelligentOperationsSystem] = None

def get_operations_system() -> IntelligentOperationsSystem:
    """获取运维系统单例"""
    global _operations_instance
    if _operations_instance is None:
        _operations_instance = IntelligentOperationsSystem()
    return _operations_instance