import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from streamlit_lottie import st_lottie
from streamlit_folium import st_folium
import folium
import urllib.parse

def is_mobile():
    ua_list = st.query_params.get("user_agent")
    if ua_list:
        ua = ua_list[0].lower()
        if any(m in ua for m in ["mobile", "android", "iphone", "ipad"]):
            return True
    return False

def get_coordinates(area_name):
    url = "https://nominatim.openstreetmap.org/search"
    params = {"q": area_name, "format": "json", "limit": 1}
    headers = {"User-Agent": "CuacaApp/1.0"}
    response = requests.get(url, params=params, headers=headers)
    response.raise_for_status()
    data = response.json()
    if data:
        return float(data[0]["lat"]), float(data[0]["lon"]), data[0]["display_name"]
    return None, None, None

@st.cache_data(ttl=1800)
def fetch_weather(lat, lon):
    url = (
        f"https://api.open-meteo.com/v1/forecast?"
        f"latitude={lat}&longitude={lon}&current_weather=true&"
        f"hourly=temperature_2m,relative_humidity_2m,pressure_msl,uv_index&timezone=auto"
    )
    resp = requests.get(url)
    resp.raise_for_status()
    return resp.json()

def translate_weather_code(code):
    mapping = {
        0: "Cerah ☀️", 1: "Cerah sebagian 🌤", 2: "Berawan ⛅", 3: "Mendung ☁️",
        45: "Kabut 🌫", 48: "Kabut tebal 🌫", 51: "Gerimis 🌦", 53: "Gerimis 🌦", 55: "Gerimis 🌦",
        61: "Hujan ringan 🌧", 63: "Hujan sedang 🌧", 65: "Hujan lebat 🌧", 80: "Hujan lokal 🌧",
        95: "Badai petir ⛈", 96: "Petir ringan ⛈", 99: "Petir berat ⛈"
    }
    return mapping.get(code, "Tidak diketahui")

def load_lottie_url(url):
    r = requests.get(url)
    if r.status_code == 200:
        return r.json()
    return None

ANIM_HUJAN = "https://assets5.lottiefiles.com/packages/lf20_49rdyysj.json"

st.set_page_config(page_title="Dashboard Cuaca", layout="centered")
st.title("Dashboard Cuaca")

mobile = is_mobile()

area_name = st.text_input("📍 Masukkan nama daerah", placeholder="Contoh: Jakarta")

if area_name:
    lat, lon, location_name = None, None, None
    try:
        lat, lon, location_name = get_coordinates(area_name)
    except Exception as e:
        st.error(f"Gagal mendapatkan koordinat: {e}")

    if lat is None or lon is None:
        st.error("Lokasi tidak ditemukan, coba nama daerah lain.")
    else:
        try:
            weather = fetch_weather(lat, lon)
            current = weather.get("current_weather", {})
            hourly = weather.get("hourly", {})

            temp = current.get("temperature")
            windspeed = current.get("windspeed")
            weather_code = current.get("weathercode")
            weather_desc = translate_weather_code(weather_code)

            col1, col2 = st.columns([3,1])
            with col1:
                st.subheader(f"📍 Lokasi: {location_name}")
                st.metric("🌡 Temperatur (°C)", temp)
                st.metric("💨 Kecepatan Angin (km/h)", windspeed)
                st.metric("☁️ Kondisi Cuaca", weather_desc)

                times = hourly.get("time", [])
                temps = hourly.get("temperature_2m", [])

                if times and temps:
                    df = pd.DataFrame({
                        "Waktu": pd.to_datetime(times[:24]),
                        "Suhu (°C)": temps[:24]
                    })

                    fig = go.Figure()
                    fig.add_trace(go.Scatter(
                        x=df["Waktu"],
                        y=df["Suhu (°C)"],
                        mode="lines+markers+text",
                        text=[f"{v}°C" for v in df["Suhu (°C)"]],
                        textposition="top center",
                        line=dict(color="royalblue", width=3),
                        marker=dict(size=8, color="royalblue", line=dict(width=1, color="darkblue")),
                        name="Suhu"
                    ))
                    fig.update_layout(
                        title="Perkiraan Suhu 24 Jam",
                        xaxis_title="Waktu",
                        yaxis_title="Temperatur (°C)",
                        template="plotly_white",
                        margin=dict(l=40, r=40, t=60, b=40),
                        hovermode="x unified",
                        yaxis=dict(range=[min(df["Suhu (°C)"]) - 3, max(df["Suhu (°C)"]) + 3])
                    )
                    st.plotly_chart(fig, use_container_width=True)

                    # Tombol Download Screenshot dan Share WA sejajar tengah
                    png_bytes = fig.to_image(format="png", scale=2)

                    st.markdown("""
                        <style>
                        .button-container {
                            display: flex;
                            justify-content: center;
                            gap: 20px;
                            margin-top: 20px;
                            margin-bottom: 30px;
                        }
                        .btn-style {
                            background:#4CAF50; 
                            color:white; 
                            padding:12px 24px; 
                            border:none; 
                            border-radius:8px; 
                            font-weight:bold;
                            cursor:pointer;
                            text-decoration:none;
                            text-align:center;
                            display: inline-block;
                        }
                        .btn-wa {
                            background:#25D366;
                        }
                        </style>
                    """, unsafe_allow_html=True)

                    col_btn1, col_btn2 = st.columns([1,1])
                    with col_btn1:
                        st.download_button(
                            label="⬇️ Download Grafik Suhu (PNG)",
                            data=png_bytes,
                            file_name="grafik_suhu_24jam.png",
                            mime="image/png",
                            key="download_btn"
                        )
                    with col_btn2:
                        dashboard_url = "https://dashboard-cuaca-qeons.streamlit.app"
                        msg = f"Cuaca saat ini di {location_name}:\n{weather_desc}\nSuhu: {temp}°C\n{dashboard_url}"
                        wa_link = "https://wa.me/?text=" + urllib.parse.quote(msg)
                        st.markdown(f"""
                            <a href="{wa_link}" target="_blank" class="btn-style btn-wa" role="button">
                            📲 Bagikan ke WhatsApp
                            </a>
                        """, unsafe_allow_html=True)

                else:
                    st.write("Data suhu tidak tersedia.")

                m = folium.Map(location=[lat, lon], zoom_start=10)
                folium.Marker([lat, lon], popup=location_name).add_to(m)
                st.subheader("🗺️ Peta Lokasi")
                st_folium(m, width=700, height=450)

                st.markdown("""
                    <p style="text-align:center; color:gray; font-size:0.9em; margin-top:10px;">
                        2025 | Asrul Azza
                    </p>
                """, unsafe_allow_html=True)

            with col2:
                anim_json = load_lottie_url(ANIM_HUJAN)
                if anim_json:
                    st_lottie(anim_json, height=300)
                else:
                    st.write("Animasi hujan gagal dimuat.")

        except Exception as e:
            st.error(f"Gagal mengambil data cuaca: {e}")
