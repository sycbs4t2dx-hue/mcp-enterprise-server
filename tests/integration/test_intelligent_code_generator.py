"""
智能代码生成器测试
"""

import asyncio
import json
from typing import Dict, Any

from src.mcp_core.services.intelligent_code_generator import (
    IntelligentCodeGenerator,
    GenerationRequest,
    GenerationContext,
    GenerationType,
    CodeStyle
)
from src.mcp_core.common.logger import get_logger

logger = get_logger(__name__)

# ============================================
# 测试用例
# ============================================

async def test_function_generation():
    """测试函数生成"""
    generator = IntelligentCodeGenerator()

    context = GenerationContext(
        type=GenerationType.FUNCTION,
        language="python",
        style=CodeStyle.PEP8,
        constraints=[
            "Must handle edge cases",
            "Include input validation",
            "Add comprehensive docstring"
        ]
    )

    request = GenerationRequest(
        prompt="Create a function to calculate fibonacci number with memoization",
        context=context,
        project_id="test_project",
        auto_test=True,
        auto_optimize=True
    )

    result = await generator.generate(request)

    print("=" * 60)
    print("FUNCTION GENERATION TEST")
    print("=" * 60)
    print(f"Generated Code:\n{result.code}")
    print(f"\nQuality Score: {result.quality_score:.2f}")
    print(f"Optimizations: {result.optimizations_applied}")
    print(f"Test Results: {result.test_results}")
    print(f"Security: {result.security_checks}")

    return result

async def test_class_generation():
    """测试类生成"""
    generator = IntelligentCodeGenerator()

    context = GenerationContext(
        type=GenerationType.CLASS,
        language="python",
        style=CodeStyle.GOOGLE,
        patterns=["singleton", "observer"],
        constraints=[
            "Thread-safe implementation",
            "Support async operations"
        ]
    )

    request = GenerationRequest(
        prompt="Create a database connection pool manager class",
        context=context,
        project_id="test_project",
        auto_test=True
    )

    result = await generator.generate(request)

    print("\n" + "=" * 60)
    print("CLASS GENERATION TEST")
    print("=" * 60)
    print(f"Generated Code:\n{result.code}")
    print(f"\nQuality Score: {result.quality_score:.2f}")
    print(f"Patterns Used: {result.patterns_used}")

    return result

async def test_api_endpoint_generation():
    """测试API端点生成"""
    generator = IntelligentCodeGenerator()

    context = GenerationContext(
        type=GenerationType.API_ENDPOINT,
        language="python",
        framework="fastapi",
        style=CodeStyle.PEP8,
        security_requirements=[
            "JWT authentication",
            "Rate limiting",
            "Input validation"
        ]
    )

    request = GenerationRequest(
        prompt="Create a REST API endpoint for user registration with email verification",
        context=context,
        project_id="test_project",
        reference_code="""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI()

class User(BaseModel):
    username: str
    email: str
"""
    )

    result = await generator.generate(request)

    print("\n" + "=" * 60)
    print("API ENDPOINT GENERATION TEST")
    print("=" * 60)
    print(f"Generated Code:\n{result.code}")
    print(f"\nQuality Score: {result.quality_score:.2f}")
    print(f"Documentation:\n{result.documentation}")

    return result

async def test_test_generation():
    """测试用例生成"""
    generator = IntelligentCodeGenerator()

    reference_code = """
def calculate_discount(price, discount_percent):
    if price < 0 or discount_percent < 0 or discount_percent > 100:
        raise ValueError("Invalid input")

    discount_amount = price * (discount_percent / 100)
    final_price = price - discount_amount
    return final_price
"""

    context = GenerationContext(
        type=GenerationType.TEST,
        language="python",
        framework="pytest",
        style=CodeStyle.PEP8,
        test_requirements={
            "coverage": "100%",
            "edge_cases": True,
            "performance": True
        }
    )

    request = GenerationRequest(
        prompt="Generate comprehensive test cases for the calculate_discount function",
        context=context,
        project_id="test_project",
        reference_code=reference_code
    )

    result = await generator.generate(request)

    print("\n" + "=" * 60)
    print("TEST GENERATION TEST")
    print("=" * 60)
    print(f"Generated Tests:\n{result.code}")
    print(f"\nQuality Score: {result.quality_score:.2f}")

    return result

async def test_refactoring():
    """测试代码重构"""
    generator = IntelligentCodeGenerator()

    old_code = """
def process_data(data):
    result = []
    for i in range(len(data)):
        if data[i] > 0:
            temp = data[i] * 2
            if temp < 100:
                result.append(temp)
    return result
"""

    context = GenerationContext(
        type=GenerationType.REFACTOR,
        language="python",
        style=CodeStyle.PEP8,
        constraints=[
            "Use list comprehension",
            "Add type hints",
            "Improve readability"
        ]
    )

    request = GenerationRequest(
        prompt="Refactor this code to be more Pythonic and efficient",
        context=context,
        project_id="test_project",
        reference_code=old_code,
        auto_optimize=True
    )

    result = await generator.generate(request)

    print("\n" + "=" * 60)
    print("REFACTORING TEST")
    print("=" * 60)
    print(f"Original Code:\n{old_code}")
    print(f"\nRefactored Code:\n{result.code}")
    print(f"\nQuality Score: {result.quality_score:.2f}")
    print(f"Optimizations: {result.optimizations_applied}")

    return result

