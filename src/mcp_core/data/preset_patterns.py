"""
预置模式库数据
包含常见设计模式、反模式、优化模式
"""

import json
import hashlib
from datetime import datetime
from typing import Dict, List, Any

# ============================================
# 设计模式库
# ============================================

DESIGN_PATTERNS = [
    {
        "pattern_name": "Singleton",
        "pattern_type": "design_pattern",
        "pattern_category": "creational",
        "pattern_description": "确保类只有一个实例，并提供全局访问点",
        "pattern_template": """class Singleton:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.initialized = True
            # 初始化代码""",
        "features": [
            {"feature_type": "structural", "feature_name": "class_definition", "feature_value": "Singleton", "weight": 2.0, "confidence": 1.0},
            {"feature_type": "structural", "feature_name": "instance_variable", "feature_value": "_instance", "weight": 1.8, "confidence": 1.0},
            {"feature_type": "semantic", "feature_name": "design_intent", "feature_value": "singleton", "weight": 2.0, "confidence": 1.0}
        ],
        "keywords": ["singleton", "instance", "global", "unique"],
        "tags": ["creational", "object-creation", "global-state"],
        "effectiveness": 0.85,
        "success_rate": 0.90,
        "reusability": 0.95,
        "complexity": 0.3
    },
    {
        "pattern_name": "Factory",
        "pattern_type": "design_pattern",
        "pattern_category": "creational",
        "pattern_description": "定义创建对象的接口，让子类决定实例化哪个类",
        "pattern_template": """class ProductFactory:
    @staticmethod
    def create_product(product_type: str):
        if product_type == "A":
            return ProductA()
        elif product_type == "B":
            return ProductB()
        else:
            raise ValueError(f"Unknown product type: {product_type}")

class Product:
    def operation(self):
        pass

class ProductA(Product):
    def operation(self):
        return "Product A operation"

class ProductB(Product):
    def operation(self):
        return "Product B operation" """,
        "features": [
            {"feature_type": "structural", "feature_name": "factory_method", "feature_value": "create_product", "weight": 2.0, "confidence": 1.0},
            {"feature_type": "semantic", "feature_name": "design_intent", "feature_value": "factory", "weight": 2.0, "confidence": 1.0}
        ],
        "keywords": ["factory", "create", "product", "builder"],
        "tags": ["creational", "object-creation", "polymorphism"],
        "effectiveness": 0.88,
        "success_rate": 0.92,
        "reusability": 0.90,
        "complexity": 0.4
    },
    {
        "pattern_name": "Observer",
        "pattern_type": "design_pattern",
        "pattern_category": "behavioral",
        "pattern_description": "定义对象间的一对多依赖，当一个对象改变时，所有依赖者都会收到通知",
        "pattern_template": """class Subject:
    def __init__(self):
        self._observers = []

    def attach(self, observer):
        self._observers.append(observer)

    def detach(self, observer):
        self._observers.remove(observer)

    def notify(self):
        for observer in self._observers:
            observer.update(self)

class Observer:
    def update(self, subject):
        pass""",
        "features": [
            {"feature_type": "structural", "feature_name": "observer_list", "feature_value": "_observers", "weight": 1.8, "confidence": 1.0},
            {"feature_type": "behavioral", "feature_name": "notification", "feature_value": "notify", "weight": 2.0, "confidence": 1.0}
        ],
        "keywords": ["observer", "subject", "notify", "listener", "event"],
        "tags": ["behavioral", "event-driven", "decoupling"],
        "effectiveness": 0.87,
        "success_rate": 0.89,
        "reusability": 0.85,
        "complexity": 0.5
    },
    {
        "pattern_name": "Strategy",
        "pattern_type": "design_pattern",
        "pattern_category": "behavioral",
        "pattern_description": "定义算法族，分别封装起来，让它们之间可以互相替换",
        "pattern_template": """from abc import ABC, abstractmethod

class Strategy(ABC):
    @abstractmethod
    def execute(self, data):
        pass

class ConcreteStrategyA(Strategy):
    def execute(self, data):
        return f"Strategy A: {data}"

class ConcreteStrategyB(Strategy):
    def execute(self, data):
        return f"Strategy B: {data}"

class Context:
    def __init__(self, strategy: Strategy):
        self._strategy = strategy

    def set_strategy(self, strategy: Strategy):
        self._strategy = strategy

    def execute_strategy(self, data):
        return self._strategy.execute(data)""",
        "features": [
            {"feature_type": "structural", "feature_name": "abstract_class", "feature_value": "Strategy", "weight": 1.8, "confidence": 1.0},
            {"feature_type": "behavioral", "feature_name": "strategy_pattern", "feature_value": "execute", "weight": 2.0, "confidence": 1.0}
        ],
        "keywords": ["strategy", "algorithm", "policy", "behavior"],
        "tags": ["behavioral", "algorithms", "encapsulation"],
        "effectiveness": 0.86,
        "success_rate": 0.88,
        "reusability": 0.92,
        "complexity": 0.6
    },
    {
        "pattern_name": "Decorator",
        "pattern_type": "design_pattern",
        "pattern_category": "structural",
        "pattern_description": "动态地给对象添加额外的职责",
        "pattern_template": """class Component:
    def operation(self):
        pass

class ConcreteComponent(Component):
    def operation(self):
        return "ConcreteComponent"

class Decorator(Component):
    def __init__(self, component: Component):
        self._component = component

    def operation(self):
        return self._component.operation()

class ConcreteDecoratorA(Decorator):
    def operation(self):
        return f"DecoratorA({super().operation()})"

class ConcreteDecoratorB(Decorator):
    def operation(self):
        return f"DecoratorB({super().operation()})" """,
        "features": [
            {"feature_type": "structural", "feature_name": "wrapper", "feature_value": "Decorator", "weight": 2.0, "confidence": 1.0},
            {"feature_type": "behavioral", "feature_name": "delegation", "feature_value": "component.operation", "weight": 1.8, "confidence": 1.0}
        ],
        "keywords": ["decorator", "wrapper", "enhance", "extend"],
        "tags": ["structural", "object-composition", "flexibility"],
        "effectiveness": 0.84,
        "success_rate": 0.86,
        "reusability": 0.88,
        "complexity": 0.5
    }
]

