from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from backend import models, database, auth, ai_service

app = FastAPI()

# Tworzymy bazę przy starcie
models.Base.metadata.create_all(bind=database.engine)

def get_db():
    db = database.SessionLocal()
    try: yield db
    finally: db.close()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

# --- MODELE DANYCH (To musi pasować do Frontendu!) ---

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
    start_date: str       # Frontend wysyła to jako napis "RRRR-MM-DD"
    days: int
    people: int
    budget: int           # Frontend wysyła liczbę
    styles: List[str]     # Frontend wysyła LISTĘ napisów (np. ["Historia", "Impreza"])

class SaveTripReq(BaseModel):
    destination: str
    days: int
    style: str            # Do zapisu w bazie sklejamy to w jeden napis
    plan_json: str

# --- ENDPOINTY ---

@app.post("/register")
def register(user: RegisterReq, db: Session = Depends(get_db)):
    if db.query(models.User).filter(models.User.email == user.email).first():
        raise HTTPException(status_code=400, detail="Email zajęty")
    new_user = models.User(
        username=user.username, 
        email=user.email, 
        hashed_password=auth.get_password_hash(user.password)
    )
    db.add(new_user)
    db.commit()
    return {"msg": "OK"}

@app.post("/login")
def login(creds: LoginReq, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == creds.email).first()
    if not user or not auth.verify_password(creds.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Błąd logowania")
    token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}

# --- TUTAJ BYŁ BŁĄD, TERAZ JEST POPRAWIONE ---
@app.post("/generate")
def generate(trip: TripReq):
    # Przekazujemy wszystkie nowe parametry do AI
    plan = ai_service.generate_trip_plan(
        trip.origin, 
        trip.destination, 
        trip.start_date,
        trip.days, 
        trip.people, 
        trip.budget, 
        trip.styles
    )
    return {"plan": plan}

@app.post("/save-trip")
def save_trip(trip: SaveTripReq, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = auth.get_user_by_token(db, token)
    if not user: raise HTTPException(status_code=401)
    
    new_trip = models.Trip(
        destination=trip.destination, days=trip.days, style=trip.style,
        plan_json=trip.plan_json, owner_id=user.id
    )
    db.add(new_trip)
    db.commit()
    return {"msg": "Zapisano"}

@app.get("/my-trips")
def get_trips(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = auth.get_user_by_token(db, token)
    if not user: raise HTTPException(status_code=401)
    return db.query(models.Trip).filter(models.Trip.owner_id == user.id).all()