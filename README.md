# 财务记账系统

一个基于 FastAPI + SQLAlchemy 构建的简易财务记账系统，支持会计凭证录入、科目管理、财务报表生成等功能。

## ✨ 功能特性

- 📝 **会计凭证管理**：支持借贷平衡的凭证录入和编辑
- 📊 **科目管理**：支持科目层级结构，可设置科目类型、编码、隐藏等属性
- 💼 **业务流程**：支持销售、采购、费用报销、收付款等业务流程单据
- 📈 **财务报表**：
  - 资产负债表
  - 利润表
  - 现金流量表
  - 科目余额表
  - 交易明细表
- ⚡ **实时报表**：快速生成当前日期的报表（不保存）
- 💰 **现金流量分类**：支持经营活动、投资活动、筹资活动的现金流量分类
- 📅 **月度报表缓存**：自动生成并缓存上一整月的报表快照
- 🔁 **固定费用管理**：配置工资、房租、水电、社保等固定费用，自动扣款并生成交易

## 🛠️ 技术栈

- **后端框架**：FastAPI 0.110.0
- **ORM**：SQLAlchemy 2.0.23
- **数据库**：MySQL（通过 PyMySQL）
- **数据验证**：Pydantic 2.6.4
- **模板引擎**：Jinja2 3.1.4
- **Web服务器**：Uvicorn 0.30.1

## 🌐 在线访问

本项目已部署在云端服务器并正常运行，您可以直接访问体验：

- **在线演示地址**：http://47.96.79.142:8000

> 💡 **提示**：系统已配置完整的财务记账功能，包括会计凭证管理、科目管理、业务流程和财务报表等。欢迎访问体验！

## 📋 环境要求

- Python 3.8+（推荐 3.10+）
- MySQL 5.7+ 或 8.0+
- 已创建数据库和必要的表结构

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/your-username/accounting-system.git
cd accounting-system
```

### 2. 创建虚拟环境

**Windows:**
```bash
python -m venv .venv
.venv\Scripts\activate
```

**Linux/Mac:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### 3. 安装依赖

```bash
pip install -r requirements.txt
```

### 4. 配置环境变量

复制 `.env.example` 文件并重命名为 `.env`：

**Windows:**
```bash
copy .env.example .env
```

**Linux/Mac:**
```bash
cp .env.example .env
```

编辑 `.env` 文件，配置数据库连接：

**本地 MySQL：**
```env
DATABASE_URL=mysql+pymysql://用户名:密码@主机:端口/数据库名
```

示例：
```env
DATABASE_URL=mysql+pymysql://root:password@127.0.0.1:3306/accounting_system
```

**云端 MySQL（阿里云、腾讯云、AWS 等）：**
```env
# 基本格式
DATABASE_URL=mysql+pymysql://用户名:密码@云端主机地址:端口/数据库名

# 示例（阿里云 RDS）
DATABASE_URL=mysql+pymysql://username:password@rm-xxxxx.mysql.rds.aliyuncs.com:3306/accounting_system
```

> **提示**：如果密码包含特殊字符（如 `@`、`#`），需要进行 URL 编码。  

### 5. 数据库准备

确保你的 MySQL 数据库中已创建以下表：
- `accounts` - 会计科目表
- `transactions` - 交易凭证表
- `splits` - 分录表
- `business_documents` - 业务单据表
- `business_document_items` - 业务单据明细表
- `cashflow_types` - 现金流量分类表
- `monthly_reports` - 月度报表缓存表（可选）
- `fixed_expenses` - 固定费用配置表（可选，但推荐创建）

以及以下视图：
- `v_account_balance` - 科目余额视图
- `v_transaction_detail` - 交易明细视图

可以参考项目中的 SQL 文件创建表结构。

### 6. 启动服务

```bash
python run.py
```

或者使用启动脚本（Windows）：
```bash
start-app.bat
```

### 7. 访问应用

启动成功后，在浏览器中访问：

- **前端页面**：http://127.0.0.1:8000/
- **API 文档**：http://127.0.0.1:8000/docs（如果启用）

> 🌐 **在线版本**：如果您想直接体验系统功能，可以访问已部署的在线版本：http://47.96.79.142:8000

## 📖 主要功能说明

### 会计凭证

系统支持标准的借贷记账法，每条凭证必须包含至少两条分录，且借贷金额必须平衡。

**创建凭证示例：**
```json
{
  "post_date": "2025-01-15",
  "description": "购置办公用品",
  "num": "JZ2025011501",
  "splits": [
    {"account_guid": "ASSET-GUID-001", "amount": 500.00, "memo": "现金支出"},
    {"account_guid": "EXPENSE-GUID-002", "amount": -500.00, "memo": "办公用品费用"}
  ]
}
```

