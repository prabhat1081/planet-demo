import argparse

import requests
import os
import pickle
import math
import numpy as np

from data_parsers.external_tools.medex import medex_input
from data_parsers.external_tools import medex
import tempfile
import json
import subprocess
import shlex
from parse import parse

from data_parsers import DiseaseExtract
from data_parsers import CriteriaOutputParser
from data_parsers import DrugMatcher, get_intervention_drug_ids
from data_parsers import OutcomeMeasureExtract
from data_parsers import UMLSConceptSearcher

from data_parsers import UMLSTFIDFMatcher
from data_parsers.umls_utils import UMLSUtils

from knowledge_graph import KnowledgeGraphBuilder
from knowledge_graph.kg import UnionFind
from knowledge_graph.build_graph import TrialGraphBuilder
from knowledge_graph.node_features import TrialAttributeFeatures

DATA_DIR = "/data/parsing_package/data"
BASE_DIR = "/data/parsing_package"

def set_data_dir(path):
    DATA_DIR = f"{path}/parsing_package/data"

def set_base_dir(path):
    BASE_DIR = f"/{path}/parsing_package"

def run_medex_and_parse_output(parsed_trial):
    result = {}

    classpath = f'{BASE_DIR}/resources/medex/Medex_UIMA_1.3.8/bin:resources/medex/Medex_UIMA_1.3.8/lib/*'
    args_template = "java -Xmx1024m -cp {0} org.apache.medex.Main -i {1} -o {2} -b n -f y -d y -t n"

    with tempfile.TemporaryDirectory() as basedir:
        # create medex input
        medex_input._generate_medex_inputs(parsed_trial, result)
        input_dir = os.path.join(basedir, 'inputs')
        os.makedirs(input_dir)
        with open(os.path.join(input_dir, 'medex_input.json'), 'w') as f:
            json.dump(result, f)

        # Run medex
        output_path = os.path.join(basedir, "outputs")
        os.makedirs(os.path.join(output_path, "data"))
        args = args_template.format(classpath, os.path.join(input_dir, 'medex_input.json'),
                                    os.path.join(output_path, "data"))
        print(args)
        # args = args_template
        try:
            subprocess.run(shlex.split(args), check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Medex execution failed with error: {e}")

        medex_output_parser = medex.MedexOutputParser(base_paths=[output_path])

        medex_output_parser.fill_medex_info(parsed_trial)

    return parsed_trial


def parse_eligiility_criteria(parsed_trial):
    args_template = f"java -Xmx4096m -jar /{BASE_DIR}/resources/criteria2query.jar  --input {0} --outputDir {1}"

    with tempfile.TemporaryDirectory() as basedir:
        # create input
        input_dir = os.path.join(basedir, 'inputs')
        os.makedirs(input_dir)
        with open(os.path.join(input_dir, 'crit_input.txt'), 'w') as f:
            f.write(parsed_trial['eligibility_criteria'])

        # Run crit2query
        output_path = os.path.join(basedir, "outputs")
        os.makedirs(os.path.join(output_path, "data"))
        args = args_template.format(os.path.join(input_dir, 'crit_input.txt'),
                                    os.path.join(output_path, "data"))
        print(args)
        # args = args_template
        try:
            subprocess.run(shlex.split(args), check=True)
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f"Crit2Query execution failed with error: {e}")

        parsed_trial['ec_umls'] = CriteriaOutputParser.parse_crit_output_from_file(
            os.path.join(output_path, "data", "output.json"))
    return parsed_trial


def extract_outcomes(parsed_trial):
    outcome_extractor = OutcomeMeasureExtract(
        f'{DATA_DIR}/outcome_data/clusters-outcome-measures.txt')

    outcome_extractor.load_phrase_models(f'{DATA_DIR}/outcome_data')
    outcome_extractor.populate_cids(parsed_trial)

    return parsed_trial


def population_extraction(umls_utils, parsed_trial):
    umls_concept_searcher = UMLSConceptSearcher(
        api_key='', version='2020AB', cache_dir=f'{DATA_DIR}/population_data/umls_search_cache')
    umls_concept_searcher.set_umls_search(False)

    criteria_all = parsed_trial['ec_umls']
    for category in criteria_all:
        for inclusion in criteria_all[category]:
            for criterion in criteria_all[category][inclusion]:
                criterion.map_concept(umls_concept_searcher)

    umls_utils.cuid2parents = {}
    criteria_all = parsed_trial['ec_umls']
    for category in criteria_all:
        for inclusion in criteria_all[category]:
            for criterion in criteria_all[category][inclusion]:
                if criterion.concept is not None:
                    criterion.parents = umls_utils.parents(criterion.concept['ui'])

    tfidf_matcher = UMLSTFIDFMatcher(umls_utils.cuid2concept, f'{DATA_DIR}/population_data', None)

    tfidf_matcher.populate_result_single(parsed_trial['ec_umls'])

    return parsed_trial


