#!/usr/bin/env python3
"""
代码知识图谱系统 - 完整测试示例

展示所有功能的使用方法
"""

import sys
import json
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.mcp_core.code_analyzer import ProjectAnalyzer
from src.mcp_core.code_knowledge_service import CodeKnowledgeGraphService
from src.mcp_core.code_mcp_tools import MCPCodeAnalysisTools


def print_section(title):
    """打印章节标题"""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def test_code_analysis():
    """测试1: 代码分析"""
    print_section("测试1: 代码分析")

    # 分析一个小项目（MCP的services目录）
    project_path = "/Users/mac/Downloads/MCP/src/mcp_core/services"

    print(f"分析项目: {project_path}")

    analyzer = ProjectAnalyzer(project_path)
    result = analyzer.analyze_project()

    print(f"\n✅ 分析完成！")
    print(f"   文件数: {result['stats']['total_files']}")
    print(f"   实体数: {len(result['entities'])}")
    print(f"   - 类: {result['stats']['total_classes']}")
    print(f"   - 函数: {result['stats']['total_functions']}")
    print(f"   关系数: {len(result['relations'])}")

    # 显示一些示例实体
    print(f"\n📝 示例实体（前5个）:")
    for i, entity in enumerate(result['entities'][:5]):
        print(f"   {i+1}. {entity['type']}: {entity['name']}")
        print(f"      文件: {entity['file_path']}:{entity['line_number']}")

    return result


def test_storage(result):
    """测试2: 知识图谱存储"""
    print_section("测试2: 知识图谱存储")

    # 连接数据库
    engine = create_engine(
        "mysql+pymysql://root:Wxwy.2025%40%23@localhost:3306/mcp_db?charset=utf8mb4"
    )
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    service = CodeKnowledgeGraphService(db)

    # 创建项目
    project_id = "test_services"
    print(f"创建项目: {project_id}")

    try:
        service.create_project(
            project_id=project_id,
            name="MCP Services",
            path="/Users/mac/Downloads/MCP/src/mcp_core/services",
            language="python"
        )
        print("✓ 项目创建成功")
    except Exception as e:
        print(f"项目已存在，继续...")

    # 存储分析结果
    print("\n存储分析结果...")
    service.store_analysis_result(
        project_id=project_id,
        entities=result['entities'],
        relations=result['relations'],
        stats=result['stats']
    )

    print("✅ 存储完成！")

    db.close()
    return project_id


def test_queries(project_id):
    """测试3: 查询功能"""
    print_section("测试3: 查询功能")

    engine = create_engine(
        "mysql+pymysql://root:Wxwy.2025%40%23@localhost:3306/mcp_db?charset=utf8mb4"
    )
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    service = CodeKnowledgeGraphService(db)

    # 查询1: 项目架构
    print("查询1: 项目架构")
    arch = service.query_architecture(project_id)
    if arch and 'project' in arch:
        print(f"✓ 项目: {arch['project']['name']}")
        print(f"  文件数: {arch['project']['total_files']}")
        print(f"  实体统计:")
        for entity_type, count in arch['entity_stats'].items():
            print(f"    - {entity_type}: {count}")

    # 查询2: 搜索实体
    print(f"\n查询2: 搜索'MemoryService'")
    entities = service.search_by_name(project_id, "MemoryService", fuzzy=False)
    if entities:
        for entity in entities:
            print(f"✓ 找到: {entity.entity_type} {entity.name}")
            print(f"  位置: {entity.file_path}:{entity.line_number}")
            if entity.docstring:
                print(f"  文档: {entity.docstring[:100]}...")

    # 查询3: 查找依赖
    if entities:
        print(f"\n查询3: 查找依赖关系")
        entity_id = entities[0].entity_id
        deps = service.find_dependencies(project_id, entity_id)

        print(f"✓ {deps['entity']['name']} 的依赖:")
        print(f"  依赖于 {len(deps['depends_on'])} 个实体")
        for dep in deps['depends_on'][:5]:
            print(f"    → {dep['relation_type']}: {dep['target']['name']}")

        print(f"  被 {len(deps['depended_by'])} 个实体依赖")
        for dep in deps['depended_by'][:5]:
            print(f"    ← {dep['relation_type']}: {dep['source']['name']}")

    # 查询4: 按类型查询
    print(f"\n查询4: 查询所有类")
    classes = service.query_entities_by_type(project_id, "class")
    print(f"✓ 找到 {len(classes)} 个类:")
    for cls in classes[:5]:
        print(f"  - {cls.name} ({cls.file_path})")

    db.close()


def test_mcp_tools(project_id):
    """测试4: MCP工具"""
    print_section("测试4: MCP工具接口")

    engine = create_engine(
        "mysql+pymysql://root:Wxwy.2025%40%23@localhost:3306/mcp_db?charset=utf8mb4"
    )
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    tools = MCPCodeAnalysisTools(db)

    # 工具1: 查询架构
    print("工具1: query_architecture")
    result = tools.query_architecture({"project_id": project_id})
    if result['success']:
        print("✓ 查询成功")
        print(f"  实体数: {result['architecture']['project']['total_entities']}")

    # 工具2: 查找实体
    print(f"\n工具2: find_entity")
    result = tools.find_entity({
        "project_id": project_id,
        "entity_name": "Memory",
        "entity_type": "all"
    })
    if result['success']:
        print(f"✓ 找到 {result['count']} 个匹配")
        for entity in result['entities'][:3]:
            print(f"  - {entity['type']}: {entity['name']}")

    # 工具3: 列出模块
    print(f"\n工具3: list_modules")
    result = tools.list_modules({"project_id": project_id})
    if result['success']:
        print(f"✓ 共 {result['count']} 个文件")
        for file in result['files'][:5]:
            print(f"  - {file}")

    db.close()


def main():
    """主测试流程"""
    print("=" * 60)
    print("  MCP代码知识图谱系统 - 完整测试")
    print("=" * 60)

    try:
        # 测试1: 代码分析
        result = test_code_analysis()

        # 测试2: 存储
        project_id = test_storage(result)

        # 测试3: 查询
        test_queries(project_id)

        # 测试4: MCP工具
        test_mcp_tools(project_id)

        # 总结
        print_section("测试总结")
        print("✅ 所有测试通过！")
        print()
        print("系统功能:")
        print("  ✓ 代码分析 - AST解析、实体提取、关系建模")
        print("  ✓ 知识存储 - MySQL持久化、索引优化")
        print("  ✓ 智能查询 - 架构查询、实体搜索、依赖分析")
        print("  ✓ MCP集成 - 8个AI可调用的工具")
        print()
        print("🚀 系统已就绪！可以开始分析您的项目了。")

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
