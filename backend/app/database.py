import os

from flask_sqlalchemy import SQLAlchemy


db = SQLAlchemy()


def get_database_url():
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        if database_url.startswith("postgres://"):
            database_url = database_url.replace("postgres://", "postgresql+psycopg://", 1)
        elif database_url.startswith("postgresql://"):
            database_url = database_url.replace("postgresql://", "postgresql+psycopg://", 1)
        return database_url
    return os.getenv("SQLALCHEMY_DATABASE_URI", "sqlite:///../kirana.db")
