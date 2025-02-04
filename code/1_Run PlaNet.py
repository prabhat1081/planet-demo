import streamlit as st
import json
from typing import Dict, Any, List
import os

from parse_trial import parse, load_tools
import requests
import zipfile
import io
import os
import pandas as pd
import subprocess
import hashlib 
import re

from st_files_connection import FilesConnection

import smtplib
import os
from google.cloud import secretmanager
import uuid  # For generating request IDs
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials

from email.mime.text import MIMEText
import base64
import json

from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from google.cloud import storage  # For GCS interaction

# Initialize Secret Manager client
client = secretmanager.SecretManagerServiceClient()
storage_client = storage.Client()

def access_secret_version(secret_name):
    """Access the payload for the given secret version."""

    name = f"projects/premium-state-449406-n8/secrets/{secret_name}/versions/latest" # Replace with your project ID
    response = client.access_secret_version(name=name)
    return response.payload.data.decode("UTF-8")

def send_email(recipient: str, subject: str, body: str):
    try:
        sendgrid_api_key = access_secret_version("sendgrid-api-key") # Get from Secret Manager
        message = Mail(
            from_email='planet.stanford@gmail.com',  # Your verified SendGrid sender
            to_emails=recipient,
            subject=subject,
            plain_text_content=body
        )
        message.cc_emails = [
            'planet.stanford@gmail.com',  # Add sender to CC if needed
        ]
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        if response.status_code == 202:
            st.success(f"Email sent to {recipient}!")
        else: 
            st.error(f"Error sending email: {response.body.decode('utf-8')}")
    except Exception as e:
        st.error(f"Error sending email: {e}")

def get_trial_data(request_id):
    """Retrieves trial data from GCS given a request ID."""
    bucket_name = "planet-stanford"  # Your GCS bucket name
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(f"{request_id}.json")

    try:
        data = json.loads(blob.download_as_bytes())
        return data
    except Exception as e:
        st.error(f"Error retrieving data for Request ID {request_id}: {e}")
        return None

def send_confirmation_email(recipient, request_id):  # Added request_id parameter
    # smtp_username = access_secret_version("smtp-username")
    # smtp_password = access_secret_version("smtp-password")
    # server = smtplib.SMTP('smtp.gmail.com', 587)  # Or your SMTP server
    # server.starttls()
    # server.login(smtp_username, smtp_password)
    email_subject = f"Subject: PlaNet - Request Confirmation (Request ID: {request_id})"
    email_body = f"""
Dear Valued User,

Thank you for using PlaNet.

This email confirms that we have received your request. Your Request ID is: {request_id}. Please refer to this ID if you need to contact us about your request.

Our team is now processing your data, and we anticipate having your results ready within 36-48 hours.

You will receive a follow-up email with a link to our website where you can view your results.

If you have any questions in the meantime, please don't hesitate to contact us at planet.stanford@gmail.com.

Sincerely,

The PlaNet Team
    """  # Using a multiline string for the email body

    #     server.sendmail(smtp_username, recipient, email_body)
    #     server.quit()
    #     st.success(f"Email sent to {recipient}!")
    # except Exception as e:
    #     st.error(f"Error sending email: {e}")

    return send_email(recipient, email_subject, email_body)


# Create connection object and retrieve file contents.
# Specify input format is a csv and to cache the result for 600 seconds.
gcs_conn = st.connection('gcs', type=FilesConnection)


def generate_filename_from_dict(data):
    """Generates a unique filename based on the hash of a dictionary."""

    # Convert the dictionary to a JSON string
    json_data = json.dumps(data, sort_keys=True).encode('utf-8')

    # Create a hash object
    hash_object = hashlib.sha256(json_data)

    # Get the hexadecimal representation of the hash
    hex_dig = hash_object.hexdigest()

    # Return a filename based on the hash
    return f"file_{hex_dig[:10]}.json"

parser_state = None

def fetch_trial_details(nct_id: str) -> Dict[str, Any]:
    """
    Fetch trial details from NCT ID
    """
    # Placeholder data - replace with actual API call
    sample_data = {
        'nct_id': 'NCT01007279',
        'arm_group': [
            {
                'type': 'ACTIVE_COMPARATOR',
                'interventionNames': ['Drug: ROSUVASTATIN'],
                'arm_group_label': 'CLOPIDOGREL'
            }
        ],
        'intervention': [
            {
                'description': '40 mg before procedure',
                'intervention_type': 'Drug',
                'intervention_name': 'ROSUVASTATIN',
                'arm_group_label': ['CLOPIDOGREL', 'ROSUVASTATIN']
            }
        ],
        'condition': ['Periprocedural Myocardial Necrosis'],
        'primary_outcome': [{'measure': 'Myocardial enzymes arise', 'timeFrame': '6-12-24 hours'}],
        'secondary_outcome': [{'measure': 'MACE', 'timeFrame': '1-6-9 MONTHS'}],
        'eligibility_criteria': 'Inclusion Criteria:\n\n* Patients with stable angina\n\nExclusion Criteria:\n\n* Baseline myocardial enzyme rise',
        'phase': ['PHASE3'],
        'enrollment': {'count': 160, 'type': 'ESTIMATED'},
        'gender_sex': 'ALL',
        'minimum_age': '18 Years',
        'maximum_age': None
    }
    return parse(nctid=nct_id)