async def test_ui_component_generation():
    """测试UI组件生成"""
    generator = IntelligentCodeGenerator()

    context = GenerationContext(
        type=GenerationType.UI_COMPONENT,
        language="typescript",
        framework="react",
        style=CodeStyle.AIRBNB,
        dependencies=["react", "antd", "@types/react"],
        constraints=[
            "Must be responsive",
            "Support dark mode",
            "Include loading states"
        ]
    )

    request = GenerationRequest(
        prompt="Create a data table component with sorting, filtering, and pagination",
        context=context,
        project_id="test_project",
        examples=[{
            "input": "columns = ['name', 'age', 'email']",
            "output": "<DataTable columns={columns} data={users} />"
        }]
    )

    result = await generator.generate(request)

    print("\n" + "=" * 60)
    print("UI COMPONENT GENERATION TEST")
    print("=" * 60)
    print(f"Generated Component:\n{result.code}")
    print(f"\nQuality Score: {result.quality_score:.2f}")

    return result

async def test_optimization():
    """测试代码优化"""
    generator = IntelligentCodeGenerator()

    slow_code = """
def find_duplicates(nums):
    duplicates = []
    for i in range(len(nums)):
        for j in range(i + 1, len(nums)):
            if nums[i] == nums[j] and nums[i] not in duplicates:
                duplicates.append(nums[i])
    return duplicates
"""

    context = GenerationContext(
        type=GenerationType.OPTIMIZATION,
        language="python",
        style=CodeStyle.PEP8,
        performance_targets={
            "time_complexity": "O(n)",
            "space_complexity": "O(n)"
        }
    )

    request = GenerationRequest(
        prompt="Optimize this function to have better time complexity",
        context=context,
        project_id="test_project",
        reference_code=slow_code,
        auto_optimize=True
    )

    result = await generator.generate(request)

    print("\n" + "=" * 60)
    print("OPTIMIZATION TEST")
    print("=" * 60)
    print(f"Original Code:\n{slow_code}")
    print(f"\nOptimized Code:\n{result.code}")
    print(f"\nQuality Score: {result.quality_score:.2f}")
    print(f"Optimizations Applied: {result.optimizations_applied}")

    return result

async def test_documentation_generation():
    """测试文档生成"""
    generator = IntelligentCodeGenerator()

    code_to_document = """
class EventBus:
    def __init__(self):
        self._events = {}

    def on(self, event, callback):
        if event not in self._events:
            self._events[event] = []
        self._events[event].append(callback)

    def emit(self, event, data=None):
        if event in self._events:
            for callback in self._events[event]:
                callback(data)

    def off(self, event, callback):
        if event in self._events:
            self._events[event].remove(callback)
"""

    context = GenerationContext(
        type=GenerationType.DOCUMENTATION,
        language="python",
        style=CodeStyle.GOOGLE
    )

    request = GenerationRequest(
        prompt="Generate comprehensive documentation for this EventBus class",
        context=context,
        project_id="test_project",
        reference_code=code_to_document
    )

    result = await generator.generate(request)

    print("\n" + "=" * 60)
    print("DOCUMENTATION GENERATION TEST")
    print("=" * 60)
    print(f"Generated Documentation:\n{result.documentation}")
    print(f"\nQuality Score: {result.quality_score:.2f}")

    return result

async def run_performance_test():
    """运行性能测试"""
    generator = IntelligentCodeGenerator()

    print("\n" + "=" * 60)
    print("PERFORMANCE TEST")
    print("=" * 60)

    # 测试批量生成
    import time
    start_time = time.time()

    tasks = []
    for i in range(5):
        context = GenerationContext(
            type=GenerationType.FUNCTION,
            language="python",
            style=CodeStyle.PEP8
        )

        request = GenerationRequest(
            prompt=f"Create a function to validate email address (version {i})",
            context=context,
            project_id="test_project",
            max_iterations=1,  # 减少迭代次数以加快测试
            auto_test=False,
            auto_optimize=False
        )

        tasks.append(generator.generate(request))

    results = await asyncio.gather(*tasks)

    elapsed_time = time.time() - start_time

    print(f"Generated {len(results)} functions in {elapsed_time:.2f} seconds")
    print(f"Average time per generation: {elapsed_time/len(results):.2f} seconds")
    print(f"Average quality score: {sum(r.quality_score for r in results)/len(results):.2f}")

# ============================================
# 主测试运行器
# ============================================

async def main():
    """运行所有测试"""
    print("=" * 60)
    print("INTELLIGENT CODE GENERATOR TEST SUITE")
    print("=" * 60)

    try:
        # 运行各种生成测试
        await test_function_generation()
        await test_class_generation()
        await test_api_endpoint_generation()
        await test_test_generation()
        await test_refactoring()
        await test_ui_component_generation()
        await test_optimization()
        await test_documentation_generation()

        # 运行性能测试
        await run_performance_test()

        print("\n" + "=" * 60)
        print("ALL TESTS COMPLETED SUCCESSFULLY!")
        print("=" * 60)

    except Exception as e:
        logger.error(f"Test failed: {e}")
        print(f"\n❌ Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())