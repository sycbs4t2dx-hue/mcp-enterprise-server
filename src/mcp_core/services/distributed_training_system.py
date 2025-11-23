"""
分布式训练系统
支持多节点协同训练和模型优化
"""

import os
import json
import pickle
import asyncio
import hashlib
from typing import Dict, List, Optional, Any, Tuple, Union
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timedelta
import numpy as np
import torch
import torch.nn as nn
import torch.optim as optim
import torch.distributed as dist
from torch.nn.parallel import DistributedDataParallel as DDP
from torch.utils.data import DataLoader, Dataset, DistributedSampler
import ray
from ray import train
from ray.train.torch import TorchTrainer
from ray.air import ScalingConfig

from ..common.logger import get_logger
from ..common.config import get_settings
from ..models import db_manager, TrainingJob, TrainingMetrics, ModelCheckpoint
from ..services.redis_client import get_redis_client
from ..services.vector_db import VectorDatabase

logger = get_logger(__name__)

# ============================================
# 训练配置
# ============================================

class TrainingStrategy(Enum):
    """训练策略"""
    DATA_PARALLEL = "data_parallel"
    MODEL_PARALLEL = "model_parallel"
    PIPELINE_PARALLEL = "pipeline_parallel"
    HYBRID_PARALLEL = "hybrid_parallel"
    FEDERATED = "federated"

class OptimizerType(Enum):
    """优化器类型"""
    SGD = "sgd"
    ADAM = "adam"
    ADAMW = "adamw"
    RMSPROP = "rmsprop"
    LAMB = "lamb"
    LARS = "lars"

@dataclass
class TrainingConfig:
    """训练配置"""
    job_id: str
    model_name: str
    dataset_path: str
    output_dir: str
    strategy: TrainingStrategy = TrainingStrategy.DATA_PARALLEL
    num_workers: int = 4
    batch_size: int = 32
    learning_rate: float = 0.001
    epochs: int = 10
    optimizer: OptimizerType = OptimizerType.ADAM
    gradient_accumulation_steps: int = 1
    mixed_precision: bool = True
    checkpoint_interval: int = 1
    early_stopping_patience: int = 3
    warmup_steps: int = 1000
    max_grad_norm: float = 1.0
    seed: int = 42
    distributed_backend: str = "nccl"
    custom_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class TrainingState:
    """训练状态"""
    epoch: int = 0
    step: int = 0
    best_metric: float = float('inf')
    best_epoch: int = 0
    patience_counter: int = 0
    training_time: float = 0.0
    metrics_history: List[Dict[str, float]] = field(default_factory=list)

# ============================================
# 自定义数据集
# ============================================

class CodeDataset(Dataset):
    """代码数据集"""

    def __init__(self, data_path: str, tokenizer=None, max_length: int = 512):
        """初始化数据集"""
        self.data = self._load_data(data_path)
        self.tokenizer = tokenizer
        self.max_length = max_length

    def _load_data(self, data_path: str) -> List[Dict[str, Any]]:
        """加载数据"""
        data = []
        if os.path.exists(data_path):
            with open(data_path, 'r') as f:
                for line in f:
                    if line.strip():
                        data.append(json.loads(line))
        return data

    def __len__(self):
        return len(self.data)

    def __getitem__(self, idx):
        item = self.data[idx]

        # 如果有tokenizer，进行tokenization
        if self.tokenizer:
            inputs = self.tokenizer(
                item['input'],
                max_length=self.max_length,
                padding='max_length',
                truncation=True,
                return_tensors='pt'
            )

            targets = self.tokenizer(
                item.get('target', item['input']),
                max_length=self.max_length,
                padding='max_length',
                truncation=True,
                return_tensors='pt'
            )

            return {
                'input_ids': inputs['input_ids'].squeeze(),
                'attention_mask': inputs['attention_mask'].squeeze(),
                'labels': targets['input_ids'].squeeze()
            }
        else:
            # 简单返回原始数据
            return {
                'input': item['input'],
                'target': item.get('target', item['input']),
                'metadata': item.get('metadata', {})
            }

# ============================================
# 模型定义
# ============================================