def _phase_feature_vec(phases):
    v = [0] * 5
    for phase in phases:
        if phase in ['EARLY_PHASE1', 'PHASE1']:
            v[1] = 1
        elif phase == 'N/A':
            v[0] = 1
        elif phase == 'PHASE2':
            v[2] = 1
        elif phase == 'PHASE3':
            v[3] = 1
        elif phase == 'PHASE4':
            v[4] = 1
        #         elif phase == 'Phase 1/Phase 2':
        #             v[1] = 1
        #             v[2] = 1
        #         elif phase == 'Phase 2/Phase 3':
        #             v[2] = 1
        #             v[3] = 1
        else:
            raise RuntimeError(f"Unknown phase: {phase}")
    return v


def _enrollment_feat(enrollment):
    is_anticipated = False
    if type(enrollment) == dict:
        if enrollment['type'] == 'ANTICIPATED':
            is_anticipated = True
        return [math.log(1 + enrollment['count']), int(is_anticipated)]
    if np.isnan(enrollment):
        return [0, 0]
    return [math.log(1 + enrollment), 0]


def _sex_vec(sex):
    if sex is None or type(sex) == float:
        return [0, 0, 0]
    sex_to_feats = {
        'ALL': [1, 0, 0],
        "MALE": [0, 1, 0],
        "FEMALE": [0, 0, 1]
    }
    return sex_to_feats[sex]


def extract_trial_features(extractor, trial_row):
    data = {}
    data['phase_vec'] = _phase_feature_vec(trial_row['phase'])
    data['enrollment_vec'] = _enrollment_feat(trial_row['enrollment'])
    data['gender_sex_vec'] = _sex_vec(trial_row['gender_sex'])
    data['minimum_age_vec'] = extractor._age_vec(trial_row['minimum_age'] or 0.0)
    data['maximum_age_vec'] = extractor._age_vec(trial_row['maximum_age'] or 0.0)

    def merge_vecs(row):
        feats = []
        for attribute in extractor.attributes:
            if attribute == 'phase':
                feats.extend(row['phase_vec'])
            elif attribute == 'enrollment':
                feats.extend(row['enrollment_vec'])
            elif attribute == 'gender':
                feats.extend(row['gender_sex_vec'])
            elif attribute == 'age':
                feats.extend(row['minimum_age_vec'])
                feats.extend(row['maximum_age_vec'])
            elif attribute == 'age_class':
                feats.extend(row['age_vec_2'])
            else:
                raise RuntimeError(f"Unknown attributes ({attribute}) for features")
        return np.array(feats)

    return merge_vecs(data)


def get_arm_text(row):
    arm2text = {}
    nct2text = {}
    summary = row['brief_summary']
    disease_text = ''
    for disease in row['condition']:
        disease_text += disease + " "
    outcome_text = ''
    if type(row['primary_outcome']) != float:
        for pom in row.get('primary_outcome', []):
            outcome_text += pom.get('measure', '') + " "
    criteria = row['eligibility_criteria']
    if type(criteria) == float:
        criteria = ''

    arm2intervention = {}
    for intervention in row['intervention']:
        intervention_text = intervention['intervention_name'] + ' '
        intervention_desc = intervention.get('description', '') + ' '
        arm_group_label = intervention.get('arm_group_label', ['default'])
        if not isinstance(arm_group_label, list):
            arm_group_label = ['default']
        for arm_label in arm_group_label:
            arm_label = arm_label.lower()
            arm2intervention[arm_label] = (intervention_text, intervention_desc)

    arms = row['arm_group']
    if not isinstance(arms, list):
        arms = [{'arm_group_label': 'default', 'arm_group_type': ''}]

    for idx, arm in enumerate(arms):
        arm_text = arm['arm_group_label'] + " " + arm.get('description', '')
        if arm['arm_group_label'].lower() in arm2intervention:
            intervention_text, intervention_desc = arm2intervention[arm['arm_group_label'].lower()]
        else:
            intervention_text, intervention_desc = '', ''
        all_text = " ".join(
            [intervention_text, disease_text, outcome_text, arm_text, summary, intervention_desc, criteria])
        arm2text[row['nct_id'], idx] = all_text
        nct2text[row['nct_id']] = [disease_text, outcome_text, summary, criteria]
    return arm2text, nct2text


