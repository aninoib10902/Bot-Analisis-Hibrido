from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
import os

# Usaremos una variable de entorno para la URL de la DB
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///historico.db') # SQLite para local, Postgres para Azure

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class AnalisisHistorial(Base):
    __tablename__ = "analisis"
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String, index=True)
    iss_score = Column(Float)
    fecha = Column(DateTime, default=datetime.datetime.utcnow)

# Crea las tablas automáticamente
def init_db():
    Base.metadata.create_all(bind=engine)

def guardar_analisis(ticker, iss_score):
    db = SessionLocal()
    registro = AnalisisHistorial(ticker=ticker, iss_score=iss_score)
    db.add(registro)
    db.commit()
    db.close()