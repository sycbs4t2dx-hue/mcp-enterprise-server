#!/usr/bin/env python3
"""
Vue.js代码分析器

解析Vue单文件组件(.vue)，提取组件、方法、属性等信息
"""

import os
import re
import json
from typing import List, Tuple, Dict, Any, Optional
from pathlib import Path

from .code_analyzer import CodeEntity, CodeRelation


class VueCodeAnalyzer:
    """Vue.js代码分析器"""

    def __init__(self, file_path: str, project_root: str):
        self.file_path = file_path
        self.project_root = project_root
        self.relative_path = os.path.relpath(file_path, project_root)

        # 存储
        self.entities: List[CodeEntity] = []
        self.relations: List[CodeRelation] = []

        # 组件信息
        self.component_name: Optional[str] = None

    def analyze(self, source_code: str) -> Tuple[List[CodeEntity], List[CodeRelation]]:
        """分析Vue源代码"""
        try:
            # 解析Vue文件的三个部分
            template = self._extract_section(source_code, 'template')
            script = self._extract_section(source_code, 'script')
            style = self._extract_section(source_code, 'style')

            # 从文件名推断组件名
            self.component_name = Path(self.file_path).stem

            # 创建组件实体
            component_id = self._create_component_entity()

            # 分析script部分
            if script:
                self._analyze_script(script, component_id)

            # 分析template部分
            if template:
                self._analyze_template(template, component_id)

            return self.entities, self.relations

        except Exception as e:
            print(f"⚠️  Vue分析失败 {self.file_path}: {e}")
            return [], []

    def _generate_id(self, type_str: str, name: str) -> str:
        """生成唯一ID"""
        import hashlib
        key = f"{self.relative_path}:{type_str}:{name}"
        return hashlib.md5(key.encode()).hexdigest()[:16]

    def _extract_section(self, content: str, tag: str) -> Optional[str]:
        """提取Vue文件的特定section"""
        # 匹配 <template>...</template> 或 <script>...</script>
        pattern = f'<{tag}[^>]*>(.*?)</{tag}>'
        match = re.search(pattern, content, re.DOTALL)
        return match.group(1).strip() if match else None

    def _create_component_entity(self) -> str:
        """创建组件实体"""
        entity_id = self._generate_id("component", self.component_name)

        entity = CodeEntity(
            id=entity_id,
            type="component",
            name=self.component_name,
            qualified_name=self.component_name,
            file_path=self.relative_path,
            line_number=1,
            end_line=0,
            metadata={
                "framework": "vue",
                "has_template": False,
                "has_script": False,
                "has_style": False
            }
        )

        self.entities.append(entity)
        return entity_id

    def _analyze_script(self, script_content: str, component_id: str):
        """分析script部分"""

        # 检测Vue 3 Composition API还是Options API
        is_composition_api = 'setup(' in script_content or '<script setup>' in script_content

        if is_composition_api:
            self._analyze_composition_api(script_content, component_id)
        else:
            self._analyze_options_api(script_content, component_id)

    def _analyze_options_api(self, script: str, component_id: str):
        """分析Vue Options API"""

        # 提取export default
        export_match = re.search(r'export\s+default\s*\{(.*)\}', script, re.DOTALL)
        if not export_match:
            return

        options_str = export_match.group(1)

        # 提取name
        name_match = re.search(r'name\s*:\s*[\'"]([^"\']+)[\'"]', options_str)
        if name_match:
            self.component_name = name_match.group(1)

        # 提取data
        self._extract_data(options_str, component_id)

        # 提取computed
        self._extract_computed(options_str, component_id)

        # 提取methods
        self._extract_methods(options_str, component_id)

        # 提取props
        self._extract_props(options_str, component_id)

        # 提取components
        self._extract_components(options_str, component_id)

    def _extract_data(self, options: str, component_id: str):
        """提取data属性"""
        data_match = re.search(r'data\s*\(\s*\)\s*\{[^}]*return\s*\{([^}]+)\}', options, re.DOTALL)
        if data_match:
            data_str = data_match.group(1)
            # 简单解析，提取属性名
            props = re.findall(r'(\w+)\s*:', data_str)
            for prop in props:
                entity_id = self._generate_id("data", prop)
                entity = CodeEntity(
                    id=entity_id,
                    type="variable",
                    name=prop,
                    qualified_name=f"{self.component_name}.{prop}",
                    file_path=self.relative_path,
                    line_number=0,
                    end_line=0,
                    parent_id=component_id,
                    metadata={"vue_type": "data"}
                )
                self.entities.append(entity)

                self.relations.append(CodeRelation(
                    source_id=component_id,
                    target_id=entity_id,
                    relation_type="contains",
                    metadata={"type": "data"}
                ))

    def _extract_computed(self, options: str, component_id: str):
        """提取computed属性"""
        computed_match = re.search(r'computed\s*:\s*\{([^}]+)\}', options, re.DOTALL)
        if computed_match:
            computed_str = computed_match.group(1)
            # 提取computed属性名
            props = re.findall(r'(\w+)\s*\(', computed_str)
            for prop in props:
                entity_id = self._generate_id("computed", prop)
                entity = CodeEntity(
                    id=entity_id,
                    type="function",
                    name=prop,
                    qualified_name=f"{self.component_name}.{prop}",
                    file_path=self.relative_path,
                    line_number=0,
                    end_line=0,
                    parent_id=component_id,
                    metadata={"vue_type": "computed"}
                )
                self.entities.append(entity)

                self.relations.append(CodeRelation(
                    source_id=component_id,
                    target_id=entity_id,
                    relation_type="contains",
                    metadata={"type": "computed"}
                ))

    def _extract_methods(self, options: str, component_id: str):
        """提取methods"""
        methods_match = re.search(r'methods\s*:\s*\{([^}]+)\}', options, re.DOTALL)
        if methods_match:
            methods_str = methods_match.group(1)
            # 提取方法名
            methods = re.findall(r'(\w+)\s*\([^)]*\)', methods_str)
            for method in methods:
                entity_id = self._generate_id("method", method)
                entity = CodeEntity(
                    id=entity_id,
                    type="function",
                    name=method,
                    qualified_name=f"{self.component_name}.{method}",
                    file_path=self.relative_path,
                    line_number=0,
                    end_line=0,
                    parent_id=component_id,
                    signature=f"{method}()",
                    metadata={"vue_type": "method"}
                )
                self.entities.append(entity)

                self.relations.append(CodeRelation(
                    source_id=component_id,
                    target_id=entity_id,
                    relation_type="contains",
                    metadata={"type": "method"}
                ))

    def _extract_props(self, options: str, component_id: str):
        """提取props"""
        # props可能是数组或对象
        props_match = re.search(r'props\s*:\s*(\[.*?\]|\{.*?\})', options, re.DOTALL)
        if props_match:
            props_str = props_match.group(1)
            # 简单提取
            if props_str.startswith('['):
                # 数组形式: props: ['name', 'age']
                props = re.findall(r'[\'"](\w+)[\'"]', props_str)
            else:
                # 对象形式: props: { name: String, age: Number }
                props = re.findall(r'(\w+)\s*:', props_str)

            for prop in props:
                # 创建prop关系（作为组件的输入）
                self.relations.append(CodeRelation(
                    source_id="parent",  # 父组件
                    target_id=component_id,
                    relation_type="props",
                    metadata={"prop_name": prop}
                ))

    def _extract_components(self, options: str, component_id: str):
        """提取子组件引用"""
        components_match = re.search(r'components\s*:\s*\{([^}]+)\}', options, re.DOTALL)
        if components_match:
            components_str = components_match.group(1)
            # 提取组件名
            comps = re.findall(r'(\w+)', components_str)
            for comp in comps:
                self.relations.append(CodeRelation(
                    source_id=component_id,
                    target_id=comp,  # 组件名
                    relation_type="imports",
                    metadata={"type": "component"}
                ))

    def _analyze_composition_api(self, script: str, component_id: str):
        """分析Vue 3 Composition API"""
        # 提取setup()内容
        setup_match = re.search(r'setup\s*\([^)]*\)\s*\{(.*)\}', script, re.DOTALL)
        if not setup_match:
            # 可能是<script setup>语法糖
            return

        setup_content = setup_match.group(1)

        # 提取ref/reactive定义
        refs = re.findall(r'const\s+(\w+)\s*=\s*ref\(', setup_content)
        for ref_name in refs:
            entity_id = self._generate_id("ref", ref_name)
            entity = CodeEntity(
                id=entity_id,
                type="variable",
                name=ref_name,
                qualified_name=f"{self.component_name}.{ref_name}",
                file_path=self.relative_path,
                line_number=0,
                end_line=0,
                parent_id=component_id,
                metadata={"vue_type": "ref"}
            )
            self.entities.append(entity)

        # 提取函数定义
        funcs = re.findall(r'const\s+(\w+)\s*=\s*\([^)]*\)\s*=>', setup_content)
        for func_name in funcs:
            entity_id = self._generate_id("function", func_name)
            entity = CodeEntity(
                id=entity_id,
                type="function",
                name=func_name,
                qualified_name=f"{self.component_name}.{func_name}",
                file_path=self.relative_path,
                line_number=0,
                end_line=0,
                parent_id=component_id,
                metadata={"vue_type": "composable"}
            )
            self.entities.append(entity)

    def _analyze_template(self, template: str, component_id: str):
        """分析template部分"""
        # 提取使用的组件
        component_tags = re.findall(r'<([A-Z][a-zA-Z0-9-]*)', template)
        for tag in set(component_tags):
            self.relations.append(CodeRelation(
                source_id=component_id,
                target_id=tag,
                relation_type="uses",
                metadata={"type": "component_in_template"}
            ))

        # 提取v-on事件
        events = re.findall(r'@(\w+)=', template)
        for event in set(events):
            # 这些事件对应methods中的方法
            pass

        # 提取v-bind属性
        bindings = re.findall(r':(\w+)=', template)
        for binding in set(bindings):
            # 这些绑定对应data或computed
            pass


