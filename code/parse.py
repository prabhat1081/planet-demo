
import requests 

def get_clinical_trial_data(nctid):
    # Base URL of the ClinicalTrials.gov API with the specified version
    base_url = "https://clinicaltrials.gov/api/v2/studies"

    # Construct the full URL for the API request using .format() method
    request_url = "{}/{}".format(base_url, nctid)

    try:
        # Make the GET request to the API
        response = requests.get(request_url)

        # Check if the request was successful
        if response.status_code == 200:
            # Parse the JSON response
            trial_data = response.json()
            return trial_data
        else:
            # If the request was not successful, return the status code and error message
            return {"error": "Failed to fetch data. Status code: {}, Message: {}".format(response.status_code,
                                                                                         response.text)}

    except Exception as e:
        return {"error": str(e)}


def parse(nctid: str):
    trial_data = get_clinical_trial_data(nctid)

    if "error" in trial_data:
        raise RuntimeError("Error fetching data: {}".format(trial_data['error']))

    attributes = {
        "nct_id": "protocolSection.identificationModule.nctId",
        "arm_group": "protocolSection.armsInterventionsModule.armGroups",
        "intervention": "protocolSection.armsInterventionsModule.interventions",
        "condition": "protocolSection.conditionsModule.conditions",
        "intervention_mesh_terms": "derivedSection.conditionBrowseModule.meshes",
        "event_groups": "resultsSection.adverseEventsModule.eventGroups",
        "primary_outcome": "protocolSection.outcomesModule.primaryOutcomes",
        "secondary_outcome": "protocolSection.outcomesModule.secondaryOutcomes",
        "eligibility_criteria": "protocolSection.eligibilityModule.eligibilityCriteria",
        'brief_summary': 'protocolSection.descriptionModule.briefSummary',
        'phase': 'protocolSection.designModule.phases',
        'enrollment': 'protocolSection.designModule.enrollmentInfo',
        'gender_sex': 'protocolSection.eligibilityModule.sex',
        'minimum_age': 'protocolSection.eligibilityModule.minimumAge',
        'maximum_age': 'protocolSection.eligibilityModule.maximumAge'
    }

    parsed_trial = {}
    for attribute, path in attributes.items():
        val = trial_data
        for component in path.split("."):
            if component not in val:
                val = None
                break
            val = val[component]
        parsed_trial[attribute] = val

    if parsed_trial['arm_group'] is None:
        raise ValueError("The trial must have atleast 1 arm.")

    for arm_group in parsed_trial['arm_group']:
        arm_group['arm_group_label'] = arm_group.pop('label')

    for intervention in parsed_trial['intervention']:
        intervention['intervention_type'] = intervention.pop('type').title()
        intervention['intervention_name'] = intervention.pop('name')
        if 'otherNames' in intervention:
            intervention['other_name'] = intervention.pop('otherNames')
        intervention['arm_group_label'] = intervention.pop('armGroupLabels')

    parsed_trial['clinical_results'] = {
        "reported_events": {
            "group_list": {"group": parsed_trial.pop('event_groups')}
        }
    } if parsed_trial.get('event_groups') is not None else {}
    return parsed_trial

