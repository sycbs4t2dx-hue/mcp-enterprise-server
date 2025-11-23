-- ============================================
-- 错误防火墙系统 - 数据库Schema
-- 版本: v1.0.0
-- 日期: 2025-11-20
-- 目标: 实现"同一错误只犯一次"的错误知识库
-- ============================================

USE mcp_db;

-- ============================================
-- 1. 错误记录表 (error_records)
-- 存储所有捕获的错误信息
-- ============================================
CREATE TABLE IF NOT EXISTS error_records (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '错误记录ID',

    -- 错误标识
    error_id VARCHAR(255) NOT NULL UNIQUE COMMENT '错误唯一标识 (Hash)',
    error_type VARCHAR(100) NOT NULL COMMENT '错误类型 (ios_build/npm_install等)',
    error_scene VARCHAR(255) NOT NULL COMMENT '错误场景描述',

    -- 错误特征
    error_pattern TEXT NOT NULL COMMENT '错误特征模式 (JSON)',
    error_message TEXT COMMENT '原始错误信息',
    error_stack TEXT COMMENT '错误堆栈',

    -- 特征向量
    feature_vector_id VARCHAR(100) COMMENT 'Milvus向量ID',

    -- 解决方案
    solution TEXT COMMENT '推荐解决方案',
    solution_confidence DECIMAL(5, 2) DEFAULT 0.00 COMMENT '解决方案置信度 (0-1)',

    -- 拦截策略
    block_level ENUM('none', 'warning', 'block') DEFAULT 'warning' COMMENT '拦截级别',
    auto_fix BOOLEAN DEFAULT FALSE COMMENT '是否支持自动修复',

    -- 统计信息
    occurrence_count INT UNSIGNED DEFAULT 1 COMMENT '发生次数',
    last_occurred_at TIMESTAMP NULL COMMENT '最后发生时间',
    blocked_count INT UNSIGNED DEFAULT 0 COMMENT '拦截次数',

    -- 元数据
    project_id BIGINT UNSIGNED COMMENT '关联项目ID',
    created_by VARCHAR(100) COMMENT '创建者',

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    -- 索引
    INDEX idx_error_type (error_type),
    INDEX idx_error_scene (error_scene),
    INDEX idx_block_level (block_level),
    INDEX idx_last_occurred (last_occurred_at),
    INDEX idx_project (project_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='错误记录表';

-- ============================================
-- 2. 错误拦截日志表 (error_intercept_logs)
-- 记录每次拦截事件的详细信息
-- ============================================
CREATE TABLE IF NOT EXISTS error_intercept_logs (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '日志ID',

    -- 关联错误
    error_record_id BIGINT UNSIGNED NOT NULL COMMENT '错误记录ID',

    -- 拦截信息
    intercept_type ENUM('before', 'after') NOT NULL COMMENT '拦截时机 (执行前/执行后)',
    intercept_action ENUM('blocked', 'warned', 'passed') NOT NULL COMMENT '拦截动作',

    -- 操作信息
    operation_type VARCHAR(100) NOT NULL COMMENT '操作类型',
    operation_params JSON COMMENT '操作参数',

    -- 匹配信息
    match_confidence DECIMAL(5, 2) NOT NULL COMMENT '匹配置信度',
    match_features JSON COMMENT '匹配到的特征',

    -- 结果
    user_action ENUM('aborted', 'override', 'fixed') COMMENT '用户动作',
    result_message TEXT COMMENT '返回给用户的消息',

    -- 元数据
    session_id VARCHAR(100) COMMENT '会话ID',
    user_id VARCHAR(100) COMMENT '用户ID',

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',

    -- 索引
    INDEX idx_error_record (error_record_id),
    INDEX idx_intercept_action (intercept_action),
    INDEX idx_operation_type (operation_type),
    INDEX idx_session (session_id),
    INDEX idx_created_at (created_at),

    -- 外键
    FOREIGN KEY (error_record_id) REFERENCES error_records(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='错误拦截日志表';

-- ============================================
-- 3. 解决方案库表 (solution_templates)
-- 存储可复用的解决方案模板
-- ============================================
CREATE TABLE IF NOT EXISTS solution_templates (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '模板ID',

    -- 模板信息
    template_name VARCHAR(255) NOT NULL COMMENT '模板名称',
    template_category VARCHAR(100) NOT NULL COMMENT '模板分类',

    -- 解决方案
    solution_steps JSON NOT NULL COMMENT '解决步骤 (JSON数组)',
    solution_code TEXT COMMENT '解决方案代码',

    -- 适用条件
    applicable_errors JSON COMMENT '适用的错误类型',
    applicable_conditions JSON COMMENT '适用条件',

    -- 效果评估
    success_rate DECIMAL(5, 2) DEFAULT 0.00 COMMENT '成功率',
    usage_count INT UNSIGNED DEFAULT 0 COMMENT '使用次数',

    -- 元数据
    is_active BOOLEAN DEFAULT TRUE COMMENT '是否启用',
    priority INT DEFAULT 0 COMMENT '优先级',

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    -- 索引
    INDEX idx_category (template_category),
    INDEX idx_active (is_active),
    INDEX idx_priority (priority)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='解决方案模板表';

-- ============================================
-- 4. 错误-解决方案关联表 (error_solution_mappings)
-- 记录错误与解决方案的关联关系和效果
-- ============================================
CREATE TABLE IF NOT EXISTS error_solution_mappings (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '映射ID',

    -- 关联
    error_record_id BIGINT UNSIGNED NOT NULL COMMENT '错误记录ID',
    solution_template_id BIGINT UNSIGNED NOT NULL COMMENT '解决方案模板ID',

    -- 效果评估
    applied_count INT UNSIGNED DEFAULT 0 COMMENT '应用次数',
    success_count INT UNSIGNED DEFAULT 0 COMMENT '成功次数',
    success_rate DECIMAL(5, 2) COMMENT '成功率',

    -- 最后应用
    last_applied_at TIMESTAMP NULL COMMENT '最后应用时间',

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    -- 索引
    INDEX idx_error (error_record_id),
    INDEX idx_solution (solution_template_id),
    UNIQUE KEY uk_error_solution (error_record_id, solution_template_id),

    -- 外键
    FOREIGN KEY (error_record_id) REFERENCES error_records(id) ON DELETE CASCADE,
    FOREIGN KEY (solution_template_id) REFERENCES solution_templates(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='错误-解决方案映射表';

-- ============================================
-- 5. 环境资源表 (environment_resources)
-- 存储可用的环境资源 (如iOS设备、npm包版本等)
-- ============================================
CREATE TABLE IF NOT EXISTS environment_resources (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY COMMENT '资源ID',

    -- 资源信息
    resource_type VARCHAR(100) NOT NULL COMMENT '资源类型 (ios_device/npm_package等)',
    resource_name VARCHAR(255) NOT NULL COMMENT '资源名称',
    resource_version VARCHAR(100) COMMENT '资源版本',

    -- 资源状态
    is_available BOOLEAN DEFAULT TRUE COMMENT '是否可用',
    availability_checked_at TIMESTAMP NULL COMMENT '最后检查时间',

    -- 资源详情
    resource_details JSON COMMENT '资源详细信息',

    -- 使用统计
    usage_count INT UNSIGNED DEFAULT 0 COMMENT '使用次数',
    last_used_at TIMESTAMP NULL COMMENT '最后使用时间',

    -- 时间戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',

    -- 索引
    INDEX idx_resource_type (resource_type),
    INDEX idx_resource_name (resource_name),
    INDEX idx_available (is_available),
    UNIQUE KEY uk_resource (resource_type, resource_name, resource_version)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='环境资源表';

-- ============================================
-- 6. 错误统计视图
-- ============================================
CREATE OR REPLACE VIEW error_statistics AS
SELECT
    er.error_type,
    er.error_scene,
    COUNT(*) as total_errors,
    SUM(er.occurrence_count) as total_occurrences,
    SUM(er.blocked_count) as total_blocks,
    AVG(er.solution_confidence) as avg_confidence,
    MAX(er.last_occurred_at) as latest_occurrence,
    COUNT(CASE WHEN er.block_level = 'block' THEN 1 END) as blocking_errors,
    COUNT(CASE WHEN er.auto_fix = TRUE THEN 1 END) as auto_fixable_errors
FROM error_records er
GROUP BY er.error_type, er.error_scene;

-- ============================================
-- 插入初始数据
-- ============================================

-- 示例错误记录
INSERT INTO error_records (
    error_id, error_type, error_scene, error_pattern,
    error_message, solution, solution_confidence, block_level, auto_fix
) VALUES (
    'ios_build_no_device_iphone15_17.0',
    'ios_build',
    'iOS编译时选择不存在的虚拟设备',
    '{"device_name": "iPhone 15", "os_version": "17.0", "operation": "build"}',
    'Error: Unable to boot device in current state: Shutdown. Device: iPhone 15 (17.0)',
    '请使用以下可用设备之一: iPhone 15 Pro (17.2), iPhone 14 (16.4)',
    0.95,
    'block',
    FALSE
), (
    'npm_install_deprecated_package',
    'npm_install',
    '安装已废弃的npm包',
    '{"package_name": "left-pad", "version": "*", "operation": "install"}',
    'npm WARN deprecated left-pad@1.3.0: use String.prototype.padStart()',
    '该包已废弃，建议使用原生方法 String.prototype.padStart()',
    0.85,
    'warning',
    TRUE
);

-- 示例解决方案模板
INSERT INTO solution_templates (
    template_name, template_category, solution_steps, success_rate, priority
) VALUES (
    'iOS设备替换方案',
    'ios_build',
    '["1. 列出所有可用iOS模拟器", "2. 选择最接近目标版本的设备", "3. 更新构建配置", "4. 重新执行构建"]',
    0.92,
    10
), (
    'npm包替换方案',
    'npm_install',
    '["1. 查找替代包或原生方法", "2. 更新package.json", "3. 运行npm install", "4. 更新代码中的引用"]',
    0.88,
    5
);

-- 示例环境资源
INSERT INTO environment_resources (
    resource_type, resource_name, resource_version, is_available, resource_details
) VALUES (
    'ios_device',
    'iPhone 15 Pro',
    '17.2',
    TRUE,
    '{"udid": "xxx-xxx", "runtime": "iOS 17.2", "state": "Shutdown"}'
), (
    'ios_device',
    'iPhone 14',
    '16.4',
    TRUE,
    '{"udid": "yyy-yyy", "runtime": "iOS 16.4", "state": "Booted"}'
);

-- ============================================
-- 完成
-- ============================================
SELECT '✅ 错误防火墙数据库Schema创建完成!' as status;
