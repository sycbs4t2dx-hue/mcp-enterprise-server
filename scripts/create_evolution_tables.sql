
-- ============================================
-- 智能进化编码系统 - 数据库扩展
-- 版本: v1.0.0
-- 日期: 2025-11-20
-- ============================================

USE mcp_db;

-- ============================================
-- 1. 编码经验表 - 存储AI编码经验和学习成果
-- ============================================
DROP TABLE IF EXISTS coding_experiences;
CREATE TABLE coding_experiences (
    experience_id VARCHAR(64) PRIMARY KEY COMMENT '经验ID',
    project_id VARCHAR(64) COMMENT '项目ID',
    session_id VARCHAR(64) COMMENT '会话ID',

    -- 场景信息
    context_type VARCHAR(50) COMMENT '场景类型: bug_fix, feature, refactor, optimization',
    problem_description TEXT COMMENT '问题描述',
    solution_description TEXT COMMENT '解决方案描述',

    -- 代码变更
    code_before TEXT COMMENT '修改前代码',
    code_after TEXT COMMENT '修改后代码',
    files_modified JSON COMMENT '修改的文件列表',

    -- 性能指标
    time_spent INT DEFAULT 0 COMMENT '花费时间(秒)',
    lines_changed INT DEFAULT 0 COMMENT '修改行数',
    complexity_reduced FLOAT DEFAULT 0 COMMENT '复杂度降低值',
    performance_improved FLOAT DEFAULT 0 COMMENT '性能提升百分比',

    -- 质量指标
    bugs_fixed INT DEFAULT 0 COMMENT '修复的bug数',
    bugs_introduced INT DEFAULT 0 COMMENT '引入的bug数',
    test_coverage_change FLOAT DEFAULT 0 COMMENT '测试覆盖率变化',

    -- 学习价值
    reusability_score FLOAT DEFAULT 0 COMMENT '可复用性评分(0-1)',
    success_rate FLOAT DEFAULT 0 COMMENT '成功率(0-1)',
    usage_count INT DEFAULT 0 COMMENT '被复用次数',

    -- 向量表示(用于相似度计算)
    context_embedding TEXT COMMENT '上下文向量(JSON)',
    solution_embedding TEXT COMMENT '解决方案向量(JSON)',

    -- 元数据
    tags JSON COMMENT '标签列表',
    metadata JSON COMMENT '额外元数据',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_context_type (context_type),
    INDEX idx_project (project_id),
    INDEX idx_session (session_id),
    INDEX idx_reusability (reusability_score DESC),
    INDEX idx_success_rate (success_rate DESC),
    INDEX idx_created (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='编码经验表 - AI学习和经验积累';

-- ============================================
-- 2. 项目图谱节点表 - 存储代码结构节点
-- ============================================
-- 先尝试删除可能存在的表和约束
DROP TABLE IF EXISTS graph_edges;
DROP TABLE IF EXISTS graph_nodes;
CREATE TABLE graph_nodes (
    node_id VARCHAR(64) PRIMARY KEY COMMENT '节点ID',
    project_id VARCHAR(64) NOT NULL COMMENT '项目ID',

    -- 节点基本信息
    node_type VARCHAR(50) NOT NULL COMMENT '节点类型: module, class, function, variable, data, pattern',
    node_name VARCHAR(255) NOT NULL COMMENT '节点名称',
    node_path VARCHAR(512) COMMENT '节点路径',
    qualified_name VARCHAR(512) COMMENT '完全限定名',

    -- 代码位置
    file_path VARCHAR(512) COMMENT '文件路径',
    line_start INT COMMENT '起始行号',
    line_end INT COMMENT '结束行号',

    -- 属性
    properties JSON COMMENT '节点属性(如参数、返回值、修饰符等)',
    docstring TEXT COMMENT '文档字符串',
    signature VARCHAR(1024) COMMENT '函数/方法签名',

    -- 度量指标
    complexity_score FLOAT DEFAULT 0 COMMENT '复杂度评分',
    importance_score FLOAT DEFAULT 0 COMMENT '重要性评分',
    stability_score FLOAT DEFAULT 0 COMMENT '稳定性评分',
    quality_score FLOAT DEFAULT 0 COMMENT '质量评分',

    -- 使用统计
    change_frequency INT DEFAULT 0 COMMENT '修改频率',
    reference_count INT DEFAULT 0 COMMENT '被引用次数',
    last_modified TIMESTAMP NULL COMMENT '最后修改时间',

    -- 关系统计
    in_degree INT DEFAULT 0 COMMENT '入度(被依赖数)',
    out_degree INT DEFAULT 0 COMMENT '出度(依赖数)',
    centrality FLOAT DEFAULT 0 COMMENT '中心度',

    -- 可视化信息
    layout_x FLOAT COMMENT 'X坐标',
    layout_y FLOAT COMMENT 'Y坐标',
    layout_z FLOAT COMMENT 'Z坐标(3D布局)',
    layout_layer INT COMMENT '层级',
    cluster_id VARCHAR(64) COMMENT '聚类ID',
    color VARCHAR(7) COMMENT '节点颜色',
    size FLOAT DEFAULT 1.0 COMMENT '节点大小',

    -- 向量表示
    embedding TEXT COMMENT '节点嵌入向量(JSON)',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_project_type (project_id, node_type),
    INDEX idx_importance (importance_score DESC),
    INDEX idx_complexity (complexity_score DESC),
    INDEX idx_cluster (cluster_id),
    INDEX idx_qualified_name (qualified_name),
    INDEX idx_file_path (file_path)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='项目图谱节点表 - 存储代码结构节点';

-- ============================================
-- 3. 图谱边关系表 - 存储节点间关系
-- ============================================
DROP TABLE IF EXISTS graph_edges;
CREATE TABLE graph_edges (
    edge_id VARCHAR(64) PRIMARY KEY COMMENT '边ID',
    project_id VARCHAR(64) NOT NULL COMMENT '项目ID',

    -- 关系信息
    source_node_id VARCHAR(64) NOT NULL COMMENT '源节点ID',
    target_node_id VARCHAR(64) NOT NULL COMMENT '目标节点ID',
    edge_type VARCHAR(50) NOT NULL COMMENT '边类型: calls, imports, inherits, implements, depends, contains, uses, dataflow',

    -- 关系强度
    weight FLOAT DEFAULT 1.0 COMMENT '权重',
    confidence FLOAT DEFAULT 1.0 COMMENT '置信度',
    frequency INT DEFAULT 1 COMMENT '发生频率',

    -- 关系详情
    context TEXT COMMENT '关系上下文',
    metadata JSON COMMENT '元数据(如调用参数、数据流信息等)',

    -- 可视化
    edge_style VARCHAR(20) DEFAULT 'solid' COMMENT '边样式: solid, dashed, dotted',
    edge_color VARCHAR(7) COMMENT '边颜色',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_source (source_node_id),
    INDEX idx_target (target_node_id),
    INDEX idx_project_edge (project_id, edge_type),
    INDEX idx_weight (weight DESC),
    UNIQUE KEY uk_source_target_type (source_node_id, target_node_id, edge_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='图谱边关系表 - 存储节点间依赖关系';

-- ============================================
-- 4. AI协同锁表 - 管理多AI并行开发
-- ============================================
DROP TABLE IF EXISTS collaboration_locks;
CREATE TABLE collaboration_locks (
    lock_id VARCHAR(64) PRIMARY KEY COMMENT '锁ID',
    agent_id VARCHAR(64) NOT NULL COMMENT 'AI代理ID',
    project_id VARCHAR(64) COMMENT '项目ID',

    -- 锁信息
    lock_type VARCHAR(50) NOT NULL COMMENT '锁类型: file, function, class, region, semantic',
    lock_level VARCHAR(20) DEFAULT 'write' COMMENT '锁级别: read, write, exclusive',
    resource_id VARCHAR(255) NOT NULL COMMENT '资源ID',
    resource_path VARCHAR(512) COMMENT '资源路径',
    resource_type VARCHAR(50) COMMENT '资源类型',

    -- 锁范围(用于区域锁)
    start_line INT COMMENT '起始行',
    end_line INT COMMENT '结束行',
    scope_description TEXT COMMENT '范围描述',

    -- 锁状态
    status VARCHAR(20) NOT NULL DEFAULT 'waiting' COMMENT '状态: waiting, acquired, releasing, released',
    priority INT DEFAULT 0 COMMENT '优先级(高优先级先获得锁)',

    -- 意图说明
    intent_description TEXT COMMENT '操作意图说明',
    operation_type VARCHAR(50) COMMENT '操作类型: create, modify, delete, refactor',
    estimated_duration INT COMMENT '预计持续时间(秒)',

    -- 冲突处理
    conflict_strategy VARCHAR(50) DEFAULT 'wait' COMMENT '冲突策略: wait, merge, abort, negotiate',
    conflicting_locks JSON COMMENT '冲突的锁ID列表',

    -- 时间管理
    requested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '请求时间',
    acquired_at TIMESTAMP NULL COMMENT '获取时间',
    expires_at TIMESTAMP NULL COMMENT '过期时间',
    released_at TIMESTAMP NULL COMMENT '释放时间',

    -- 性能统计
    wait_time INT COMMENT '等待时间(秒)',
    hold_time INT COMMENT '持有时间(秒)',

    INDEX idx_agent (agent_id),
    INDEX idx_resource (resource_id),
    INDEX idx_status (status),
    INDEX idx_priority (priority DESC),
    INDEX idx_expires (expires_at),
    INDEX idx_project_status (project_id, status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='AI协同锁表 - 防止多AI编码冲突';

-- ============================================
-- 5. AI决策历史表 - 记录AI决策过程
-- ============================================
DROP TABLE IF EXISTS ai_decisions;
CREATE TABLE ai_decisions (
    decision_id VARCHAR(64) PRIMARY KEY COMMENT '决策ID',
    agent_id VARCHAR(64) NOT NULL COMMENT 'AI代理ID',
    project_id VARCHAR(64) COMMENT '项目ID',
    session_id VARCHAR(64) COMMENT '会话ID',

    -- 决策信息
    decision_type VARCHAR(50) NOT NULL COMMENT '决策类型: design, implementation, optimization, refactor',
    decision_category VARCHAR(50) COMMENT '决策类别',
    context TEXT COMMENT '决策上下文',
    problem_statement TEXT COMMENT '问题陈述',

    -- 决策选项
    options JSON COMMENT '可选方案列表',
    chosen_option JSON COMMENT '选中的方案',
    rejected_options JSON COMMENT '拒绝的方案',

    -- 决策依据
    reasoning TEXT COMMENT '决策理由',
    factors JSON COMMENT '考虑因素',
    confidence_score FLOAT DEFAULT 0 COMMENT '置信度(0-1)',
    risk_assessment JSON COMMENT '风险评估',

    -- 决策结果
    outcome VARCHAR(50) COMMENT '结果: success, failure, partial, pending',
    actual_impact JSON COMMENT '实际影响',
    performance_metrics JSON COMMENT '性能指标',
    lessons_learned TEXT COMMENT '经验教训',

    -- 反馈和调整
    user_feedback VARCHAR(50) COMMENT '用户反馈: approved, rejected, modified',
    user_comment TEXT COMMENT '用户评论',
    adjustments JSON COMMENT '调整内容',

    -- 关联信息
    related_experiences JSON COMMENT '相关经验ID列表',
    related_decisions JSON COMMENT '相关决策ID列表',

    -- 时间追踪
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    evaluated_at TIMESTAMP NULL COMMENT '评估时间',
    feedback_at TIMESTAMP NULL COMMENT '反馈时间',

    INDEX idx_agent_project (agent_id, project_id),
    INDEX idx_decision_type (decision_type),
    INDEX idx_outcome (outcome),
    INDEX idx_confidence (confidence_score DESC),
    INDEX idx_created (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='AI决策历史表 - 记录和学习决策过程';

-- ============================================
-- 6. 学习模式表 - 存储识别的代码模式
-- ============================================
DROP TABLE IF EXISTS learning_patterns;
CREATE TABLE learning_patterns (
    pattern_id VARCHAR(64) PRIMARY KEY COMMENT '模式ID',
    project_id VARCHAR(64) COMMENT '项目ID',

    -- 模式信息
    pattern_type VARCHAR(50) NOT NULL COMMENT '模式类型: design, coding, error, optimization',
    pattern_name VARCHAR(255) NOT NULL COMMENT '模式名称',
    pattern_description TEXT COMMENT '模式描述',

    -- 模式内容
    pattern_template TEXT COMMENT '模式模板',
    pattern_examples JSON COMMENT '模式示例',
    anti_pattern TEXT COMMENT '反模式',

    -- 使用统计
    occurrence_count INT DEFAULT 0 COMMENT '出现次数',
    success_count INT DEFAULT 0 COMMENT '成功次数',
    failure_count INT DEFAULT 0 COMMENT '失败次数',
    effectiveness FLOAT DEFAULT 0 COMMENT '有效性(0-1)',

    -- 适用场景
    applicable_contexts JSON COMMENT '适用场景',
    prerequisites JSON COMMENT '前提条件',
    limitations TEXT COMMENT '限制条件',

    -- 向量表示
    pattern_embedding TEXT COMMENT '模式向量(JSON)',

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    INDEX idx_pattern_type (pattern_type),
    INDEX idx_effectiveness (effectiveness DESC),
    INDEX idx_occurrence (occurrence_count DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='学习模式表 - 存储识别的代码模式';

-- ============================================
-- 7. 协作会话表 - 管理多AI协作会话
-- ============================================
DROP TABLE IF EXISTS collaboration_sessions;
CREATE TABLE collaboration_sessions (
    session_id VARCHAR(64) PRIMARY KEY COMMENT '协作会话ID',
    project_id VARCHAR(64) NOT NULL COMMENT '项目ID',

    -- 会话信息
    session_name VARCHAR(255) COMMENT '会话名称',
    session_goal TEXT COMMENT '会话目标',
    session_type VARCHAR(50) COMMENT '会话类型: feature, bugfix, refactor',

    -- 参与者
    participating_agents JSON NOT NULL COMMENT '参与的AI代理列表',
    coordinator_agent VARCHAR(64) COMMENT '协调者代理ID',

    -- 任务分配
    task_distribution JSON COMMENT '任务分配情况',
    dependencies JSON COMMENT '任务依赖关系',

    -- 会话状态
    status VARCHAR(20) DEFAULT 'planning' COMMENT '状态: planning, executing, reviewing, completed',
    progress FLOAT DEFAULT 0 COMMENT '进度(0-100)',

    -- 协作统计
    total_changes INT DEFAULT 0 COMMENT '总变更数',
    conflicts_count INT DEFAULT 0 COMMENT '冲突次数',
    conflicts_resolved INT DEFAULT 0 COMMENT '解决的冲突数',

    -- 性能指标
    estimated_time INT COMMENT '预计时间(秒)',
    actual_time INT COMMENT '实际时间(秒)',
    efficiency_score FLOAT COMMENT '效率评分',

    -- 时间管理
    started_at TIMESTAMP NULL COMMENT '开始时间',
    completed_at TIMESTAMP NULL COMMENT '完成时间',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    INDEX idx_project (project_id),
    INDEX idx_status (status),
    INDEX idx_created (created_at DESC)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci
COMMENT='协作会话表 - 管理多AI协作';

-- ============================================
-- 添加外键约束
-- ============================================

-- graph_nodes -> projects
ALTER TABLE graph_nodes
ADD CONSTRAINT fk_graph_nodes_project
FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE;

-- graph_edges -> projects
ALTER TABLE graph_edges
ADD CONSTRAINT fk_graph_edges_project
FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE;

-- graph_edges -> graph_nodes
ALTER TABLE graph_edges
ADD CONSTRAINT fk_graph_edges_source
FOREIGN KEY (source_node_id) REFERENCES graph_nodes(node_id) ON DELETE CASCADE;

ALTER TABLE graph_edges
ADD CONSTRAINT fk_graph_edges_target
FOREIGN KEY (target_node_id) REFERENCES graph_nodes(node_id) ON DELETE CASCADE;

-- coding_experiences -> projects
ALTER TABLE coding_experiences
ADD CONSTRAINT fk_experiences_project
FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE;

-- ai_decisions -> projects
ALTER TABLE ai_decisions
ADD CONSTRAINT fk_decisions_project
FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE;

-- collaboration_sessions -> projects
ALTER TABLE collaboration_sessions
ADD CONSTRAINT fk_collab_sessions_project
FOREIGN KEY (project_id) REFERENCES projects(project_id) ON DELETE CASCADE;

-- ============================================
-- 创建视图
-- ============================================

-- 高价值经验视图
CREATE OR REPLACE VIEW high_value_experiences AS
SELECT
    e.*,
    p.name as project_name
FROM coding_experiences e
LEFT JOIN projects p ON e.project_id = p.project_id
WHERE e.reusability_score > 0.7
AND e.success_rate > 0.8
ORDER BY e.reusability_score DESC;

-- 项目图谱统计视图
CREATE OR REPLACE VIEW graph_statistics AS
SELECT
    project_id,
    COUNT(DISTINCT node_id) as total_nodes,
    SUM(CASE WHEN node_type = 'class' THEN 1 ELSE 0 END) as class_count,
    SUM(CASE WHEN node_type = 'function' THEN 1 ELSE 0 END) as function_count,
    AVG(complexity_score) as avg_complexity,
    MAX(importance_score) as max_importance
FROM graph_nodes
GROUP BY project_id;

-- 活跃锁视图
CREATE OR REPLACE VIEW active_locks AS
SELECT
    l.*,
    TIMESTAMPDIFF(SECOND, l.requested_at, NOW()) as wait_seconds
FROM collaboration_locks l
WHERE l.status IN ('waiting', 'acquired')
AND (l.expires_at IS NULL OR l.expires_at > NOW())
ORDER BY l.priority DESC, l.requested_at ASC;

-- ============================================
-- 初始化数据
-- ============================================

-- 插入默认项目(如果不存在)
INSERT IGNORE INTO projects (project_id, name, description)
VALUES ('default', 'Default Project', 'Default project for testing');

-- ============================================
-- 创建存储过程
-- ============================================

DELIMITER $$

-- 自动释放过期锁
CREATE PROCEDURE release_expired_locks()
BEGIN
    UPDATE collaboration_locks
    SET status = 'released',
        released_at = NOW()
    WHERE status = 'acquired'
    AND expires_at < NOW();
END$$

-- 计算节点重要性
CREATE PROCEDURE calculate_node_importance(IN p_project_id VARCHAR(64))
BEGIN
    -- 基于PageRank算法计算节点重要性
    UPDATE graph_nodes n
    SET importance_score = (
        SELECT
            0.15 + 0.85 * SUM(
                src.importance_score / NULLIF(src.out_degree, 0)
            )
        FROM graph_edges e
        JOIN graph_nodes src ON e.source_node_id = src.node_id
        WHERE e.target_node_id = n.node_id
        AND n.project_id = p_project_id
    )
    WHERE n.project_id = p_project_id;
END$$

DELIMITER ;

-- ============================================
-- 创建定时任务(需要启用event scheduler)
-- ============================================

-- 启用事件调度器
SET GLOBAL event_scheduler = ON;

-- 定期释放过期锁
CREATE EVENT IF NOT EXISTS auto_release_locks
ON SCHEDULE EVERY 1 MINUTE
DO CALL release_expired_locks();

-- ============================================
-- 权限设置
-- ============================================

-- 创建应用用户(如果需要)
-- CREATE USER IF NOT EXISTS 'mcp_app'@'%' IDENTIFIED BY 'your_password';
-- GRANT SELECT, INSERT, UPDATE, DELETE ON mcp_db.* TO 'mcp_app'@'%';
-- FLUSH PRIVILEGES;

-- ============================================
-- 完成提示
-- ============================================
SELECT 'Evolution tables created successfully!' as status;
SELECT
    TABLE_NAME,
    TABLE_COMMENT
FROM information_schema.TABLES
WHERE TABLE_SCHEMA = 'mcp_db'
AND TABLE_NAME IN (
    'coding_experiences',
    'graph_nodes',
    'graph_edges',
    'collaboration_locks',
    'ai_decisions',
    'learning_patterns',
    'collaboration_sessions'
);