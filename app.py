import streamlit as st
import requests
import pandas as pd
from collections import defaultdict
from datetime import datetime
from tqdm import tqdm

# Caching requests to avoid re-fetching
@st.cache_data(show_spinner=False)
def fetch_summits():
    url = "https://api-db2.sota.org.uk/api/regions/GM/SI"
    response = requests.get(url)
    response.raise_for_status()
    return response.json()["summits"]

@st.cache_data(ttl=86400, show_spinner=False)
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

st.set_page_config(page_title="GM3VLB SOTA Island Award", page_icon="🏝️")
st.title("Andre Saunders SOTA Island Award")

# Display loading
loading_msg = st.empty()
progress_bar = st.empty()
loading_msg.info("Fetching summit list and activation data. This may take a moment...")
progress = progress_bar.progress(0)

summits = fetch_summits()

activations_by_year = defaultdict(lambda: defaultdict(set))  # year -> callsign -> set of summit_codes
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

# Remove loading once complete
loading_msg.empty()
progress_bar.empty()

# Prepare DataFrame of top 2 per year
rows = []

for year in sorted(activations_by_year.keys()):
    activator_data = activations_by_year[year]
    sorted_activators = sorted(
        activator_data.items(),
        key=lambda x: len(x[1]),
        reverse=True
    )[:2]  # Top 2

    for rank, (callsign, summits) in enumerate(sorted_activators, start=1):
        rows.append({
            "Year": year,
            "Rank": rank,
            "Callsign": callsign,
            "Summits Activated": len(summits)
        })

df = pd.DataFrame(rows)

# Sort by Year (desc) and Rank (asc)
df = df.sort_values(by=["Year", "Rank"], ascending=[False, True])

# Display table without index
st.subheader("Top 2 Activators per Year (by unique GM/SI summits)")
st.dataframe(df, use_container_width=True, hide_index=True)

with st.expander("What is the Andre Saunders SOTA Island Award?", icon="ℹ️"):
    st.markdown('''
    The Andre Saunders (GM3VLB) SOTA Island Award is a special award for SOTA activators who have activated the most Island summits (GM/SI) in Scotland.
    The award is named in memory of Andre Saunders, a passionate island activator.
    More details of the actual award can be found on this SOTA reflector [post](https://reflector.sota.org.uk/t/andre-saunders-gm3vlb-sota-island-award/27642).
    Tool designed by [GM5ALX](https://gm5alx.uk), source code [here](https://github.com/alexjj/island-awards).
    ''')
