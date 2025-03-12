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


def display_trial_data(trial_data, request_id):
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
    
    st.subheader("Safety")
    st.markdown("""
<div style="background-color: #f0f8ff; padding: 20px; border-radius: 8px; border-left: 4px solid #4682B4; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
  <h3 style="margin-top: 0; color: #2c5282; font-size: 18px;">Serious Adverse Event Prediction</h3>
  <p>
    This tool predicts the overall probability of serious adverse events occurring in a clinical trial by:
  </p>
  <ul style="margin-top: 8px; margin-bottom: 12px;">
    <li>Using placebo arm data to establish the baseline risk of serious adverse events for the specific disease and population</li>
    <li>Comparing the observed rate of serious adverse events in the treatment arm against this estimated baseline</li>
    <li>Quantifying potential safety concerns associated with the treatment</li>
  </ul>
  <p>
    <strong>Interpretation:</strong> A higher predicted score suggests an increased risk of serious adverse events associated with the treatment compared to placebo.
  </p>
  <p style="margin-top: 12px; font-size: 14px;">
    For methodology and validation details, please refer to our <a href="https://www.medrxiv.org/content/10.1101/2024.03.06.24303800v2" target="_blank" style="color: #4682B4; text-decoration: underline;">research paper</a>.
  </p>
</div><br>
""", unsafe_allow_html=True)
    
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

    st.subheader("Adverse Events")
    st.markdown("""
<div style="background-color: #f0f8ff; padding: 20px; border-radius: 8px; border-left: 4px solid #4682B4; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
  <h3 style="margin-top: 0; color: #2c5282; font-size: 18px;">Specific Adverse Event Category Prediction</h3>
  <p>
    This tool predicts the probability of a <strong>specific category</strong> of adverse events occurring in a clinical trial. The analysis works by:
  </p>
  <ul style="margin-top: 8px; margin-bottom: 12px;">
    <li>Utilizing placebo arm data to establish a baseline expectation for the frequency of the specific adverse event type</li>
    <li>Comparing the observed frequency in the treatment arm against this estimated baseline</li>
    <li>Identifying potential enrichment of particular adverse event categories attributable to the treatment</li>
  </ul>
  <p>
    <strong>Interpretation:</strong> A higher predicted score indicates an increased likelihood that the specific adverse event category is associated with the treatment compared to placebo.
  </p>
  <p style="margin-top: 12px; font-size: 14px;">
    For methodology and validation details, please refer to our <a href="https://www.medrxiv.org/content/10.1101/2024.03.06.24303800v2" target="_blank" style="color: #4682B4; text-decoration: underline;">research paper</a>.
  </p>
</div><br>
""", unsafe_allow_html=True)

    st.write(f"**Top 10 adverse events predicted with the highest scores**")
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
    
    st.subheader("Efficacy")
    st.markdown("""
<div style="background-color: #f0f8ff; padding: 20px; border-radius: 8px; border-left: 4px solid #4682B4; box-shadow: 0 2px 4px rgba(0,0,0,0.1);">
  <h3 style="margin-top: 0; color: #2c5282; font-size: 18px;">Trial Arm Efficacy Prediction</h3>
  <p>
    This tool predicts which of two trial arms (testing different drugs) will demonstrate superior efficacy, using <strong>survival endpoint</strong> as the outcome measure. Results are presented as the probability that one trial arm will achieve higher survival rates than the other.
  </p>
  <p style="margin-bottom: 0;">
    <strong>Important:</strong> PlaNet is specifically trained on survival endpoints and cannot make accurate predictions for other outcome metrics without model fine-tuning using relevant data for those metrics.
  </p>
  <p style="margin-top: 10px; font-size: 14px;">
    For comprehensive methodology and validation details, please refer to our <a href="https://www.medrxiv.org/content/10.1101/2024.03.06.24303800v2" target="_blank" style="color: #4682B4; text-decoration: underline;">research paper</a>.
  </p>
</div>
<br>
""", unsafe_allow_html=True)
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
    
    
def display_result_data(result_data, trial_data, request_id):
    if result_data:
        # st.write("PlaNet Predictions:")
        st.markdown("<u>PlaNet Predictions:</u>", unsafe_allow_html=True) 
        layout_result_data(result_data, trial_data)
    else:
        st.write(f"No data found for request ID: {request_id}")

st.title("Retrieve Results for Request ID")

request_id_from_url = st.query_params.get("id", None) #Get id from query params

if request_id_from_url: #If id is in url
    trial_data = get_trial_data(request_id_from_url)
    result_data = get_result_data(request_id_from_url)
    display_result_data(result_data, trial_data, request_id_from_url)
    st.divider() # make it clear that everything above this line is model prediction result, and below is original input provided by the user
    display_trial_data(trial_data, request_id_from_url)
else: #If id is not in url
    request_id_input = st.text_input("Enter Request ID") #Allow user to input request id
    if request_id_input: #If user inputted request id
        trial_data = get_trial_data(request_id_input)
        result_data = get_result_data(request_id_input)
        display_result_data(result_data, trial_data, request_id_input)
        st.divider() # make it clear that everything above this line is model prediction result, and below is original input provided by the user
        display_trial_data(trial_data, request_id_input)
        

