"""
测试数据库连接脚本。

用于验证数据库配置是否正确，特别是切换到云端 MySQL 后。

使用方法：
    python test_db_connection.py
"""
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from app.database import engine
    from sqlalchemy import text
    
    print("=" * 60)
    print("数据库连接测试")
    print("=" * 60)
    print()
    
    print("正在尝试连接数据库...")
    try:
        with engine.connect() as conn:
            # 测试基本连接
            result = conn.execute(text("SELECT 1 as test"))
            test_value = result.fetchone()[0]
            
            if test_value == 1:
                print("✅ 数据库连接成功！")
                print()
                
                # 获取数据库版本
                version_result = conn.execute(text("SELECT VERSION() as version"))
                version = version_result.fetchone()[0]
                print(f"📊 MySQL 版本：{version}")
                
                # 获取当前数据库名
                db_result = conn.execute(text("SELECT DATABASE() as db_name"))
                db_name = db_result.fetchone()[0]
                print(f"📁 当前数据库：{db_name}")
                
                # 测试查询表是否存在
                tables_result = conn.execute(text("SHOW TABLES"))
                tables = [row[0] for row in tables_result.fetchall()]
                print(f"📋 数据库表数量：{len(tables)}")
                
                if tables:
                    print("   表列表：")
                    for table in tables[:10]:  # 只显示前10个
                        print(f"   - {table}")
                    if len(tables) > 10:
                        print(f"   ... 还有 {len(tables) - 10} 个表")
                
                print()
                print("=" * 60)
                print("✅ 所有测试通过！数据库配置正确。")
                print("=" * 60)
                
    except Exception as e:
        print("❌ 数据库连接失败！")
        print()
        print("错误信息：")
        print(f"  {type(e).__name__}: {str(e)}")
        print()
        print("可能的原因：")
        print("  1. 数据库地址或端口错误")
        print("  2. 用户名或密码错误")
        print("  3. 数据库不存在")
        print("  4. 网络不通或防火墙阻止")
        print("  5. SSL 配置错误（云端数据库）")
        print()
        print("请检查：")
        print("  - .env 文件中的 DATABASE_URL 配置")
        print("  - 云端数据库的白名单/安全组设置")
        print("  - SSL 证书配置（如需要）")
        print()
        print("=" * 60)
        sys.exit(1)
        
except ImportError as e:
    print("❌ 导入模块失败！")
    print(f"错误：{e}")
    print()
    print("请确保：")
    print("  1. 已安装所有依赖：pip install -r requirements.txt")
    print("  2. 已创建虚拟环境并激活")
    sys.exit(1)

