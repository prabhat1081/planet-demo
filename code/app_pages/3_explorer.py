import streamlit as st
import json
from google.cloud import storage

import streamlit as st
import json
from google.cloud import storage  # For GCS interaction
from app.common import layout_trial_data

from app.common import send_email, SENDER_EMAIL

# Initialize GCS client
storage_client = storage.Client()


def send_results_available_email(recipient: str, request_id: str) -> bool:
    """
    Sends an email to the recipient notifying them that their results are available.

    Args:
        recipient (str): The email address of the recipient.
        request_id (str): The ID of the request.
        results_link (str): The URL where the results can be accessed.

    Returns:
        bool: True if the email was sent successfully, False otherwise.
    """
    results_link = f'https://go.epfl.ch/planet-stanford/result?id={request_id}'

    email_subject = f"Subject: PlaNet - Results Available (Request ID: {request_id})"
    email_body = f"""
    <p>Dear Valued User,</p>

    <p>Your PlaNet results are now available for Request ID: {request_id}.</p>

    <p>You can access your results here: <a href="{results_link}">{results_link}</a></p>

    <p>Please review your results at your convenience.</p>

    <p>If you have any questions, please don't hesitate to contact us at <a href="mailto:{SENDER_EMAIL}">{SENDER_EMAIL}</a>.</p>

    <p>Sincerely,</p>

    <p>The PlaNet Team</p>
    """
    return send_email(recipient, email_subject, email_body)

# Example usage (assuming send_email is defined elsewhere and SENDER_EMAIL is a global variable):
# send_results_available_email("user@example.com", "request123")



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
                continue # Skip if search doesn't match
            request = download_request(request_id)

            if request is None:
                continue

            email = request.get('email', 'NA')

            email_sent = request.get('results_emailed', False)

            requests.append({"id": request_id, "results_exist": results_exist, "email": email, 
                             'results_emailed': email_sent, 'request_timestamp': request.get('timestamp', 'NA')})
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
    
def update_email_sent_status(request_id: str, email_sent:bool=True):
    """
    Updates the email sent status for a specific request in the JSON data stored in GCS.

    Args:
        request_id (str): The ID of the request.
        email_sent (bool, optional): The new email sent status (True or False). Defaults to True.

    Returns:
        bool: True if the update was successful, False otherwise.
    """
    bucket_name = "planet-stanford"
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(f"{request_id}.json")

    try:
        data = json.loads(blob.download_as_bytes())
        data["results_emailed"] = email_sent  # Update the email_sent field
        blob.upload_from_string(json.dumps(data), content_type="application/json")  # Upload the updated JSON
        return True
    except Exception as e:
        st.error(f"Error updating email sent status for request {request_id}: {e}")
        return False

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

import streamlit as st
import datetime
import time  # For Unix timestamp handling

# Assuming send_results_available_email and update_email_sent_status are defined elsewhere

def format_timestamp(timestamp_str: str):
    """Formats a timestamp string into a readable format."""
    try:
        dt_obj = datetime.datetime.fromisoformat(timestamp_str)  # ISO format
        return dt_obj.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        try:
            dt_obj = datetime.datetime.fromtimestamp(int(timestamp_str))  # Unix timestamp
            return dt_obj.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            return "Invalid Timestamp"

def display_request_row(request):
    """Displays a single request row in the Streamlit table."""
    col1, col2, col3, col4, col5, col6 = st.columns([2, 1, 1, 1, 1, 1])

    with col1:
        st.write(request["id"])
    with col2:
        st.write(request["email"])
    with col3:
        st.write(format_timestamp(request["request_timestamp"]))
    with col4:
        st.link_button(
            url=f"/result?id={request['id']}",
            label="View Results",
            icon=":material/analytics:",
            disabled=not request["results_exist"],
        )
    with col5:
        if st.button(
            f"Send Results Email",
            disabled=not request["results_exist"] or request.get("results_emailed", False),
            key=f"send_email_{request['id']}",
        ):
            result = send_results_available_email(request["email"], request["id"])
            if result:
                update_email_sent_status(request["id"])
    with col6:
        if st.button(f"View Details", key=f"details_{request['id']}",):
            st.session_state["show_details"] = request["id"]


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
            display_request_row(request)


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


main()