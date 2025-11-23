-- 修复 project_notes 和 development_todos 表缺失字段
-- 日期: 2025-11-20
-- 问题: (1054, "Unknown column 'session_id' in 'field list'")
-- 影响: 导致 6个MCP工具无法使用 + Session回滚连锁失败

USE mcp_db;

-- ====================================
-- 1. 修复 project_notes 表
-- ====================================

-- 添加 session_id (外键到 project_sessions)
ALTER TABLE project_notes
ADD COLUMN session_id VARCHAR(64) AFTER project_id;

-- 添加外键约束
ALTER TABLE project_notes
ADD CONSTRAINT fk_project_notes_session
FOREIGN KEY (session_id) REFERENCES project_sessions(session_id) ON DELETE SET NULL;

-- 添加缺失的业务字段
ALTER TABLE project_notes
ADD COLUMN related_code TEXT AFTER importance,
ADD COLUMN related_entities JSON AFTER related_code,
ADD COLUMN related_files JSON AFTER related_entities,
ADD COLUMN is_resolved TINYINT(1) DEFAULT 0 AFTER tags,
ADD COLUMN resolved_at DATETIME AFTER is_resolved,
ADD COLUMN resolved_note TEXT AFTER resolved_at;

-- 修改 importance 从 VARCHAR 改为 INT
ALTER TABLE project_notes
MODIFY COLUMN importance INT DEFAULT 3;

-- 修改时间戳字段为标准格式
ALTER TABLE project_notes
MODIFY COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
MODIFY COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP;

-- ====================================
-- 2. 修复 development_todos 表
-- ====================================

-- 添加 session_id (外键到 project_sessions)
ALTER TABLE development_todos
ADD COLUMN session_id VARCHAR(64) AFTER project_id;

-- 添加外键约束
ALTER TABLE development_todos
ADD CONSTRAINT fk_development_todos_session
FOREIGN KEY (session_id) REFERENCES project_sessions(session_id) ON DELETE SET NULL;

-- 添加缺失的业务字段
ALTER TABLE development_todos
ADD COLUMN category VARCHAR(64) AFTER description,
ADD COLUMN estimated_difficulty INT DEFAULT 3 AFTER priority,
ADD COLUMN progress INT DEFAULT 0 AFTER status,
ADD COLUMN blocks JSON AFTER depends_on,
ADD COLUMN related_entities JSON AFTER blocks,
ADD COLUMN related_files JSON AFTER related_entities,
ADD COLUMN completion_note TEXT AFTER completed_at;

-- 修改 priority 从 VARCHAR 改为 INT
ALTER TABLE development_todos
MODIFY COLUMN priority INT DEFAULT 3;

-- 修改 estimated_hours 从 FLOAT 改为 INT
ALTER TABLE development_todos
MODIFY COLUMN estimated_hours INT;

-- 修改 assigned_to 字段 (代码中没有这个字段，但表里有，保留)
-- 不做修改

-- 修改时间戳字段为标准格式
ALTER TABLE development_todos
MODIFY COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP;

-- 添加 updated_at 字段 (表中缺失)
ALTER TABLE development_todos
ADD COLUMN updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at;

-- ====================================
-- 3. 创建索引 (忽略已存在的索引)
-- ====================================

-- project_notes 索引
-- Note: 索引可能已经存在，忽略错误
SET @s = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
     WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='project_notes' AND INDEX_NAME='idx_project_category') > 0,
    'SELECT 1',
    'CREATE INDEX idx_project_category ON project_notes(project_id, category)'
));
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @s = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
     WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='project_notes' AND INDEX_NAME='idx_importance') > 0,
    'SELECT 1',
    'CREATE INDEX idx_importance ON project_notes(importance)'
));
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- development_todos 索引
SET @s = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
     WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='development_todos' AND INDEX_NAME='idx_project_status') > 0,
    'SELECT 1',
    'CREATE INDEX idx_project_status ON development_todos(project_id, status)'
));
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

SET @s = (SELECT IF(
    (SELECT COUNT(*) FROM INFORMATION_SCHEMA.STATISTICS
     WHERE TABLE_SCHEMA=DATABASE() AND TABLE_NAME='development_todos' AND INDEX_NAME='idx_priority') > 0,
    'SELECT 1',
    'CREATE INDEX idx_priority ON development_todos(priority)'
));
PREPARE stmt FROM @s;
EXECUTE stmt;
DEALLOCATE PREPARE stmt;

-- ====================================
-- 4. 验证修复
-- ====================================

SELECT '========================================' AS '';
SELECT '✅ project_notes 表修复完成' AS 'Status';
SELECT '========================================' AS '';
DESCRIBE project_notes;

SELECT '' AS '';
SELECT '========================================' AS '';
SELECT '✅ development_todos 表修复完成' AS 'Status';
SELECT '========================================' AS '';
DESCRIBE development_todos;

-- 显示字段对比
SELECT '' AS '';
SELECT '========================================' AS '';
SELECT '📊 字段数量统计' AS '';
SELECT '========================================' AS '';

SELECT
    'project_notes' AS table_name,
    COUNT(*) AS field_count
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'mcp_db' AND TABLE_NAME = 'project_notes'

UNION ALL

SELECT
    'development_todos' AS table_name,
    COUNT(*) AS field_count
FROM information_schema.COLUMNS
WHERE TABLE_SCHEMA = 'mcp_db' AND TABLE_NAME = 'development_todos';
