import streamlit as st
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
        data = json.loads(blob.download_as_bytes())['trial_data']
        return data
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


def get_result_data(request_id):
    """Retrieves trial data from GCS given a request ID."""
    bucket_name = "planet-stanford"  # Your GCS bucket name
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(f"{request_id}_results.json")

    try:
        data = json.loads(blob.download_as_bytes())
        return data
    except Exception as e:
        st.error(f"Error retrieving data for Request ID {request_id}: {e}")
        return None


def layout_result_data(result_data):
    """Displays result data in a structured format."""

    if result_data is None:
        return

    st.subheader("Adverse Events")
    st.write(f"**Top 5 adverse events with the highest probability:**")
    aes = result_data["Top adverse events predicted for trial 1"]
    for ae_name, score in aes.items():
        st.write(f"**{ae_name}:** {score:0.3f}")
    
    st.subheader("Safety")
    score = result_data["Probability of safety concern for trial 1"]
    st.write(f"**Probability of safety concern:** {score:0.3f}")
    
    st.subheader("Efficacy")
    score = result_data["Probability of trial 1 being more effective than trial 2"]
    st.write(f"**Probability of trial 1 being more effective than trial 2:** {score:0.3f}")
    
    
def display_result_data(request_id):
    result_data = get_result_data(request_id)
    if result_data:
        st.write("PlaNet Predictions:")
        layout_result_data(result_data)
    else:
        st.write(f"No data found for request ID: {request_id}")

st.title("Retrieve Results for Request ID")

request_id_from_url = st.query_params.get("id", None) #Get id from query params

if request_id_from_url: #If id is in url
    display_trial_data(request_id_from_url)
    display_result_data(request_id_from_url)
else: #If id is not in url
    request_id_input = st.text_input("Enter Request ID") #Allow user to input request id
    if request_id_input: #If user inputted request id
        display_trial_data(request_id_input)
        display_result_data(request_id_input)

