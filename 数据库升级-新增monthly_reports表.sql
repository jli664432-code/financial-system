-- 新增 monthly_reports 表，用于缓存上一整月的报表快照

CREATE TABLE IF NOT EXISTS `monthly_reports` (
    `id` INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
    `report_month` DATE NOT NULL COMMENT '报表所属月份（取当月第一天）',
    `report_type` VARCHAR(50) NOT NULL COMMENT '报表类型：balance_sheet / income_statement / cashflow_statement',
    `payload` LONGTEXT NOT NULL COMMENT '报表 JSON 数据',
    `created_at` DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY `uk_month_type` (`report_month`, `report_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='月度报表缓存，只保留最新月份';




