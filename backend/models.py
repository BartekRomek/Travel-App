from sqlalchemy import Column, Integer, String, ForeignKey, Text
from backend.database import Base
from pydantic import BaseModel
from typing import List, Optional

# BAZA DANYCH
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
    style = Column(String) 
    plan_json = Column(Text)
    owner_id = Column(Integer, ForeignKey("users.id"))

# API
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
    start_date: str
    days: int
    people: int
    budget: int
    styles: List[str]

class SaveTripReq(BaseModel):
    destination: str
    days: int
    style: str
    plan_json: str