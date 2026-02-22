import google.generativeai as genai
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
from .external_apis import get_nbp_exchange_rate, get_weather_forecast

load_dotenv()

def generate_trip_plan(origin, destination, start_date, days, people, budget_per_person, styles):
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key: return json.dumps({"error": "Brak klucza API"})

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash')
        
        style_desc = ", ".join(styles) if styles else "Mix zwiedzania i relaksu"

        prompt = f"""
        Jesteś ekspertem podróży. Zaplanuj wyjazd: {origin} -> {destination}.
        Start: {start_date}. Czas trwania: {days} dni.
        Budżet: {budget_per_person} PLN/os. Styl: {style_desc}.

        WYMAGANIA:
        1. Zidentyfikuj kod waluty docelowej.
        2. Zidentyfikuj współrzędne (lat, lon) centrum miasta docelowego.
        3. Stwórz plan dnia.
        4. Stwórz SZCZEGÓŁOWĄ sekcję transportu (loty, transfer z lotniska, alternatywa np. pociąg/autobus).
        
        Zwróć TYLKO JSON:
        {{
            "is_feasible": true,
            "feasibility_message": "...",
            "currency_code": "EUR", 
            "location_coordinates": [0.0, 0.0],
            
            "transport_detailed": {{
                "flight": {{
                    "best_option": "Ryanair/Wizzair (Bezpośredni)",
                    "estimated_price": "...",
                    "duration": "...",
                    "search_query": {{ "origin_iata": "WAW", "dest_iata": "XXX" }}
                }},
                "airport_transfer": [
                    {{ "name": "Pociąg Express", "price": "...", "duration": "..." }},
                    {{ "name": "Autobus Shuttle", "price": "...", "duration": "..." }}
                ],
                "alternative_transport": {{
                    "type": "Autobus (FlixBus) lub Pociąg",
                    "price": "...",
                    "duration": "...",
                    "description": "Dla osób bojących się latać..."
                }}
            }},

            "accommodation_summary": "...",
            "pole_abroad": {{ "visa_info": "...", "safety_warning": "...", "emergency_numbers": "..." }},
            "financial_analysis": {{ "total_estimated_cost": "...", "transport_cost": "...", "accommodation_cost": "...", "food_cost": "..." }},
            "daily_plan": [
                {{
                    "day": 1, "theme": "...", 
                    "schedule": {{ "morning": "...", "afternoon": "...", "evening": "..." }},
                    "key_attraction_coords": [0.0, 0.0], "key_attraction_name": "..."
                }}
            ],
            "attractions": [
                 {{ "name": "...", "description": "...", "price": "..." }}
            ]
        }}
        """
        
        response = model.generate_content(prompt)
        text = response.text.replace("```json", "").replace("```", "").strip()
        
        try:
            data = json.loads(text)
            
            curr = data.get("currency_code", "EUR")
            rate = get_nbp_exchange_rate(curr)
            if rate: data["real_exchange_rate"] = rate
            
            coords = data.get("location_coordinates")
            if coords and len(coords) == 2:
                lat, lon = coords[0], coords[1]
                weather = get_weather_forecast(lat, lon, start_date)
                if weather: data["real_weather_forecast"] = weather
            
            return json.dumps(data)
            
        except json.JSONDecodeError:
            return text

    except Exception as e:
        print(f"Błąd AI: {e}")
        return json.dumps({"error": "Błąd generowania"})