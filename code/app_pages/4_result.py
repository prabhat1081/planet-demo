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
        data = json.loads(blob.download_as_bytes())
        return data.get('trial_data', data)
    except Exception as e:
        st.error(f"Error retrieving data for Request ID {request_id}: {e}")
        return None


def display_trial_data(trial_data):
    if trial_data:
        # st.write("Trial Data Details:")
        st.markdown("<u>Input Trial Data Details:</u>", unsafe_allow_html=True) 
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


def layout_result_data(result_data, trial_data):
    """Displays result data in a structured format."""

    if result_data is None:
        return

    st.subheader("Adverse Events")
    st.write(f"**Top 10 adverse events predicted with the highest probabilities**")
    cols = st.columns(len(trial_data["arm_group"]))
    for i, arm in enumerate(trial_data["arm_group"]):
        with cols[i]:
            if "AE" in result_data:
                aes = result_data["AE"][f"Top adverse events predicted for trial {i+1}"]
            elif f"Top adverse events predicted for trial {i+1}" in result_data:
                aes = result_data[f"Top adverse events predicted for trial {i+1}"]
            else:
                break
            arm_label = arm["arm_group_label"]
            st.write(f"Trial arm {i+1} ({arm_label}):")
            for ae_name, score in list(aes.items())[:10]:
                st.write(f"{ae_name}: {score:0.3f}")

    st.subheader("Safety")
    st.write(f"**Probability of serious adverse event occurrence**")
    cols = st.columns(len(trial_data["arm_group"]))
    for i, arm in enumerate(trial_data["arm_group"]):
        with cols[i]:
            if "safety" in result_data:
                score = result_data["safety"][f"Probability of safety concern for trial {i+1}"]
            elif f"Probability of safety concern for trial {i+1}" in result_data:
                score = result_data[f"Probability of safety concern for trial {i+1}"]
            else:
                break
            arm_label = arm["arm_group_label"]
            st.write(f"Trial arm {i+1} ({arm_label}):")
            st.write(f"{score:0.3f}")
    
    st.subheader("Efficacy")
    if "efficacy" in result_data:
        score = result_data["efficacy"]["Probability of trial 1 being more effective than trial 2"]
    elif "Probability of trial 1 being more effective than trial 2" in result_data:
        score = result_data["Probability of trial 1 being more effective than trial 2"]
    else:
        score = None 
    if score:
        arm1_label = trial_data["arm_group"][0]["arm_group_label"]
        arm2_label = trial_data["arm_group"][1]["arm_group_label"]
        outcome_measure = trial_data["primary_outcome"][0]["measure"]
        if arm1_label.lower() == "placebo":
            st.write(f"**Probability of trial arm 2 ({arm2_label}) being more effective than trial arm 1 ({arm1_label}) in terms of the provided primary outcome measure ({outcome_measure}):**")
            st.write(f"{1-score:0.3f}")
        else:
            st.write(f"**Probability of trial arm 1 ({arm1_label}) being more effective than trial arm 2 ({arm2_label}) in terms of the provided primary outcome measure ({outcome_measure}):**")
            st.write(f"{score:0.3f}")
    else:
        st.write(f"Efficacy prediction was not run because only one trial arm was provided as input. Efficacy prediction requires a pair of trial arms (1 and 2) and predicts the probability of trial arm 1 being more effective than trial arm 2 in terms of the provided primary outcome measure.")
    
    
def display_result_data(result_data):
    if result_data:
        # st.write("PlaNet Predictions:")
        st.markdown("<u>PlaNet Predictions:</u>", unsafe_allow_html=True) 
        layout_result_data(result_data)
    else:
        st.write(f"No data found for request ID: {request_id}")

st.title("Retrieve Results for Request ID")

request_id_from_url = st.query_params.get("id", None) #Get id from query params

if request_id_from_url: #If id is in url
    trial_data = get_trial_data(request_id_from_url)
    result_data = get_result_data(request_id_from_url)
    display_result_data(result_data, trial_data)
    st.divider() # make it clear that everything above this line is model prediction result, and below is original input provided by the user
    display_trial_data(trial_data)
else: #If id is not in url
    request_id_input = st.text_input("Enter Request ID") #Allow user to input request id
    if request_id_input: #If user inputted request id
        trial_data = get_trial_data(request_id_input)
        result_data = get_result_data(request_id_input)
        display_result_data(result_data, trial_data)
        st.divider() # make it clear that everything above this line is model prediction result, and below is original input provided by the user
        display_trial_data(trial_data)
        

