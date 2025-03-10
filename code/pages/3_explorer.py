import streamlit as st
st.set_page_config(layout="wide", page_title='PlaNet Demo', initial_sidebar_state="collapsed")
import json
from google.cloud import storage

import streamlit as st
import json
from google.cloud import storage  # For GCS interaction
from app.common import layout_trial_data

# Initialize GCS client
storage_client = storage.Client()


def list_requests(filter_status=None, search_id=None):
    """Lists all request IDs (JSON files) in the GCS bucket, with filtering and search."""
    bucket_name = "planet-stanford"
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blobs = bucket.list_blobs()
    requests = []
    for blob in blobs:
        if blob.name.endswith(".json") and not blob.name.endswith("_results.json"):
            request_id = blob.name[:-5]
            results_blob = bucket.blob(f"{request_id}_results.json")
            results_exist = results_blob.exists()

            # Apply filters
            if filter_status is not None and results_exist != filter_status:
                continue  # Skip if filter doesn't match

            if search_id and search_id.lower() not in request_id.lower(): #Case insensitive search
                continue #Skip if search doesn't match

            requests.append({"id": request_id, "results_exist": results_exist})
    return requests


def download_request(request_id):
    """Downloads a specific request's JSON data."""
    bucket_name = "planet-stanford"
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(f"{request_id}.json")
    try:
        data = json.loads(blob.download_as_bytes())
        return data
    except Exception as e:
        st.error(f"Error downloading request {request_id}: {e}")
        return None

def upload_results(request_id, results_data):
    """Uploads results data for a specific request."""
    bucket_name = "planet-stanford"
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(f"{request_id}_results.json")  # Use a different naming convention
    try:
        blob.upload_from_string(json.dumps(results_data), content_type='application/json')
        st.success(f"Results uploaded for request {request_id}!")
    except Exception as e:
        st.error(f"Error uploading results for request {request_id}: {e}")

def download_all_requests(request_ids): #Callback function
    all_data = {}
    for request_id in request_ids:
        data = download_request(request_id)
        if data:
            all_data[request_id] = data
    json_data = json.dumps(all_data, indent=4)
    return json_data


def main():
    st.title("Request Management")

    # Filters
    st.sidebar.header("Filters")
    status_filter = st.sidebar.selectbox("Filter by Results Status", [None, "Results Exist", "Results Missing"])
    search_term = st.sidebar.text_input("Search by Request ID")

    # Convert filter selection to boolean
    filter_status_bool = None
    if status_filter == "Results Exist":
        filter_status_bool = True
    elif status_filter == "Results Missing":
        filter_status_bool = False

    # List and Browse Requests
    st.header("Browse Requests")
    requests = list_requests(filter_status=filter_status_bool, search_id=search_term)  # Apply filters
    

    if requests:
        for request in requests:
            col1, col2, col3 = st.columns([2, 1, 1])  # Adjust column ratios as needed
            with col1:
                st.write(request["id"])  # Display request ID
            with col2:
                if request["results_exist"]:
                    st.success("Results Exist")
                else:
                    st.warning("Results Missing")

            with col3:
                if st.button(f"View Details - {request['id']}"):
                    st.session_state["show_details"] = request['id']

        if st.session_state.get("show_details", None): #Check if the details should be shown
            trial_data = download_request(st.session_state["show_details"]) #If they should be shown, download and display
            if trial_data:
                layout_trial_data(trial_data.get('trial_data', trial_data))

        # Download All button
        if st.button("Download All Requests"):
            request_ids = [req["id"] for req in requests] #Get all request ids
            json_data = download_all_requests(request_ids)  # Call download function

            st.download_button(
                label="Download All Data (JSON)",
                data=json_data,
                file_name="all_requests.json",
                mime="application/json",
            )

    else:
        st.write("No requests found matching the criteria.")

    # Upload Results
    st.header("Upload Results")
    request_id_upload = st.text_input("Enter Request ID for Results Upload")
    results_upload = st.text_area("Enter Results Data (JSON)")
    if st.button("Upload Results"):
        try:
            results_data = json.loads(results_upload)  # Validate JSON
            upload_results(request_id_upload, results_data)
        except json.JSONDecodeError:
            st.error("Invalid JSON in results data.")


if __name__ == "__main__":
    main()