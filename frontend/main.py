import streamlit as st
import requests
import extra_streamlit_components as stx
import json
from datetime import date, timedelta
import folium
from streamlit_folium import st_folium

API_URL = "http://localhost:8000"

st.set_page_config(page_title="Planer Podróży AI", layout="wide")

# --- HELPERY ---
def get_manager(): return stx.CookieManager()
cookie_manager = get_manager()
cookie_token = cookie_manager.get(cookie="auth_token")

# Inicjalizacja sesji
if 'token' not in st.session_state: st.session_state['token'] = cookie_token
if 'current_plan' not in st.session_state: st.session_state['current_plan'] = None
if 'plan_meta' not in st.session_state: st.session_state['plan_meta'] = {}

TRAVEL_STYLES = [
    "Zwiedzanie", "Jedzenie", "Historia", "Imprezy", 
    "Natura", "Sztuka", "Foto", "Relaks", "Sport", "Zakupy"
]

def format_date_for_skyscanner(date_str):
    try:
        parts = date_str.split('-')
        if len(parts) == 3:
            year, month, day = parts
            return f"{year[2:]}{month}{day}"
    except Exception:
        pass
    return date_str

def generate_flight_links(origin, dest, start_date_str, end_date_str):
    safe_origin = origin.replace(" ", "-").lower()
    safe_dest = dest.replace(" ", "-").lower()
    s_date = format_date_for_skyscanner(start_date_str)
    e_date = format_date_for_skyscanner(end_date_str)
    base_url = f"https://www.skyscanner.pl/transport/loty/{safe_origin}/{safe_dest}/{s_date}/{e_date}/"
    params = "?adultsv2=1&cabinclass=economy&ref=home&rtn=1"
    return base_url + params

def generate_booking_link(city, start_date_str, end_date_str, people):
    city_slug = city.replace(" ", "+")
    return f"https://www.booking.com/searchresults.html?ss={city_slug}&checkin={start_date_str}&checkout={end_date_str}&group_adults={people}"

def display_map(data):
    coords = data.get("location_coordinates", [41.9028, 12.4964])
    m = folium.Map(location=coords, zoom_start=12)
    for day in data.get("daily_plan", []):
        kc = day.get("key_attraction_coords")
        name = day.get("key_attraction_name", f"Dzień {day['day']}")
        if kc and len(kc) == 2:
            folium.Marker(
                location=kc, 
                popup=name, 
                tooltip=f"Dzień {day['day']}", 
                icon=folium.Icon(color="blue", icon="info-sign")
            ).add_to(m)
    st_folium(m, width=None, height=400)