# ==================== 测试代码 ====================

def test_vue_analyzer():
    """测试Vue分析器"""

    vue_code = """
<template>
  <div class="user-profile">
    <h1>{{ user.name }}</h1>
    <UserAvatar :user="user" @click="handleClick" />
    <button @click="saveUser">Save</button>
  </div>
</template>

<script>
import UserAvatar from './UserAvatar.vue'

export default {
  name: 'UserProfile',

  components: {
    UserAvatar
  },

  props: ['userId'],

  data() {
    return {
      user: null,
      loading: false
    }
  },

  computed: {
    displayName() {
      return this.user ? this.user.name : 'Guest'
    }
  },

  methods: {
    async fetchUser() {
      this.loading = true
      this.user = await api.getUser(this.userId)
      this.loading = false
    },

    saveUser() {
      api.updateUser(this.user)
    },

    handleClick() {
      console.log('Clicked')
    }
  },

  mounted() {
    this.fetchUser()
  }
}
</script>

<style scoped>
.user-profile {
  padding: 20px;
}
</style>
"""

    analyzer = VueCodeAnalyzer("components/UserProfile.vue", "src")
    entities, relations = analyzer.analyze(vue_code)

    print("=" * 60)
    print("Vue.js代码分析测试")
    print("=" * 60)

    print(f"\n提取实体: {len(entities)}个")
    for entity in entities:
        print(f"  - {entity.type}: {entity.name}")
        if entity.metadata:
            vue_type = entity.metadata.get('vue_type')
            if vue_type:
                print(f"    类型: {vue_type}")

    print(f"\n提取关系: {len(relations)}个")
    for relation in relations:
        print(f"  - {relation.relation_type}")


if __name__ == "__main__":
    test_vue_analyzer()
