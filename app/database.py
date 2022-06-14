from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import psycopg2
from psycopg2.extras import RealDictCursor
import time
from config import settings
# Connection Using SQLAlchemy
# Connection Format of Connection String
# SQLALCHEMY_DATABASE_URL = 'postgresql://<username>:<password>@<ip-address/hostname>/<database_name>'
SQLALCHEMY_DATABASE_URL = f'postgresql://{settings.database_username}:{settings.database_password}@{settings.database_hostname}:{settings.database_port}/{settings.database_name}'

# Create an Engine: (Responsible for SQLAlchemy to connect to a DB)
engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base  = declarative_base()

# Dependency
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

#Connection using PostGreSQL, {psycopg} A Python driver for PostgreSQL

# while True:
#     try:
#         conn = psycopg2.connect(host='localhost', database='fastapi',
#                                 user='postgres', password='hellojee',
#                                 cursor_factory=RealDictCursor)
#         cursor = conn.cursor()
#         print("DB connection was Success")
#         break
#     except Exception as error:
#         print("Conneting to DB failed")
#         print("Error: ", error)
#         time.sleep(3)
