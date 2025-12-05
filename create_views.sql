-- 创建数据库视图
-- 执行此 SQL 脚本创建必需的视图

-- 1. 科目余额视图
CREATE OR REPLACE VIEW v_account_balance AS
SELECT 
    a.guid AS account_guid,
    a.name AS account_name,
    a.account_type,
    COALESCE(SUM(
        CASE 
            WHEN s.action = 'debit' OR s.action IS NULL THEN s.value_num * 1.0 / s.value_denom
            ELSE -s.value_num * 1.0 / s.value_denom
        END
    ), 0) AS balance
FROM accounts a
LEFT JOIN splits s ON a.guid = s.account_guid
GROUP BY a.guid, a.name, a.account_type;

-- 2. 交易明细视图
CREATE OR REPLACE VIEW v_transaction_detail AS
SELECT 
    t.guid AS tx_guid,
    t.num AS transaction_num,
    t.post_date,
    t.description,
    t.business_type,
    t.reference_no,
    s.guid AS split_guid,
    s.account_guid,
    a.name AS account_name,
    a.account_type,
    s.value_num * 1.0 / s.value_denom AS amount,
    s.memo,
    s.cashflow_type_id,
    cf.name AS cashflow_type_name
FROM transactions t
JOIN splits s ON t.guid = s.tx_guid
JOIN accounts a ON s.account_guid = a.guid
LEFT JOIN cashflow_types cf ON s.cashflow_type_id = cf.id
ORDER BY t.post_date DESC, t.guid, s.guid;

-- 注意：如果使用 MySQL，请使用以下语法：
-- CREATE OR REPLACE VIEW 在 MySQL 5.7.1+ 中可用
-- 如果版本较低，请先删除视图再创建：
-- DROP VIEW IF EXISTS v_account_balance;
-- CREATE VIEW v_account_balance AS ...

