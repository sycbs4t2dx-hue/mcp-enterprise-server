"""
JavaScript/TypeScript分析器测试套件
"""

import pytest
import tempfile
import os
from pathlib import Path
from typing import List, Tuple

from src.mcp_core.js_ts_analyzer import JavaScriptTypeScriptAnalyzer
from src.mcp_core.models.code_entity import CodeEntity, CodeRelation


class TestJavaScriptTypeScriptAnalyzer:
    """JavaScript/TypeScript分析器测试"""

    @pytest.fixture
    def temp_dir(self):
        """创建临时目录"""
        with tempfile.TemporaryDirectory() as td:
            yield Path(td)

    @pytest.fixture
    def analyzer(self, temp_dir):
        """创建分析器实例"""
        test_file = temp_dir / "test.js"
        test_file.write_text("")
        return JavaScriptTypeScriptAnalyzer(str(test_file), str(temp_dir))

    def test_analyze_es6_class(self, temp_dir):
        """测试ES6类分析"""
        code = """
        export default class UserManager {
            constructor(database) {
                this.db = database;
                this.users = [];
            }

            async addUser(user) {
                this.users.push(user);
                await this.db.save(user);
                return user.id;
            }

            getUser(id) {
                return this.users.find(u => u.id === id);
            }

            static createDefaultUser() {
                return { id: 0, name: 'Guest' };
            }
        }
        """

        test_file = temp_dir / "user_manager.js"
        test_file.write_text(code)

        analyzer = JavaScriptTypeScriptAnalyzer(str(test_file), str(temp_dir))
        entities, relations = analyzer.analyze(code)

        # 验证类实体
        class_entities = [e for e in entities if e.type == "class"]
        assert len(class_entities) == 1
        assert class_entities[0].name == "UserManager"

        # 验证方法
        method_entities = [e for e in entities if e.type == "method"]
        assert len(method_entities) == 3  # addUser, getUser, createDefaultUser
        method_names = {e.name for e in method_entities}
        assert "addUser" in method_names
        assert "getUser" in method_names
        assert "createDefaultUser" in method_names

    def test_analyze_typescript_interface(self, temp_dir):
        """测试TypeScript接口分析"""
        code = """
        export interface User {
            id: number;
            name: string;
            email: string;
            roles?: string[];
        }

        export interface Admin extends User {
            permissions: string[];
            level: number;
        }

        export type UserRole = 'admin' | 'user' | 'guest';

        export enum Status {
            Active = 1,
            Inactive = 0,
            Pending = 2
        }
        """

        test_file = temp_dir / "types.ts"
        test_file.write_text(code)

        analyzer = JavaScriptTypeScriptAnalyzer(str(test_file), str(temp_dir))
        entities, relations = analyzer.analyze(code)

        # 验证接口
        interface_entities = [e for e in entities if e.type == "interface"]
        assert len(interface_entities) == 2
        interface_names = {e.name for e in interface_entities}
        assert "User" in interface_names
        assert "Admin" in interface_names

        # 验证类型别名
        type_entities = [e for e in entities if e.type == "type_alias"]
        assert len(type_entities) == 1
        assert type_entities[0].name == "UserRole"

        # 验证枚举
        enum_entities = [e for e in entities if e.type == "enum"]
        assert len(enum_entities) == 1
        assert enum_entities[0].name == "Status"

        # 验证继承关系
        inherit_relations = [r for r in relations if r.type == "inherits"]
        assert len(inherit_relations) == 1

    def test_analyze_react_components(self, temp_dir):
        """测试React组件分析"""
        code = """
        import React, { useState, useEffect } from 'react';

        export const UserList = ({ users }) => {
            return (
                <div>
                    {users.map(user => (
                        <UserCard key={user.id} user={user} />
                    ))}
                </div>
            );
        };

        export function UserCard({ user }) {
            const [expanded, setExpanded] = useState(false);

            return (
                <div onClick={() => setExpanded(!expanded)}>
                    <h3>{user.name}</h3>
                    {expanded && <p>{user.bio}</p>}
                </div>
            );
        }

        export const useUserData = () => {
            const [users, setUsers] = useState([]);

            useEffect(() => {
                fetchUsers().then(setUsers);
            }, []);

            return { users, setUsers };
        };
        """

        test_file = temp_dir / "components.jsx"
        test_file.write_text(code)

        analyzer = JavaScriptTypeScriptAnalyzer(str(test_file), str(temp_dir))
        entities, relations = analyzer.analyze(code)

        # 验证React组件
        component_entities = [e for e in entities if e.type == "react_component"]
        assert len(component_entities) == 2
        component_names = {e.name for e in component_entities}
        assert "UserList" in component_names
        assert "UserCard" in component_names

        # 验证React Hook
        hook_entities = [e for e in entities if e.type == "react_hook"]
        assert len(hook_entities) == 1
        assert hook_entities[0].name == "useUserData"

    def test_analyze_arrow_functions(self, temp_dir):
        """测试箭头函数分析"""
        code = """
        export const add = (a, b) => a + b;

        export const multiply = async (a, b) => {
            await delay(100);
            return a * b;
        };

        const processData = (data) => {
            return data.map(item => ({
                ...item,
                processed: true
            }));
        };

        export default processData;
        """

        test_file = temp_dir / "functions.js"
        test_file.write_text(code)

        analyzer = JavaScriptTypeScriptAnalyzer(str(test_file), str(temp_dir))
        entities, relations = analyzer.analyze(code)

        # 验证函数
        function_entities = [e for e in entities if e.type == "function"]
        assert len(function_entities) >= 2
        function_names = {e.name for e in function_entities}
        assert "add" in function_names
        assert "multiply" in function_names

        # 验证async函数
        async_functions = [e for e in function_entities if e.metadata.get("is_async")]
        assert len(async_functions) == 1
        assert async_functions[0].name == "multiply"

    def test_analyze_imports_exports(self, temp_dir):
        """测试导入导出分析"""
        code = """
        import React from 'react';
        import { Component } from '@angular/core';
        import * as utils from './utils';
        import './styles.css';

        const API_KEY = 'secret';
        export const CONFIG = { apiKey: API_KEY };

        export { utils };
        export default class App extends React.Component {}
        """

        test_file = temp_dir / "app.js"
        test_file.write_text(code)

        analyzer = JavaScriptTypeScriptAnalyzer(str(test_file), str(temp_dir))
        entities, relations = analyzer.analyze(code)

        # 验证导入
        assert "React" in analyzer.imports
        assert "Component" in analyzer.imports
        assert "utils" in analyzer.imports

        # 验证导出
        assert "CONFIG" in analyzer.exports
        assert "default:App" in analyzer.exports or "App" in analyzer.exports

    def test_analyze_typescript_generics(self, temp_dir):
        """测试TypeScript泛型分析"""
        code = """
        export interface Repository<T> {
            findById(id: string): Promise<T | null>;
            save(entity: T): Promise<T>;
            delete(id: string): Promise<boolean>;
        }

        export class UserRepository<U extends User> implements Repository<U> {
            async findById(id: string): Promise<U | null> {
                return null;
            }

            async save(user: U): Promise<U> {
                return user;
            }

            async delete(id: string): Promise<boolean> {
                return true;
            }
        }

        export function createRepository<T>(): Repository<T> {
            return new GenericRepository<T>();
        }
        """

        test_file = temp_dir / "repository.ts"
        test_file.write_text(code)

        analyzer = JavaScriptTypeScriptAnalyzer(str(test_file), str(temp_dir))
        entities, relations = analyzer.analyze(code)

        # 验证泛型接口
        interface_entities = [e for e in entities if e.type == "interface"]
        assert len(interface_entities) == 1
        assert interface_entities[0].metadata.get("generic_params")

        # 验证泛型类
        class_entities = [e for e in entities if e.type == "class"]
        assert len(class_entities) == 1
        assert class_entities[0].metadata.get("generic_params")

        # 验证泛型函数
        function_entities = [e for e in entities if e.type == "function"]
        assert any(e.metadata.get("generic_params") for e in function_entities)

    def test_analyze_decorators(self, temp_dir):
        """测试装饰器分析（TypeScript）"""
        code = """
        @Component({
            selector: 'app-root',
            templateUrl: './app.component.html'
        })
        export class AppComponent {
            @Input() title: string;
            @Output() onClick = new EventEmitter();

            @HostListener('click')
            handleClick() {
                this.onClick.emit();
            }
        }

        @Injectable()
        export class UserService {
            constructor(private http: HttpClient) {}
        }
        """

        test_file = temp_dir / "component.ts"
        test_file.write_text(code)

        analyzer = JavaScriptTypeScriptAnalyzer(str(test_file), str(temp_dir))
        entities, relations = analyzer.analyze(code)

        # 验证类
        class_entities = [e for e in entities if e.type == "class"]
        assert len(class_entities) == 2
        class_names = {e.name for e in class_entities}
        assert "AppComponent" in class_names
        assert "UserService" in class_names

    def test_analyze_complex_project_structure(self, temp_dir):
        """测试复杂项目结构分析"""
        # 创建多个文件
        files = {
            "index.ts": """
                export * from './models';
                export * from './services';
                export { default as App } from './App';
            """,
            "models/User.ts": """
                export interface User {
                    id: string;
                    name: string;
                }

                export class UserModel implements User {
                    constructor(public id: string, public name: string) {}
                }
            """,
            "services/UserService.ts": """
                import { User, UserModel } from '../models/User';

                export class UserService {
                    private users: User[] = [];

                    addUser(name: string): User {
                        const user = new UserModel(Date.now().toString(), name);
                        this.users.push(user);
                        return user;
                    }
                }
            """
        }

        # 创建文件
        for file_path, content in files.items():
            full_path = temp_dir / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

        # 分析每个文件
        all_entities = []
        all_relations = []

        for file_path in files.keys():
            full_path = temp_dir / file_path
            analyzer = JavaScriptTypeScriptAnalyzer(str(full_path), str(temp_dir))
            entities, relations = analyzer.analyze(files[file_path])
            all_entities.extend(entities)
            all_relations.extend(relations)

        # 验证实体总数
        assert len(all_entities) > 0
        assert len(all_relations) > 0

        # 验证跨文件关系
        import_relations = [r for r in all_relations if r.type == "imports"]
        assert len(import_relations) > 0

    @pytest.mark.parametrize("code,expected_entities", [
        ("const x = 1;", 0),  # 简单常量不创建实体
        ("export const API_URL = 'http://api.com';", 1),  # 导出的常量创建实体
        ("function helper() {}", 0),  # 内部函数不创建实体
        ("export function helper() {}", 1),  # 导出的函数创建实体
        ("class Internal {}", 1),  # 类总是创建实体
    ])
    def test_entity_creation_rules(self, temp_dir, code, expected_entities):
        """测试实体创建规则"""
        test_file = temp_dir / "test.js"
        test_file.write_text(code)

        analyzer = JavaScriptTypeScriptAnalyzer(str(test_file), str(temp_dir))
        entities, _ = analyzer.analyze(code)

        # 根据规则验证实体数量
        assert len(entities) == expected_entities


