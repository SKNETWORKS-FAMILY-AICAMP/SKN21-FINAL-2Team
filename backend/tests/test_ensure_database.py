from app.database.ensure_database import ensure_database_exists


class _FakeCursor:
    def __init__(self):
        self.executed = []

    def execute(self, sql, params=None):
        self.executed.append((sql, params))

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class _FakeConnection:
    def __init__(self):
        self.cursor_instance = _FakeCursor()
        self.closed = False

    def cursor(self):
        return self.cursor_instance

    def close(self):
        self.closed = True


def test_ensure_database_creates_database_and_grants_user(monkeypatch):
    fake_connection = _FakeConnection()

    monkeypatch.setenv("MYSQL_DATABASE", "skn_db")
    monkeypatch.setenv("MYSQL_USER", "skn_user")
    monkeypatch.setenv("MYSQL_PASSWORD", "skn_password")
    monkeypatch.setattr(
        "app.database.ensure_database.pymysql.connect",
        lambda **kwargs: fake_connection,
    )

    ensure_database_exists()

    executed = fake_connection.cursor_instance.executed
    assert any("CREATE DATABASE IF NOT EXISTS `skn_db`" in sql for sql, _ in executed)
    assert any("CREATE USER IF NOT EXISTS %s@'%%' IDENTIFIED BY %s" == sql for sql, _ in executed)
    assert any("GRANT ALL PRIVILEGES ON `skn_db`.* TO %s@'%%'" == sql for sql, _ in executed)
    assert fake_connection.closed is True