# ============================================
# 反模式库
# ============================================

ANTI_PATTERNS = [
    {
        "pattern_name": "Spaghetti Code",
        "pattern_type": "anti_pattern",
        "pattern_category": "structural",
        "pattern_description": "代码结构混乱，缺乏清晰的架构",
        "pattern_template": """# 反模式示例 - 不要这样做！
def process_data(data):
    result = []
    for item in data:
        if item > 0:
            if item < 10:
                if item % 2 == 0:
                    temp = item * 2
                    if temp > 5:
                        result.append(temp)
                    else:
                        result.append(item)
                else:
                    result.append(item + 1)
            else:
                result.append(item - 1)
        else:
            result.append(0)
    return result""",
        "features": [
            {"feature_type": "quality", "feature_name": "high_complexity", "feature_value": 15, "weight": 0.3, "confidence": 1.0},
            {"feature_type": "quality", "feature_name": "deep_nesting", "feature_value": 5, "weight": 0.3, "confidence": 1.0}
        ],
        "keywords": ["spaghetti", "complex", "tangled", "unstructured"],
        "tags": ["anti-pattern", "complexity", "maintainability"],
        "effectiveness": 0.2,
        "success_rate": 0.3,
        "reusability": 0.1,
        "complexity": 0.9
    },
    {
        "pattern_name": "God Class",
        "pattern_type": "anti_pattern",
        "pattern_category": "structural",
        "pattern_description": "一个类承担了太多职责",
        "pattern_template": """# 反模式示例 - 不要这样做！
class GodClass:
    def __init__(self):
        self.database = None
        self.cache = None
        self.logger = None
        self.config = None
        # ... 太多属性

    def connect_database(self): pass
    def query_data(self): pass
    def update_data(self): pass
    def delete_data(self): pass
    def cache_data(self): pass
    def log_error(self): pass
    def log_info(self): pass
    def load_config(self): pass
    def save_config(self): pass
    def send_email(self): pass
    def generate_report(self): pass
    # ... 太多方法""",
        "features": [
            {"feature_type": "quality", "feature_name": "too_many_methods", "feature_value": 20, "weight": 0.3, "confidence": 1.0},
            {"feature_type": "quality", "feature_name": "low_cohesion", "feature_value": 0.2, "weight": 0.3, "confidence": 1.0}
        ],
        "keywords": ["god", "monolithic", "bloated", "responsibilities"],
        "tags": ["anti-pattern", "coupling", "single-responsibility"],
        "effectiveness": 0.15,
        "success_rate": 0.25,
        "reusability": 0.1,
        "complexity": 0.95
    },
    {
        "pattern_name": "Copy-Paste Programming",
        "pattern_type": "anti_pattern",
        "pattern_category": "behavioral",
        "pattern_description": "通过复制粘贴代码而不是重用",
        "pattern_template": """# 反模式示例 - 不要这样做！
def process_user_data(user_data):
    # 处理用户数据
    result = []
    for item in user_data:
        if item['age'] > 18:
            result.append(item['name'])
    return result

def process_customer_data(customer_data):
    # 几乎相同的代码
    result = []
    for item in customer_data:
        if item['age'] > 18:
            result.append(item['name'])
    return result

def process_employee_data(employee_data):
    # 又是复制粘贴
    result = []
    for item in employee_data:
        if item['age'] > 18:
            result.append(item['name'])
    return result""",
        "features": [
            {"feature_type": "quality", "feature_name": "code_duplication", "feature_value": 3, "weight": 0.3, "confidence": 1.0}
        ],
        "keywords": ["copy", "paste", "duplicate", "redundant"],
        "tags": ["anti-pattern", "duplication", "DRY"],
        "effectiveness": 0.25,
        "success_rate": 0.4,
        "reusability": 0.15,
        "complexity": 0.7
    }
]

