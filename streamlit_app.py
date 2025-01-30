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

from st_files_connection import FilesConnection


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
        
        # Submit button
        if st.form_submit_button("Save Trial Data"):
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
            
            # Success message
            st.success("Trial data saved successfully!")

            filename = generate_filename_from_dict(trial_data)

            with gcs_conn.open(f'planet-stanford/{filename}', 'w') as f:
                json.dump(trial_data, f)
            
            # Download button
            # st.download_button(
            #     label="Download Trial Data",
            #     data=json.dumps(trial_data, indent=2).encode('utf-8'),
            #     file_name=f"{trial_nct_id}_trial_data.json",
            #     mime="application/json"
            # )



if __name__ == "__main__":
    main()