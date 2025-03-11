import streamlit as st

import json
from typing import Dict, Any, List
import os

from parse import parse
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
from sendgrid.helpers.mail import Mail, Cc, Email
from google.cloud import storage  # For GCS interaction



try:
    # Initialize Secret Manager client
    client = secretmanager.SecretManagerServiceClient()
    storage_client = storage.Client()
except:
    st.info("Secret agent not available")

def access_secret_version(secret_name):
    """Access the payload for the given secret version."""

    name = f"projects/premium-state-449406-n8/secrets/{secret_name}/versions/latest" # Replace with your project ID
    response = client.access_secret_version(name=name)
    return response.payload.data.decode("UTF-8")

SENDER_EMAIL = 'prabhat.agarwal@cs.stanford.edu'

def send_email(recipient: str, subject: str, body: str):
    try:
        sendgrid_api_key = access_secret_version("sendgrid-api-key") # Get from Secret Manager
        message = Mail(
            from_email=Email(email=SENDER_EMAIL, name='PlaNet Team'),  # Your verified SendGrid sender
            to_emails=recipient,
            subject=subject,
            html_content=body
        )
        message.cc = [
            Cc('mbrbic@epfl.ch', 'Maria Brbic'),
            Cc('myasu@cs.stanford.edu', 'Michi Yasunaga'),
            Cc('prabhat.agarwal@cs.stanford.edu', 'Prabhat Agarwal')
        ]
        sg = SendGridAPIClient(sendgrid_api_key)
        response = sg.send(message)
        if response.status_code == 202:
            st.success(f"Confirmation email sent to {recipient}. Please check your inbox!")
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

def send_confirmation_email(recipient, request_id):  # Add task parameter
    email_subject = f"Subject: PlaNet - Request Confirmation (Request ID: {request_id})"
    email_body = f"""
    <p>Dear Valued User,</p> 

    <p>Thank you for using PlaNet!</p>

    <p>This email confirms that we have received your request. Your Request ID is: {request_id}.</p>

    <p>You can view your request details here: <a href="https://tinyurl.com/planet-stanford/lookup?id={request_id}">https://tinyurl.com/planet-stanford/lookup?id={request_id}</a></p>

    <p>The system is now processing your data, and we anticipate having your results ready within 72 hours.</p>

    <p>You will receive a follow-up email with a link to our website where you can view your results.</p>

    <p>If you have any questions, please don't hesitate to contact us at <a href="mailto:{SENDER_EMAIL}">{SENDER_EMAIL}</a>.</p>

    <p>Sincerely,</p>

    <p>The PlaNet Team</p>
    """
    #     <p>In the meantime, you can learn more about PlaNet and our research on our <a href="YOUR_WEBSITE_LINK">website</a>.</p>
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


def validate_trial_data(trial_data):
    """
    Validates the trial data to ensure it meets the following criteria:
    1. There should be at least one arm with a drug intervention.
    """

    return True

    has_drug_intervention = False
    for arm in trial_data.get('arm_group',):
        for intervention_name in arm.get('interventionNames',):
            for intervention in trial_data.get('intervention',):
                if intervention_name == intervention.get('intervention_name') and \
                   intervention.get('intervention_type') == 'Drug':
                    has_drug_intervention = True
                    break
            if has_drug_intervention:
                break
        if has_drug_intervention:
            break

    if not has_drug_intervention:
        st.error("Error: There must be at least one arm with a drug intervention.")
        return False

    # Add more validation checks here if needed

    return True

