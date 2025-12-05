"""
创建数据库视图的脚本
在服务器上执行：python create_views.py
"""
import pymysql
import os
from pathlib import Path
from dotenv import load_dotenv

def main():
    # 加载环境变量
    env_path = Path(__file__).parent / ".env"
    load_dotenv(env_path)
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        print("❌ 错误：未找到 DATABASE_URL 环境变量")
        print("请确保 .env 文件存在并包含 DATABASE_URL")
        return
    
    print(f"📋 数据库连接字符串: {database_url[:50]}...")
    
    # 解析连接信息
    try:
        url_part = database_url.replace("mysql+pymysql://", "")
        auth, rest = url_part.split("@")
        username, password = auth.split(":")
        host_port, database = rest.split("/")
        host, port = host_port.split(":")
    except Exception as e:
        print(f"❌ 错误：无法解析 DATABASE_URL: {e}")
        return
    
    print(f"🔗 连接信息: {username}@{host}:{port}/{database}")
    
    # 连接数据库
    try:
        conn = pymysql.connect(
            host=host,
            port=int(port),
            user=username,
            password=password,
            database=database,
            charset='utf8mb4'
        )
        print("✅ 数据库连接成功！")
    except Exception as e:
        print(f"❌ 数据库连接失败: {e}")
        return
    
    cursor = conn.cursor()
    
    # 创建视图的 SQL 语句
    sql_statements = [
        ("DROP VIEW IF EXISTS v_account_balance", "删除旧视图（如果存在）"),
        ("""CREATE VIEW v_account_balance AS
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
GROUP BY a.guid, a.name, a.account_type""", "创建科目余额视图"),
        ("DROP VIEW IF EXISTS v_transaction_detail", "删除旧视图（如果存在）"),
        ("""CREATE VIEW v_transaction_detail AS
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
ORDER BY t.post_date DESC, t.guid, s.guid""", "创建交易明细视图")
    ]
    
    # 执行每个 SQL 语句
    print("\n📝 开始创建视图...")
    for i, (sql, description) in enumerate(sql_statements, 1):
        try:
            cursor.execute(sql)
            print(f"✅ [{i}/{len(sql_statements)}] {description}")
        except Exception as e:
            print(f"❌ [{i}/{len(sql_statements)}] {description} - 错误: {e}")
            conn.rollback()
            conn.close()
            return
    
    # 提交事务
    conn.commit()
    print("\n✅ 所有视图创建完成！")
    
    # 验证视图
    try:
        cursor.execute("SHOW FULL TABLES WHERE Table_type = 'VIEW'")
        views = cursor.fetchall()
        print(f"\n📋 已创建的视图：")
        for view in views:
            print(f"   - {view[0]}")
        
        # 测试查询
        cursor.execute("SELECT COUNT(*) FROM v_account_balance")
        count1 = cursor.fetchone()[0]
        print(f"\n📊 v_account_balance 记录数: {count1}")
        
        cursor.execute("SELECT COUNT(*) FROM v_transaction_detail")
        count2 = cursor.fetchone()[0]
        print(f"📊 v_transaction_detail 记录数: {count2}")
    except Exception as e:
        print(f"⚠️ 验证时出现错误: {e}")
    
    # 关闭连接
    conn.close()
    print("\n✅ 完成！现在可以重启应用了。")

if __name__ == "__main__":
    main()

