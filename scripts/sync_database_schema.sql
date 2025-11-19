-- ============================================
-- MCP项目 - 数据库Schema同步脚本
-- 修复project_sessions表缺失字段
-- ============================================

USE mcp_db;

-- ============================================
-- 1. 检查当前表结构
-- ============================================

SELECT '=== 修复前的project_sessions表结构 ===' AS info;
DESCRIBE project_sessions;

-- ============================================
-- 2. 添加缺失的字段
-- ============================================

SELECT '=== 开始添加缺失字段 ===' AS info;

-- 添加 duration_minutes
ALTER TABLE project_sessions
ADD COLUMN IF NOT EXISTS duration_minutes INT COMMENT '持续时间(分钟)';

-- 添加 context_summary
ALTER TABLE project_sessions
ADD COLUMN IF NOT EXISTS context_summary TEXT COMMENT 'AI生成的摘要';

-- 添加 files_modified
ALTER TABLE project_sessions
ADD COLUMN IF NOT EXISTS files_modified JSON COMMENT '修改的文件列表';

-- 添加 files_created
ALTER TABLE project_sessions
ADD COLUMN IF NOT EXISTS files_created JSON COMMENT '新建的文件列表';

-- 添加 issues_encountered
ALTER TABLE project_sessions
ADD COLUMN IF NOT EXISTS issues_encountered JSON COMMENT '遇到的问题';

-- 添加 todos_completed
ALTER TABLE project_sessions
ADD COLUMN IF NOT EXISTS todos_completed JSON COMMENT '完成的TODO';

-- 添加 created_at
ALTER TABLE project_sessions
ADD COLUMN IF NOT EXISTS created_at DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间';

-- 添加 updated_at
ALTER TABLE project_sessions
ADD COLUMN IF NOT EXISTS updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间';

SELECT '✅ 字段添加完成' AS message;

-- ============================================
-- 3. 验证修复结果
-- ============================================

SELECT '=== 修复后的project_sessions表结构 ===' AS info;
DESCRIBE project_sessions;

SELECT '=== 字段统计 ===' AS info;
SELECT
    COUNT(*) as total_columns
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'mcp_db'
AND TABLE_NAME = 'project_sessions';

-- ============================================
-- 4. 检查其他可能缺失的表字段
-- ============================================

SELECT '=== 检查其他表 ===' AS info;

-- 检查 design_decisions 表
SELECT
    TABLE_NAME,
    COUNT(*) as column_count
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'mcp_db'
AND TABLE_NAME IN ('design_decisions', 'project_notes', 'development_todos')
GROUP BY TABLE_NAME;

-- ============================================
-- 完成提示
-- ============================================

SELECT '✅ 数据库Schema同步完成!' AS message;
SELECT 'project_sessions表已更新,新增8个字段' AS details;

-- ============================================
-- 使用说明:
-- ============================================

-- 执行方式1 - 通过Docker:
-- docker exec mcp-mysql mysql -uroot -p'Wxwy.2025@#' < scripts/sync_database_schema.sql

-- 执行方式2 - 直接连接:
-- mysql -uroot -p'Wxwy.2025@#' < scripts/sync_database_schema.sql

-- 执行方式3 - 交互式:
-- mysql -uroot -p'Wxwy.2025@#'
-- source scripts/sync_database_schema.sql
-- ============================================
