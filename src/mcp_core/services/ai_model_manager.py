"""
AI模型集成层
支持多种大语言模型和专业AI服务
"""

import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Union, AsyncGenerator
from dataclasses import dataclass, field
from enum import Enum
from abc import ABC, abstractmethod
import aiohttp
import openai
import anthropic
from transformers import AutoTokenizer, AutoModelForCausalLM, pipeline
import torch
import numpy as np

from ..common.logger import get_logger
from ..common.config import get_settings

logger = get_logger(__name__)

# ============================================
# 模型类型定义
# ============================================

class ModelProvider(Enum):
    """模型提供商"""
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    HUGGINGFACE = "huggingface"
    LOCAL = "local"
    CUSTOM = "custom"

class ModelCapability(Enum):
    """模型能力"""
    CODE_GENERATION = "code_generation"
    CODE_COMPLETION = "code_completion"
    CODE_REVIEW = "code_review"
    BUG_DETECTION = "bug_detection"
    REFACTORING = "refactoring"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    EXPLANATION = "explanation"
    TRANSLATION = "translation"
    OPTIMIZATION = "optimization"

@dataclass
class ModelConfig:
    """模型配置"""
    model_id: str
    provider: ModelProvider
    model_name: str
    api_key: Optional[str] = None
    endpoint: Optional[str] = None
    max_tokens: int = 2048
    temperature: float = 0.7
    top_p: float = 0.95
    frequency_penalty: float = 0.0
    presence_penalty: float = 0.0
    capabilities: List[ModelCapability] = field(default_factory=list)
    context_window: int = 4096
    cost_per_token: float = 0.0
    rate_limit: int = 100  # requests per minute
    timeout: int = 30
    retry_count: int = 3
    custom_params: Dict[str, Any] = field(default_factory=dict)

@dataclass
class ModelRequest:
    """模型请求"""
    prompt: str
    model_id: Optional[str] = None
    capability: Optional[ModelCapability] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    stream: bool = False
    context: Optional[Dict[str, Any]] = None
    system_prompt: Optional[str] = None
    examples: Optional[List[Dict[str, str]]] = None
    stop_sequences: Optional[List[str]] = None

@dataclass
class ModelResponse:
    """模型响应"""
    content: str
    model_id: str
    tokens_used: int
    latency_ms: float
    cost: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None

# ============================================
# 基础模型接口
# ============================================

class BaseModelInterface(ABC):
    """基础模型接口"""

    def __init__(self, config: ModelConfig):
        self.config = config
        self.session: Optional[aiohttp.ClientSession] = None

    @abstractmethod
    async def generate(self, request: ModelRequest) -> ModelResponse:
        """生成响应"""
        pass

    @abstractmethod
    async def stream_generate(self, request: ModelRequest) -> AsyncGenerator[str, None]:
        """流式生成"""
        pass

    async def validate(self) -> bool:
        """验证模型连接"""
        try:
            test_request = ModelRequest(
                prompt="Hello",
                max_tokens=10
            )
            response = await self.generate(test_request)
            return response.error is None
        except Exception as e:
            logger.error(f"Model validation failed: {e}")
            return False

    async def close(self):
        """关闭连接"""
        if self.session:
            await self.session.close()

# ============================================
# OpenAI模型接口
# ============================================

