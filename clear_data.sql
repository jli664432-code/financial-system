-- 数据库数据清除 SQL 脚本
-- 
-- 使用前请务必备份数据库！
-- 此脚本提供两种清除模式：
-- 1. 只清除交易数据（保留科目结构）
-- 2. 完全重置（清除所有数据）

-- ============================================================
-- 模式1：只清除交易数据（保留科目结构和现金流量分类）
-- ============================================================
-- 执行以下 SQL 语句将清除所有交易相关数据，但保留科目结构

-- 1. 删除业务单据明细
DELETE FROM business_document_items;

-- 2. 删除业务单据
DELETE FROM business_documents;

-- 3. 删除分录明细
DELETE FROM splits;

-- 4. 删除交易凭证
DELETE FROM transactions;

-- 5. 重置所有科目余额为0
UPDATE accounts SET current_balance = 0;


-- ============================================================
-- 模式2：完全重置（清除所有数据，包括科目）
-- ============================================================
-- ⚠️ 警告：此操作会删除所有数据，包括科目结构！
-- 执行前请确保已备份数据库！

-- 1. 删除业务单据明细
DELETE FROM business_document_items;

-- 2. 删除业务单据
DELETE FROM business_documents;

-- 3. 删除分录明细
DELETE FROM splits;

-- 4. 删除交易凭证
DELETE FROM transactions;

-- 5. 删除现金流量分类
DELETE FROM cashflow_types;

-- 6. 删除会计科目
DELETE FROM accounts;


-- ============================================================
-- 查看当前数据统计（执行清除前后可以运行此查询）
-- ============================================================
SELECT 
    (SELECT COUNT(*) FROM accounts) AS 科目数量,
    (SELECT COUNT(*) FROM transactions) AS 交易凭证数量,
    (SELECT COUNT(*) FROM splits) AS 分录明细数量,
    (SELECT COUNT(*) FROM business_documents) AS 业务单据数量,
    (SELECT COUNT(*) FROM cashflow_types) AS 现金流量分类数量,
    (SELECT SUM(current_balance) FROM accounts) AS 科目余额总和;

