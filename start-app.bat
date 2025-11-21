@echo off
REM ============================================================
REM  一键启动 FastAPI 财务记账系统
REM  步骤：
REM    1. 切换到项目目录
REM    2. 激活虚拟环境 .venv312
REM    3. 运行 python run.py
REM ============================================================

cd /d D:\1
call .venv312\Scripts\activate.bat
python run.py

REM 保持窗口，方便查看日志；按任意键关闭
pause