class OpenAIInterface(BaseModelInterface):
    """OpenAI模型接口"""

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        openai.api_key = config.api_key or os.getenv("OPENAI_API_KEY")
        if config.endpoint:
            openai.api_base = config.endpoint

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """生成响应"""
        import time
        start_time = time.time()

        try:
            # 构建消息
            messages = []

            if request.system_prompt:
                messages.append({
                    "role": "system",
                    "content": request.system_prompt
                })

            if request.examples:
                for example in request.examples:
                    messages.append({"role": "user", "content": example.get("input", "")})
                    messages.append({"role": "assistant", "content": example.get("output", "")})

            messages.append({"role": "user", "content": request.prompt})

            # 调用API
            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                model=self.config.model_name,
                messages=messages,
                max_tokens=request.max_tokens or self.config.max_tokens,
                temperature=request.temperature or self.config.temperature,
                top_p=self.config.top_p,
                frequency_penalty=self.config.frequency_penalty,
                presence_penalty=self.config.presence_penalty,
                stop=request.stop_sequences
            )

            # 提取结果
            content = response.choices[0].message.content
            tokens_used = response.usage.total_tokens

            latency_ms = (time.time() - start_time) * 1000
            cost = tokens_used * self.config.cost_per_token

            return ModelResponse(
                content=content,
                model_id=self.config.model_id,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                cost=cost,
                metadata={"model": self.config.model_name}
            )

        except Exception as e:
            logger.error(f"OpenAI generation failed: {e}")
            return ModelResponse(
                content="",
                model_id=self.config.model_id,
                tokens_used=0,
                latency_ms=(time.time() - start_time) * 1000,
                cost=0,
                error=str(e)
            )

    async def stream_generate(self, request: ModelRequest) -> AsyncGenerator[str, None]:
        """流式生成"""
        messages = []

        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})

        messages.append({"role": "user", "content": request.prompt})

        try:
            response = await asyncio.to_thread(
                openai.ChatCompletion.create,
                model=self.config.model_name,
                messages=messages,
                max_tokens=request.max_tokens or self.config.max_tokens,
                temperature=request.temperature or self.config.temperature,
                stream=True
            )

            for chunk in response:
                if chunk.choices[0].delta.get("content"):
                    yield chunk.choices[0].delta.content

        except Exception as e:
            logger.error(f"OpenAI streaming failed: {e}")
            yield f"Error: {str(e)}"

# ============================================
# Anthropic模型接口
# ============================================

class AnthropicInterface(BaseModelInterface):
    """Anthropic模型接口"""

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.client = anthropic.Client(
            api_key=config.api_key or os.getenv("ANTHROPIC_API_KEY")
        )

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """生成响应"""
        import time
        start_time = time.time()

        try:
            # 构建提示
            prompt = ""

            if request.system_prompt:
                prompt += f"{request.system_prompt}\n\n"

            if request.examples:
                prompt += "Examples:\n"
                for example in request.examples:
                    prompt += f"Input: {example.get('input', '')}\n"
                    prompt += f"Output: {example.get('output', '')}\n\n"

            prompt += f"Human: {request.prompt}\n\nAssistant:"

            # 调用API
            response = await asyncio.to_thread(
                self.client.completions.create,
                model=self.config.model_name,
                prompt=prompt,
                max_tokens_to_sample=request.max_tokens or self.config.max_tokens,
                temperature=request.temperature or self.config.temperature,
                stop_sequences=request.stop_sequences or ["Human:"]
            )

            content = response.completion
            tokens_used = len(prompt.split()) + len(content.split())  # 估算

            latency_ms = (time.time() - start_time) * 1000
            cost = tokens_used * self.config.cost_per_token

            return ModelResponse(
                content=content,
                model_id=self.config.model_id,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                cost=cost,
                metadata={"model": self.config.model_name}
            )

        except Exception as e:
            logger.error(f"Anthropic generation failed: {e}")
            return ModelResponse(
                content="",
                model_id=self.config.model_id,
                tokens_used=0,
                latency_ms=(time.time() - start_time) * 1000,
                cost=0,
                error=str(e)
            )

    async def stream_generate(self, request: ModelRequest) -> AsyncGenerator[str, None]:
        """流式生成"""
        prompt = f"Human: {request.prompt}\n\nAssistant:"

        try:
            response = await asyncio.to_thread(
                self.client.completions.create,
                model=self.config.model_name,
                prompt=prompt,
                max_tokens_to_sample=request.max_tokens or self.config.max_tokens,
                stream=True
            )

            for chunk in response:
                yield chunk.completion

        except Exception as e:
            logger.error(f"Anthropic streaming failed: {e}")
            yield f"Error: {str(e)}"

# ============================================
# HuggingFace模型接口
# ============================================