# ============================================
# 优化模式库
# ============================================

OPTIMIZATION_PATTERNS = [
    {
        "pattern_name": "Caching",
        "pattern_type": "optimization",
        "pattern_category": "performance",
        "pattern_description": "缓存计算结果以避免重复计算",
        "pattern_template": """from functools import lru_cache

@lru_cache(maxsize=128)
def expensive_computation(n):
    # 模拟耗时计算
    result = 0
    for i in range(n):
        result += i ** 2
    return result

# 或手动实现缓存
class CachedComputation:
    def __init__(self):
        self.cache = {}

    def compute(self, n):
        if n in self.cache:
            return self.cache[n]

        result = self._expensive_computation(n)
        self.cache[n] = result
        return result

    def _expensive_computation(self, n):
        # 实际计算逻辑
        return sum(i ** 2 for i in range(n))""",
        "features": [
            {"feature_type": "behavioral", "feature_name": "caching", "feature_value": "cache", "weight": 2.0, "confidence": 1.0},
            {"feature_type": "quality", "feature_name": "performance", "feature_value": "optimization", "weight": 1.8, "confidence": 1.0}
        ],
        "keywords": ["cache", "memoize", "performance", "optimization"],
        "tags": ["optimization", "performance", "memory-trade-off"],
        "effectiveness": 0.92,
        "success_rate": 0.94,
        "reusability": 0.85,
        "complexity": 0.4
    },
    {
        "pattern_name": "Lazy Loading",
        "pattern_type": "optimization",
        "pattern_category": "performance",
        "pattern_description": "延迟初始化，直到真正需要时才加载",
        "pattern_template": """class LazyProperty:
    def __init__(self, function):
        self.function = function
        self.name = function.__name__

    def __get__(self, obj, type=None):
        if obj is None:
            return self

        value = self.function(obj)
        setattr(obj, self.name, value)
        return value

class DataProcessor:
    def __init__(self, data_source):
        self.data_source = data_source

    @LazyProperty
    def processed_data(self):
        # 只在第一次访问时处理
        print("Processing data...")
        return self._heavy_processing(self.data_source)

    def _heavy_processing(self, data):
        # 模拟耗时处理
        return [d * 2 for d in data]""",
        "features": [
            {"feature_type": "behavioral", "feature_name": "lazy_loading", "feature_value": "lazy", "weight": 2.0, "confidence": 1.0}
        ],
        "keywords": ["lazy", "deferred", "on-demand", "property"],
        "tags": ["optimization", "performance", "initialization"],
        "effectiveness": 0.88,
        "success_rate": 0.90,
        "reusability": 0.82,
        "complexity": 0.5
    },
    {
        "pattern_name": "Object Pooling",
        "pattern_type": "optimization",
        "pattern_category": "performance",
        "pattern_description": "重用对象而不是频繁创建和销毁",
        "pattern_template": """from queue import Queue
import threading

class ObjectPool:
    def __init__(self, create_func, max_size=10):
        self.create_func = create_func
        self.pool = Queue(maxsize=max_size)
        self.lock = threading.Lock()

        # 预创建一些对象
        for _ in range(min(3, max_size)):
            self.pool.put(create_func())

    def acquire(self):
        try:
            # 尝试从池中获取
            return self.pool.get_nowait()
        except:
            # 池为空，创建新对象
            return self.create_func()

    def release(self, obj):
        try:
            # 重置对象状态
            if hasattr(obj, 'reset'):
                obj.reset()
            # 放回池中
            self.pool.put_nowait(obj)
        except:
            # 池已满，丢弃对象
            pass

# 使用示例
class Connection:
    def __init__(self):
        self.active = True

    def reset(self):
        self.active = True

connection_pool = ObjectPool(Connection, max_size=20)""",
        "features": [
            {"feature_type": "structural", "feature_name": "pool", "feature_value": "ObjectPool", "weight": 2.0, "confidence": 1.0}
        ],
        "keywords": ["pool", "reuse", "connection", "resource"],
        "tags": ["optimization", "resource-management", "performance"],
        "effectiveness": 0.90,
        "success_rate": 0.91,
        "reusability": 0.87,
        "complexity": 0.6
    },
    {
        "pattern_name": "Batch Processing",
        "pattern_type": "optimization",
        "pattern_category": "performance",
        "pattern_description": "批量处理数据以减少开销",
        "pattern_template": """def batch_process(items, batch_size=100):
    \"\"\"批量处理项目以提高效率\"\"\"
    results = []

    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        # 批量处理
        batch_results = process_batch(batch)
        results.extend(batch_results)

    return results

def process_batch(batch):
    \"\"\"处理一批数据\"\"\"
    # 批量数据库操作示例
    with database.begin_transaction():
        results = []
        for item in batch:
            result = database.insert(item)
            results.append(result)
        database.commit()
    return results

# 异步批处理
import asyncio

async def async_batch_process(items, batch_size=100):
    tasks = []
    for i in range(0, len(items), batch_size):
        batch = items[i:i + batch_size]
        task = asyncio.create_task(async_process_batch(batch))
        tasks.append(task)

    results = await asyncio.gather(*tasks)
    return [item for batch in results for item in batch]""",
        "features": [
            {"feature_type": "behavioral", "feature_name": "batch_processing", "feature_value": "batch", "weight": 2.0, "confidence": 1.0}
        ],
        "keywords": ["batch", "bulk", "chunk", "group"],
        "tags": ["optimization", "performance", "throughput"],
        "effectiveness": 0.89,
        "success_rate": 0.92,
        "reusability": 0.83,
        "complexity": 0.5
    }
]

