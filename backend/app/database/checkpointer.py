import os
import aiomysql
from langgraph.checkpoint.mysql.aio import AIOMySQLSaver


async def get_checkpointer() -> AIOMySQLSaver:
    """AIOMySQLSaver 체크포인터 인스턴스 생성 및 테이블 초기화

    aiomysql.connect()로 장수명 연결을 직접 생성합니다.
    (from_conn_string은 async context manager라 context 밖에서 연결이 끊어짐)
    """
    conn = await aiomysql.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root"),
        password=os.getenv("MYSQL_PASSWORD", ""),
        db=os.getenv("MYSQL_DATABASE", ""),
        autocommit=True,
    )
    checkpointer = AIOMySQLSaver(conn=conn)
    await checkpointer.setup()  # checkpoint 테이블 자동 생성
    return checkpointer
