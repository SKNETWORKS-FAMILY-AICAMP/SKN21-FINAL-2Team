import os
import time
import socket
from pathlib import Path
import pymysql
from pydbml import PyDBML
from dotenv import load_dotenv
from app.database.insert_db import insert_data

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

Table country {
    code varchar [primary key]
    name varchar
}

// 2. 회원 정보
Table users {
  id integer [primary key, increment]
  email varchar [unique, not null]
  name varchar
  nickname varchar
  profile_picture varchar
  gender gender_type // 정의한 Enum 사용
  country_code varchar

  // Google Login
  social_provider varchar
  social_id varchar [unique]
  social_access_token varchar
  social_refresh_token varchar
  
  // 선호도 조사 및 특이사항
  plan_prefer varchar
  vibe_prefer varchar
  places_prefer varchar
  extra_prefer1 varchar
  extra_prefer2 varchar
  extra_prefer3 varchar

  is_join bool [not null, default: false]
  is_prefer bool [not null, default: false]
  created_at timestamp [default: `now()`]
  updated_at timestamp [default: `now()`]
}

// 3. 채팅방
Table chat_rooms {
  id integer [primary key, increment]
  user_id integer
  title varchar
  created_at timestamp [default: `now()`]
  history text
  adult_num integer
  child_num integer
  start_date date
  end_date date
  bookmark_yn bool [not null, default: false]
}

// 4. 채팅방 & 추천 장소
Table chat_messages {
  id integer [primary key, increment]
  room_id integer
  message text
  role role_type [default: 'human'] // 정의한 Enum 사용
  image_path text
  created_at timestamp [default: `now()` ]
  longitude float
  latitude float
}

Table chat_places {
  id integer [primary key, increment]
  messages_id integer
  place_id integer
  name varchar
  adress varchar
  image_path varchar
  longitude float
  latitude float
  bookmark_yn bool [not null, default: false]
}

// 5. 핫플레이스 DB
Table hot_places {
  id integer [primary key, increment]
  name text
  adress text
  feature text
  tag1 text
  tag2 text
  image_path varchar
}

// 6. 예매내역 이미지 DB
Table reservation_list {
  id integer [primary key, increment]
  user_id integer
  category varchar
  name varchar
  date date
  image_path varchar
}

// --- 관계 설정 (Ref) ---

// Users - 국적 연결 (1:N)
Ref: users.country_code > country.code

// 채팅방 및 메시지
Ref: users.id < chat_rooms.user_id
Ref: chat_rooms.id < chat_messages.room_id
Ref: chat_messages.id < chat_places.messages_id

// 예약 내역
Ref: users.id < reservation_list.user_id
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
        'collation': 'utf8mb4_0900_ai_ci',
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
            
            # 기존 테이블 삭제 (LangGraph 체크포인터 테이블 포함)
            tables = [
                "chat_places", "chat_messages", "chat_rooms",
                "reservation_list", "hot_places",
                "users", "country",
                "checkpoints", "checkpoint_blobs", "checkpoint_writes", "checkpoint_migrations"
            ]
            for table in tables:
                cursor.execute(f"DROP TABLE IF EXISTS {table}")
                print(f"🗑️ Table '{table}' dropped.")
            
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

            # 기본 데이터 삽입 자동 호출 (country)
            print("🚀 기본 데이터(country) 삽입을 시작합니다...")
            try:
                from app.database.insert_db import insert_country
                cntry_res = insert_country()
                print(f"   - country: inserted={cntry_res['inserted']}, skipped={cntry_res['skipped']}")
            except Exception as e:
                print(f"⚠️ 데이터 삽입 중 경고 발생: {e}")
            
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
    finally:
        if connection:
            connection.close()

if __name__ == "__main__":
    print(f"[INFO] dbml deploy start")
    deploy_db_from_dbml()
    print(f"[INFO] dbml deploy done")

    print(f"[INFO] data insert start")
    insert_data()
    print(f"[INFO] data insert done")