def is_valid_email(email):
    """Validates if the given string is a valid email address."""
    # Basic email validation regex (can be improved for stricter validation)
    email_regex = r"[^@]+@[^@]+\.[^@]+"  
    return re.match(email_regex, email) is not None

def main():
    st.title("Clinical Trial Data Editor")
    
    # Top section for NCT ID fetch
    st.header("Auto-fill from NCT ID (Optional)")
    col1, col2 = st.columns([3, 1])
    with col1:
        nct_id = st.text_input(
            "NCT ID",
            placeholder="Enter NCT ID (e.g., NCT01007279)",
            key="nct_id_input"
        )
    with col2:
        fetch_button = st.button("Fetch Trial Details", use_container_width=True)
    
    if fetch_button and nct_id:
        with st.spinner("Fetching trial details..."):
            try:
                trial_data = fetch_trial_details(nct_id)
                st.session_state.trial_data = trial_data
                st.success("Trial details fetched successfully!")
            except Exception as e:
                st.error(f"Error fetching trial details: {str(e)}")
    
    # Main form for all fields
    st.header("Trial Details")
    st.info("Fill in the fields manually or fetch from NCT ID above")
    
    with st.form("trial_form"):
        # Use fetched data if available, otherwise empty/default values
        data = st.session_state.get('trial_data', fetch_trial_details('NCT02376244'))
        
        # Basic Information
        st.subheader("Basic Information")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            trial_nct_id = st.text_input(
                "NCT ID",
                value=data.get('nct_id', ''),
                placeholder="NCT00000000"
            )
            
            gender = st.selectbox(
                "Gender",
                options=["ALL", "MALE", "FEMALE"],
                index=["ALL", "MALE", "FEMALE"].index(data.get('gender_sex', 'ALL'))
            )
        
        with col2:
            min_age = st.text_input(
                "Minimum Age",
                value=data.get('minimum_age', ''),
                placeholder="e.g., 18 Years"
            )
            
            phase = st.multiselect(
                "Phase",
                options=["PHASE1", "PHASE2", "PHASE3", "PHASE4", "NA"],
                default=data.get('phase', [])
            )
        
        with col3:
            max_age = st.text_input(
                "Maximum Age",
                value=data.get('maximum_age', ''),
                placeholder="e.g., 65 Years"
            )
            
            enrollment = st.number_input(
                "Enrollment Count",
                value=data.get('enrollment', {}).get('count', 0),
                min_value=0
            )
        
        # Conditions
        st.subheader("Conditions")
        conditions = st.text_area(
            "Conditions (one per line)",
            value="\n".join(data.get('condition', [])),
            height=100,
            placeholder="Enter each condition on a new line"
        )
        
        # Arm Groups
        st.subheader("Arm Groups")
        num_arms = st.number_input("Number of Arms", min_value=1, value=len(data.get('arm_group', [1])))
        
        arm_groups = []
        for i in range(int(num_arms)):
            st.markdown(f"**Arm {i+1}**")
            col1, col2 = st.columns(2)
            existing_arm = data.get('arm_group', [])[i] if i < len(data.get('arm_group', [])) else {}
            
            with col1:
                arm_type = st.selectbox(
                    "Type",
                    options=["ACTIVE_COMPARATOR", "EXPERIMENTAL", "PLACEBO_COMPARATOR", "SHAM_COMPARATOR"],
                    key=f"arm_type_{i}",
                    index=0
                )
                
                arm_label = st.text_input(
                    "Label",
                    value=existing_arm.get('arm_group_label', ''),
                    key=f"arm_label_{i}"
                )
            
            with col2:
                arm_interventions = st.text_area(
                    "Interventions (one per line)",
                    value="\n".join(existing_arm.get('interventionNames', [])),
                    key=f"arm_interventions_{i}",
                    height=100
                )
            
            arm_groups.append({
                'type': arm_type,
                'arm_group_label': arm_label,
                'interventionNames': [x.strip() for x in arm_interventions.splitlines() if x.strip()]
            })
        
        # Interventions
        st.subheader("Interventions")
        num_interventions = st.number_input("Number of Interventions", min_value=1, 
                                          value=len(data.get('intervention', [1])))
        
        interventions = []
        for i in range(int(num_interventions)):
            st.markdown(f"**Intervention {i+1}**")
            existing_int = data.get('intervention', [])[i] if i < len(data.get('intervention', [])) else {}
            
            col1, col2 = st.columns(2)
            with col1:
                int_name = st.text_input(
                    "Name",
                    value=existing_int.get('intervention_name', ''),
                    key=f"int_name_{i}"
                )
                
                int_type = st.selectbox(
                    "Type",
                    options=["Drug", "Device", "Procedure", "Other"],
                    key=f"int_type_{i}"
                )
            
            with col2:
                int_desc = st.text_area(
                    "Description",
                    value=existing_int.get('description', ''),
                    key=f"int_desc_{i}",
                    height=100
                )
            
            interventions.append({
                'intervention_name': int_name,
                'intervention_type': int_type,
                'description': int_desc,
                'arm_group_label': [x.strip() for x in arm_interventions.splitlines() if x.strip()]
            })
        
        # Outcomes
        st.subheader("Outcomes")
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Primary Outcomes**")
            num_primary = st.number_input("Number of Primary Outcomes", min_value=1, 
                                        value=len(data.get('primary_outcome', [1])))
            
            primary_outcomes = []
            for i in range(int(num_primary)):
                existing_outcome = data.get('primary_outcome', [])[i] if i < len(data.get('primary_outcome', [])) else {}
                
                measure = st.text_input(
                    "Measure",
                    value=existing_outcome.get('measure', ''),
                    key=f"pri_measure_{i}"
                )
                
                timeframe = st.text_input(
                    "Time Frame",
                    value=existing_outcome.get('timeFrame', ''),
                    key=f"pri_time_{i}"
                )
                
                primary_outcomes.append({
                    'measure': measure,
                    'timeFrame': timeframe
                })
        
        with col2:
            st.markdown("**Secondary Outcomes**")
            num_secondary = st.number_input("Number of Secondary Outcomes", min_value=1,
                                          value=len(data.get('secondary_outcome', [1])))
            
            secondary_outcomes = []
            for i in range(int(num_secondary)):
                existing_outcome = data.get('secondary_outcome', [])[i] if i < len(data.get('secondary_outcome', [])) else {}
                
                measure = st.text_input(
                    "Measure",
                    value=existing_outcome.get('measure', ''),
                    key=f"sec_measure_{i}"
                )
                
                timeframe = st.text_input(
                    "Time Frame",
                    value=existing_outcome.get('timeFrame', ''),
                    key=f"sec_time_{i}"
                )
                
                secondary_outcomes.append({
                    'measure': measure,
                    'timeFrame': timeframe
                })
        
        # Eligibility Criteria
        st.subheader("Eligibility Criteria")
        eligibility = st.text_area(
            "Criteria",
            value=data.get('eligibility_criteria', ''),
            height=200,
            placeholder="Inclusion Criteria:\n\n* Criterion 1\n* Criterion 2\n\nExclusion Criteria:\n\n* Criterion 1\n* Criterion 2"
        )

        recipient_email = st.text_input("Recipient Email", placeholder="Enter your email address")

        if st.form_submit_button("Save Trial Data and Send Email"):  # Submit button is OUTSIDE the email check
            if not recipient_email:
                st.warning("Please enter a recipient email address.")
            elif not is_valid_email(recipient_email):
                st.error("Invalid email address. Please enter a valid email.")
            else:  # Proceed only if the email is valid
                # Compile all data
                trial_data = {
                    'nct_id': trial_nct_id,
                    'phase': phase,
                    'gender_sex': gender,
                    'minimum_age': min_age,
                    'maximum_age': max_age,
                    'enrollment': {
                        'count': enrollment,
                        'type': 'ESTIMATED'
                    },
                    'condition': [x.strip() for x in conditions.splitlines() if x.strip()],
                    'arm_group': arm_groups,
                    'intervention': interventions,
                    'primary_outcome': primary_outcomes,
                    'secondary_outcome': secondary_outcomes,
                    'eligibility_criteria': eligibility
                }
                
                # Store in session state
                st.session_state.trial_data = trial_data

                request_id = str(uuid.uuid4())

                with gcs_conn.open(f'planet-stanford/{request_id}.json', 'w') as f:
                    json.dump(trial_data, f)

                if send_confirmation_email(recipient_email, request_id):
                    st.success(f"Trial data saved successfully! Your Request ID is: {request_id}. Please keep this for your records.")  # Success message only here

if __name__ == "__main__":
    main()