def show_dashboard(json_str):
    try:
        # Pętla upewniająca się, że odkodujemy JSON z tekstu do słownika
        data = json_str
        while isinstance(data, str):
            data = json.loads(data)
            
        if not data.get("is_feasible", True):
            st.error(f"Błąd: {data.get('feasibility_message', 'Nie udało się wygenerować planu.')}")
            return

        meta = st.session_state.get('plan_meta', {})
        start_date_str = meta.get('start_date', str(date.today()))
        end_date_str = meta.get('end_date', str(date.today() + timedelta(days=2)))
        people = meta.get('people', 1)
        dest_city = meta.get('dest', 'Cel')

        # 1. POLAK ZA GRANICĄ
        with st.expander("Polak za granicą", expanded=True):
            abroad = data.get("pole_abroad", {})
            c1, c2 = st.columns(2)
            with c1:
                st.markdown(f"""
                <div style="background-color: rgba(255, 0, 0, 0.7); padding: 20px; border-radius: 8px; color: white; height: 100%;">
                    <div style="font-weight: bold; font-size: 1.1rem; margin-bottom: 10px;">Bezpieczeństwo i Alarmowe</div>
                    <div style="margin-bottom: 10px;">{abroad.get('safety_warning', '-')}</div>
                    <div><strong>Numery alarmowe:</strong> {abroad.get('emergency_numbers', '-')}</div>
                </div>
                """, unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                <div style="background-color: rgba(0, 0, 255, 0.7); padding: 20px; border-radius: 8px; color: white; height: 100%;">
                    <div style="font-weight: bold; font-size: 1.1rem; margin-bottom: 10px;">Wiza i formalności</div>
                    <div>{abroad.get('visa_info', '-')}</div>
                </div>
                """, unsafe_allow_html=True)

        # 2. FINANSE I ATRAKCJE
        with st.expander("Finanse i Główne Atrakcje", expanded=True):
            fin = data.get("financial_analysis", {})
            st.metric(label="Szacowany koszt całkowity", value=fin.get('total_estimated_cost', '-'))
            st.markdown("---")
            c1, c2, c3 = st.columns(3)
            c1.markdown(f"**Transport:**\n{fin.get('transport_cost', '-')}")
            c2.markdown(f"**Nocleg:**\n{fin.get('accommodation_cost', '-')}")
            c3.markdown(f"**Jedzenie:**\n{fin.get('food_cost', '-')}")
            if "real_exchange_rate" in data:
                st.caption(f"Aktualny kurs: 1 {data.get('currency_code')} ≈ {data['real_exchange_rate']:.2f} PLN")
            st.divider()
            st.markdown("#### Lista Atrakcji")
            attractions = data.get("attractions", [])
            for i in range(0, len(attractions), 2):
                cols = st.columns(2)
                with cols[0]:
                    with st.container(border=True):
                        st.subheader(attractions[i].get('name'))
                        st.write(attractions[i].get('description'))
                        st.caption(f"Cena: {attractions[i].get('price')}")
                if i + 1 < len(attractions):
                    with cols[1]:
                        with st.container(border=True):
                            st.subheader(attractions[i+1].get('name'))
                            st.write(attractions[i+1].get('description'))
                            st.caption(f"Cena: {attractions[i+1].get('price')}")

        # 3. POGODA
        weather = data.get("real_weather_forecast", {})
        if "error" not in weather:
            with st.expander("Pogoda", expanded=True):
                st.caption(f"Prognoza dla pierwszego dnia wyjazdu ({start_date_str})")
                c1, c2, c3 = st.columns(3)
                c1.metric(label="Temperatura Max", value=f"{weather.get('max_temp')}°C")
                c2.metric(label="Temperatura Min", value=f"{weather.get('min_temp')}°C")
                c3.metric(label="Warunki", value=weather.get('desc', '-'))

        # 4. PLAN WYJAZDU
        with st.expander("Harmonogram Podróży", expanded=True):
            for day in data.get("daily_plan", []):
                with st.container(border=True):
                    st.markdown(f"### Dzień {day['day']}: {day['theme']}")
                    sch = day.get('schedule', {})
                    st.write(f"**Rano:** {sch.get('morning', '-')}")
                    st.write(f"**Południe:** {sch.get('afternoon', '-')}")
                    if day.get('key_attraction_name'):
                        st.caption(f"Główna atrakcja: {day.get('key_attraction_name')}")
                    st.write(f"**Wieczór:** {sch.get('evening', '-')}")

        # 5. TRANSPORT I ZAKWATEROWANIE
        with st.expander("Transport i Zakwaterowanie", expanded=True):
            trans = data.get("transport_detailed", {})
            flight = trans.get("flight", {})
            st.subheader("1. Loty")
            st.markdown(f"**Opcja:** {flight.get('best_option', '-')}")
            c1, c2 = st.columns(2)
            c1.markdown(f"**Cena:** {flight.get('estimated_price', '-')}")
            c2.markdown(f"**Czas:** {flight.get('duration', '-')}")
            f_query = flight.get("search_query", {})
            origin_place = f_query.get('origin_iata')
            if not origin_place or len(origin_place) < 3: origin_place = meta.get('origin', 'WAW')
            dest_place = f_query.get('dest_iata')
            if not dest_place or len(dest_place) < 3: dest_place = meta.get('dest', '')
            flight_url = generate_flight_links(origin_place, dest_place, start_date_str, end_date_str)
            st.link_button("Sprawdź loty na Skyscanner", flight_url, type="primary")
            st.markdown("---")
            tc1, tc2 = st.columns(2)
            with tc1:
                st.markdown("#### Z Lotniska")
                for t in trans.get("airport_transfer", []):
                    st.markdown(f"- **{t.get('name')}**: {t.get('price')} ({t.get('duration')})")
            with tc2:
                st.markdown("#### Alternatywa lądowa")
                alt = trans.get("alternative_transport", {})
                st.markdown(f"**{alt.get('type', '-')}**")
                st.markdown(f"Cena: {alt.get('price', '-')}")
                st.caption(alt.get('description', '-'))
            st.divider()
            st.subheader("2. Zakwaterowanie")
            st.info(data.get('accommodation_summary', 'Sprawdź polecane dzielnice.'))
            booking_url = generate_booking_link(dest_city, start_date_str, end_date_str, people)
            st.link_button("Zarezerwuj nocleg na Booking.com", booking_url)

        # 6. MAPA
        with st.expander("Mapa", expanded=True):
            display_map(data)

    except Exception as e:
        st.error(f"Wystąpił błąd wyświetlania danych: {e}")

# --- GŁÓWNY UKŁAD STRONY ---
col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.title("Planer Podróży AI")
    if st.session_state['plan_meta']:
        m = st.session_state['plan_meta']
        st.caption(f"Aktualny plan: **{m.get('origin')}** → **{m.get('dest')}** | {m.get('days')} dni | {m.get('people')} os.")

with col_h2:
    if st.session_state['token']:
        st.write(f"Zalogowany")
        if st.button("Wyloguj"):
            cookie_manager.delete("auth_token")
            st.session_state['token'] = None
            st.rerun()

# --- ZAKŁADKI ---
tab1, tab2 = st.tabs(["Plan podróży", "Konto"])

# --- ZAKŁADKA 1: PLAN PODRÓŻY ---
with tab1:
    if not st.session_state['current_plan']:
        st.markdown("### Wprowadź szczegóły podróży")
        with st.form("travel_form"):
            c1, c2 = st.columns(2)
            orig = c1.text_input("Skąd wyruszasz?", "Warszawa")
            dest = c2.text_input("Gdzie chcesz jechać?", "Rzym")
            
            c3, c4 = st.columns(2)
            start_date = c3.date_input("Data wylotu", date.today() + timedelta(days=7))
            days = c4.number_input("Ile dni?", min_value=1, max_value=14, value=3)
            
            styles = st.multiselect("Co lubisz robić?", TRAVEL_STYLES, default=["Zwiedzanie", "Jedzenie"])
            
            c5, c6 = st.columns(2)
            ppl = c5.number_input("Liczba osób", 1, 10, 2)
            bud = c6.number_input("Budżet na osobę (PLN)", 500, 50000, 2500, step=100)
            
            if st.form_submit_button("Generuj Plan Podróży", type="primary"):
                with st.status("AI pracuje nad Twoim planem...", expanded=True) as status:
                    st.write("Łączenie z modelem Gemini...")
                    st.write("Pobieranie danych o pogodzie i walutach...")
                    
                    payload = {
                        "origin": orig, "destination": dest, "start_date": str(start_date), 
                        "days": int(days), "people": int(ppl), "budget_per_person": int(bud), "styles": styles
                    }
                    try:
                        res = requests.post(f"{API_URL}/generate", json=payload, timeout=60)
                        if res.status_code == 200:
                            status.update(label="Gotowe!", state="complete", expanded=False)
                            st.session_state['current_plan'] = res.json().get('plan')
                            st.session_state['plan_meta'] = {
                                "origin": orig, "dest": dest, "start_date": str(start_date), 
                                "days": days, "people": ppl, "end_date": str(start_date + timedelta(days=days - 1))
                            }
                            st.rerun()
                        else:
                            status.update(label="Błąd!", state="error")
                            st.error(f"Błąd serwera: {res.status_code}")
                    except Exception as e:
                        status.update(label="Błąd połączenia!", state="error")
                        st.error(f"Nie udało się połączyć z backendem: {e}")
    else:
        if st.button("Rozpocznij nowy plan"):
            st.session_state['current_plan'] = None
            st.rerun()
            
        show_dashboard(st.session_state['current_plan'])
        
        # ZAPISZ PLAN NA SAMYM DOLE
        st.markdown("<br>", unsafe_allow_html=True)
        if st.session_state['token']:
            if st.button("Zapisz plan", type="primary", use_container_width=True):
                meta = st.session_state['plan_meta']
                save_payload = {
                    "destination": meta['dest'], "days": meta['days'], "style": "AI Plan",
                    "plan_json": st.session_state['current_plan'] 
                }
                h = {"Authorization": f"Bearer {st.session_state['token']}"}
                try:
                    requests.post(f"{API_URL}/save-trip", json=save_payload, headers=h)
                    st.success("Plan został zapisany w zakładce 'Konto' -> 'Moje wyprawy'!")
                except Exception as e:
                    st.error(f"Błąd zapisu: {e}")
        else:
            st.info("Zaloguj się w zakładce Konto, aby zapisać ten plan.")

# --- ZAKŁADKA 2: KONTO ---
with tab2:
    if not st.session_state['token']:
        st.subheader("Dostęp do konta")
        mode = st.radio("Wybierz:", ["Logowanie", "Rejestracja"], horizontal=True)
        
        email = st.text_input("Email")
        password = st.text_input("Hasło", type="password")
        
        if mode == "Rejestracja":
            username = st.text_input("Nazwa użytkownika")
            if st.button("Zarejestruj się", type="primary"):
                try:
                    reg = requests.post(f"{API_URL}/register", json={"email": email, "password": password, "username": username})
                    if reg.status_code == 200: 
                        st.success("Konto utworzone! Przełącz się na logowanie.")
                    else: 
                        st.error("Błąd rejestracji (może email jest zajęty?).")
                except Exception as e: 
                    st.error(f"Błąd połączenia: {e}")
        else:
            if st.button("Zaloguj się", type="primary"):
                try:
                    log = requests.post(f"{API_URL}/login", json={"email": email, "password": password})
                    if log.status_code == 200:
                        token = log.json().get("access_token")
                        st.session_state['token'] = token
                        cookie_manager.set("auth_token", token)
                        st.rerun()
                    else: 
                        st.error("Nieprawidłowe dane logowania.")
                except Exception as e: 
                    st.error(f"Błąd połączenia: {e}")
    else:
        sub_tab1, sub_tab2 = st.tabs(["Moje dane", "Moje wyprawy"])
        
        with sub_tab1:
            st.subheader("Profil użytkownika")
            st.success("Jesteś zalogowany.")
            st.info("Tutaj możesz zmienić hasło lub ustawić domyślny budżet (funkcje w przygotowaniu).")
            if st.button("Wyloguj sesję", key="logout_sub"):
                cookie_manager.delete("auth_token")
                st.session_state['token'] = None
                st.rerun()
                
        with sub_tab2:
            st.subheader("Historia Twoich planów")
            h = {"Authorization": f"Bearer {st.session_state['token']}"}
            try:
                r = requests.get(f"{API_URL}/my-trips", headers=h)
                if r.status_code == 200:
                    trips = r.json()
                    if not trips:
                        st.info("Twoja historia jest pusta.")
                    for t in trips:
                        with st.expander(f"{t['destination']} ({t['days']} dni)"):
                            # PRZYCISK USUWANIA PLANU
                            trip_id = t.get("id")
                            c_del1, c_del2 = st.columns([5, 1])
                            with c_del2:
                                if trip_id is not None:
                                    if st.button("Usuń plan", key=f"del_{trip_id}", use_container_width=True):
                                        del_res = requests.delete(f"{API_URL}/delete-trip/{trip_id}", headers=h)
                                        if del_res.status_code == 200:
                                            st.rerun()
                                        else:
                                            st.error("Nie udało się usunąć.")
                            st.divider()
                            show_dashboard(t['plan_json'])
                else:
                    st.error("Nie udało się pobrać historii.")
            except Exception as e:
                st.error(f"Błąd połączenia: {e}")