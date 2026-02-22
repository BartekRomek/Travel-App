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

# --- MODELE DANYCH ---

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
    budget_per_person: int  
    styles: List[str]     

class SaveTripReq(BaseModel):
    destination: str
    days: int
    style: str            
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

@app.post("/generate")
def generate(trip: TripReq):
    plan = ai_service.generate_trip_plan(
        trip.origin, 
        trip.destination, 
        trip.start_date,
        trip.days, 
        trip.people, 
        trip.budget_per_person, 
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
def get_my_trips(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = auth.get_user_by_token(db, token)
    if not user: raise HTTPException(status_code=401)
    
    # Zmiana na models.Trip i owner_id
    trips = db.query(models.Trip).filter(models.Trip.owner_id == user.id).all()
    return [{"id": t.id, "destination": t.destination, "days": t.days, "plan_json": t.plan_json} for t in trips]

@app.delete("/delete-trip/{trip_id}")
def delete_trip(trip_id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = auth.get_user_by_token(db, token)
    if not user: raise HTTPException(status_code=401)
    
    # Zmiana na models.Trip i owner_id, upewniamy się że to plan tego użytkownika
    trip = db.query(models.Trip).filter(models.Trip.id == trip_id, models.Trip.owner_id == user.id).first()
    
    if not trip:
        raise HTTPException(status_code=404, detail="Plan nie został znaleziony lub nie masz do niego dostępu")
    
    db.delete(trip)
    db.commit()
    return {"message": "Plan usunięty pomyślnie"}