class CodeGenerationModel(nn.Module):
    """代码生成模型"""

    def __init__(self, vocab_size: int, hidden_size: int = 768, num_layers: int = 12):
        super().__init__()

        self.embedding = nn.Embedding(vocab_size, hidden_size)
        self.transformer = nn.TransformerEncoder(
            nn.TransformerEncoderLayer(
                d_model=hidden_size,
                nhead=12,
                dim_feedforward=3072,
                dropout=0.1
            ),
            num_layers=num_layers
        )
        self.output_layer = nn.Linear(hidden_size, vocab_size)

    def forward(self, input_ids, attention_mask=None):
        # 嵌入
        x = self.embedding(input_ids)

        # Transformer编码
        x = self.transformer(x)

        # 输出层
        logits = self.output_layer(x)

        return logits

# ============================================
# 分布式训练器
# ============================================

class DistributedTrainer:
    """分布式训练器"""

    def __init__(self, config: TrainingConfig):
        """初始化训练器"""
        self.config = config
        self.state = TrainingState()
        self.model = None
        self.optimizer = None
        self.scheduler = None
        self.scaler = None
        self.redis_client = get_redis_client()
        self.vector_db = VectorDatabase()

        # 设置随机种子
        self._set_seed(config.seed)

    def _set_seed(self, seed: int):
        """设置随机种子"""
        torch.manual_seed(seed)
        np.random.seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)

    async def initialize(self):
        """初始化训练环境"""
        try:
            # 初始化分布式环境
            if self.config.strategy != TrainingStrategy.FEDERATED:
                self._init_distributed()

            # 创建模型
            self.model = self._create_model()

            # 创建优化器
            self.optimizer = self._create_optimizer()

            # 创建学习率调度器
            self.scheduler = self._create_scheduler()

            # 混合精度训练
            if self.config.mixed_precision:
                from torch.cuda.amp import GradScaler
                self.scaler = GradScaler()

            logger.info(f"Trainer initialized for job {self.config.job_id}")

        except Exception as e:
            logger.error(f"Failed to initialize trainer: {e}")
            raise

    def _init_distributed(self):
        """初始化分布式环境"""
        if not dist.is_initialized():
            dist.init_process_group(backend=self.config.distributed_backend)

    def _create_model(self) -> nn.Module:
        """创建模型"""
        # 这里简化处理，实际应该根据配置加载不同模型
        model = CodeGenerationModel(vocab_size=50000)

        # 分布式包装
        if dist.is_initialized():
            model = model.cuda()
            model = DDP(model)
        elif torch.cuda.is_available():
            model = model.cuda()

        return model

    def _create_optimizer(self) -> optim.Optimizer:
        """创建优化器"""
        if self.config.optimizer == OptimizerType.SGD:
            return optim.SGD(
                self.model.parameters(),
                lr=self.config.learning_rate,
                momentum=0.9
            )
        elif self.config.optimizer == OptimizerType.ADAM:
            return optim.Adam(
                self.model.parameters(),
                lr=self.config.learning_rate
            )
        elif self.config.optimizer == OptimizerType.ADAMW:
            return optim.AdamW(
                self.model.parameters(),
                lr=self.config.learning_rate
            )
        else:
            return optim.Adam(
                self.model.parameters(),
                lr=self.config.learning_rate
            )

    def _create_scheduler(self):
        """创建学习率调度器"""
        return optim.lr_scheduler.CosineAnnealingLR(
            self.optimizer,
            T_max=self.config.epochs
        )

    async def train(self) -> Dict[str, Any]:
        """执行训练"""
        try:
            # 加载数据
            train_loader, val_loader = await self._prepare_data()

            # 训练循环
            for epoch in range(self.state.epoch, self.config.epochs):
                self.state.epoch = epoch

                # 训练一个epoch
                train_metrics = await self._train_epoch(train_loader)

                # 验证
                val_metrics = await self._validate(val_loader)

                # 更新状态
                self._update_state(train_metrics, val_metrics)

                # 保存检查点
                if epoch % self.config.checkpoint_interval == 0:
                    await self._save_checkpoint()

                # 早停检查
                if self._should_stop():
                    logger.info(f"Early stopping at epoch {epoch}")
                    break

                # 更新学习率
                if self.scheduler:
                    self.scheduler.step()

            # 最终评估
            final_metrics = await self._final_evaluation(val_loader)

            return {
                "status": "completed",
                "epochs_trained": self.state.epoch,
                "best_metric": self.state.best_metric,
                "final_metrics": final_metrics,
                "training_time": self.state.training_time
            }

        except Exception as e:
            logger.error(f"Training failed: {e}")
            return {
                "status": "failed",
                "error": str(e)
            }

    async def _prepare_data(self) -> Tuple[DataLoader, DataLoader]:
        """准备数据加载器"""
        # 创建数据集
        train_dataset = CodeDataset(
            os.path.join(self.config.dataset_path, "train.jsonl")
        )
        val_dataset = CodeDataset(
            os.path.join(self.config.dataset_path, "val.jsonl")
        )

        # 创建采样器
        train_sampler = None
        val_sampler = None
        if dist.is_initialized():
            train_sampler = DistributedSampler(train_dataset)
            val_sampler = DistributedSampler(val_dataset, shuffle=False)

        # 创建数据加载器
        train_loader = DataLoader(
            train_dataset,
            batch_size=self.config.batch_size,
            sampler=train_sampler,
            shuffle=(train_sampler is None),
            num_workers=self.config.num_workers
        )

        val_loader = DataLoader(
            val_dataset,
            batch_size=self.config.batch_size,
            sampler=val_sampler,
            shuffle=False,
            num_workers=self.config.num_workers
        )

        return train_loader, val_loader

    async def _train_epoch(self, dataloader: DataLoader) -> Dict[str, float]:
        """训练一个epoch"""
        self.model.train()
        total_loss = 0.0
        total_steps = 0

        import time
        start_time = time.time()

        for batch_idx, batch in enumerate(dataloader):
            # 移到GPU
            if torch.cuda.is_available():
                batch = {k: v.cuda() if isinstance(v, torch.Tensor) else v
                        for k, v in batch.items()}

            # 前向传播
            if self.config.mixed_precision and self.scaler:
                with torch.cuda.amp.autocast():
                    loss = self._compute_loss(batch)
            else:
                loss = self._compute_loss(batch)

            # 反向传播
            if self.config.gradient_accumulation_steps > 1:
                loss = loss / self.config.gradient_accumulation_steps

            if self.scaler:
                self.scaler.scale(loss).backward()
            else:
                loss.backward()

            # 梯度累积
            if (batch_idx + 1) % self.config.gradient_accumulation_steps == 0:
                # 梯度裁剪
                if self.config.max_grad_norm > 0:
                    if self.scaler:
                        self.scaler.unscale_(self.optimizer)
                    torch.nn.utils.clip_grad_norm_(
                        self.model.parameters(),
                        self.config.max_grad_norm
                    )

                # 优化器步进
                if self.scaler:
                    self.scaler.step(self.optimizer)
                    self.scaler.update()
                else:
                    self.optimizer.step()

                self.optimizer.zero_grad()

            total_loss += loss.item()
            total_steps += 1
            self.state.step += 1

            # 记录进度
            if batch_idx % 10 == 0:
                await self._update_progress(batch_idx, len(dataloader))

        epoch_time = time.time() - start_time
        self.state.training_time += epoch_time

        metrics = {
            "train_loss": total_loss / total_steps,
            "epoch_time": epoch_time,
            "learning_rate": self.optimizer.param_groups[0]['lr']
        }

        return metrics

    def _compute_loss(self, batch: Dict[str, torch.Tensor]) -> torch.Tensor:
        """计算损失"""
        # 简化的损失计算
        logits = self.model(
            batch['input_ids'],
            batch.get('attention_mask')
        )

        loss_fn = nn.CrossEntropyLoss()
        loss = loss_fn(
            logits.view(-1, logits.size(-1)),
            batch['labels'].view(-1)
        )

        return loss

    async def _validate(self, dataloader: DataLoader) -> Dict[str, float]:
        """验证模型"""
        self.model.eval()
        total_loss = 0.0
        total_steps = 0

        with torch.no_grad():
            for batch in dataloader:
                if torch.cuda.is_available():
                    batch = {k: v.cuda() if isinstance(v, torch.Tensor) else v
                            for k, v in batch.items()}

                loss = self._compute_loss(batch)
                total_loss += loss.item()
                total_steps += 1

        metrics = {
            "val_loss": total_loss / total_steps
        }

        return metrics

    def _update_state(self, train_metrics: Dict, val_metrics: Dict):
        """更新训练状态"""
        # 记录指标
        metrics = {**train_metrics, **val_metrics, "epoch": self.state.epoch}
        self.state.metrics_history.append(metrics)

        # 更新最佳指标
        val_loss = val_metrics.get("val_loss", float('inf'))
        if val_loss < self.state.best_metric:
            self.state.best_metric = val_loss
            self.state.best_epoch = self.state.epoch
            self.state.patience_counter = 0
        else:
            self.state.patience_counter += 1

        logger.info(f"Epoch {self.state.epoch}: {metrics}")

    def _should_stop(self) -> bool:
        """检查是否应该早停"""
        return self.state.patience_counter >= self.config.early_stopping_patience

    async def _save_checkpoint(self):
        """保存检查点"""
        try:
            checkpoint = {
                "epoch": self.state.epoch,
                "model_state_dict": self.model.state_dict(),
                "optimizer_state_dict": self.optimizer.state_dict(),
                "scheduler_state_dict": self.scheduler.state_dict() if self.scheduler else None,
                "state": self.state,
                "config": self.config
            }

            checkpoint_path = os.path.join(
                self.config.output_dir,
                f"checkpoint_epoch_{self.state.epoch}.pt"
            )

            torch.save(checkpoint, checkpoint_path)

            # 保存到数据库
            await self._save_checkpoint_to_db(checkpoint_path)

            logger.info(f"Checkpoint saved: {checkpoint_path}")

        except Exception as e:
            logger.error(f"Failed to save checkpoint: {e}")

    async def _save_checkpoint_to_db(self, checkpoint_path: str):
        """保存检查点到数据库"""
        try:
            with db_manager.get_session() as session:
                checkpoint = ModelCheckpoint(
                    job_id=self.config.job_id,
                    epoch=self.state.epoch,
                    path=checkpoint_path,
                    metrics=json.dumps(self.state.metrics_history[-1]),
                    is_best=self.state.epoch == self.state.best_epoch
                )
                session.add(checkpoint)
                session.commit()
        except Exception as e:
            logger.error(f"Failed to save checkpoint to DB: {e}")

    async def _update_progress(self, current: int, total: int):
        """更新训练进度"""
        progress = {
            "job_id": self.config.job_id,
            "epoch": self.state.epoch,
            "batch": current,
            "total_batches": total,
            "percentage": (current / total) * 100
        }

        # 发送到Redis
        await self.redis_client.publish(
            f"training_progress:{self.config.job_id}",
            json.dumps(progress)
        )

    async def _final_evaluation(self, dataloader: DataLoader) -> Dict[str, Any]:
        """最终评估"""
        # 加载最佳模型
        best_checkpoint = os.path.join(
            self.config.output_dir,
            f"checkpoint_epoch_{self.state.best_epoch}.pt"
        )

        if os.path.exists(best_checkpoint):
            checkpoint = torch.load(best_checkpoint)
            self.model.load_state_dict(checkpoint["model_state_dict"])

        # 评估
        val_metrics = await self._validate(dataloader)

        return {
            "best_epoch": self.state.best_epoch,
            **val_metrics
        }

    async def resume_training(self, checkpoint_path: str):
        """恢复训练"""
        try:
            checkpoint = torch.load(checkpoint_path)

            self.model.load_state_dict(checkpoint["model_state_dict"])
            self.optimizer.load_state_dict(checkpoint["optimizer_state_dict"])

            if self.scheduler and checkpoint.get("scheduler_state_dict"):
                self.scheduler.load_state_dict(checkpoint["scheduler_state_dict"])

            self.state = checkpoint["state"]

            logger.info(f"Training resumed from epoch {self.state.epoch}")

        except Exception as e:
            logger.error(f"Failed to resume training: {e}")
            raise

