"""
简化版数据清除工具 - 不依赖 app 模块，直接连接数据库。

使用方法：
1. 确保已安装 pymysql: pip install pymysql
2. 修改下面的数据库连接信息
3. 运行: python clear_data_simple.py
"""
import sys

try:
    import pymysql
except ImportError:
    print("❌ 错误：缺少 pymysql 模块")
    print("请运行: pip install pymysql")
    sys.exit(1)

# ============================================================
# 数据库连接配置（请根据实际情况修改）
# ============================================================
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "12345",  # 请修改为您的数据库密码
    "database": "accounting_system",  # 请修改为您的数据库名
    "charset": "utf8mb4",
}


def get_connection():
    """获取数据库连接。"""
    try:
        return pymysql.connect(**DB_CONFIG)
    except Exception as e:
        print(f"❌ 数据库连接失败：{str(e)}")
        print("\n请检查：")
        print("  1. 数据库服务是否启动")
        print("  2. 数据库连接信息是否正确（host, port, user, password, database）")
        print("  3. 数据库用户是否有相应权限")
        sys.exit(1)


def show_data_summary(conn):
    """显示当前数据统计。"""
    print("\n当前数据统计：")
    print("-" * 50)
    
    try:
        with conn.cursor() as cursor:
            # 统计各表记录数
            cursor.execute("SELECT COUNT(*) FROM accounts")
            account_count = cursor.fetchone()[0]
            print(f"  会计科目数量: {account_count}")
            
            cursor.execute("SELECT COUNT(*) FROM transactions")
            tx_count = cursor.fetchone()[0]
            print(f"  交易凭证数量: {tx_count}")
            
            cursor.execute("SELECT COUNT(*) FROM splits")
            split_count = cursor.fetchone()[0]
            print(f"  分录明细数量: {split_count}")
            
            cursor.execute("SELECT COUNT(*) FROM business_documents")
            doc_count = cursor.fetchone()[0]
            print(f"  业务单据数量: {doc_count}")
            
            cursor.execute("SELECT COUNT(*) FROM cashflow_types")
            cf_count = cursor.fetchone()[0]
            print(f"  现金流量分类数量: {cf_count}")
            
            cursor.execute("SELECT SUM(current_balance) FROM accounts")
            total_balance = cursor.fetchone()[0] or 0
            print(f"  科目余额总和: {total_balance}")
            
    except Exception as e:
        print(f"❌ 查询数据统计失败：{str(e)}")
    
    print("-" * 50)


def clear_transaction_data(conn):
    """清除所有交易相关数据，但保留科目结构和现金流量分类。"""
    print("\n正在清除交易数据...")
    
    try:
        with conn.cursor() as cursor:
            # 按外键依赖顺序删除
            print("  1. 删除业务单据明细...")
            cursor.execute("DELETE FROM business_document_items")
            
            print("  2. 删除业务单据...")
            cursor.execute("DELETE FROM business_documents")
            
            print("  3. 删除分录明细...")
            cursor.execute("DELETE FROM splits")
            
            print("  4. 删除交易凭证...")
            cursor.execute("DELETE FROM transactions")
            
            print("  5. 重置所有科目余额为0...")
            cursor.execute("UPDATE accounts SET current_balance = 0")
            
            conn.commit()
            print("✓ 交易数据清除完成！")
            
    except Exception as e:
        conn.rollback()
        print(f"❌ 清除数据失败：{str(e)}")
        raise


def clear_all_data(conn):
    """完全清除所有数据（包括科目和现金流量分类）。"""
    print("\n⚠️  警告：即将清除所有数据，包括科目结构！")
    confirm = input("确认要继续吗？(输入 'YES' 确认): ")
    
    if confirm != "YES":
        print("操作已取消。")
        return
    
    print("\n正在清除所有数据...")
    
    try:
        with conn.cursor() as cursor:
            # 按外键依赖顺序删除
            print("  1. 删除业务单据明细...")
            cursor.execute("DELETE FROM business_document_items")
            
            print("  2. 删除业务单据...")
            cursor.execute("DELETE FROM business_documents")
            
            print("  3. 删除分录明细...")
            cursor.execute("DELETE FROM splits")
            
            print("  4. 删除交易凭证...")
            cursor.execute("DELETE FROM transactions")
            
            print("  5. 删除现金流量分类...")
            cursor.execute("DELETE FROM cashflow_types")
            
            print("  6. 删除会计科目...")
            cursor.execute("DELETE FROM accounts")
            
            conn.commit()
            print("✓ 所有数据清除完成！")
            
    except Exception as e:
        conn.rollback()
        print(f"❌ 清除数据失败：{str(e)}")
        raise


def main():
    """主函数。"""
    print("=" * 60)
    print("数据库数据清除工具（简化版）")
    print("=" * 60)
    print()
    print("⚠️  重要提示：")
    print("   1. 清除数据前请务必备份数据库！")
    print("   2. 此操作不可恢复，请谨慎操作！")
    print("   3. 请确保已修改脚本中的数据库连接信息！")
    print()
    
    # 检查数据库配置
    if DB_CONFIG["password"] == "your_password":
        print("❌ 错误：请先修改脚本中的数据库连接信息！")
        print("   打开 clear_data_simple.py，修改 DB_CONFIG 字典中的配置")
        sys.exit(1)
    
    conn = None
    try:
        conn = get_connection()
        
        # 显示当前数据统计
        show_data_summary(conn)
        
        print("\n请选择清除模式：")
        print("  1. 只清除交易数据（保留科目结构和现金流量分类）")
        print("  2. 完全重置（清除所有数据，包括科目）")
        print("  3. 退出")
        
        choice = input("\n请输入选项 (1/2/3): ").strip()
        
        if choice == "1":
            print("\n您选择了：只清除交易数据")
            print("这将清除所有交易凭证、分录、业务单据，但保留科目结构。")
            confirm = input("确认继续？(y/N): ").strip().lower()
            if confirm == "y":
                clear_transaction_data(conn)
                print("\n清除后的数据统计：")
                show_data_summary(conn)
            else:
                print("操作已取消。")
        
        elif choice == "2":
            print("\n您选择了：完全重置")
            clear_all_data(conn)
            print("\n清除后的数据统计：")
            show_data_summary(conn)
        
        elif choice == "3":
            print("退出。")
        
        else:
            print("无效的选项，退出。")
    
    except Exception as e:
        print(f"\n❌ 错误：{str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
    
    finally:
        if conn:
            conn.close()


if __name__ == "__main__":
    main()

