import streamlit as st
import requests
import extra_streamlit_components as stx
import json
import pandas as pd
from datetime import date, timedelta

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Planer AI", page_icon="🗺️", layout="wide")

# --- CSS (Clean & Professional) ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    .dashboard-row { display: flex; gap: 20px; margin-bottom: 20px; flex-wrap: wrap; }
    
    .equal-card {
        background-color: white; padding: 20px; border-radius: 8px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05); border: 1px solid #e0e0e0;
        color: #333 !important; flex: 1; display: flex; flex-direction: column;
    }
    
    .card-red {
        background-color: #fff5f5; padding: 20px; border-radius: 8px;
        border: 1px solid #ffcdd2; color: #b71c1c !important; flex: 1;
    }
    .card-red .card-header { border-bottom: 1px solid #ffcdd2; color: #b71c1c; font-weight: bold; margin-bottom: 10px; }

    .card-blue {
        background-color: #e3f2fd; padding: 20px; border-radius: 8px;
        border: 1px solid #90caf9; color: #0d47a1 !important; flex: 1;
    }
    .card-blue .card-header { border-bottom: 1px solid #90caf9; color: #0d47a1; font-weight: bold; margin-bottom: 10px; }

    /* Live Data Cards */
    .card-gray {
        background-color: #f8f9fa; padding: 15px; border-radius: 8px;
        border: 1px solid #dee2e6; color: #495057 !important; flex: 1;
    }
    
    /* Events Styling */
    .event-card {
        background-color: #fff; border: 1px solid #eee; border-radius: 8px;
        padding: 15px; margin-bottom: 10px; display: flex; align-items: center; gap: 15px;
        transition: transform 0.2s;
    }
    .event-card:hover { border-color: #ccc; transform: translateX(2px); }
    .event-date {
        background-color: #212529; color: #fff; padding: 8px 12px; border-radius: 6px;
        text-align: center; min-width: 80px; font-weight: bold;
        display: flex; flex-direction: column; justify-content: center;
    }
    .event-details { flex-grow: 1; }
    .event-title { font-weight: bold; font-size: 1rem; color: #000; margin-bottom: 4px; }
    .event-venue { font-size: 0.85rem; color: #666; }
    
    .custom-btn { display: inline-block; width: 100%; padding: 10px 0; background-color: #333; color: white !important; text-align: center; text-decoration: none; font-weight: 600; border-radius: 6px; border: none; cursor: pointer; margin-top: 5px; font-size: 0.9rem; }
    .booking-btn { background-color: #003580; }
    .ticket-btn { 
        background-color: #e91e63; color: white !important; padding: 8px 15px; 
        font-size: 0.85rem; border-radius: 6px; text-decoration: none; font-weight: 600;
        white-space: nowrap;
    }
    .ticket-btn:hover { background-color: #c2185b; }

    .card-header { font-size: 1.1rem; font-weight: 700; margin-bottom: 15px; border-bottom: 1px solid #eee; padding-bottom: 10px; color: #000; }
    .card-text { font-size: 0.95rem; line-height: 1.5; color: #333; }
    .flight-info-box { background-color: #f8f9fa; border-radius: 6px; padding: 10px; margin-bottom: 15px; border: 1px solid #eee; display: flex; justify-content: space-around; text-align: center; }
    .day-container { display: flex; gap: 15px; margin-bottom: 15px; align-items: stretch; }
    .time-slot-box { background-color: white; border: 1px solid #ddd; border-radius: 8px; padding: 15px; color: #333; flex: 1; display: flex; flex-direction: column; }
    .nav-link { color: #007bff; text-decoration: none; font-size: 0.85rem; font-weight: bold; }
    .meal-link-box { margin-top: auto; padding-top: 8px; border-top: 1px dashed #eee; font-size: 0.85rem; color: #555; }
    
    .stButton button { width: 100%; border-radius: 6px; font-weight: 600; }
    @media (max-width: 768px) { .day-container { flex-direction: column; } }
</style>
""", unsafe_allow_html=True)

TRAVEL_STYLES = ["Historia", "Imprezy", "Natura", "Sztuka", "Foto", "Relaks", "Sport", "Zakupy"]

# --- SESJA ---
def get_manager(): return stx.CookieManager()
cookie_manager = get_manager()
cookie_token = cookie_manager.get(cookie="auth_token")

if 'token' not in st.session_state: st.session_state['token'] = cookie_token
if 'current_plan' not in st.session_state: st.session_state['current_plan'] = None
if 'plan_meta' not in st.session_state: st.session_state['plan_meta'] = {}
if 'form_start_date' not in st.session_state: st.session_state['form_start_date'] = date.today()
if 'form_end_date' not in st.session_state: st.session_state['form_end_date'] = date.today() + timedelta(days=3)

# --- HELPERY ---
def generate_flight_links(origin, dest, start_date_str, end_date_str):
    try:
        s_start = start_date_str.replace("-", "")[2:] 
        s_end = end_date_str.replace("-", "")[2:]
        s_url = f"https://www.skyscanner.pl/transport/loty/{origin}/{dest}/{s_start}/{s_end}"
    except: s_url = "https://www.skyscanner.pl/"
    g_query = f"Flights to {dest} from {origin} on {start_date_str} returning {end_date_str}"
    g_url = f"https://www.google.com/travel/flights?q={g_query}&hl=pl&curr=PLN"
    return g_url, s_url

def generate_booking_link(city, start_date_str, end_date_str, people):
    city_slug = city.replace(" ", "+")
    return f"https://www.booking.com/searchresults.html?ss={city_slug}&checkin={start_date_str}&checkout={end_date_str}&group_adults={people}&no_rooms=1&group_children=0"

def make_maps_link(lat, lon):
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

# --- DASHBOARD ---
def show_dashboard(json_str, start_date_str, end_date_str, people_count):
    try:
        data = json.loads(json_str)
        
        if data.get("is_feasible") is False:
            st.error("BUDŻET KRYTYCZNY")
            st.warning(data.get("feasibility_message"))
            return

        # 1. INFO GÓRA
        abroad = data.get("pole_abroad", {})
        fin = data.get("financial_analysis", {})
        
        html_top = f"""
<div class="dashboard-row">
    <div class="card-red">
        <div class="card-header">Polak za granicą</div>
        <div class="card-text">
            <strong>Wiza/Wjazd:</strong><br>{abroad.get('visa_info', '-')}<br><br>
            <strong>Ostrzeżenia:</strong><br>{abroad.get('safety_warning', '-')}<br><br>
            <strong>Alarmowe:</strong><br>{abroad.get('emergency_numbers', '-')}
        </div>
    </div>
    <div class="card-blue">
        <div class="card-header">Analiza Finansowa</div>
        <div class="card-text">
            <div style="font-size: 2rem; font-weight: bold;">{fin.get('total_estimated_cost', '-')}</div>
            <br>
            <strong>Transport:</strong> {fin.get('transport_cost', '-')}<br>
            <strong>Noclegi:</strong> {fin.get('accommodation_cost', '-')}<br>
            <strong>Jedzenie:</strong> {fin.get('food_cost', '-')}<br><br>
            <em>{data.get('feasibility_message')}</em>
        </div>
    </div>
</div>
"""
        st.markdown(html_top, unsafe_allow_html=True)

        # 2. LIVE DATA
        weather_content = "Brak danych"
        currency_content = "Brak danych"
        
        if "real_weather_forecast" in data:
            w = data["real_weather_forecast"]
            if "error" in w: weather_content = w['error']
            else: weather_content = f"<strong>{w['desc']}</strong> (Max: {w['max_temp']}°C | Min: {w['min_temp']}°C)"
            
        if "real_exchange_rate" in data:
            curr = data.get("currency_code", "EUR")
            rate = data["real_exchange_rate"]
            currency_content = f"<strong>1 {curr} = {rate:.4f} PLN</strong> (Kurs NBP)"

        html_live = f"""
<div class="dashboard-row">
    <div class="card-gray">
        <strong>Pogoda (Prognoza):</strong><br>
        {weather_content}
    </div>
    <div class="card-gray">
        <strong>Waluta (Live):</strong><br>
        {currency_content}
    </div>
</div>
"""
        st.markdown(html_live, unsafe_allow_html=True)

        # 3. LOGISTYKA
        c3, c4 = st.columns(2)
        with c3:
            st.markdown("### Transport")
            flight_data = data.get('flights_and_transport', {})
            f_query = data.get("flight_search_query", {})
            iata_origin = f_query.get('origin_iata', '')
            iata_dest = f_query.get('dest_iata', '')
            if not iata_origin or not iata_dest:
                meta = st.session_state.get('plan_meta', {})
                if not iata_origin: iata_origin = meta.get('origin', 'Warszawa')
                if not iata_dest: iata_dest = meta.get('dest', '')

            g_link, s_link = generate_flight_links(iata_origin, iata_dest, start_date_str, end_date_str)
            trans_list = ""
            for t in flight_data.get('airport_transfer', []):
                trans_list += f"<li><strong>{t['type']}</strong> ({t['cost']}): {t.get('details','')}</li>"

            html_transport = f"""
<div class="equal-card">
    <div class="card-header">Połączenie Lotnicze</div>
    <div class="flight-info-box">
        <div>
            <div class="flight-metric-lbl">Szac. Cena</div>
            <div class="flight-metric-val">{flight_data.get('estimated_flight_price', '-')}</div>
        </div>
        <div style="border-left: 1px solid #ddd;"></div>
        <div>
            <div class="flight-metric-lbl">Czas Lotu</div>
            <div class="flight-metric-val">{flight_data.get('flight_duration', '-')}</div>
        </div>
    </div>
    <div style="display: flex; gap: 10px;">
        <a href="{g_link}" target="_blank" class="custom-btn">Google Flights</a>
        <a href="{s_link}" target="_blank" class="custom-btn">Skyscanner</a>
    </div>
    <div style="margin-top: 20px;">
        <strong>Transfer z lotniska:</strong>
        <ul style="margin-top: 5px; padding-left: 20px; font-size: 0.9rem;">
            {trans_list}
        </ul>
    </div>
</div>
"""
            st.markdown(html_transport, unsafe_allow_html=True)

        with c4:
            st.markdown("### Noclegi")
            acc = data.get("accommodation_section", {})
            spec = data.get("coordinates_special", {})
            acc_map_link = ""
            if "accommodation" in spec and spec["accommodation"]:
                link = make_maps_link(spec["accommodation"][0], spec["accommodation"][1])
                acc_map_link = f'<br><a href="{link}" target="_blank" class="nav-link">Pokaż sugerowany rejon (Google Maps)</a>'
            
            meta_dest = st.session_state.get('plan_meta', {}).get('dest', 'Hotel')
            booking_link = generate_booking_link(meta_dest, start_date_str, end_date_str, people_count)

            html_logistics = f"""
<div class="equal-card">
    <div class="card-text">
        <strong>Sugerowane dzielnice:</strong><br>
        {', '.join(acc.get('best_districts', []))}<br>
        <span style="color: #666; font-size: 0.8rem;">{acc.get('avg_prices')}</span>
        {acc_map_link}
        <hr style="margin: 10px 0;">
        <a href="{booking_link}" target="_blank" class="custom-btn booking-btn">Znajdź nocleg na Booking.com</a>
        <div style="margin-top: 10px; font-size: 0.8rem; color: #666;">
            Automatycznie wyszukuje dla {people_count} os. w terminie {start_date_str} - {end_date_str}
        </div>
    </div>
</div>
"""
            st.markdown(html_logistics, unsafe_allow_html=True)

        st.divider()

        # 4. HARMONOGRAM
        st.subheader("Szczegółowy Plan Podróży")
        for day in data.get("daily_plan", []):
            st.markdown(f"#### Dzień {day['day']}: {day['theme']}")
            
            main_attr_link = ""
            kc = day.get("key_attraction_coords")
            if kc and len(kc) == 2:
                lnk = make_maps_link(kc[0], kc[1])
                main_attr_link = f'<a href="{lnk}" target="_blank" class="nav-link">Atrakcja: {day.get("key_attraction_name")}</a>'

            sch = day.get('schedule', {})
            meals = day.get('meals_data', {})

            def get_meal_html(meal_key, label):
                if meal_key in meals:
                    m = meals[meal_key]
                    if "coords" in m and len(m["coords"]) == 2:
                        l = make_maps_link(m["coords"][0], m["coords"][1])
                        return f"<div class='meal-link-box'>{label}: <a href='{l}' target='_blank' class='nav-link'>{m.get('name')}</a></div>"
                return ""

            day_html = f"""
<div class="day-container">
    <div class="time-slot-box">
        <div class="time-label">PORANEK</div>
        <div class="slot-content">{sch.get('morning', '-')}</div>
        {get_meal_html('breakfast', 'Śniadanie')}
    </div>
    <div class="time-slot-box">
        <div class="time-label">POŁUDNIE</div>
        <div class="slot-content">
            {sch.get('afternoon', '-')}
            <br>{main_attr_link}
        </div>
        {get_meal_html('lunch', 'Lunch')}
    </div>
    <div class="time-slot-box">
        <div class="time-label">WIECZÓR</div>
        <div class="slot-content">{sch.get('evening', '-')}</div>
        {get_meal_html('dinner', 'Kolacja')}
    </div>
</div>
"""
            st.markdown(day_html, unsafe_allow_html=True)

        st.divider()

        # 5. WYDARZENIA - NA SAMYM DOLE, ZWIJANE
        if "real_events" in data and data["real_events"]:
            with st.expander("🎭 Ciekawostki: Sprawdź wydarzenia w okolicy (Opcjonalne)"):
                st.caption("Poniżej znajdziesz koncerty, wydarzenia sportowe i kulturalne odbywające się w czasie Twojego pobytu.")
                events_html = ""
                for e in data["real_events"]:
                    events_html += f"""
                    <div class="event-card">
                        <div class="event-date">
                            <div>{e['date']}</div>
                            <div style="font-size:0.8rem; font-weight:normal; margin-top:2px;">{e['time']}</div>
                        </div>
                        <div class="event-details">
                            <div class="event-title">{e['name']}</div>
                            <div class="event-venue">📍 {e['venue']}</div>
                        </div>
                        <a href="{e['url']}" target="_blank" class="ticket-btn">Kup Bilet</a>
                    </div>
                    """
                st.markdown(events_html, unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Błąd wyświetlania: {e}")

# --- UI STARTOWE ---
st.title("Planer AI")

tabs = st.tabs(["Zaplanuj", "Moje Plany", "Konto"])

with tabs[0]:
    if not st.session_state['current_plan']:
        with st.container():
            st.info("Wypełnij formularz. Podaj daty, aby znaleźć najlepsze loty.")
            with st.form("main"):
                c1, c2 = st.columns(2)
                orig = c1.text_input("Start", "Warszawa")
                dest = c2.text_input("Cel", "Rzym")
                c3, c4 = st.columns(2)
                start_date = c3.date_input("Data Wylotu", value=st.session_state['form_start_date'])
                end_date = c4.date_input("Data Powrotu", value=st.session_state['form_end_date'])
                styles = st.multiselect("Styl (Opcjonalne)", TRAVEL_STYLES, max_selections=3)
                c5, c6 = st.columns(2)
                ppl = c5.number_input("Osób", 1, 10, 2)
                bud = c6.number_input("Budżet/os (PLN)", value=3000, step=100)
                
                submitted = st.form_submit_button("Generuj Plan")
                if submitted:
                    st.session_state['form_start_date'] = start_date
                    st.session_state['form_end_date'] = end_date
                    if end_date < start_date:
                        st.error("Data powrotu musi być późniejsza niż wylotu!")
                    else:
                        days = (end_date - start_date).days + 1
                        with st.spinner(f"Pobieram wydarzenia, pogodę i układam plan na {days} dni..."):
                            payload = {
                                "origin": orig, "destination": dest, "start_date": str(start_date),
                                "days": days, "people": ppl, "budget": bud, "styles": styles
                            }
                            try:
                                res = requests.post(f"{API_URL}/generate", json=payload, timeout=120)
                                if res.status_code == 200:
                                    st.session_state['current_plan'] = res.json()['plan']
                                    st_style = ", ".join(styles) if styles else "Ogólny"
                                    st.session_state['plan_meta'] = {
                                        "origin": orig, "dest": dest, 
                                        "days": days, "style": st_style, 
                                        "start_date": str(start_date), "end_date": str(end_date),
                                        "people": ppl
                                    }
                                    st.rerun()
                                else: st.error("Błąd AI")
                            except Exception as e: st.error(f"Błąd: {e}")
    else:
        c_left, c_right = st.columns([1, 5])
        with c_left:
            if st.button("⬅️ Nowy"):
                st.session_state['current_plan'] = None
                st.rerun()
        with c_right:
            st.header(f"Raport: {st.session_state['plan_meta'].get('dest', 'Podróż')}")
        
        meta = st.session_state.get('plan_meta', {})
        show_dashboard(st.session_state['current_plan'], meta.get('start_date'), meta.get('end_date'), meta.get('people', 2))
        
        if st.session_state['token']:
            st.divider()
            if st.button("Zapisz raport"):
                h = {"Authorization": f"Bearer {st.session_state['token']}"}
                p = {"destination": meta.get('dest'), "days": meta.get('days'), "style": meta.get('style'), "plan_json": st.session_state['current_plan']}
                requests.post(f"{API_URL}/save-trip", json=p, headers=h)
                st.success("Zapisano!")

with tabs[1]:
    if st.session_state['token']:
        h = {"Authorization": f"Bearer {st.session_state['token']}"}
        r = requests.get(f"{API_URL}/my-trips", headers=h)
        if r.status_code == 200:
            for t in r.json():
                with st.expander(f"{t['destination']} ({t['days']} dni)"): 
                    fallback_start = str(date.today())
                    fallback_end = str(date.today() + timedelta(days=t['days']))
                    show_dashboard(t['plan_json'], fallback_start, fallback_end, 2)
    else: st.info("Zaloguj się.")

with tabs[2]:
    if not st.session_state['token']:
        m = st.radio("Opcja", ["Logowanie", "Rejestracja"])
        e = st.text_input("Email")
        p = st.text_input("Hasło", type="password")
        if st.button("Wykonaj"):
            ep = "login" if m == "Logowanie" else "register"
            pay = {"email": e, "password": p}
            if m == "Rejestracja": pay["username"] = st.text_input("Nick")
            try:
                rr = requests.post(f"{API_URL}/{ep}", json=pay)
                if rr.status_code == 200:
                    tok = rr.json()['access_token'] if m == "Logowanie" else None
                    if tok: 
                        st.session_state['token'] = tok
                        cookie_manager.set("auth_token", tok)
                        st.rerun()
                    else: st.success("Gotowe!")
            except: pass
    else:
        st.write("Zalogowany.")
        if st.button("Wyloguj"):
            cookie_manager.delete("auth_token")
            st.session_state['token'] = None
            st.rerun()