class HuggingFaceInterface(BaseModelInterface):
    """HuggingFace模型接口"""

    def __init__(self, config: ModelConfig):
        super().__init__(config)
        self.tokenizer = None
        self.model = None
        self.pipeline = None
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self._load_model()

    def _load_model(self):
        """加载模型"""
        try:
            self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
            self.model = AutoModelForCausalLM.from_pretrained(
                self.config.model_name,
                torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
                device_map="auto"
            )

            self.pipeline = pipeline(
                "text-generation",
                model=self.model,
                tokenizer=self.tokenizer,
                device=0 if self.device == "cuda" else -1
            )

            logger.info(f"Loaded HuggingFace model: {self.config.model_name}")

        except Exception as e:
            logger.error(f"Failed to load HuggingFace model: {e}")

    async def generate(self, request: ModelRequest) -> ModelResponse:
        """生成响应"""
        import time
        start_time = time.time()

        if not self.pipeline:
            return ModelResponse(
                content="",
                model_id=self.config.model_id,
                tokens_used=0,
                latency_ms=0,
                cost=0,
                error="Model not loaded"
            )

        try:
            # 构建提示
            prompt = request.system_prompt + "\n\n" if request.system_prompt else ""
            prompt += request.prompt

            # 生成
            result = await asyncio.to_thread(
                self.pipeline,
                prompt,
                max_new_tokens=request.max_tokens or self.config.max_tokens,
                temperature=request.temperature or self.config.temperature,
                top_p=self.config.top_p,
                do_sample=True,
                return_full_text=False
            )

            content = result[0]["generated_text"]
            tokens_used = len(self.tokenizer.encode(prompt + content))

            latency_ms = (time.time() - start_time) * 1000
            cost = tokens_used * self.config.cost_per_token

            return ModelResponse(
                content=content,
                model_id=self.config.model_id,
                tokens_used=tokens_used,
                latency_ms=latency_ms,
                cost=cost,
                metadata={"model": self.config.model_name, "device": self.device}
            )

        except Exception as e:
            logger.error(f"HuggingFace generation failed: {e}")
            return ModelResponse(
                content="",
                model_id=self.config.model_id,
                tokens_used=0,
                latency_ms=(time.time() - start_time) * 1000,
                cost=0,
                error=str(e)
            )

    async def stream_generate(self, request: ModelRequest) -> AsyncGenerator[str, None]:
        """流式生成"""
        if not self.pipeline:
            yield "Error: Model not loaded"
            return

        # HuggingFace transformers不原生支持流式，模拟实现
        response = await self.generate(request)

        if response.error:
            yield f"Error: {response.error}"
        else:
            # 分块返回
            words = response.content.split()
            for i in range(0, len(words), 5):
                chunk = " ".join(words[i:i+5])
                yield chunk + " "
                await asyncio.sleep(0.1)  # 模拟流式延迟

# ============================================
# AI模型管理器
# ============================================