def build_trial_arms(disease_matcher, drug_matcher, umls_utils, cuid2term, parsed_trial):
    entity2cid_path = f'{DATA_DIR}/kg_data/kg-entity2cid-31_7_21.pkl'
    with open(entity2cid_path, 'rb') as f:
        entity2cid = pickle.load(f)

    ext_basepath = f'{DATA_DIR}/kg_data/external_data'
    builder = KnowledgeGraphBuilder(disease_matcher.mesh_dis_data, drug_matcher.drug_data, ext_basepath,
                                    cuid2term, umls_utils, umls_graph_clip_threshold=10,
                                    build_ae=False)

    builder.build_external_networks()
    builder._mesh_children()

    parsed_trial['has_results'] = False

    trial_builder = TrialGraphBuilder(builder, parsed_trial)
    trial_builder.build(use_population=True)

    uf = UnionFind()
    cnt = 0
    for u, v, data in builder.biokg.graph.edges(data=True):
        if data['relation'] == 'KG-MERGE-SAME':
            cnt += 1
            uf.union(u, v)

    trial_attribute_featurizer = TrialAttributeFeatures(attributes=('age', 'gender', 'enrollment', 'phase'))
    trial_attribute_feats = extract_trial_features(trial_attribute_featurizer, parsed_trial)

    trial_data = []
    arm2text, _ = get_arm_text(parsed_trial)
    for arm_label, arm_idx in trial_builder.arm_labels.items():
        trial_arm_data = []
        for u, v, k, data in builder.biokg.graph.edges(nbunch=[trial_builder.arm_key(arm_idx)], data=True, keys=True):
            #         print(u, v, k, data['relation'], entity2cid[uf.find_parent(v)])
            trial_arm_data.append({
                'kg_id': entity2cid[uf.find_parent(v)],
                'relation': data['relation'],
                'key': k,
                'data': data
            })
        trial_data.append({
            'nct_id': parsed_trial['nct_id'],
            'arm_label': arm_label,
            'arm_idx': arm_idx,
            'trial_arm_edges': trial_arm_data,
            'arm_text': arm2text[parsed_trial['nct_id'], arm_idx],
            'trial_attribute_feats_vec': trial_attribute_feats
        })

    return trial_data

def load_cuid2term():
    basedir = f'{DATA_DIR}/population_data'
    filepath = os.path.join(basedir, "umls_graph_clipper_output.pkl")
    with open(filepath, "rb") as f:
        g_clipper_state = pickle.load(f)
        cuid2term = g_clipper_state['cuid2term']
    return cuid2term


def load_tools():
    drug_matcher = DrugMatcher(data_paths={
        'drug_data': f'{DATA_DIR}/drug_data/drugs_all_03_04_21.pkl',
        'pubchem_synonyms': f'{DATA_DIR}/drug_data/pubchem-drugbankid-synonyms.json',
        'rxnorm2drugbank-umls': f'{DATA_DIR}/drug_data/rxnorm2drugbank-umls.pkl',
        'RXNCONSO': f'{DATA_DIR}/drug_data/RXNCONSO.RRF'
    })
    disease_matcher = DiseaseExtract(data_dir=DATA_DIR, data_year=2021)
    umls_utils = UMLSUtils(f'{DATA_DIR}/population_data/umls-install/2020AB')
    umls_utils.load_relations()
    cuid2term = load_cuid2term()

    return drug_matcher, disease_matcher, umls_utils, cuid2term


def parse_trial(nct_id, state):
    drug_matcher, disease_matcher, umls_utils, cuid2term = state

    trial = parse(nct_id)
    trial = run_medex_and_parse_output(trial)
    trial = parse_eligiility_criteria(trial)
    trial['mesh_ids'] = disease_matcher.get_disease_ids(trial)

    interventions = trial['intervention']
    for intervention in interventions:
        get_intervention_drug_ids(drug_matcher, intervention, trial)

    trial = extract_outcomes(trial)
    trial = population_extraction(umls_utils, trial)

    trial_data = build_trial_arms(disease_matcher, drug_matcher, umls_utils, cuid2term, trial)

    return trial_data


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Process clinical trial data.')
    parser.add_argument('nctid', type=str, help='NCT ID of the clinical trial', default='NCT02370680')
    args = parser.parse_args()

    state = load_tools()

    print(parse_trial(args.nctid, state))
