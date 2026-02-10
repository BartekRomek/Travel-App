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

# --- CSS (Stylizacja zgodna z Twoim szkicem + KARTY ATRAKCJI) ---
st.markdown("""
<style>
    #MainMenu {visibility: hidden;} footer {visibility: hidden;}
    .block-container { padding-top: 2rem; }
    
    /* SIDEBAR (PRAWA STRONA) */
    .side-card {
        padding: 20px; border-radius: 12px; margin-bottom: 20px;
        color: white; box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .card-safety { background-color: #ff0000; } 
    .card-finance { background-color: #6200ea; } 
    .card-weather { background-color: #00bcd4; color: #000 !important; }
    
    .side-header { font-size: 1.1rem; font-weight: 800; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px; border-bottom: 1px solid rgba(255,255,255,0.3); padding-bottom: 5px; }
    .side-text { font-size: 0.9rem; line-height: 1.4; }
    
    /* DNI (LEWA STRONA) */
    .day-card {
        background-color: #ffca28; color: #000; padding: 15px 20px;
        border-radius: 10px; margin-bottom: 15px; font-weight: bold;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1); border-left: 5px solid #ff6f00;
    }

    /* BUTTONS (AKCJE) */
    .action-btn {
        display: block; text-align: center; font-weight: bold; color: white !important;
        text-decoration: none; padding: 15px; border-radius: 10px;
        transition: transform 0.2s; box-shadow: 0 2px 5px rgba(0,0,0,0.15); margin-bottom: 20px;
    }
    .action-btn:hover { transform: scale(1.02); text-decoration: none; color: white; }
    .btn-booking { background-color: #757575; } 
    .btn-transport { background-color: #76ff03; color: #000 !important; }

    /* --- NOWE STYLE: KARTY ATRAKCJI (ZGODNIE Z OBRAZEM 2) --- */
    .attraction-box {
        background-color: white; border: 1px solid #e0e0e0; border-radius: 12px;
        padding: 15px; margin-bottom: 15px; box-shadow: 0 2px 5px rgba(0,0,0,0.05);
    }
    .attr-title { font-size: 1rem; font-weight: bold; color: #333; margin-bottom: 5px; }
    .attr-desc { font-size: 0.85rem; color: #666; margin-bottom: 10px; line-height: 1.4; }
    
    .tag-container { display: flex; gap: 8px; flex-wrap: wrap; }
    .tag { padding: 4px 8px; border-radius: 4px; font-size: 0.75rem; font-weight: 600; }
    .tag-price { background-color: #e8f5e9; color: #2e7d32; } /* Zielony */
    .tag-res { background-color: #fff8e1; color: #f57f17; }   /* Żółty */
    .tag-type { background-color: #f3e5f5; color: #7b1fa2; }  /* Fioletowy */

    h4 { margin-top: 0 !important; margin-bottom: 15px !important; }

    /* MAPA */
    .map-container { border: 4px solid #ffca28; border-radius: 12px; overflow: hidden; margin-top: 20px; }
    
    /* LOADER */
    .loader-container { display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 50px 0; text-align: center; height: 70vh; }
    .custom-loader { border: 5px solid #f3f3f3; border-top: 5px solid #5d5fef; border-radius: 50%; width: 80px; height: 80px; animation: spin 1s linear infinite; margin-bottom: 30px; }
    @keyframes spin { 0% { transform: rotate(0deg); } 100% { transform: rotate(360deg); } }
    .loader-text { font-size: 1.8rem; font-weight: 700; color: #333; margin-bottom: 10px; }
    .streamlit-expanderHeader { background-color: white; border-radius: 8px; }
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

# --- MAPA ---
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

# --- DASHBOARD ---
def show_dashboard(json_str, start_date_str, end_date_str, people_count):
    try:
        data = json.loads(json_str)
        if data.get("is_feasible") is False:
            st.error("BUDŻET KRYTYCZNY: " + data.get("feasibility_message"))
            return

        abroad = data.get("pole_abroad", {})
        fin = data.get("financial_analysis", {})
        
        # --- UKŁAD: LEWA (TREŚĆ) | PRAWA (SIDEBAR) ---
        col_main, col_sidebar = st.columns([2.2, 1], gap="medium")

        # === PRAWA STRONA (SIDEBAR) ===
        with col_sidebar:
            st.markdown(f"""
            <div class="side-card card-safety">
                <div class="side-header">⚠️ Polak za granicą</div>
                <div class="side-text">
                    <strong>Wiza:</strong> {abroad.get('visa_info', '-')}<br><br>
                    <strong>Bezpieczeństwo:</strong> {abroad.get('safety_warning', '-')}<br><br>
                    <strong>Alarmowe:</strong> {abroad.get('emergency_numbers', '-')}
                </div>
            </div>
            """, unsafe_allow_html=True)

            curr_info = "Brak danych"
            if "real_exchange_rate" in data:
                code = data.get("currency_code", "EUR")
                rate = data["real_exchange_rate"]
                curr_info = f"1 {code} = {rate:.2f} PLN"

            st.markdown(f"""
            <div class="side-card card-finance">
                <div class="side-header">💰 Finanse i Waluta</div>
                <div class="side-text">
                    <div style="font-size: 1.8rem; font-weight:bold; margin-bottom:5px;">{fin.get('total_estimated_cost', '-')}</div>
                    Transport: {fin.get('transport_cost', '-')}<br>
                    Noclegi: {fin.get('accommodation_cost', '-')}<br>
                    Jedzenie: {fin.get('food_cost', '-')}<br><hr style="border-color: rgba(255,255,255,0.3);">
                    <strong>Kurs NBP:</strong> {curr_info}
                </div>
            </div>
            """, unsafe_allow_html=True)

            weather_txt = "Brak danych"
            if "real_weather_forecast" in data:
                w = data["real_weather_forecast"]
                if "error" not in w:
                    weather_txt = f"{w['desc']}<br>Max: {w['max_temp']}°C | Min: {w['min_temp']}°C"
            
            st.markdown(f"""
            <div class="side-card card-weather">
                <div class="side-header">☀️ Pogoda</div>
                <div class="side-text">{weather_txt}</div>
            </div>
            """, unsafe_allow_html=True)

        # === LEWA STRONA (TREŚĆ) ===
        with col_main:
            # 1. PRZYCISKI GÓRNE (BOOKING / TRANSPORT)
            # Umieszczamy je teraz tutaj, lub pod planem. Zgodnie ze szkicem były pod planem, ale nad atrakcjami.
            # Zróbmy tak: Plan -> Przyciski -> Sekcja Atrakcji -> Mapa
            
            # --- SEKCJA PLANU DNIA ---
            st.subheader("📅 Harmonogram Podróży")
            for day in data.get("daily_plan", []):
                st.markdown(f"""<div class="day-card">Dzień {day['day']}: {day['theme']}</div>""", unsafe_allow_html=True)
                with st.expander("Zobacz szczegóły", expanded=False):
                    sch = day.get('schedule', {})
                    kc = day.get("key_attraction_coords")
                    attr_link = ""
                    if kc: attr_link = f" <a href='{make_maps_link(kc[0], kc[1])}' target='_blank'>[Mapa]</a>"
                    st.markdown(f"**Rano:** {sch.get('morning','-')}")
                    st.markdown(f"**Południe:** {sch.get('afternoon','-')} **{day.get('key_attraction_name','')}** {attr_link}")
                    st.markdown(f"**Wieczór:** {sch.get('evening','-')}")

            st.divider()

            # --- SEKCJA NARZĘDZI (BOOKING & TRANSPORT) ---
            meta_dest = st.session_state.get('plan_meta', {}).get('dest', 'Hotel')
            booking_url = generate_booking_link(meta_dest, start_date_str, end_date_str, people_count)
            f_query = data.get("flight_search_query", {})
            g_flight, s_flight = generate_flight_links(f_query.get('origin_iata','WAW'), f_query.get('dest_iata',''), start_date_str, end_date_str)

            c_btn1, c_btn2 = st.columns(2)
            with c_btn1:
                st.markdown(f'<a href="{booking_url}" target="_blank" class="action-btn btn-booking">🏨 BOOKING<br><span style="font-size:0.8rem; font-weight:normal">Rezerwuj nocleg</span></a>', unsafe_allow_html=True)
            with c_btn2:
                st.markdown(f'<a href="{g_flight}" target="_blank" class="action-btn btn-transport">✈️ TRANSPORT<br><span style="font-size:0.8rem; font-weight:normal; color:black">Znajdź loty</span></a>', unsafe_allow_html=True)

            # --- SEKCJA SZCZEGÓŁOWA: ATRAKCJE I WYDARZENIA (ZAMIAST FIOLETOWEGO PRZYCISKU) ---
            # Tutaj wchodzi layout z "obrazu 2"
            
            c_attr, c_event = st.columns(2)
            
            with c_attr:
                st.markdown("#### 🏰 Atrakcje")
                # Jeśli API zwróciło dedykowaną listę atrakcji, użyj jej. Jeśli nie, wyciągnij z planu dnia.
                attractions_list = data.get("attractions", [])
                
                # Fallback: jeśli lista pusta, wyciągnij główne atrakcje z dni
                if not attractions_list:
                    for day in data.get("daily_plan", []):
                        if day.get("key_attraction_name"):
                            attractions_list.append({
                                "name": day.get("key_attraction_name"),
                                "description": day.get("theme", "Atrakcja dnia"),
                                "price": "Cena wg cennika",
                                "reservation": "Sprawdź dostępność"
                            })

                for item in attractions_list[:4]: # Pokaż max 4, żeby nie wydłużać
                    name = item.get("name", "Atrakcja")
                    desc = item.get("description", "Opis niedostępny")
                    price = item.get("price", "Bilet")
                    res = item.get("reservation", "")
                    
                    res_tag = f'<div class="tag tag-res">{res}</div>' if res else ""
                    
                    st.markdown(f"""
                    <div class="attraction-box">
                        <div class="attr-title">{name}</div>
                        <div class="attr-desc">{desc}</div>
                        <div class="tag-container">
                            <div class="tag tag-price">{price}</div>
                            {res_tag}
                        </div>
                    </div>
                    """, unsafe_allow_html=True)

            with c_event:
                st.markdown("#### 🎉 Wydarzenia")
                events = data.get("real_events", [])
                if events:
                    for e in events[:4]:
                        st.markdown(f"""
                        <div class="attraction-box">
                            <div class="attr-title">{e['name']}</div>
                            <div class="attr-desc">{e['venue']} | {e['date']}</div>
                            <div class="tag-container">
                                <div class="tag tag-type">BILET</div>
                                <a href="{e['url']}" target="_blank" style="font-size:0.8rem; margin-left:auto;">Kup Bilet &rarr;</a>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                else:
                    st.info("Brak dużych wydarzeń w tym terminie.")

            # --- MAPA (NA SAMYM DOLE) ---
            st.markdown('<div class="map-container">', unsafe_allow_html=True)
            display_map(data)
            st.markdown('</div>', unsafe_allow_html=True)

    except Exception as e:
        st.error(f"Błąd wyświetlania dashboardu: {e}")

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
                st.error(f"Błąd: {e}")
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