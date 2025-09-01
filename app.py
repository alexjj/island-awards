import streamlit as st
import requests
import pandas as pd
from collections import defaultdict
from datetime import datetime

# ----------------------
# API Fetch Functions
# ----------------------

@st.cache_data(show_spinner=False)
def fetch_summits():
    url = "https://api-db2.sota.org.uk/api/regions/GM/SI"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()["summits"]

@st.cache_data(ttl=86400, show_spinner=False)  # cache for 1 day
def fetch_activations(summit_code):
    url = f"https://api-db2.sota.org.uk/api/activations/{summit_code}"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()

@st.cache_data(show_spinner=False)
def get_callsign(user_id):
    url = f"https://sotl.as/api/activators/{user_id}"
    response = requests.get(url)
    if response.status_code == 200:
        return response.json().get("callsign", "Unknown")
    return "Unknown"

# ----------------------
# Main App
# ----------------------

st.set_page_config(page_title="GM3VLB SOTA Island Award", page_icon="🏝️")
st.title("Andre Saunders SOTA Island Award")

# Loading message + progress
loading_msg = st.empty()
progress_bar = st.empty()
loading_msg.info("Fetching summit list and activation data. This may take a moment...")
progress = progress_bar.progress(0)

# Fetch summits
summits = fetch_summits()

# Build activations by year {year -> {callsign -> set(summits)}}
activations_by_year = defaultdict(lambda: defaultdict(set))
total = len(summits)

for idx, summit in enumerate(summits):
    summit_code = summit["summitCode"]
    activations = fetch_activations(summit_code)

    for activation in activations:
        date = activation.get("activationDate")
        if not date:
            continue
        year = datetime.fromisoformat(date).year
        user_id = activation.get("userId")
        if user_id is None:
            continue
        callsign = get_callsign(user_id)
        activations_by_year[year][callsign].add(summit_code)

    progress.progress((idx + 1) / total)

# Remove loading UI
loading_msg.empty()
progress_bar.empty()

# ----------------------
# Current Year Summary
# ----------------------

current_year = datetime.now().year

if current_year in activations_by_year:
    col1, col2 = st.columns(2)

    # --- Total activations in current year ---
    total_activations = sum(len(s) for s in activations_by_year[current_year].values())
    with col1:
        st.markdown(
            f"""
            <div style='text-align: center;'>
                <div style='font-size: 18px; color: grey;'>Total Activations</div>
                <div style='font-size: 32px; font-weight: bold;'>{total_activations}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    # --- Most common summit ---
    all_summits = []
    for summits_set in activations_by_year[current_year].values():
        all_summits.extend(list(summits_set))

    if all_summits:
        most_common_code = pd.Series(all_summits).mode()[0]
        summit_info = next((s for s in summits if s["summitCode"] == most_common_code), None)
        summit_name = summit_info["name"] if summit_info else "Unknown"

        with col2:
            st.markdown(
                f"""
                <div style='text-align: center;'>
                    <div style='font-size: 18px; color: grey;'>Most Common Summit</div>
                    <div style='font-size: 28px; font-weight: bold;'>{summit_name}</div>
                    <div style='font-size: 16px; color: grey;'>{most_common_code}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

    # ----------------------
    # All current year activations (by callsign)
    # ----------------------
    rows_current = []
    for callsign, summits_set in activations_by_year[current_year].items():
        rows_current.append({
            "Callsign": callsign,
            "Summits Activated": len(summits_set)
        })

    df_current = pd.DataFrame(rows_current)
    df_current = df_current.sort_values(by="Summits Activated", ascending=False)

    st.subheader(f"All Activations in {current_year} (by Operator)")
    st.dataframe(df_current, use_container_width=True, hide_index=True)

else:
    st.subheader(f"No activations found in {current_year}")


# ----------------------
# Top 2 Activators per Year
# ----------------------

rows = []
for year in sorted(activations_by_year.keys()):
    activator_data = activations_by_year[year]
    sorted_activators = sorted(
        activator_data.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )[:2]  # Top 2

    for rank, (callsign, summits_set) in enumerate(sorted_activators, start=1):
        rows.append({
            "Year": year,
            "Rank": rank,
            "Callsign": callsign,
            "Summits Activated": len(summits_set)
        })

df_top = pd.DataFrame(rows)
df_top = df_top.sort_values(by=["Year", "Rank"], ascending=[False, True])

st.subheader("Top 2 Activators per Year (by unique GM/SI summits)")
st.dataframe(df_top, use_container_width=True, hide_index=True)



with st.expander("What is the Andre Saunders SOTA Island Award?", icon="ℹ️"):
    st.markdown('''
    The Andre Saunders (GM3VLB) SOTA Island Award is a special award for SOTA activators who have activated the most Island summits (GM/SI) in Scotland.
    The award is named in memory of Andre Saunders, a passionate island activator.
    More details of the actual award can be found on this SOTA reflector [post](https://reflector.sota.org.uk/t/andre-saunders-gm3vlb-sota-island-award/27642).
    Tool designed by [GM5ALX](https://gm5alx.uk), source code [here](https://github.com/alexjj/island-awards).
    ''')
