from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import os
from dotenv import load_dotenv

load_dotenv() # Load environment variables from .env file

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://user:password@db:5432/orgchart_db") # Added default for local dev

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()
