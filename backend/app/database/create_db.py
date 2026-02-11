import pymysql
from pydbml import PyDBML
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(override=True) # .env 로드

# 1. DBML 파일 내용 (위에서 작성한 내용을 string으로 넣거나 파일을 읽음)
dbml_content = """
// 1. Enum 정의
Enum gender_type {
  male
  female
  other
}

Enum role_type {
  human
  ai
}

// 2. 회원 정보
Table users {
  id integer [primary key, increment]
  email varchar [unique, not null]
  name varchar
  gender gender_type // 정의한 Enum 사용

  // 
  social_provider varchar
  social_id varchar [unique]
  social_access_token varchar
  social_refresh_token varchar
  
  // 기존 방식대로 유지 (특정 카테고리 고정)
  actor_prefer_id integer
  movie_prefer_id integer
  drama_prefer_id integer
  celeb_prefer_id integer
  variety_prefer_id integer

  with_yn bool
  dog_yn bool
  vegan_yn bool

  is_join bool [not null, default: true]
  is_perfer bool [not null, default: false]

  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}

// 3. 선호도 마스터
Table prefers {
  id integer [primary key, increment]
  category varchar // 'actor', 'movie', 'travel_theme' 등
  type varchar
  value varchar
  image_path text // 파일 경로는 보통 text/varchar
}

// 4. 채팅방 및 메시지
Table chat_rooms {
  id integer [primary key, increment]
  user_id integer
  title varchar
  created_at timestamp [default: `now()`]
}

Table chat_messages {
  id integer [primary key, increment]
  room_id integer
  message text
  role role_type [default: 'human'] // 정의한 Enum 사용
  latitude float
  longitude float
  image_path text
  bookmark_yn bool [not null, default: false]
  created_at timestamp [default: `now()` ]
}

// --- 관계 설정 (Ref) ---

// Users - 특정 선호도 연결 (1:N)
Ref: users.actor_prefer_id > prefers.id
Ref: users.movie_prefer_id > prefers.id
Ref: users.drama_prefer_id > prefers.id
Ref: users.celeb_prefer_id > prefers.id
Ref: users.variety_prefer_id > prefers.id

// 채팅방 및 메시지
Ref: chat_rooms.user_id > users.id
Ref: chat_messages.room_id > chat_rooms.id
"""