# ============================================
# 代码异味模式库
# ============================================

CODE_SMELLS = [
    {
        "pattern_name": "Long Method",
        "pattern_type": "code_smell",
        "pattern_category": "quality",
        "pattern_description": "方法过长，难以理解和维护",
        "pattern_template": """# 代码异味示例 - 需要重构
def process_order(order_data):
    # 验证订单
    if not order_data:
        return None

    # 计算价格
    total = 0
    for item in order_data['items']:
        price = item['price']
        quantity = item['quantity']
        discount = item.get('discount', 0)
        tax = item.get('tax', 0.1)
        subtotal = price * quantity
        subtotal -= subtotal * discount
        subtotal += subtotal * tax
        total += subtotal

    # 检查库存
    for item in order_data['items']:
        stock = check_inventory(item['id'])
        if stock < item['quantity']:
            return {'error': 'Insufficient stock'}

    # 处理支付
    payment_method = order_data['payment_method']
    if payment_method == 'credit_card':
        # ... 信用卡处理逻辑
        pass
    elif payment_method == 'paypal':
        # ... PayPal处理逻辑
        pass

    # 更新库存
    # ... 更多代码

    # 发送确认邮件
    # ... 更多代码

    return {'success': True, 'total': total}""",
        "features": [
            {"feature_type": "quality", "feature_name": "long_method", "feature_value": 50, "weight": 0.5, "confidence": 1.0}
        ],
        "keywords": ["long", "method", "function", "refactor"],
        "tags": ["code-smell", "maintainability", "readability"],
        "effectiveness": 0.3,
        "success_rate": 0.5,
        "reusability": 0.2,
        "complexity": 0.8
    },
    {
        "pattern_name": "Magic Numbers",
        "pattern_type": "code_smell",
        "pattern_category": "quality",
        "pattern_description": "代码中使用未解释的数字常量",
        "pattern_template": """# 代码异味示例 - 需要重构
def calculate_shipping(weight, distance):
    if weight > 50:  # 魔法数字
        return distance * 0.5  # 魔法数字
    elif weight > 20:  # 魔法数字
        return distance * 0.3  # 魔法数字
    else:
        return distance * 0.1  # 魔法数字

# 改进版本
class ShippingConstants:
    HEAVY_WEIGHT_THRESHOLD = 50
    MEDIUM_WEIGHT_THRESHOLD = 20
    HEAVY_RATE = 0.5
    MEDIUM_RATE = 0.3
    LIGHT_RATE = 0.1

def calculate_shipping_improved(weight, distance):
    if weight > ShippingConstants.HEAVY_WEIGHT_THRESHOLD:
        return distance * ShippingConstants.HEAVY_RATE
    elif weight > ShippingConstants.MEDIUM_WEIGHT_THRESHOLD:
        return distance * ShippingConstants.MEDIUM_RATE
    else:
        return distance * ShippingConstants.LIGHT_RATE""",
        "features": [
            {"feature_type": "quality", "feature_name": "magic_numbers", "feature_value": 5, "weight": 0.4, "confidence": 1.0}
        ],
        "keywords": ["magic", "number", "constant", "literal"],
        "tags": ["code-smell", "readability", "maintainability"],
        "effectiveness": 0.4,
        "success_rate": 0.6,
        "reusability": 0.3,
        "complexity": 0.3
    }
]

