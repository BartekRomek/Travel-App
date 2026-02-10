import streamlit as st
import requests
import extra_streamlit_components as stx
import json
import pandas as pd
from datetime import date, timedelta
import folium
from streamlit_folium import st_folium

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Planer AI", page_icon="🗺️", layout="wide")

# --- CSS: Stylizacja kart i harmonogramu ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    .block-container { padding-top: 2rem; }
    
    /* SIDEBAR */
    .side-card { padding: 20px; border-radius: 12px; margin-bottom: 20px; color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }
    .card-safety { background-color: #ff0000; } 
    .card-finance { background-color: #6200ea; } 
    .card-weather { background-color: #00bcd4; color: #000 !important; }
    .side-header { font-size: 1.1rem; font-weight: 800; margin-bottom: 10px; border-bottom: 1px solid rgba(255,255,255,0.3); padding-bottom: 5px; }
    .side-text { font-size: 0.9rem; line-height: 1.4; }
    
    /* HARMONOGRAM - DZIEŃ */
    .day-card { 
        background-color: #ffca28; 
        color: #000; 
        padding: 12px 20px; 
        border-radius: 10px 10px 0 0; 
        font-weight: 800; 
        font-size: 1.1rem;
        border-left: 5px solid #ff6f00;
        margin-top: 25px;
    }
    
    /* HARMONOGRAM - TREŚĆ (Biała Karta) */
    .day-content-box {
        background-color: white;
        border: 1px solid #ddd;
        border-top: none;
        border-radius: 0 0 10px 10px;
        padding: 20px;
        margin-bottom: 10px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .day-row { display: flex; margin-bottom: 12px; align-items: baseline; }
    .day-label { 
        font-weight: 800; 
        color: #555; 
        width: 100px; 
        min-width: 100px;
        text-transform: uppercase; 
        font-size: 0.8rem; 
        letter-spacing: 0.5px;
    }
    .day-desc { font-size: 0.95rem; color: #333; line-height: 1.5; }

    /* PRZYCISKI I ATRAKCJE */
    .action-btn { display: block; text-align: center; font-weight: bold; color: white !important; text-decoration: none; padding: 15px; border-radius: 10px; transition: transform 0.2s; box-shadow: 0 2px 5px rgba(0,0,0,0.15); margin-bottom: 20px; }
    .action-btn:hover { transform: scale(1.02); }
    .btn-booking { background-color: #003580; } 
    .btn-transport { background-color: #00a859; }
    .attraction-box { background-color: white; border: 1px solid #e0e0e0; border-radius: 12px; padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05); }
    .attr-title { font-size: 1rem; font-weight: bold; color: #333; margin-bottom: 5px; }
    .attr-desc { font-size: 0.85rem; color: #666; margin-bottom: 10px; line-height: 1.4; }
    .tag-container { display: flex; gap: 8px; flex-wrap: wrap; }
    .tag { padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
    .tag-price { background-color: #e8f5e9; color: #2e7d32; }
    .tag-type { background-color: #f3e5f5; color: #7b1fa2; }
    .map-container { border: 4px solid #ffca28; border-radius: 12px; overflow: hidden; margin-top: 20px; }
    .loader-container { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 50px 0; text-align: center; height: 70vh; }
    .custom-loader { border: 5px solid #f3f3f3; border-top: 5px solid #5d5fef; border-radius: 50%; width: 80px; height: 80px; animation: spin 1s linear infinite; margin-bottom: 30px; }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    .loader-text { font-size: 1.8rem; font-weight: 700; color: #333; margin-bottom: 10px; }
</style>
""", unsafe_allow_html=True)

TRAVEL_STYLES = ["Historia", "Imprezy", "Natura", "Sztuka", "Foto", "Relaks", "Sport", "Zakupy"]

# --- HELPERY ---
def get_manager(): return stx.CookieManager()
cookie_manager = get_manager()
cookie_token = cookie_manager.get(cookie="auth_token")

if 'token' not in st.session_state: st.session_state['token'] = cookie_token
if 'current_plan' not in st.session_state: st.session_state['current_plan'] = None
if 'plan_meta' not in st.session_state: st.session_state['plan_meta'] = {}
if 'form_start_date' not in st.session_state: st.session_state['form_start_date'] = date.today()
if 'form_end_date' not in st.session_state: st.session_state['form_end_date'] = date.today() + timedelta(days=3)

def generate_flight_links(origin, dest, start_date_str, end_date_str):
    return f"https://www.skyscanner.pl/transport/loty/{origin}/{dest}"

def generate_booking_link(city, start_date_str, end_date_str, people):
    city_slug = city.replace(" ", "+")
    return f"https://www.booking.com/searchresults.html?ss={city_slug}&checkin={start_date_str}&checkout={end_date_str}&group_adults={people}&no_rooms=1"

def make_maps_link(lat, lon):
    return f"https://www.google.com/maps/search/?api=1&query={lat},{lon}"

def display_map(data):
    lat, lon = 41.9028, 12.4964
    if "location_coordinates" in data and len(data["location_coordinates"]) == 2:
        lat, lon = data["location_coordinates"]
    m = folium.Map(location=[lat, lon], zoom_start=12)
    if "daily_plan" in data:
        for day in data["daily_plan"]:
            kc = day.get("key_attraction_coords")
            name = day.get("key_attraction_name", "Atrakcja")
            if kc and len(kc) == 2:
                folium.Marker(kc, popup=f"Dzień {day['day']}: {name}", tooltip=name, icon=folium.Icon(color="red", icon="camera")).add_to(m)
    st_folium(m, width=None, height=400)

def show_dashboard(json_str, start_date_str, end_date_str, people_count):
    try:
        if isinstance(json_str, str):
            data = json.loads(json_str)
        else:
            data = json_str

        if data.get("is_feasible") is False:
            msg = data.get("feasibility_message") or "Błąd generowania."
            st.error(f"⚠️ {msg}")
            return

        abroad = data.get("pole_abroad", {})
        fin = data.get("financial_analysis", {})
        
        col_main, col_sidebar = st.columns([2.2, 1], gap="medium")

        with col_sidebar:
            st.markdown(f"""
            <div class="side-card card-safety">
                <div class="side-header">⚠️ Polak za granicą</div>
                <div class="side-text">
                    <strong>Wiza:</strong> {abroad.get('visa_info', '-')}<br>
                    <strong>Bezpieczeństwo:</strong> {abroad.get('safety_warning', '-')}<br>
                    <strong>Alarmowe:</strong> {abroad.get('emergency_numbers', '-')}
                </div>
            </div>
            """, unsafe_allow_html=True)

            rate_txt = "Brak danych"
            if "real_exchange_rate" in data:
                rate_txt = f"1 EUR = {data['real_exchange_rate']:.2f} PLN"

            st.markdown(f"""
            <div class="side-card card-finance">
                <div class="side-header">💰 Finanse</div>
                <div class="side-text">
                    <div style="font-size: 1.5rem; font-weight:bold;">{fin.get('total_estimated_cost', '-')}</div>
                    Transport: {fin.get('transport_cost', '-')}<br>
                    Noclegi: {fin.get('accommodation_cost', '-')}<br>
                    Jedzenie: {fin.get('food_cost', '-')}<br>
                    <hr style="margin:5px 0;">{rate_txt}
                </div>
            </div>
            """, unsafe_allow_html=True)

            w_txt = "Brak danych"
            if "real_weather_forecast" in data:
                w = data["real_weather_forecast"]
                if "error" not in w:
                    w_txt = f"{w.get('desc')}<br>Max: {w.get('max_temp')}°C | Min: {w.get('min_temp')}°C"
            
            st.markdown(f"""
            <div class="side-card card-weather">
                <div class="side-header">☀️ Pogoda</div>
                <div class="side-text">{w_txt}</div>
            </div>
            """, unsafe_allow_html=True)

        with col_main:
            # --- ZMIENIONA SEKCJA HARMONOGRAMU (Karty zamiast zwijania) ---
            st.subheader("📅 Harmonogram Podróży")
            
            for day in data.get("daily_plan", []):
                # Żółta belka (Nagłówek)
                st.markdown(f"""<div class="day-card">Dzień {day['day']}: {day['theme']}</div>""", unsafe_allow_html=True)
                
                # Biała karta z detalami
                sch = day.get('schedule', {})
                kc = day.get("key_attraction_coords")
                attr_link = ""
                if kc: attr_link = f" <a href='{make_maps_link(kc[0], kc[1])}' target='_blank'>[Mapa]</a>"
                
                st.markdown(f"""
                <div class="day-content-box">
                    <div class="day-row">
                        <div class="day-label">🌅 RANO</div>
                        <div class="day-desc">{sch.get('morning','-')}</div>
                    </div>
                    <div class="day-row">
                        <div class="day-label">☀️ POŁUDNIE</div>
                        <div class="day-desc">{sch.get('afternoon','-')} <strong>{day.get('key_attraction_name','')}</strong> {attr_link}</div>
                    </div>
                    <div class="day-row">
                        <div class="day-label">🌙 WIECZÓR</div>
                        <div class="day-desc">{sch.get('evening','-')}</div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            st.divider()

            meta_dest = st.session_state.get('plan_meta', {}).get('dest', 'Hotel')
            booking_url = generate_booking_link(meta_dest, start_date_str, end_date_str, people_count)
            f_query = data.get("flight_search_query", {})
            g_flight = generate_flight_links(f_query.get('origin_iata','WAW'), f_query.get('dest_iata',''), start_date_str, end_date_str)

            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                st.markdown(f'<a href="{booking_url}" target="_blank" class="action-btn btn-booking">🏨 BOOKING<br><span style="font-size:0.8rem; font-weight:normal">Rezerwuj nocleg</span></a>', unsafe_allow_html=True)
            with c_btn2:
                st.markdown(f'<a href="{g_flight}" target="_blank" class="action-btn btn-transport">✈️ TRANSPORT<br><span style="font-size:0.8rem; font-weight:normal; color:white">Znajdź loty</span></a>', unsafe_allow_html=True)

            c_attr, c_event = st.columns(2)
            
            with c_attr:
                st.markdown("#### 🏰 Atrakcje")
                for item in data.get("attractions", [])[:4]:
                    st.markdown(f"""
                    <div class="attraction-box">
                        <div class="attr-title">{item.get('name','-')}</div>
                        <div class="attr-desc">{item.get('description','-')}</div>
                        <div class="tag-container"><div class="tag tag-price">{item.get('price','-')}</div></div>
                    </div>
                    """, unsafe_allow_html=True)

            with c_event:
                st.markdown("#### 🎉 Wydarzenia (Ticketmaster)")
                events = data.get("real_events", [])
                if events:
                    for e in events[:4]:
                        st.markdown(f"""
                        <div class="attraction-box">
                            <div class="attr-title">{e['name']}</div>
                            <div class="attr-desc">{e['venue']} | {e['date']}</div>
                            <div class="tag-container">
                                <div class="tag tag-type">BILET</div>
                                <a href="{e['url']}" target="_blank" style="font-size:0.8rem; margin-left:auto;">Kup →</a>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("Brak wydarzeń w tym terminie.")

            st.markdown('<div class="map-container">', unsafe_allow_html=True)
            display_map(data)
            st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Błąd UI: {e}")

# --- UI STARTOWE ---
col_head_left, col_head_right = st.columns([4, 1])
with col_head_left:
    st.title("Planer AI 🌍")
    if st.session_state['plan_meta']:
        m = st.session_state['plan_meta']
        st.caption(f"Kierunek: **{m.get('dest')}** | {m.get('start_date')} - {m.get('end_date')} | {m.get('people')} os.")

with col_head_right:
    if st.session_state['token']:
        if st.button("👤 Wyloguj"):
            cookie_manager.delete("auth_token")
            st.session_state['token'] = None
            st.rerun()
    else:
        st.info("Gość")

tabs = st.tabs(["Zaplanuj", "Moje Plany", "Konto"])

with tabs[0]:
    form_placeholder = st.empty()
    if not st.session_state['current_plan']:
        with form_placeholder.container():
            st.info("Wypełnij formularz. Podaj daty, aby znaleźć najlepsze loty.")
            with st.form("main"):
                c1, c2 = st.columns(2)
                orig = c1.text_input("Start", "Warszawa")
                dest = c2.text_input("Cel", "Rzym")
                c3, c4 = st.columns(2)
                start_date = c3.date_input("Data Wylotu", value=st.session_state['form_start_date'])
                end_date = c4.date_input("Data Powrotu", value=st.session_state['form_end_date'])
                styles = st.multiselect("Styl", TRAVEL_STYLES, max_selections=3)
                c5, c6 = st.columns(2)
                ppl = c5.number_input("Osób", 1, 10, 2)
                bud = c6.number_input("Budżet/os (PLN)", value=3000, step=100)
                submitted = st.form_submit_button("Generuj Plan")
        
        if submitted:
            form_placeholder.empty()
            loader_placeholder = st.empty()
            with loader_placeholder.container():
                st.markdown("""<div class="loader-container"><div class="custom-loader"></div><div class="loader-text">AI planuje Twoją podróż...</div><div class="loader-subtext">To może potrwać chwilę.</div></div>""", unsafe_allow_html=True)

            st.session_state['form_start_date'] = start_date
            st.session_state['form_end_date'] = end_date
            days = (end_date - start_date).days + 1
            payload = {"origin": orig, "destination": dest, "start_date": str(start_date), "days": days, "people": ppl, "budget": bud, "styles": styles}
            try:
                res = requests.post(f"{API_URL}/generate", json=payload, timeout=120)
                if res.status_code == 200:
                    st.session_state['current_plan'] = res.json()['plan']
                    st_style = ", ".join(styles) if styles else "Ogólny"
                    st.session_state['plan_meta'] = {"origin": orig, "dest": dest, "days": days, "style": st_style, "start_date": str(start_date), "end_date": str(end_date), "people": ppl}
                    st.rerun()
                else:
                    loader_placeholder.empty()
                    st.error("Błąd AI")
            except Exception as e:
                loader_placeholder.empty()
                st.error(f"Błąd połączenia: {e}")
    else:
        c_left, c_right = st.columns([1, 5])
        with c_left:
            if st.button("⬅️ Nowy"):
                st.session_state['current_plan'] = None
                st.rerun()
        meta = st.session_state.get('plan_meta', {})
        show_dashboard(st.session_state['current_plan'], meta.get('start_date'), meta.get('end_date'), meta.get('people', 2))
        if st.session_state['token']:
            st.divider()
            if st.button("Zapisz w historii"):
                h = {"Authorization": f"Bearer {st.session_state['token']}"}
                p = {"destination": meta.get('dest'), "days": meta.get('days'), "style": meta.get('style'), "plan_json": json.dumps(st.session_state['current_plan'])}
                requests.post(f"{API_URL}/save-trip", json=p, headers=h)
                st.success("Zapisano!")

with tabs[1]:
    if st.session_state['token']:
        h = {"Authorization": f"Bearer {st.session_state['token']}"}
        r = requests.get(f"{API_URL}/my-trips", headers=h)
        if r.status_code == 200:
            for t in r.json():
                with st.expander(f"{t['destination']} ({t['days']} dni)"):
                    show_dashboard(t['plan_json'], str(date.today()), str(date.today()+timedelta(days=t['days'])), 2)
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
            except: pass
    else:
        st.write("Jesteś zalogowany.")
        if st.button("Wyloguj sesję"):
            cookie_manager.delete("auth_token")
            st.session_state['token'] = None
            st.rerun()