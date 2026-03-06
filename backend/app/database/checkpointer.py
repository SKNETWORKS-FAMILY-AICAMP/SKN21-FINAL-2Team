import os
import asyncio
import aiomysql
from langgraph.checkpoint.mysql.aio import AIOMySQLSaver

_checkpointer: AIOMySQLSaver | None = None
_conn: aiomysql.Connection | None = None
_checkpointer_lock = asyncio.Lock()

async def _create_checkpointer() -> AIOMySQLSaver:
    global _conn

    _conn = await aiomysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        db=os.getenv("MYSQL_DATABASE", ""),
        charset="utf8mb4",
        autocommit=True,
    )
    checkpointer = AIOMySQLSaver(conn=_conn)
    await checkpointer.setup()  # checkpoint 테이블 자동 생성
    return checkpointer


async def _is_conn_alive() -> bool:
    if _conn is None:
        return False
    try:
        await _conn.ping(reconnect=False)
        return True
    except Exception:
        return False


async def get_checkpointer(force_reconnect: bool = False) -> AIOMySQLSaver:
    """AIOMySQLSaver 체크포인터 인스턴스 생성/재연결"""
    global _checkpointer, _conn

    if not force_reconnect and _checkpointer is not None and await _is_conn_alive():
        return _checkpointer

    async with _checkpointer_lock:
        if not force_reconnect and _checkpointer is not None and await _is_conn_alive():
            return _checkpointer

        # 기존 커넥션 정리
        if _conn is not None:
            try:
                _conn.close()
            except Exception:
                pass
            _conn = None

        _checkpointer = await _create_checkpointer()
        return _checkpointer