# ============================================
# Ray分布式训练
# ============================================

class RayDistributedTrainer:
    """基于Ray的分布式训练器"""

    def __init__(self, config: TrainingConfig):
        self.config = config
        ray.init(ignore_reinit_error=True)

    def train_func(self, config: Dict):
        """Ray训练函数"""
        import torch
        from ray.air import session

        # 创建模型
        model = CodeGenerationModel(vocab_size=50000)
        model = train.torch.prepare_model(model)

        # 创建优化器
        optimizer = optim.Adam(model.parameters(), lr=config["lr"])

        # 创建数据加载器
        dataset = CodeDataset(config["data_path"])
        dataloader = DataLoader(dataset, batch_size=config["batch_size"])
        dataloader = train.torch.prepare_data_loader(dataloader)

        # 训练循环
        for epoch in range(config["epochs"]):
            model.train()
            total_loss = 0.0

            for batch in dataloader:
                optimizer.zero_grad()

                # 前向传播
                logits = model(batch['input_ids'])
                loss = nn.functional.cross_entropy(
                    logits.view(-1, logits.size(-1)),
                    batch['labels'].view(-1)
                )

                # 反向传播
                loss.backward()
                optimizer.step()

                total_loss += loss.item()

            # 报告指标
            session.report({
                "epoch": epoch,
                "train_loss": total_loss / len(dataloader)
            })

    async def train(self):
        """执行Ray分布式训练"""
        trainer = TorchTrainer(
            train_func=self.train_func,
            train_loop_config={
                "lr": self.config.learning_rate,
                "epochs": self.config.epochs,
                "batch_size": self.config.batch_size,
                "data_path": self.config.dataset_path
            },
            scaling_config=ScalingConfig(
                num_workers=self.config.num_workers,
                use_gpu=torch.cuda.is_available()
            )
        )

        result = trainer.fit()
        return result.metrics