@pytest.mark.integration
class TestJavaScriptTypeScriptIntegration:
    """JavaScript/TypeScript分析器集成测试"""

    def test_analyze_real_react_project(self, tmp_path):
        """测试真实的React项目分析"""
        # 创建一个简化的React项目结构
        project_files = {
            "src/App.tsx": """
                import React from 'react';
                import { UserList } from './components/UserList';
                import { useAuth } from './hooks/useAuth';

                const App: React.FC = () => {
                    const { user, login, logout } = useAuth();

                    return (
                        <div>
                            {user ? <UserList /> : <Login onLogin={login} />}
                        </div>
                    );
                };

                export default App;
            """,
            "src/components/UserList.tsx": """
                import React from 'react';
                import { User } from '../types';

                export const UserList: React.FC<{ users?: User[] }> = ({ users = [] }) => {
                    return (
                        <ul>
                            {users.map(user => (
                                <li key={user.id}>{user.name}</li>
                            ))}
                        </ul>
                    );
                };
            """,
            "src/hooks/useAuth.ts": """
                import { useState, useEffect } from 'react';
                import { User } from '../types';

                export function useAuth() {
                    const [user, setUser] = useState<User | null>(null);

                    const login = async (email: string, password: string) => {
                        const user = await authService.login(email, password);
                        setUser(user);
                    };

                    const logout = () => setUser(null);

                    return { user, login, logout };
                }
            """,
            "src/types/index.ts": """
                export interface User {
                    id: string;
                    name: string;
                    email: string;
                }

                export type Role = 'admin' | 'user' | 'guest';
            """
        }

        # 创建项目文件
        for file_path, content in project_files.items():
            full_path = tmp_path / file_path
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

        # 使用MultiLanguageAnalyzer分析项目
        from src.mcp_core.multi_lang_analyzer import MultiLanguageAnalyzer

        analyzer = MultiLanguageAnalyzer(str(tmp_path))
        result = analyzer.analyze_project()

        # 验证结果
        assert result["stats"]["languages"]["typescript"] == 4
        assert len(result["entities"]) > 0

        # 验证特定实体
        entity_names = {e["name"] for e in result["entities"]}
        assert "App" in entity_names
        assert "UserList" in entity_names
        assert "useAuth" in entity_names
        assert "User" in entity_names