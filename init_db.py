"""
初始化数据库表结构。

使用方法：
    python init_db.py
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from app.database import Base, engine
# 直接导入模型类，避免导入 __init__.py 中的视图（视图在表创建后才存在）
from app.models.account import Account
from app.models.transaction import Transaction
from app.models.split import Split
from app.models.cashflow_type import CashflowType
from app.models.business_document import BusinessDocument, BusinessDocumentItem
from app.models.monthly_report import MonthlyReport
from app.models.fixed_expense import FixedExpense


def init_db():
    """创建所有数据库表"""
    print("=" * 60)
    print("数据库初始化")
    print("=" * 60)
    print()
    
    try:
        print("正在创建数据库表...")
        Base.metadata.create_all(bind=engine)
        print("✅ 数据库表创建完成！")
        print()
        
        # 验证表是否创建成功
        from sqlalchemy import inspect, text
        
        with engine.connect() as conn:
            inspector = inspect(engine)
            tables = inspector.get_table_names()
            
            print(f"📋 已创建 {len(tables)} 个表：")
            for table in sorted(tables):
                print(f"   - {table}")
            print()
            
            # 检查必需的视图（这些视图需要在数据库中手动创建）
            print("⚠️  注意：以下视图需要在数据库中手动创建：")
            print("   - v_account_balance (科目余额视图)")
            print("   - v_transaction_detail (交易明细视图)")
            print()
            print("如果这些视图不存在，某些报表功能可能无法正常工作。")
            print("请参考项目文档或 SQL 脚本创建这些视图。")
            print()
            
    except Exception as e:
        print("❌ 创建数据库表失败！")
        print()
        print(f"错误信息：{type(e).__name__}: {str(e)}")
        print()
        print("可能的原因：")
        print("  1. 数据库连接失败")
        print("  2. 数据库不存在")
        print("  3. 用户权限不足")
        print()
        print("请检查：")
        print("  - .env 文件中的 DATABASE_URL 配置")
        print("  - 数据库是否已创建")
        print("  - MySQL 服务是否正在运行")
        sys.exit(1)
    
    print("=" * 60)
    print("✅ 数据库初始化完成！")
    print("=" * 60)


if __name__ == "__main__":
    init_db()