# ============================================
# 联邦学习训练器
# ============================================

class FederatedTrainer:
    """联邦学习训练器"""

    def __init__(self, config: TrainingConfig):
        self.config = config
        self.global_model = None
        self.client_models = {}

    async def initialize_global_model(self):
        """初始化全局模型"""
        self.global_model = CodeGenerationModel(vocab_size=50000)

    async def train_client(self, client_id: str, client_data: Dataset) -> Dict:
        """训练客户端模型"""
        # 复制全局模型
        client_model = CodeGenerationModel(vocab_size=50000)
        client_model.load_state_dict(self.global_model.state_dict())

        # 创建优化器
        optimizer = optim.SGD(
            client_model.parameters(),
            lr=self.config.learning_rate
        )

        # 本地训练
        dataloader = DataLoader(client_data, batch_size=self.config.batch_size)

        client_model.train()
        total_loss = 0.0

        for batch in dataloader:
            optimizer.zero_grad()

            logits = client_model(batch['input_ids'])
            loss = nn.functional.cross_entropy(
                logits.view(-1, logits.size(-1)),
                batch['labels'].view(-1)
            )

            loss.backward()
            optimizer.step()

            total_loss += loss.item()

        # 返回更新后的模型参数
        return {
            "client_id": client_id,
            "model_state": client_model.state_dict(),
            "loss": total_loss / len(dataloader),
            "num_samples": len(client_data)
        }

    async def aggregate_models(self, client_updates: List[Dict]):
        """聚合客户端模型"""
        # 加权平均
        total_samples = sum(update["num_samples"] for update in client_updates)

        averaged_state = {}
        for key in self.global_model.state_dict().keys():
            averaged_state[key] = sum(
                update["model_state"][key] * update["num_samples"] / total_samples
                for update in client_updates
            )

        # 更新全局模型
        self.global_model.load_state_dict(averaged_state)

    async def train(self) -> Dict:
        """执行联邦学习"""
        await self.initialize_global_model()

        for round_num in range(self.config.epochs):
            logger.info(f"Federated learning round {round_num}")

            # 选择客户端
            client_ids = self._select_clients()

            # 客户端训练
            client_updates = []
            for client_id in client_ids:
                client_data = await self._get_client_data(client_id)
                update = await self.train_client(client_id, client_data)
                client_updates.append(update)

            # 模型聚合
            await self.aggregate_models(client_updates)

            # 评估全局模型
            metrics = await self._evaluate_global_model()
            logger.info(f"Round {round_num} metrics: {metrics}")

        return {
            "status": "completed",
            "rounds": self.config.epochs
        }

    def _select_clients(self) -> List[str]:
        """选择参与训练的客户端"""
        # 简化实现，返回固定客户端
        return [f"client_{i}" for i in range(self.config.num_workers)]

    async def _get_client_data(self, client_id: str) -> Dataset:
        """获取客户端数据"""
        # 简化实现，返回部分数据
        return CodeDataset(os.path.join(self.config.dataset_path, f"{client_id}.jsonl"))

    async def _evaluate_global_model(self) -> Dict:
        """评估全局模型"""
        # 简化实现
        return {"global_loss": 0.1}