> **注意**：金额以 "借为正、贷为负" 的方式录入，系统会在保存前校验总和必须为 0。

### 业务流程

系统支持以下业务流程，每个流程会自动生成对应的会计凭证：

- **销售业务** (`POST /business/sales`)：销售商品给客户
- **采购业务** (`POST /business/purchases`)：从供应商采购商品
- **费用报销** (`POST /business/expenses`)：员工报销费用
- **收付款** (`POST /business/cashflow`)：记录收款或付款

### 财务报表

- **月度报表** (`GET /reports/financial`)：查看上一整月的报表快照
- **实时报表** (`GET /reports/financial/current`)：快速生成当前日期的报表（不保存）

### 固定费用管理

在 **“固定费用”** 页面可以配置工资、房租、水电、社保等固定扣费项目：

- 支持设置扣款金额、费用科目、优先扣款科目（库存现金）、备用扣款科目（银行存款）和预计扣款日
- 每次执行会自动生成标准的会计交易并记录到分录中
- 如果库存现金余额不足，会自动改用备用科目并显示警报
- 可手动执行单个配置，也可一键执行当月所有到期的固定费用

## 📁 项目结构

```
accounting-system/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置管理
│   ├── database.py          # 数据库连接
│   ├── api/                 # API 路由
│   │   ├── accounts.py      # 科目相关接口
│   │   ├── transactions.py  # 交易相关接口
│   │   ├── pages.py         # 页面路由
│   │   └── business.py      # 业务流程接口
│   ├── models/              # 数据库模型
│   │   ├── account.py
│   │   ├── transaction.py
│   │   ├── split.py
│   │   ├── business_document.py
│   │   └── ...
│   ├── schemas/             # Pydantic 模式
│   │   ├── account.py
│   │   ├── transaction.py
│   │   └── ...
│   ├── crud/                # 数据库操作
│   │   ├── account.py
│   │   ├── transaction.py
│   │   ├── financial_report.py
│   │   └── ...
│   ├── templates/           # Jinja2 模板
│   │   ├── base.html
│   │   ├── index.html
│   │   ├── accounts.html
│   │   └── ...
│   ├── static/              # 静态文件
│   │   └── js/
│   └── utils/               # 工具函数
│       ├── guid_helper.py
│       └── amount_helper.py
├── .env.example             # 环境变量示例
├── .gitignore
├── requirements.txt         # Python 依赖
├── README.md
└── run.py                   # 启动脚本
```

## 🔌 API 接口

### 科目管理

- `GET /accounts/` - 查询所有科目
- `GET /accounts/{guid}` - 查看单个科目详情

### 交易管理

- `GET /transactions/` - 查询交易列表
- `GET /transactions/{guid}` - 查看交易详情
- `POST /transactions/` - 创建新交易
- `PUT /transactions/{guid}` - 更新交易
- `DELETE /transactions/{guid}` - 删除交易

### 业务流程

- `POST /business/sales` - 创建销售单
- `POST /business/purchases` - 创建采购单
- `POST /business/expenses` - 创建费用单
- `POST /business/cashflow` - 创建收付款单

### 报表查询

- `GET /reports/balances` - 科目余额表
- `GET /reports/transaction-details` - 交易明细表
- `GET /reports/financial` - 月度财务报表
- `GET /reports/financial/current` - 当前实时报表

## ❓ 常见问题

### 连接数据库失败

- 检查 MySQL 服务是否已启动
- 确认 `DATABASE_URL` 配置是否正确
- 验证数据库用户是否有足够的权限

### 金额精度问题

系统使用 `value_num/value_denom` 分数形式存储金额，确保不会引入浮点误差。显示时默认保留 2 位小数。

### 报表数据为空

- 确认数据库中已有交易数据
- 检查科目类型分类是否正确
- 验证报表日期范围是否合理

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！



## 📝 更新日志

### v0.2.0
- 新增固定费用管理功能，可配置工资/房租/水电/社保等固定扣费
- 支持优先扣库存现金、余额不足时自动切换银行存款并提醒
- 新增固定费用执行页面与自动生成交易记录的逻辑

### v0.1.0
- 初始版本发布
- 支持基本的会计凭证管理
- 支持科目管理和层级结构
- 支持业务流程单据
- 支持财务报表生成
- 支持实时报表生成（不保存）

## 👤 作者

你的名字

---

如果这个项目对你有帮助，请给一个 ⭐ Star！
