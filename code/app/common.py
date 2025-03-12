import streamlit as st


from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To
from google.cloud import secretmanager

try:
    # Initialize Secret Manager client
    client = secretmanager.SecretManagerServiceClient()
except:
    st.info("Secret agent not available")

SITE_URL = 'https://planet-stanford-klfwgz3hta-ue.a.run.app'

def layout_trial_data(trial_data):
    """Displays trial data in a structured format."""

    if trial_data is None:
        return

    st.subheader("Basic Information")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(f"**NCT ID:** {trial_data.get('nct_id', 'N/A')}")
        st.write(f"**Gender:** {trial_data.get('gender_sex', 'N/A')}")
    with col2:
        st.write(f"**Min Age:** {trial_data.get('minimum_age', 'N/A')}")
        st.write(f"**Phase:** {', '.join(trial_data.get('phase', []) or 'N/A')}")
    with col3:
        st.write(f"**Max Age:** {trial_data.get('maximum_age', 'N/A')}")
        st.write(f"**Enrollment:** {trial_data.get('enrollment', {}).get('count', 'N/A')}")

    st.subheader("Conditions")
    for condition in trial_data.get('condition', []):
        st.markdown(f"* {condition}")  # Use markdown for better formatting

    st.subheader("Arm Groups")
    for i, arm in enumerate(trial_data.get('arm_group', []) or []):  # Handle empty arm_group
        st.markdown(f"**Arm {i+1}**")
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Type:** {arm.get('type', 'N/A')}")
            st.write(f"**Label:** {arm.get('arm_group_label', 'N/A')}")
        with col2:
            st.write(f"**Interventions:** {', '.join(arm.get('interventionNames', []) or 'N/A')}")

    st.subheader("Interventions")
    for intervention in trial_data.get('intervention', []) or []: # Handle empty intervention
        st.markdown(f"**{intervention.get('intervention_name', 'N/A')}**") # Use markdown for name
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Type:** {intervention.get('intervention_type', 'N/A')}")
        with col2:
            st.write(f"**Description:** {intervention.get('description', 'N/A')}")
        st.write(f"**Arm Group Label:** {', '.join(intervention.get('arm_group_label', []) or 'N/A')}") #Handle missing arm_group_label

    st.subheader("Primary Outcome")
    for outcome in trial_data.get('primary_outcome', []) or []:  # Handle empty primary_outcome
        st.write(f"**Measure:** {outcome.get('measure', 'N/A')}")
        st.write(f"**Time Frame:** {outcome.get('timeFrame', 'N/A')}")

    st.subheader("Secondary Outcome")
    for outcome in trial_data.get('secondary_outcome', []) or []:  # Handle empty secondary_outcome
        st.write(f"**Measure:** {outcome.get('measure', 'N/A')}")
        st.write(f"**Time Frame:** {outcome.get('timeFrame', 'N/A')}")

    st.subheader("Eligibility Criteria")
    eligibility = trial_data.get('eligibility_criteria', 'N/A')
    st.write(eligibility.replace('\n', '<br>'), unsafe_allow_html=True) # Format newlines as <br>


def access_secret_version(secret_name):
    """Access the payload for the given secret version."""

    name = f"projects/premium-state-449406-n8/secrets/{secret_name}/versions/latest" # Replace with your project ID
    response = client.access_secret_version(name=name)
    return response.payload.data.decode("UTF-8")


SENDER_EMAIL = 'prabhat.agarwal@cs.stanford.edu'

 # Get from Secret Manager
SENDGRID_API_KEY = access_secret_version("sendgrid-api-key")

def send_email(recipient: str, subject: str, body: str) -> bool:
    try:
        message = Mail(
            from_email=Email(email=SENDER_EMAIL, name='PlaNet Team'),  # Your verified SendGrid sender
            to_emails=recipient,
            subject=subject,
            html_content=body
        )
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        response = sg.send(message)
        if response.status_code == 202:
            st.success(f"A confirmation email has been sent to {recipient}. Kindly check your inbox for this message. " 
                       "If it's not there, please check your spam or junk folder. "
                       "Should you require further assistance, please contact us at prabhat.agarwal@cs.stanford.edu")
            our_emails = [
                To('mbrbic@epfl.ch', 'Maria Brbic'),
                To('myasu@cs.stanford.edu', 'Michi Yasunaga'),
                To('prabhat.agarwal@cs.stanford.edu', 'Prabhat Agarwal')
            ]
            message = Mail(
                from_email=Email(email=SENDER_EMAIL, name='PlaNet Team'),  # Your verified SendGrid sender
                to_emails=our_emails,
                subject=subject,
                html_content=body
            )
            sg.send(message)
            return True
        else: 
            st.error(f"Error sending email: {response.body.decode('utf-8')}")
            return False
    except Exception as e:
        st.error(f"Error sending email: {e}")
        return False
