from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List
from backend import models, database, auth, ai_service

app = FastAPI(title="Travel AI API")

# Tworzymy bazę przy starcie
models.Base.metadata.create_all(bind=database.engine)

def get_db():
    db = database.SessionLocal()
    try: yield db
    finally: db.close()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# --- MODELE DANYCH (TWARDA WALIDACJA SERWEROWA) ---
class RegisterReq(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., min_length=5, max_length=100)
    password: str = Field(..., min_length=6, max_length=100)

class LoginReq(BaseModel):
    email: str
    password: str

class TripReq(BaseModel):
    # Nawet jak haker zmieni HTML, serwer odrzuci dane poza tymi widełkami!
    origin: str = Field(..., min_length=2, max_length=100)
    destination: str = Field(..., min_length=2, max_length=100)
    start_date: str       
    days: int = Field(..., ge=1, le=30)              # ge=Greater/Equal (min 1), le=Less/Equal (max 30)
    people: int = Field(..., ge=1, le=20)            # max 20 osób
    budget_per_person: int = Field(..., ge=100, le=100000) # budżet od 100 zł do 100 000 zł
    styles: List[str]     

class SaveTripReq(BaseModel):
    destination: str
    days: int
    style: str            
    plan_json: str


# --- ENDPOINTY AUTORYZACJI (/api/auth/...) ---

@app.post("/api/auth/register", tags=["Auth"])
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
    return {"msg": "Utworzono konto"}

@app.post("/api/auth/login", tags=["Auth"])
def login(creds: LoginReq, db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.email == creds.email).first()
    if not user or not auth.verify_password(creds.password, user.hashed_password):
        raise HTTPException(status_code=400, detail="Nieprawidłowy email lub hasło")
    token = auth.create_access_token(data={"sub": user.email})
    return {"access_token": token, "token_type": "bearer"}


# --- ENDPOINTY PODRÓŻY (/api/trips/...) ---

@app.post("/api/trips/generate", tags=["Trips"])
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

@app.post("/api/trips", tags=["Trips"])
def save_trip(trip: SaveTripReq, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = auth.get_user_by_token(db, token)
    if not user: raise HTTPException(status_code=401, detail="Brak autoryzacji")
    
    new_trip = models.Trip(
        destination=trip.destination, days=trip.days, style=trip.style,
        plan_json=trip.plan_json, owner_id=user.id
    )
    db.add(new_trip)
    db.commit()
    return {"msg": "Plan został zapisany"}

@app.get("/api/trips", tags=["Trips"])
def get_my_trips(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = auth.get_user_by_token(db, token)
    if not user: raise HTTPException(status_code=401, detail="Brak autoryzacji")
    
    trips = db.query(models.Trip).filter(models.Trip.owner_id == user.id).all()
    return [{"id": t.id, "destination": t.destination, "days": t.days, "plan_json": t.plan_json} for t in trips]

@app.delete("/api/trips/{trip_id}", tags=["Trips"])
def delete_trip(trip_id: int, token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    user = auth.get_user_by_token(db, token)
    if not user: raise HTTPException(status_code=401, detail="Brak autoryzacji")
    
    trip = db.query(models.Trip).filter(models.Trip.id == trip_id, models.Trip.owner_id == user.id).first()
    if not trip:
        raise HTTPException(status_code=404, detail="Plan nie został znaleziony")
    
    db.delete(trip)
    db.commit()
    return {"message": "Plan usunięty pomyślnie"}