# -*- coding: utf-8 -*-
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

load_dotenv()

def get_database_url():
    db_type = os.getenv('DB_TYPE', 'sqlite').lower()

    if db_type == 'sqlite':
        return 'sqlite:///music.db'

    elif db_type == 'postgres':
        return (f"postgresql://{os.getenv('DB_USER', 'postgres')}:"
                f"{os.getenv('DB_PASS', '')}@"
                f"{os.getenv('DB_HOST', 'localhost')}:"
                f"{os.getenv('DB_PORT', '5432')}/"
                f"{os.getenv('DB_NAME', 'musicdb')}")
    
    elif db_type == 'mariadb':
        return (f"mysql+pymysql://{os.getenv('DB_USER', 'root')}:"
                f"{os.getenv('DB_PASS', '')}@"
                f"{os.getenv('DB_HOST', 'localhost')}:"
                f"{os.getenv('DB_PORT', '3306')}/"
                f"{os.getenv('DB_NAME', 'musicdb')}")
    
    raise ValueError(f"Base de données non supportée: {db_type}")

engine = create_engine(get_database_url())
Session = sessionmaker(bind=engine)
session = Session()
Base = declarative_base()

def get_db():
    db = Session()
    try:
        yield db
    finally:
        db.close()