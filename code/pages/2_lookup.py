import streamlit as st
st.set_page_config(layout="wide", page_title='PlaNet Demo', initial_sidebar_state="collapsed")
import json
from google.cloud import storage
from app.common import layout_trial_data

# Initialize GCS client
storage_client = storage.Client()

def get_trial_data(request_id):
    """Retrieves trial data from GCS given a request ID."""
    bucket_name = "planet-stanford"  # Your GCS bucket name
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(f"{request_id}.json")

    try:
        data = json.loads(blob.download_as_bytes())
        return data.get('trial_data', data)
    except Exception as e:
        st.error(f"Error retrieving data for Request ID {request_id}: {e}")
        return None

    
def display_trial_data(request_id):
    trial_data = get_trial_data(request_id)
    if trial_data:
        st.write("Trial Data Details:")
        layout_trial_data(trial_data)
    else:
        st.write(f"No data found for request ID: {request_id}")

st.title("Request ID Lookup")

request_id_from_url = st.query_params.get("id", None) #Get id from query params

if request_id_from_url: #If id is in url
    display_trial_data(request_id_from_url)
else: #If id is not in url
    request_id_input = st.text_input("Enter Request ID") #Allow user to input request id
    if request_id_input: #If user inputted request id
        display_trial_data(request_id_input)

