from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# If your password starts with @, replace the @ with %40
# Example: if password is '@xyz0', use 'root:%40xyz0@localhost'
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://mu_user:mypass123@localhost:3306/AnnonymousComplaint"

engine = create_engine(SQLALCHEMY_DATABASE_URL)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()