-- ============================================
-- MCP v2.0.0 - 完整数据库Schema同步脚本
-- 一次性修复所有Schema不一致问题
-- ============================================

USE mcp_db;

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ============================================
-- 1. development_todos 表
-- ============================================

ALTER TABLE development_todos
ADD COLUMN IF NOT EXISTS session_id VARCHAR(64) COMMENT '会话ID';

ALTER TABLE development_todos
ADD COLUMN IF NOT EXISTS created_at DATETIME DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE development_todos
ADD COLUMN IF NOT EXISTS updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

-- ============================================
-- 2. design_decisions 表
-- ============================================

ALTER TABLE design_decisions
ADD COLUMN IF NOT EXISTS description TEXT COMMENT '详细描述';

ALTER TABLE design_decisions
ADD COLUMN IF NOT EXISTS alternatives_considered TEXT COMMENT '考虑的替代方案';

ALTER TABLE design_decisions
ADD COLUMN IF NOT EXISTS created_at DATETIME DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE design_decisions
ADD COLUMN IF NOT EXISTS updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

-- ============================================
-- 3. project_notes 表
-- ============================================

ALTER TABLE project_notes
ADD COLUMN IF NOT EXISTS session_id VARCHAR(64) COMMENT '会话ID';

ALTER TABLE project_notes
ADD COLUMN IF NOT EXISTS created_at DATETIME DEFAULT CURRENT_TIMESTAMP;

ALTER TABLE project_notes
ADD COLUMN IF NOT EXISTS updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

SET FOREIGN_KEY_CHECKS = 1;

-- ============================================
-- 验证结果
-- ============================================

SELECT '✅ Schema同步完成!' AS message;

SELECT
    TABLE_NAME,
    COUNT(*) as column_count
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'mcp_db'
AND TABLE_NAME IN ('development_todos', 'design_decisions', 'project_notes', 'project_sessions')
GROUP BY TABLE_NAME
ORDER BY TABLE_NAME;
