-- 修复 design_decisions 表缺失字段
-- 日期: 2025-11-20
-- 问题: (1054, "Unknown column 'description' in 'field list'")

USE mcp_db;

-- 添加缺失字段
ALTER TABLE design_decisions
ADD COLUMN IF NOT EXISTS description TEXT AFTER title,
ADD COLUMN IF NOT EXISTS impact_scope VARCHAR(64) AFTER trade_offs,
ADD COLUMN IF NOT EXISTS related_entities JSON AFTER impact_scope,
ADD COLUMN IF NOT EXISTS related_files JSON AFTER related_files,
ADD COLUMN IF NOT EXISTS status VARCHAR(32) DEFAULT 'active' AFTER related_files,
ADD COLUMN IF NOT EXISTS superseded_by VARCHAR(64) AFTER status,
ADD COLUMN IF NOT EXISTS created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP AFTER superseded_by,
ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP AFTER created_at;

-- 验证修复
SELECT 'design_decisions 表字段修复完成' AS status;
DESCRIBE design_decisions;
