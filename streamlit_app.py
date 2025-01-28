
import streamlit as st

def main():
    st.title("Clinical Study Input Form")
    
    # Add a description
    st.write("Please enter the details for your clinical study below:")
    
    # Create form to collect all inputs at once
    with st.form("study_form"):
        # Drug input
        drug_name = st.text_input(
            "Drug Name",
            placeholder="Enter the drug name"
        )
        
        # Disease input
        disease = st.text_area(
            "Disease/Condition",
            placeholder="Enter the disease or condition being studied"
        )
        
        # Inclusion criteria
        inclusion_criteria = st.text_area(
            "Inclusion Criteria",
            placeholder="Enter inclusion criteria (one per line)",
            help="List the criteria that participants must meet to be included in the study"
        )
        
        # Exclusion criteria
        exclusion_criteria = st.text_area(
            "Exclusion Criteria",
            placeholder="Enter exclusion criteria (one per line)",
            help="List the criteria that would exclude participants from the study"
        )
        
        # Submit button
        submitted = st.form_submit_button("Submit")
        
        if submitted:
            # Display the collected information
            st.success("Form submitted successfully!")
            
            st.subheader("Study Details:")
            st.write(f"**Drug:** {drug_name}")
            st.write(f"**Disease/Condition:** {disease}")
            
            st.subheader("Inclusion Criteria:")
            # Split the criteria into bullet points if multiple lines were entered
            for criterion in inclusion_criteria.split('\n'):
                if criterion.strip():
                    st.write(f"• {criterion.strip()}")
            
            st.subheader("Exclusion Criteria:")
            for criterion in exclusion_criteria.split('\n'):
                if criterion.strip():
                    st.write(f"• {criterion.strip()}")
            
            # Add option to download as text file
            combined_text = f"""Clinical Study Details
            
Drug: {drug_name}
Disease/Condition: {disease}

Inclusion Criteria:
{inclusion_criteria}

Exclusion Criteria:
{exclusion_criteria}
"""
            st.download_button(
                label="Download Study Details",
                data=combined_text,
                file_name="study_details.txt",
                mime="text/plain"
            )

if __name__ == "__main__":
    main()