def deploy_db_from_dbml():
    # 2. DBML을 SQL로 파싱
    parsed = PyDBML(dbml_content)
    
    # 3. MySQL 호환성 변환 (PostgreSQL ENUM -> MySQL ENUM)
    # PyDBML은 기본적으로 PostgreSQL 문법을 생성함 (CREATE TYPE ... AS ENUM)
    # 이를 MySQL의 CREATE TABLE 내 ENUM(...) 정의로 변환해야 함
    
    sql_statements = parsed.sql
    
    # 변환 로직:
    # 1. 'CREATE TYPE ... AS ENUM ...' 문장을 찾아서 ENUM 정의를 추출
    # 2. 'CREATE TABLE' 문 내에서 해당 타입을 사용할 때 ENUM definition으로 치환
    # 3. 'CREATE TYPE' 문 제거
    
    # 간단한 문자열 치환 방식으로 처리 (복잡한 파싱 대신 정규식 사용)
    import re
    
    # ENUM 정의 추출
    enum_defs = {}
    enum_pattern = re.compile(r"CREATE TYPE \"?(\w+)\"? AS ENUM\s*\(([^)]+)\);", re.MULTILINE | re.DOTALL)
    
    for match in enum_pattern.finditer(sql_statements):
        enum_name = match.group(1)
        enum_values = match.group(2)
        # 줄바꿈과 공백 정리
        enum_values_clean = ", ".join([v.strip() for v in enum_values.split(',') if v.strip()])
        enum_defs[enum_name] = f"ENUM({enum_values_clean})"
    
    # CREATE TYPE 문 제거
    sql_statements = enum_pattern.sub("", sql_statements)
    
    # 테이블 정의 내에서 ENUM 타입 치환
    for enum_name, enum_def in enum_defs.items():
        # "column_name" "enum_type" 패턴을 찾아서 치환
        sql_statements = sql_statements.replace(f" {enum_name}", f" {enum_def}")
        sql_statements = sql_statements.replace(f"\"{enum_name}\"", f"{enum_def}") # 혹시 따옴표가 있는 경우

    # 4. MySQL 연결 설정 (따옴표 제거 및 추가 변환)
    # PyDBML은 테이블명과 컬럼명에 쌍따옴표를 사용함 ("table", "column")
    # MySQL은 기본적으로 백틱(`)을 사용하거나 따옴표 없이 사용해야 함 (ANSI_QUOTES 모드가 아닐 경우)
    sql_statements = sql_statements.replace('"', '')
    
    # AUTOINCREMENT -> AUTO_INCREMENT
    sql_statements = sql_statements.replace("AUTOINCREMENT", "AUTO_INCREMENT")
    
    # timestamp DEFAULT (now()) -> timestamp DEFAULT CURRENT_TIMESTAMP
    sql_statements = sql_statements.replace("DEFAULT (now())", "DEFAULT CURRENT_TIMESTAMP")
    sql_statements = sql_statements.replace("DEFAULT `now()`", "DEFAULT CURRENT_TIMESTAMP") # 혹시 백틱으로 나올 경우 대비
    
    # varchar -> varchar(255) (MySQL에서는 varchar 길이 지정 필수)
    # 단, 이미 길이가 지정된 경우는 제외해야 하지만, PyDBML은 기본적으로 타입명만 가져옴
    # 정규식으로 'varchar' 뒤에 '('가 오지 않는 경우만 치환
    sql_statements = re.sub(r"varchar(?!\()", "varchar(255)", sql_statements)

    import os
    import time
    import socket
    from pathlib import Path
    
    # .env 파일 로드 (상위 디렉토리까지 탐색) - main block에서 로드했지만 여기서도 안전하게
    # load_dotenv() # 이미 상단에서 로드됨
    if not os.getenv("MYSQL_ROOT_PASSWORD"):
        load_dotenv(Path(__file__).resolve().parent.parent.parent / '.env', override=True)
        
    # Docker 내부에서는 'mysql', 로컬에서는 'localhost'
    
    host = os.getenv('MYSQL_HOST', 'localhost')
    port = int(os.getenv('MYSQL_PORT', 3307))
    
    # 호스트 해석 시도
    try:
        if host == 'mysql':
            socket.gethostbyname(host)
    except socket.gaierror:
        # 'mysql' 호스트를 찾을 수 없으면 로컬 실행으로 간주
        print(f"⚠️ '{host}' 호스트를 찾을 수 없습니다. 로컬 환경(localhost)으로 전환합니다.")
        host = 'localhost'
        port = 3307 # 로컬 포트 강제 (Docker Compose 매핑 포트)

    user = os.getenv('MYSQL_USER', 'root')
    password = os.getenv('MYSQL_PASSWORD', 'your_password') #.env가 없을 때 주의
    db_name = os.getenv('MYSQL_DATABASE', 'your_database_name')

    db_config = {
        'host': host,
        'user': user,
        'password': password,
        'db': db_name,
        'port': port,
        'charset': 'utf8mb4',
        'cursorclass': pymysql.cursors.DictCursor
    }
    
    print(f"🔌 DB 연결 시도: {host}:{port} / User: {user} / DB: {db_name}")

    connection = None
    retries = 5
    while retries > 0:
        try:
            connection = pymysql.connect(**db_config)
            break
        except pymysql.MySQLError as e:
            print(f"⏳ DB 연결 실패 (재시도 {6 - retries}/5): {e}")
            time.sleep(2)
            retries -= 1
    
    if not connection:
        print("❌ DB 연결에 실패했습니다. 설정과 컨테이너 상태를 확인해주세요.")
        return
    
    try:
        with connection.cursor() as cursor:
            # 외래키 제약 조건 잠시 해제 (순서 상관없이 테이블 생성 위함)
            cursor.execute("SET FOREIGN_KEY_CHECKS = 0;")
            
            # 생성된 SQL 실행 (세미콜론으로 나누어 개별 실행)
            # 빈 줄이나 주석 라인 처리 필요할 수 있음
            for statement in sql_statements.split(';'):
                stmt = statement.strip()
                if stmt:
                    try:
                        cursor.execute(stmt)
                        # print(f"Executed: {stmt[:50]}...")
                    except Exception as sql_err:
                        print(f"⚠️ SQL 실행 경고: {sql_err}")
                        print(f"Query: {stmt}")

            
            cursor.execute("SET FOREIGN_KEY_CHECKS = 1;")
            connection.commit()
            print("✅ DB 테이블이 성공적으로 생성되었습니다!")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    deploy_db_from_dbml()
