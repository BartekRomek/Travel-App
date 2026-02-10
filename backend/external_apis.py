import requests
import os
from datetime import datetime, timedelta

# --- API 1: NBP (Kursy Walut) ---
def get_nbp_exchange_rate(currency_code):
    if currency_code == "PLN": return 1.0
    try:
        url = f"http://api.nbp.pl/api/exchangerates/rates/a/{currency_code}/?format=json"
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            return response.json()['rates'][0]['mid']
    except Exception as e:
        print(f"Błąd NBP: {e}")
    return None

# --- API 2: Open-Meteo (Pogoda) ---
def get_weather_forecast(lat, lon, start_date_str):
    try:
        start = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        today = datetime.now().date()
        days_diff = (start - today).days

        if days_diff < 0 or days_diff > 14:
            return {"error": "Prognoza niedostępna (termin > 14 dni)"}

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat, "longitude": lon,
            "daily": ["temperature_2m_max", "temperature_2m_min", "weathercode"],
            "timezone": "auto",
            "start_date": start_date_str, "end_date": start_date_str
        }
        
        response = requests.get(url, params=params, timeout=5)
        if response.status_code == 200:
            data = response.json()
            daily = data.get("daily", {})
            return {
                "max_temp": daily["temperature_2m_max"][0],
                "min_temp": daily["temperature_2m_min"][0],
                "desc": wmo_code_to_text(daily["weathercode"][0])
            }
    except Exception as e:
        print(f"Błąd Pogody: {e}")
    return None

def wmo_code_to_text(code):
    # Styl Clean (Bez emotikon)
    if code == 0: return "Bezchmurnie"
    if code in [1, 2, 3]: return "Częściowe zachmurzenie"
    if code in [45, 48]: return "Mgła"
    if code in [51, 53, 55]: return "Mżawka"
    if code in [61, 63, 65]: return "Deszcz"
    if code in [71, 73, 75]: return "Śnieg"
    if code >= 95: return "Burza"
    return "Pochmurno"

# --- API 3: Ticketmaster (Wydarzenia) ---
def get_ticketmaster_events(lat, lon, start_date_str, end_date_str):
    """
    Pobiera wydarzenia (Muzyka, Sport, Sztuka) w okolicy w zadanym terminie.
    """
    api_key = os.getenv("TICKETMASTER_API_KEY")
    if not api_key:
        return []

    try:
        # Format daty Ticketmaster: YYYY-MM-DDTHH:mm:ssZ
        start_dt = f"{start_date_str}T00:00:00Z"
        # Jeśli end_date to ten sam dzień, dodajemy czas do końca dnia
        end_dt = f"{end_date_str}T23:59:59Z"

        url = "https://app.ticketmaster.com/discovery/v2/events.json"
        params = {
            "apikey": api_key,
            "latlong": f"{lat},{lon}",
            "radius": "25",
            "unit": "km",
            "startDateTime": start_dt,
            "endDateTime": end_dt,
            "sort": "date,asc",
            "size": "5" # Max 5 topowych wydarzeń
        }

        response = requests.get(url, params=params, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            if "_embedded" in data and "events" in data["_embedded"]:
                events = []
                for e in data["_embedded"]["events"]:
                    # Pobieramy najmniejsze zdjęcie (dla oszczędności transferu) lub pierwsze
                    img_url = e["images"][0]["url"] if e.get("images") else ""
                    
                    event_info = {
                        "name": e.get("name"),
                        "date": e["dates"]["start"].get("localDate"),
                        "time": e["dates"]["start"].get("localTime", "")[:5], # Format HH:MM
                        "venue": e["_embedded"]["venues"][0].get("name", "Lokalizacja nieznana"),
                        "url": e.get("url"),
                        "image": img_url
                    }
                    events.append(event_info)
                return events
    except Exception as e:
        print(f"Błąd Ticketmaster: {e}")
    
    return []