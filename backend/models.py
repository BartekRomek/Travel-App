from sqlalchemy import Column, Integer, String, ForeignKey, Text
from backend.database import Base
from pydantic import BaseModel
from typing import List, Optional

# --- BAZA DANYCH (SQL) ---
class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)

class Trip(Base):
    __tablename__ = "trips"
    id = Column(Integer, primary_key=True, index=True)
    destination = Column(String)
    days = Column(Integer)
    # W bazie zapiszemy style jako jeden napis po przecinku np. "Historia, Impreza"
    style = Column(String) 
    plan_json = Column(Text)
    owner_id = Column(Integer, ForeignKey("users.id"))

# --- MODELE KOMUNIKACJI (API) ---
class RegisterReq(BaseModel):
    username: str
    email: str
    password: str

class LoginReq(BaseModel):
    email: str
    password: str

class TripReq(BaseModel):
    origin: str
    destination: str
    start_date: str      # NOWOŚĆ: Data początkowa (np. "2024-05-01")
    days: int
    people: int
    budget: int          # NOWOŚĆ: Liczba (sztywny limit)
    styles: List[str]    # NOWOŚĆ: Lista wybranych stylów

class SaveTripReq(BaseModel):
    destination: str
    days: int
    style: str           # Tu już wysyłamy sklejony napis
    plan_json: str