# ============================================
# 生成预置模式库
# ============================================

def generate_pattern_id(pattern_name: str) -> str:
    """生成模式ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    hash_suffix = hashlib.md5(pattern_name.encode()).hexdigest()[:8]
    return f"preset_{timestamp}_{hash_suffix}"

def prepare_pattern_data(patterns: List[Dict], pattern_source: str) -> List[Dict]:
    """准备模式数据用于插入数据库"""
    prepared_patterns = []

    for pattern in patterns:
        pattern_data = pattern.copy()
        pattern_data['pattern_id'] = generate_pattern_id(pattern['pattern_name'])
        pattern_data['pattern_signature'] = hashlib.md5(
            pattern['pattern_template'].encode()
        ).hexdigest()
        pattern_data['pattern_source'] = pattern_source
        pattern_data['usage_count'] = 0
        pattern_data['evolution_stage'] = 1
        pattern_data['created_at'] = datetime.now().isoformat()
        pattern_data['updated_at'] = datetime.now().isoformat()

        prepared_patterns.append(pattern_data)

    return prepared_patterns

def export_patterns_to_json(filename: str = "preset_patterns.json"):
    """导出所有预置模式到JSON文件"""
    all_patterns = {
        "design_patterns": prepare_pattern_data(DESIGN_PATTERNS, "preset_design"),
        "anti_patterns": prepare_pattern_data(ANTI_PATTERNS, "preset_anti"),
        "optimization_patterns": prepare_pattern_data(OPTIMIZATION_PATTERNS, "preset_optimization"),
        "code_smells": prepare_pattern_data(CODE_SMELLS, "preset_smell"),
        "metadata": {
            "version": "1.0.0",
            "created_at": datetime.now().isoformat(),
            "total_patterns": len(DESIGN_PATTERNS) + len(ANTI_PATTERNS) +
                            len(OPTIMIZATION_PATTERNS) + len(CODE_SMELLS)
        }
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(all_patterns, f, ensure_ascii=False, indent=2)

    print(f"预置模式库已导出到 {filename}")
    print(f"总计 {all_patterns['metadata']['total_patterns']} 个模式")
    return all_patterns

def load_patterns_to_database():
    """加载预置模式到数据库"""
    from ..services.pattern_recognizer import get_pattern_recognizer

    recognizer = get_pattern_recognizer()

    # 加载所有模式
    all_patterns = []
    all_patterns.extend(prepare_pattern_data(DESIGN_PATTERNS, "preset_design"))
    all_patterns.extend(prepare_pattern_data(ANTI_PATTERNS, "preset_anti"))
    all_patterns.extend(prepare_pattern_data(OPTIMIZATION_PATTERNS, "preset_optimization"))
    all_patterns.extend(prepare_pattern_data(CODE_SMELLS, "preset_smell"))

    # 存储到模式识别器
    for pattern_data in all_patterns:
        pattern = recognizer.create_pattern(
            pattern_type=pattern_data['pattern_type'],
            pattern_name=pattern_data['pattern_name'],
            description=pattern_data['pattern_description']
        )

        # 设置所有属性
        for key, value in pattern_data.items():
            if hasattr(pattern, key):
                setattr(pattern, key, value)

        # 添加到模式库
        recognizer.patterns[pattern.pattern_id] = pattern
        recognizer.pattern_index[pattern.pattern_type].add(pattern.pattern_id)

    print(f"已加载 {len(all_patterns)} 个预置模式到数据库")
    return len(all_patterns)

if __name__ == "__main__":
    # 导出到JSON文件
    export_patterns_to_json("/Users/mac/Downloads/MCP/data/preset_patterns.json")