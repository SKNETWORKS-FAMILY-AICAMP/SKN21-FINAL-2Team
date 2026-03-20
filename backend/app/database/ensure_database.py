import os
import time

import pymysql
from dotenv import load_dotenv


load_dotenv(override=True)

DEFAULT_CHARSET = "utf8mb4"
DEFAULT_COLLATION = "utf8mb4_0900_ai_ci"


def _build_root_connection_kwargs() -> dict:
    host = os.getenv("MYSQL_HOST", "localhost")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    user = os.getenv("MYSQL_ROOT_USER", "root")
    password = os.getenv("MYSQL_ROOT_PASSWORD", "")

    return {
        "host": host,
        "port": port,
        "user": user,
        "password": password,
        "database": "mysql",
        "charset": DEFAULT_CHARSET,
        "cursorclass": pymysql.cursors.DictCursor,
        "autocommit": True,
    }


def wait_for_mysql(max_retries: int = 30, retry_interval: int = 2) -> None:
    connection_kwargs = _build_root_connection_kwargs()
    last_error = None

    for attempt in range(1, max_retries + 1):
        try:
            connection = pymysql.connect(**connection_kwargs)
            connection.close()
            return
        except pymysql.MySQLError as exc:
            last_error = exc
            print(f"[DB] MySQL 대기 중 ({attempt}/{max_retries}): {exc}")
            time.sleep(retry_interval)

    raise RuntimeError(f"MySQL 연결에 실패했습니다: {last_error}")


def ensure_database_exists() -> None:
    db_name = os.getenv("MYSQL_DATABASE")
    if not db_name:
        raise RuntimeError("MYSQL_DATABASE 환경변수가 설정되지 않았습니다.")

    charset = os.getenv("MYSQL_CHARSET", DEFAULT_CHARSET)
    collation = os.getenv("MYSQL_COLLATION", DEFAULT_COLLATION)
    app_user = os.getenv("MYSQL_USER")
    app_password = os.getenv("MYSQL_PASSWORD")

    connection = pymysql.connect(**_build_root_connection_kwargs())
    try:
        with connection.cursor() as cursor:
            cursor.execute(
                f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
                f"CHARACTER SET {charset} COLLATE {collation}"
            )

            if app_user and app_password is not None:
                cursor.execute(
                    "CREATE USER IF NOT EXISTS %s@'%%' IDENTIFIED BY %s",
                    (app_user, app_password),
                )
                cursor.execute(
                    f"GRANT ALL PRIVILEGES ON `{db_name}`.* TO %s@'%%'",
                    (app_user,),
                )
                cursor.execute("FLUSH PRIVILEGES")

        print(f"[DB] 데이터베이스 `{db_name}` 준비 완료")
    finally:
        connection.close()


def main() -> None:
    wait_for_mysql()
    ensure_database_exists()


if __name__ == "__main__":
    main()
