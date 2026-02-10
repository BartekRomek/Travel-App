import google.generativeai as genai
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from .external_apis import get_nbp_exchange_rate, get_weather_forecast, get_ticketmaster_events

load_dotenv()

def generate_trip_plan(origin, destination, start_date, days, people, budget_per_person, styles):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: return json.dumps({"error": "Brak klucza API"})

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-flash-latest')
        
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
            "is_feasible": true/false,
            "feasibility_message": "...",
            "currency_code": "KOD", 
            "location_coordinates": [lat, lon],
            
            "flight_search_query": {{ "origin_iata": "...", "dest_iata": "..." }},
            "pole_abroad": {{ "visa_info": "...", "safety_warning": "...", "emergency_numbers": "..." }},
            "financial_analysis": {{ "total_estimated_cost": "...", "transport_cost": "...", "accommodation_cost": "...", "food_cost": "..." }},
            "flights_and_transport": {{
                "estimated_flight_price": "...", "flight_duration": "...",
                "airport_transfer": [ {{ "type": "...", "cost": "...", "details": "..." }} ]
            }},
            "accommodation_section": {{ "best_districts": ["..."], "avg_prices": "...", "recommendation": "..." }},
            "daily_plan": [
                {{
                    "day": 1, "theme": "...", 
                    "schedule": {{ "morning": "...", "afternoon": "...", "evening": "..." }},
                    "meals_data": {{ "breakfast": {{"name": "...", "coords": []}}, "lunch": {{"name": "...", "coords": []}}, "dinner": {{"name": "...", "coords": []}} }},
                    "key_attraction_coords": [lat, lon], "key_attraction_name": "..."
                }}
            ],
            "coordinates_special": {{ "accommodation": [lat, lon] }}
        }}
        """
        
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        
        try:
            data = json.loads(text)
            
            # 1. API: Kurs Walut
            curr = data.get("currency_code", "EUR")
            rate = get_nbp_exchange_rate(curr)
            if rate: data["real_exchange_rate"] = rate
            
            # 2. Współrzędne i API Lokalne
            coords = data.get("location_coordinates")
            if coords and len(coords) == 2:
                lat, lon = coords[0], coords[1]
                
                # A. Pogoda (Dla daty startu)
                weather = get_weather_forecast(lat, lon, start_date)
                if weather: data["real_weather_forecast"] = weather
                
                # B. Wydarzenia (Dla całego pobytu)
                # Obliczamy datę końca: start + days - 1
                s_dt = datetime.strptime(start_date, "%Y-%m-%d")
                e_dt = s_dt + timedelta(days=days)
                end_date_str = e_dt.strftime("%Y-%m-%d")
                
                events = get_ticketmaster_events(lat, lon, start_date, end_date_str)
                if events: data["real_events"] = events
            
            return json.dumps(data)
            
        except json.JSONDecodeError:
            return text

    except Exception as e:
        print(f"Błąd AI: {e}")
        return json.dumps({"error": "Błąd generowania"})