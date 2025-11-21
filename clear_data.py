"""
数据库数据清除工具。

提供两种清除模式：
1. 只清除交易数据（保留科目结构和现金流量分类）
2. 完全重置（清除所有数据，包括科目）

使用前请务必备份数据库！
"""
import sys
import os
from decimal import Decimal

# 检查是否在虚拟环境中
try:
    from sqlalchemy import text
    from sqlalchemy.orm import Session
    from app.database import session_scope, engine
except ImportError as e:
    print("=" * 60)
    print("❌ 导入错误：缺少必要的模块")
    print("=" * 60)
    print(f"\n错误信息：{str(e)}")
    print("\n请确保：")
    print("  1. 已激活虚拟环境（.venv312\\Scripts\\activate）")
    print("  2. 已安装所有依赖（pip install -r requirements.txt）")
    print("\n或者，您可以直接使用 SQL 脚本清除数据：")
    print("  1. 打开 clear_data.sql 文件")
    print("  2. 在 MySQL 客户端中执行相应的 SQL 语句")
    print("  3. 或者使用 MySQL Workbench 执行 SQL 脚本")
    print("\n详细说明请查看：数据清除说明.md")
    sys.exit(1)


def clear_transaction_data(db: Session) -> None:
    """
    清除所有交易相关数据，但保留科目结构和现金流量分类。
    
    清除的表：
    - business_document_items (业务单据明细)
    - business_documents (业务单据)
    - splits (分录明细)
    - transactions (交易凭证)
    
    同时重置所有科目的余额为0。
    """
    print("正在清除交易数据...")
    
    # 按外键依赖顺序删除
    print("  1. 删除业务单据明细...")
    db.execute(text("DELETE FROM business_document_items"))
    
    print("  2. 删除业务单据...")
    db.execute(text("DELETE FROM business_documents"))
    
    print("  3. 删除分录明细...")
    db.execute(text("DELETE FROM splits"))
    
    print("  4. 删除交易凭证...")
    db.execute(text("DELETE FROM transactions"))
    
    print("  5. 重置所有科目余额为0...")
    db.execute(text("UPDATE accounts SET current_balance = 0"))
    
    db.commit()
    print("✓ 交易数据清除完成！")


def clear_all_data(db: Session) -> None:
    """
    完全清除所有数据（包括科目和现金流量分类）。
    
    警告：此操作会删除所有数据，包括科目结构！
    """
    print("⚠️  警告：即将清除所有数据，包括科目结构！")
    confirm = input("确认要继续吗？(输入 'YES' 确认): ")
    
    if confirm != "YES":
        print("操作已取消。")
        return
    
    print("正在清除所有数据...")
    
    # 按外键依赖顺序删除
    print("  1. 删除业务单据明细...")
    db.execute(text("DELETE FROM business_document_items"))
    
    print("  2. 删除业务单据...")
    db.execute(text("DELETE FROM business_documents"))
    
    print("  3. 删除分录明细...")
    db.execute(text("DELETE FROM splits"))
    
    print("  4. 删除交易凭证...")
    db.execute(text("DELETE FROM transactions"))
    
    print("  5. 删除现金流量分类...")
    db.execute(text("DELETE FROM cashflow_types"))
    
    print("  6. 删除会计科目...")
    db.execute(text("DELETE FROM accounts"))
    
    db.commit()
    print("✓ 所有数据清除完成！")


def show_data_summary(db: Session) -> None:
    """显示当前数据统计。"""
    print("\n当前数据统计：")
    print("-" * 50)
    
    # 统计各表记录数
    result = db.execute(text("SELECT COUNT(*) as cnt FROM accounts")).fetchone()
    print(f"  会计科目数量: {result[0] if result else 0}")
    
    result = db.execute(text("SELECT COUNT(*) as cnt FROM transactions")).fetchone()
    print(f"  交易凭证数量: {result[0] if result else 0}")
    
    result = db.execute(text("SELECT COUNT(*) as cnt FROM splits")).fetchone()
    print(f"  分录明细数量: {result[0] if result else 0}")
    
    result = db.execute(text("SELECT COUNT(*) as cnt FROM business_documents")).fetchone()
    print(f"  业务单据数量: {result[0] if result else 0}")
    
    result = db.execute(text("SELECT COUNT(*) as cnt FROM cashflow_types")).fetchone()
    print(f"  现金流量分类数量: {result[0] if result else 0}")
    
    # 统计科目余额总和
    result = db.execute(text("SELECT SUM(current_balance) as total FROM accounts")).fetchone()
    total_balance = result[0] if result and result[0] else Decimal("0")
    print(f"  科目余额总和: {total_balance}")
    
    print("-" * 50)


def main():
    """主函数。"""
    print("=" * 60)
    print("数据库数据清除工具")
    print("=" * 60)
    print()
    print("⚠️  重要提示：")
    print("   1. 清除数据前请务必备份数据库！")
    print("   2. 此操作不可恢复，请谨慎操作！")
    print()
    
    try:
        with session_scope() as db:
            # 显示当前数据统计
            show_data_summary(db)
            
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
                    clear_transaction_data(db)
                    print("\n清除后的数据统计：")
                    show_data_summary(db)
                else:
                    print("操作已取消。")
            
            elif choice == "2":
                print("\n您选择了：完全重置")
                clear_all_data(db)
                # 重新打开会话查看统计
                db.commit()
                print("\n清除后的数据统计：")
                show_data_summary(db)
            
            elif choice == "3":
                print("退出。")
            
            else:
                print("无效的选项，退出。")
    
    except Exception as e:
        print(f"\n❌ 错误：{str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