class AIModelManager:
    """AI模型管理器"""

    def __init__(self):
        """初始化管理器"""
        self.models: Dict[str, BaseModelInterface] = {}
        self.configs: Dict[str, ModelConfig] = {}
        self.default_model_id: Optional[str] = None
        self.capability_map: Dict[ModelCapability, List[str]] = {}
        self.usage_stats: Dict[str, Dict[str, Any]] = {}

        # 加载预配置模型
        self._load_default_models()

    def _load_default_models(self):
        """加载默认模型配置"""
        default_configs = [
            ModelConfig(
                model_id="gpt-4",
                provider=ModelProvider.OPENAI,
                model_name="gpt-4",
                capabilities=[
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_REVIEW,
                    ModelCapability.REFACTORING,
                    ModelCapability.DOCUMENTATION
                ],
                context_window=8192,
                cost_per_token=0.00003
            ),
            ModelConfig(
                model_id="gpt-3.5-turbo",
                provider=ModelProvider.OPENAI,
                model_name="gpt-3.5-turbo",
                capabilities=[
                    ModelCapability.CODE_COMPLETION,
                    ModelCapability.EXPLANATION,
                    ModelCapability.TESTING
                ],
                context_window=4096,
                cost_per_token=0.000002
            ),
            ModelConfig(
                model_id="claude-3-opus",
                provider=ModelProvider.ANTHROPIC,
                model_name="claude-3-opus-20240229",
                capabilities=[
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_REVIEW,
                    ModelCapability.BUG_DETECTION,
                    ModelCapability.OPTIMIZATION
                ],
                context_window=200000,
                cost_per_token=0.000015
            ),
            ModelConfig(
                model_id="codellama-7b",
                provider=ModelProvider.HUGGINGFACE,
                model_name="codellama/CodeLlama-7b-Python-hf",
                capabilities=[
                    ModelCapability.CODE_GENERATION,
                    ModelCapability.CODE_COMPLETION
                ],
                context_window=4096,
                cost_per_token=0.0
            )
        ]

        for config in default_configs:
            self.register_model(config)

    def register_model(self, config: ModelConfig) -> bool:
        """注册模型"""
        try:
            # 创建接口实例
            if config.provider == ModelProvider.OPENAI:
                interface = OpenAIInterface(config)
            elif config.provider == ModelProvider.ANTHROPIC:
                interface = AnthropicInterface(config)
            elif config.provider == ModelProvider.HUGGINGFACE:
                interface = HuggingFaceInterface(config)
            else:
                logger.warning(f"Unsupported provider: {config.provider}")
                return False

            # 存储
            self.models[config.model_id] = interface
            self.configs[config.model_id] = config

            # 更新能力映射
            for capability in config.capabilities:
                if capability not in self.capability_map:
                    self.capability_map[capability] = []
                self.capability_map[capability].append(config.model_id)

            # 初始化统计
            self.usage_stats[config.model_id] = {
                "requests": 0,
                "tokens": 0,
                "cost": 0,
                "errors": 0,
                "avg_latency": 0
            }

            # 设置默认模型
            if not self.default_model_id:
                self.default_model_id = config.model_id

            logger.info(f"Registered model: {config.model_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to register model {config.model_id}: {e}")
            return False

    async def generate(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        capability: Optional[ModelCapability] = None,
        **kwargs
    ) -> ModelResponse:
        """生成响应"""

        # 选择模型
        if not model_id:
            if capability:
                model_id = self.select_model_for_capability(capability)
            else:
                model_id = self.default_model_id

        if not model_id or model_id not in self.models:
            return ModelResponse(
                content="",
                model_id="",
                tokens_used=0,
                latency_ms=0,
                cost=0,
                error="No model available"
            )

        # 创建请求
        request = ModelRequest(
            prompt=prompt,
            model_id=model_id,
            capability=capability,
            **kwargs
        )

        # 调用模型
        model = self.models[model_id]
        response = await model.generate(request)

        # 更新统计
        self._update_statistics(model_id, response)

        return response

    async def stream_generate(
        self,
        prompt: str,
        model_id: Optional[str] = None,
        capability: Optional[ModelCapability] = None,
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """流式生成"""

        # 选择模型
        if not model_id:
            if capability:
                model_id = self.select_model_for_capability(capability)
            else:
                model_id = self.default_model_id

        if not model_id or model_id not in self.models:
            yield "Error: No model available"
            return

        # 创建请求
        request = ModelRequest(
            prompt=prompt,
            model_id=model_id,
            capability=capability,
            stream=True,
            **kwargs
        )

        # 流式调用
        model = self.models[model_id]
        async for chunk in model.stream_generate(request):
            yield chunk

    def select_model_for_capability(self, capability: ModelCapability) -> Optional[str]:
        """根据能力选择模型"""
        model_ids = self.capability_map.get(capability, [])

        if not model_ids:
            return self.default_model_id

        # 选择成本最低的模型
        best_model_id = None
        lowest_cost = float('inf')

        for model_id in model_ids:
            config = self.configs[model_id]
            if config.cost_per_token < lowest_cost:
                lowest_cost = config.cost_per_token
                best_model_id = model_id

        return best_model_id or model_ids[0]

    def _update_statistics(self, model_id: str, response: ModelResponse):
        """更新统计信息"""
        stats = self.usage_stats.get(model_id, {})

        stats["requests"] += 1
        stats["tokens"] += response.tokens_used
        stats["cost"] += response.cost

        if response.error:
            stats["errors"] += 1

        # 更新平均延迟
        current_avg = stats.get("avg_latency", 0)
        new_avg = (current_avg * (stats["requests"] - 1) + response.latency_ms) / stats["requests"]
        stats["avg_latency"] = new_avg

        self.usage_stats[model_id] = stats

    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "models": list(self.models.keys()),
            "default_model": self.default_model_id,
            "usage": self.usage_stats,
            "capabilities": {
                capability.value: models
                for capability, models in self.capability_map.items()
            }
        }

    async def validate_all_models(self) -> Dict[str, bool]:
        """验证所有模型"""
        results = {}

        for model_id, model in self.models.items():
            results[model_id] = await model.validate()

        return results

    async def close_all(self):
        """关闭所有连接"""
        for model in self.models.values():
            await model.close()

# ============================================
# 单例实例
# ============================================

_model_manager_instance: Optional[AIModelManager] = None

def get_model_manager() -> AIModelManager:
    """获取模型管理器单例"""
    global _model_manager_instance
    if _model_manager_instance is None:
        _model_manager_instance = AIModelManager()
    return _model_manager_instance