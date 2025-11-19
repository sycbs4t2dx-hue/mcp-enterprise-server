-- ============================================
-- MCP项目 - 外键修复脚本
-- 创建时间: 2025-01-19
-- 说明: 添加缺失的外键约束
-- ============================================

-- 使用数据库
USE mcp_db;

-- ============================================
-- 1. 检查当前外键状态
-- ============================================

SELECT
    '=== 当前外键状态 ===' AS info;

SELECT
    TABLE_NAME,
    CONSTRAINT_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'mcp_db'
AND REFERENCED_TABLE_NAME IS NOT NULL
ORDER BY TABLE_NAME, CONSTRAINT_NAME;

-- ============================================
-- 2. 添加缺失的外键约束
-- ============================================

SELECT
    '=== 添加project_sessions外键 ===' AS info;

-- 检查外键是否已存在
SELECT COUNT(*) INTO @fk_exists
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'mcp_db'
AND TABLE_NAME = 'project_sessions'
AND CONSTRAINT_NAME = 'fk_project_sessions_project';

-- 如果不存在则添加
SET @sql = IF(
    @fk_exists = 0,
    'ALTER TABLE project_sessions
     ADD CONSTRAINT fk_project_sessions_project
     FOREIGN KEY (project_id) REFERENCES code_projects(project_id)
     ON DELETE CASCADE',
    'SELECT "外键已存在,跳过" AS message'
);

PREPARE stmt FROM @sql;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ============================================
-- 3. 验证外键已创建
-- ============================================

SELECT
    '=== 验证外键创建结果 ===' AS info;

SELECT
    CONSTRAINT_NAME,
    COLUMN_NAME,
    REFERENCED_TABLE_NAME,
    REFERENCED_COLUMN_NAME
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_NAME = 'project_sessions'
AND TABLE_SCHEMA = 'mcp_db'
AND REFERENCED_TABLE_NAME IS NOT NULL;

-- ============================================
-- 4. 检查其他可能缺失的外键
-- ============================================

SELECT
    '=== 检查其他表的外键 ===' AS info;

-- 检查所有引用code_projects的表
SELECT
    TABLE_NAME,
    COUNT(*) as foreign_key_count
FROM information_schema.KEY_COLUMN_USAGE
WHERE TABLE_SCHEMA = 'mcp_db'
AND REFERENCED_TABLE_NAME = 'code_projects'
GROUP BY TABLE_NAME;

-- ============================================
-- 完成提示
-- ============================================

SELECT '✅ 外键修复完成!' AS message;
SELECT
    'project_sessions.project_id -> code_projects.project_id' AS foreign_key_created;

-- ============================================
-- 使用说明:
-- ============================================

-- 执行方式1 - 通过Docker:
-- docker exec mcp-mysql mysql -uroot -p'Wxwy.2025@#' < scripts/fix_foreign_keys.sql

-- 执行方式2 - 直接连接:
-- mysql -uroot -p'Wxwy.2025@#' < scripts/fix_foreign_keys.sql

-- 执行方式3 - 交互式:
-- mysql -uroot -p'Wxwy.2025@#'
-- source scripts/fix_foreign_keys.sql
-- ============================================
