import google.generativeai as genai
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
# Zostawiamy tylko to, co działa pewnie (waluty i pogoda)
from .external_apis import get_nbp_exchange_rate, get_weather_forecast

load_dotenv()

def generate_trip_plan(origin, destination, start_date, days, people, budget_per_person, styles):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: return json.dumps({"error": "Brak klucza API"})

    try:
        genai.configure(api_key=api_key)
        
        # Używamy modelu, który u Ciebie działał ostatnio
        model = genai.GenerativeModel('gemini-2.5-flash') 
        
        style_desc = ", ".join(styles) if styles else "Mix zwiedzania i relaksu"

        prompt = f"""
        Jesteś ekspertem podróży. Zaplanuj wyjazd: {origin} -> {destination}.
        Start: {start_date}. Czas trwania: {days} dni.
        Budżet: {budget_per_person} PLN/os. Styl: {style_desc}.

        WYMAGANIA:
        1. Zidentyfikuj kod waluty docelowej (np. EUR, USD).
        2. Zidentyfikuj współrzędne geograficzne (lat, lon) centrum miasta docelowego.
        3. Stwórz spójny, narracyjny plan dnia z wplecionymi posiłkami.
        
        Zwróć TYLKO JSON:
        {{
            "is_feasible": true,
            "feasibility_message": "Plan OK.",
            "currency_code": "EUR", 
            "location_coordinates": [0.0, 0.0],
            "flight_search_query": {{ "origin_iata": "WAW", "dest_iata": "XXX" }},
            "pole_abroad": {{ "visa_info": "...", "safety_warning": "...", "emergency_numbers": "..." }},
            "financial_analysis": {{ "total_estimated_cost": "...", "transport_cost": "...", "accommodation_cost": "...", "food_cost": "..." }},
            "accommodation_section": {{ "best_districts": ["..."], "avg_prices": "..." }},
            "daily_plan": [
                {{
                    "day": 1, "theme": "...", 
                    "schedule": {{ "morning": "...", "afternoon": "...", "evening": "..." }},
                    "key_attraction_coords": [0.0, 0.0], "key_attraction_name": "..."
                }}
            ],
            "attractions": [
                 {{ "name": "...", "description": "...", "price": "..." }},
                 {{ "name": "...", "description": "...", "price": "..." }},
                 {{ "name": "...", "description": "...", "price": "..." }},
                 {{ "name": "...", "description": "...", "price": "..." }}
            ]
        }}
        """
        
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        
        try:
            data = json.loads(text)
            
            # 1. API: Kurs Walut
            curr = data.get("currency_code", "EUR")
            try:
                rate = get_nbp_exchange_rate(curr)
                if rate: data["real_exchange_rate"] = rate
            except: pass
            
            # 2. API: Pogoda (po współrzędnych)
            coords = data.get("location_coordinates")
            if coords and len(coords) == 2:
                lat, lon = coords[0], coords[1]
                try:
                    weather = get_weather_forecast(lat, lon, start_date)
                    if weather: data["real_weather_forecast"] = weather
                except: pass
            
            return json.dumps(data)
            
        except json.JSONDecodeError:
            return text

    except Exception as e:
        print(f"Błąd AI: {e}")
        return json.dumps({"is_feasible": False, "feasibility_message": f"Błąd generowania: {str(e)}"})