def main():
    st.title("Run PlaNet on your Clinical Trial")

    # Information Box at the Top
    st.markdown(
        """
        <div style="background-color: #f0f8ff; padding: 20px; border-radius: 5px;">
            <h3>About PlaNet</h3>
            <p>
                PlaNet is a tool that predicts the efficacy and side effects of drugs for specific populations using a clinical knowledge graph. 
                By leveraging a vast network of biomedical knowledge, PlaNet can provide insights into how different drugs might affect various patient groups.
            </p>
            <p>
                This app allows you to upload clinical trial details and receive predictions on the potential outcomes, including efficacy and safety, for your target population.
            </p>
            <p>
                Learn more about the research behind PlaNet: 
                <a href="https://www.medrxiv.org/content/10.1101/2024.03.06.24303800v2" target="_blank">View our publication here</a>.
            </p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.header("Import trial data using clinicalTrials.gov identifier (NCT ID) [Optional]")
    
    st.markdown(
        """
        If you have a ClinicalTrials.gov identifier (NCT ID), you can import trial data directly. 
        This will pre-fill the form below. You can then review and edit the imported data before running PlaNet. 
        If you don't have an NCT ID or prefer to enter data manually, you can skip this step.
        """
    )

    # Example NCT ID Buttons
    col1, col2 = st.columns(2)
    with col1:
        if st.button("Example 1 (NCT01586975)"):  # Replace with your actual NCT ID
            st.session_state.nct_id = "NCT01586975"
    with col2:
        if st.button("Example 2 (NCT05828836)"):  # Replace with another NCT ID
            st.session_state.nct_id = "NCT05828836"

    col1, col2 = st.columns([3, 1])
    with col1:
        nct_id = st.text_input(
            "Enter NCT ID",
            placeholder="e.g., NCT01586975",
            key="nct_id_input",
            value=st.session_state.get('nct_id', '')
        )
    with col2:
        fetch_button = st.button("Import Trial Details", use_container_width=True)

    if fetch_button and nct_id:
        with st.spinner("Fetching trial details..."):
            try:
                trial_data = fetch_trial_details(nct_id)
                st.session_state.trial_data = trial_data
                st.success("Trial details fetched successfully! You can now review and edit the data below.")
            except Exception as e:
                st.error(f"Error fetching trial details: {str(e)}")
    
    # Section for Manual Data Entry or Editing Imported Data
    st.header("Enter or edit trial details")
    st.markdown(
        """
        You can manually enter trial details or edit the data imported from ClinicalTrials.gov. 
        Please fill in the following fields.
        """
    )
    
    with st.form("trial_form"):
        # Use fetched data if available, otherwise empty/default values
        data = st.session_state.get('trial_data', fetch_trial_details('NCT01586975'))
        
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
            data_secondary_outcomes = data.get('secondary_outcome') or []
            num_secondary = st.number_input("Number of Secondary Outcomes", min_value=0,  # Changed to 0
                                      value=len(data_secondary_outcomes))  # Also adjust initial value
            
            secondary_outcomes = []
            for i in range(int(num_secondary)):
                existing_outcome = data_secondary_outcomes[i] if i < len(data_secondary_outcomes) else {}
                
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

        confirm_button = st.form_submit_button("Comfirm Trial Details")

    # Confirmation Step with Validation
    if confirm_button:
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

        if validate_trial_data(trial_data):  # Perform validation here
            st.session_state.confirmed = True
            st.session_state.trial_data = trial_data  # Store validated data
            st.success("Trial details confirmed! Please enter your email and run PlaNet.")
        else:
            st.session_state.confirmed = False 

    # Email Input and Run PlaNet Button
    if st.session_state.get('confirmed', False):
        recipient_email = st.text_input("Recipient Email", placeholder="Enter your email address")

        if st.button("Run PlaNet"):
            if not recipient_email:
                st.warning("Please enter a recipient email address.")
            elif not is_valid_email(recipient_email):
                st.error("Invalid email address. Please enter a valid email.")
            else:
                request_id = str(uuid.uuid4())

                data = {
                    "trial_data": st.session_state.trial_data,
                    "email": recipient_email
                }

                with gcs_conn.open(f'planet-stanford/{request_id}.json', 'w') as f:
                    json.dump(data, f)

                if send_confirmation_email(recipient_email, request_id):
                    st.success(
                        f"""
                        Request saved successfully! Your Request ID is: {request_id}. Please keep this for your records. 
                        You can view your request at https://planet-stanford-klfwgz3hta-ue.a.run.app/lookup?id={request_id}. 
                        You should get an email with the results link in 72 hours.
                        """
                    )
                    
main()