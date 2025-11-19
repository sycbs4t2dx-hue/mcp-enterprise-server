-- ============================================
-- MCP项目 - 数据库清理脚本
-- 创建时间: 2025-01-19
-- 说明: 清理僵尸记录和重置失败状态
-- ============================================

USE mcp_db;

-- ============================================
-- 1. 查看当前项目状态
-- ============================================

SELECT
    '=== 当前项目列表 ===' AS info;

SELECT
    project_id,
    name,
    status,
    total_files,
    total_entities,
    analyzed_at,
    created_at
FROM code_projects
ORDER BY created_at DESC;

-- ============================================
-- 2. 删除特定项目(如果需要重新分析)
-- ============================================

-- 注意: 取消下面的注释来删除特定项目
-- DELETE FROM code_projects WHERE project_id = 'history-timeline';

-- ============================================
-- 3. 清理未完成的项目(状态为pending超过1小时)
-- ============================================

SELECT
    '=== 查找僵尸项目 ===' AS info;

SELECT
    project_id,
    name,
    status,
    TIMESTAMPDIFF(HOUR, created_at, NOW()) as hours_since_creation
FROM code_projects
WHERE status = 'pending'
AND TIMESTAMPDIFF(HOUR, created_at, NOW()) > 1;

-- 自动清理(可选)
-- DELETE FROM code_projects
-- WHERE status = 'pending'
-- AND TIMESTAMPDIFF(HOUR, created_at, NOW()) > 1;

-- ============================================
-- 4. 重置分析中状态(如果服务器崩溃)
-- ============================================

UPDATE code_projects
SET status = 'pending'
WHERE status = 'analyzing'
AND TIMESTAMPDIFF(HOUR, updated_at, NOW()) > 1;

SELECT ROW_COUNT() as reset_count;

-- ============================================
-- 5. 查看项目实体统计
-- ============================================

SELECT
    '=== 项目实体统计 ===' AS info;

SELECT
    cp.project_id,
    cp.name,
    cp.status,
    COUNT(DISTINCT ce.entity_id) as actual_entities,
    cp.total_entities as recorded_entities,
    COUNT(DISTINCT cr.relation_id) as actual_relations,
    cp.total_relations as recorded_relations
FROM code_projects cp
LEFT JOIN code_entities ce ON cp.project_id = ce.project_id
LEFT JOIN code_relations cr ON cp.project_id = cr.project_id
GROUP BY cp.project_id, cp.name, cp.status, cp.total_entities, cp.total_relations;

-- ============================================
-- 6. 清理孤立实体(项目已删除)
-- ============================================

SELECT
    '=== 查找孤立实体 ===' AS info;

SELECT COUNT(*) as orphaned_entities
FROM code_entities ce
WHERE NOT EXISTS (
    SELECT 1 FROM code_projects cp
    WHERE cp.project_id = ce.project_id
);

-- 删除孤立实体(可选)
-- DELETE ce FROM code_entities ce
-- WHERE NOT EXISTS (
--     SELECT 1 FROM code_projects cp
--     WHERE cp.project_id = ce.project_id
-- );

-- ============================================
-- 7. 清理孤立关系
-- ============================================

SELECT
    '=== 查找孤立关系 ===' AS info;

SELECT COUNT(*) as orphaned_relations
FROM code_relations cr
WHERE NOT EXISTS (
    SELECT 1 FROM code_projects cp
    WHERE cp.project_id = cr.project_id
);

-- 删除孤立关系(可选)
-- DELETE cr FROM code_relations cr
-- WHERE NOT EXISTS (
--     SELECT 1 FROM code_projects cp
--     WHERE cp.project_id = cr.project_id
-- );

-- ============================================
-- 完成提示
-- ============================================

SELECT '✅ 数据库清理检查完成!' AS message;

-- ============================================
-- 使用说明:
-- ============================================

-- 执行方式1 - 查看状态(安全):
-- docker exec mcp-mysql mysql -uroot -p'Wxwy.2025@#' < scripts/cleanup_database.sql

-- 执行方式2 - 删除特定项目:
-- 1. 编辑此文件,取消第25行的注释
-- 2. 修改project_id为要删除的项目
-- 3. 执行脚本

-- 执行方式3 - 清理所有僵尸数据:
-- 1. 取消所有DELETE语句的注释
-- 2. 执行脚本
-- ============================================
