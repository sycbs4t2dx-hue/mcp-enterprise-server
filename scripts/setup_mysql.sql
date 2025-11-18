-- ============================================
-- MCP项目 MySQL数据库初始化脚本
-- 创建时间: 2025-01-18
-- 说明: 在MySQL中执行此脚本创建数据库
-- ============================================

-- 使用root账户执行:
-- mysql -u root -p < scripts/setup_mysql.sql
-- 密码: Wxwy.2025@#

-- ============================================
-- 1. 创建数据库
-- ============================================

-- 删除旧数据库 (谨慎使用)
-- DROP DATABASE IF EXISTS mcp_db;

-- 创建数据库 (UTF8MB4编码，支持emoji)
CREATE DATABASE IF NOT EXISTS mcp_db
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;

-- 查看数据库
SHOW DATABASES LIKE 'mcp_db';

-- ============================================
-- 2. 查看当前root用户权限
-- ============================================

-- 显示root用户
SELECT user, host FROM mysql.user WHERE user='root';

-- 显示当前用户权限
SHOW GRANTS FOR 'root'@'localhost';

-- ============================================
-- 3. 验证数据库创建成功
-- ============================================

-- 切换到新数据库
USE mcp_db;

-- 查看数据库配置
SHOW CREATE DATABASE mcp_db;

-- 查看表 (应该为空)
SHOW TABLES;

-- ============================================
-- 4. 测试连接
-- ============================================

-- 显示MySQL版本
SELECT VERSION();

-- 显示字符集
SHOW VARIABLES LIKE 'character_set%';
SHOW VARIABLES LIKE 'collation%';

-- ============================================
-- 完成提示
-- ============================================

SELECT '数据库创建完成!' AS message;
SELECT 'mcp_db' AS database_name, 'utf8mb4' AS charset, 'utf8mb4_unicode_ci' AS collation;

-- ============================================
-- 下一步操作:
-- ============================================

-- 1. 退出MySQL:
--    EXIT;

-- 2. 运行Python初始化脚本:
--    python scripts/init_database.py

-- 3. 这将创建所有数据表并插入初始数据
-- ============================================
