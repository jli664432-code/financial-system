"""
应用启动脚本。

执行 `python run.py` 即可启动开发服务器。
"""
import uvicorn


def main() -> None:
    """
    启动 Uvicorn 服务器。
    """
    uvicorn.run(
        "app.main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
        reload_dirs=["app"],  # 明确指定要监控的目录
    )


if __name__ == "__main__":
    main()