# ============================================
# 训练管理器
# ============================================

class DistributedTrainingManager:
    """分布式训练管理器"""

    def __init__(self):
        self.active_jobs: Dict[str, Any] = {}
        self.redis_client = get_redis_client()

    async def submit_job(self, config: TrainingConfig) -> str:
        """提交训练任务"""
        try:
            # 保存任务到数据库
            job_id = await self._save_job_to_db(config)
            config.job_id = job_id

            # 根据策略选择训练器
            if config.strategy == TrainingStrategy.FEDERATED:
                trainer = FederatedTrainer(config)
            elif config.num_workers > 1:
                trainer = RayDistributedTrainer(config)
            else:
                trainer = DistributedTrainer(config)
                await trainer.initialize()

            # 启动异步训练
            self.active_jobs[job_id] = trainer
            asyncio.create_task(self._run_training(job_id, trainer))

            return job_id

        except Exception as e:
            logger.error(f"Failed to submit job: {e}")
            raise

    async def _save_job_to_db(self, config: TrainingConfig) -> str:
        """保存任务到数据库"""
        with db_manager.get_session() as session:
            job = TrainingJob(
                model_name=config.model_name,
                dataset_path=config.dataset_path,
                config=json.dumps(config.__dict__),
                status="pending"
            )
            session.add(job)
            session.commit()
            return str(job.id)

    async def _run_training(self, job_id: str, trainer):
        """运行训练"""
        try:
            # 更新状态为运行中
            await self._update_job_status(job_id, "running")

            # 执行训练
            result = await trainer.train()

            # 更新状态
            status = result.get("status", "completed")
            await self._update_job_status(job_id, status, result)

        except Exception as e:
            logger.error(f"Training job {job_id} failed: {e}")
            await self._update_job_status(job_id, "failed", {"error": str(e)})

        finally:
            # 清理
            if job_id in self.active_jobs:
                del self.active_jobs[job_id]

    async def _update_job_status(self, job_id: str, status: str, result: Dict = None):
        """更新任务状态"""
        with db_manager.get_session() as session:
            job = session.query(TrainingJob).filter_by(id=job_id).first()
            if job:
                job.status = status
                if result:
                    job.result = json.dumps(result)
                if status in ["completed", "failed"]:
                    job.end_time = datetime.now()
                session.commit()

    async def get_job_status(self, job_id: str) -> Dict:
        """获取任务状态"""
        with db_manager.get_session() as session:
            job = session.query(TrainingJob).filter_by(id=job_id).first()
            if job:
                return {
                    "id": job.id,
                    "status": job.status,
                    "start_time": job.start_time.isoformat() if job.start_time else None,
                    "end_time": job.end_time.isoformat() if job.end_time else None,
                    "result": json.loads(job.result) if job.result else None
                }
            return None

    async def cancel_job(self, job_id: str) -> bool:
        """取消任务"""
        if job_id in self.active_jobs:
            # 这里应该实现优雅的取消逻辑
            del self.active_jobs[job_id]
            await self._update_job_status(job_id, "cancelled")
            return True
        return False

# ============================================
# 单例实例
# ============================================

_training_manager_instance: Optional[DistributedTrainingManager] = None

def get_training_manager() -> DistributedTrainingManager:
    """获取训练管理器单例"""
    global _training_manager_instance
    if _training_manager_instance is None:
        _training_manager_instance = DistributedTrainingManager()
    return _training_manager_instance