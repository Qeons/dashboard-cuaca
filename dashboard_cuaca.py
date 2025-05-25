import streamlit as st
import requests
import pandas as pd
import plotly.graph_objects as go
from streamlit_lottie import st_lottie
from streamlit_folium import st_folium
import folium
import urllib.parse

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

dark_mode = st.checkbox("🌙 Mode Gelap")
if dark_mode:
    st.markdown(
        """
        <style>
        body {background-color: #121212; color: white;}
        </style>
        """,
        unsafe_allow_html=True,
    )
else:
    st.markdown(
        """
        <style>
        body {background-color: white; color: black;}
        </style>
        """,
        unsafe_allow_html=True,
    )

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

            col1, col2 = st.columns([3, 1])
            with col1:
                st.subheader(f"📍 Lokasi: {location_name}")
                st.metric("🌡 Temperatur (°C)", temp)
                st.metric("💨 Kecepatan Angin (km/h)", windspeed)
                st.metric("☁️ Kondisi Cuaca", weather_desc)

                times = hourly.get("time", [])
                temps = hourly.get("temperature_2m", [])

                if times and temps:
                    df = pd.DataFrame(
                        {
                            "Waktu": pd.to_datetime(times[:24]),
                            "Suhu (°C)": temps[:24],
                        }
                    )

                    fig = go.Figure()
                    fig.add_trace(
                        go.Scatter(
                            x=df["Waktu"],
                            y=df["Suhu (°C)"],
                            mode="lines+markers+text",
                            text=[f"{v}°C" for v in df["Suhu (°C)"]],
                            textposition="top center",
                            line=dict(color="royalblue", width=3),
                            marker=dict(
                                size=8, color="royalblue", line=dict(width=1, color="darkblue")
                            ),
                            name="Suhu",
                        )
                    )
                    fig.update_layout(
                        title="Perkiraan Suhu 24 Jam",
                        xaxis_title="Waktu",
                        yaxis_title="Temperatur (°C)",
                        template="plotly_dark" if dark_mode else "plotly_white",
                        margin=dict(l=40, r=40, t=60, b=40),
                        hovermode="x unified",
                        yaxis=dict(range=[min(df["Suhu (°C)"]) - 3, max(df["Suhu (°C)"]) + 3]),
                    )

                    st.plotly_chart(fig, use_container_width=True)

                    png_bytes = fig.to_image(format="png", scale=2)
                    st.download_button(
                        label="⬇️ Download Grafik Suhu (PNG)",
                        data=png_bytes,
                        file_name="grafik_suhu_24jam.png",
                        mime="image/png",
                    )
                else:
                    st.write("Data suhu tidak tersedia.")

                humidity = hourly.get("relative_humidity_2m", [])
                pressure = hourly.get("pressure_msl", [])
                uv_index = hourly.get("uv_index", [])

                if humidity and pressure and uv_index:
                    df_env = pd.DataFrame(
                        {
                            "Waktu": pd.to_datetime(times[:24]),
                            "Kelembapan (%)": humidity[:24],
                            "Tekanan (hPa)": pressure[:24],
                            "Indeks UV": uv_index[:24],
                        }
                    )

                    fig_env = go.Figure()
                    fig_env.add_trace(
                        go.Scatter(
                            x=df_env["Waktu"],
                            y=df_env["Kelembapan (%)"],
                            name="💧 Kelembapan",
                            fill="tozeroy",
                            line=dict(color="mediumturquoise"),
                        )
                    )
                    fig_env.add_trace(
                        go.Scatter(
                            x=df_env["Waktu"],
                            y=df_env["Tekanan (hPa)"],
                            name="⚖️ Tekanan",
                            line=dict(color="orange"),
                        )
                    )
                    fig_env.add_trace(
                        go.Scatter(
                            x=df_env["Waktu"],
                            y=df_env["Indeks UV"],
                            name="☀️ Indeks UV",
                            line=dict(color="gold", dash="dot"),
                        )
                    )

                    fig_env.update_layout(
                        title="Visualisasi Kelembapan, Tekanan, dan Indeks UV",
                        template="plotly_dark" if dark_mode else "plotly_white",
                        margin=dict(l=40, r=40, t=60, b=40),
                        hovermode="x unified",
                        yaxis_title="Nilai",
                        xaxis_title="Waktu",
                    )

                    st.plotly_chart(fig_env, use_container_width=True)
                else:
                    st.write("Data kelembapan, tekanan, atau UV tidak tersedia.")

                m = folium.Map(location=[lat, lon], zoom_start=10)
                folium.Marker([lat, lon], popup=location_name).add_to(m)
                st.subheader("🗺️ Peta Lokasi")
                st_folium(m, width=700, height=450)

            with col2:
                anim_json = load_lottie_url(ANIM_HUJAN)
                if anim_json:
                    st_lottie(anim_json, height=300)
                else:
                    st.write("Animasi hujan gagal dimuat.")

            # Tombol share WhatsApp di bawah grafik
            dashboard_url = "https://cuaca.streamlit.app"  # Ganti dengan URL dashboard kamu
            msg = f"Cuaca saat ini di {location_name}:\n{weather_desc}\nSuhu: {temp}°C\n{dashboard_url}"
            wa_link = "https://wa.me/?text=" + urllib.parse.quote(msg)
            st.markdown(f"""
                <div style="text-align:center; margin-top:20px;">
                    <a href="{wa_link}" target="_blank" 
                       style="background:#25D366; color:white; padding:12px 24px; border-radius:8px; text-decoration:none; font-weight:bold;">
                       📲 Bagikan ke WhatsApp
                    </a>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("""
                <p style="text-align:center; color:gray; font-size:0.9em; margin-top:10px;">
                    Dibuat oleh Asrul Azza
                </p>
            """, unsafe_allow_html=True)

        except Exception as e:
            st.error(f"Gagal mengambil data cuaca: {e}")
