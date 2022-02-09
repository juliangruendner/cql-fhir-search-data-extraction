import requests
import json
import base64
import uuid
import csv


def extract_subjects(subject_resp):
    pat_list = ""

    for entry in subject_resp['entry']:
        pat_list = f'{pat_list},{entry["item"]["reference"].split("/")[1]}'

    return pat_list[1:]

def get_next_link(link_elem):
    for elem in link_elem:
        if elem['relation'] == 'next':
            return elem['url']

    return None


def page_through_results_and_collect(resp):

    result_list = []
    next_link = get_next_link(resp.json()['link'])
    result_list = list(map(lambda entry: {"patient": entry['resource']['subject']['reference'].split('/')[1], "code": entry['resource']['code']['coding'][0]['code'], "value": entry['resource']['valueQuantity']['value']}, resp.json()['entry']))

    while next_link:

        resp = requests.get(next_link)
        result_list_temp = list(map(lambda entry: {"patient": entry['resource']['subject']['reference'].split('/')[1], "code": entry['resource']['code']['coding'][0]['code'], "value": entry['resource']['valueQuantity']['value']}, resp.json()['entry']))
        next_link = get_next_link(resp.json()['link'])
        result_list = result_list + result_list_temp

    return result_list


cql_input = '''
library Retrieve
using FHIR version '4.0.0'
include FHIRHelpers version '4.0.0'

codesystem loinc: 'http://loinc.org'
codesystem admingender: 'http://hl7.org/fhir/administrative-gender'

context Patient

define InInitialPopulation:
  exists from [Observation: Code '76689-9' from loinc] O
    where O.value.coding contains Code 'female' from admingender
'''


library_template = '''{
  "resourceType": "Library",
  "url": "urn:uuid:a2b9f4b4-5d5b-46bd-a9fd-35f024c852fa",
  "status": "active",
  "type" : {
    "coding" : [
      {
        "system": "http://terminology.hl7.org/CodeSystem/library-type",
        "code" : "logic-library"
      }
    ]
  },
  "content": [
    {
      "contentType": "text/cql",
      "data": "CmxpYnJhcnkgUmV0cmlldmUKdXNpbmcgRkhJUiB2ZXJzaW9uICc0LjAuMCcKaW5jbHVkZSBGSElSSGVscGVycyB2ZXJzaW9uICc0LjAuMCcKCmNvbnRleHQgUGF0aWVudAoKY29kZXN5c3RlbSBsb2luYzogJ2h0dHA6Ly9sb2luYy5vcmcnCmNvZGVzeXN0ZW0gYWRtaW5nZW5kZXI6ICdodHRwOi8vaGw3Lm9yZy9maGlyL2FkbWluaXN0cmF0aXZlLWdlbmRlcicKCmRlZmluZSBJbkluaXRpYWxQb3B1bGF0aW9uOgogIGV4aXN0cyhmcm9tIFtPYnNlcnZhdGlvbjogQ29kZSAnNzY2ODktOScgZnJvbSBsb2luY10gTwogICAgd2hlcmUgTy52YWx1ZS5jb2RpbmcgY29udGFpbnMgQ29kZSAnZmVtYWxlJyBmcm9tIGFkbWluZ2VuZGVyCg=="
    }
  ]
}'''


measure_template = '''{
  "resourceType": "Measure",
  "url": "urn:uuid:49f4c7de-3320-4208-8e60-ecc0d8824e08",
  "status": "active",
  "library": "urn:uuid:a2b9f4b4-5d5b-46bd-a9fd-35f024c852fa",
  "scoring": {
    "coding": [
      {
        "system": "http://terminology.hl7.org/CodeSystem/measure-scoring",
        "code": "cohort"
      }
    ]
  },
  "group": [
    {
      "population": [
        {
          "code": {
            "coding": [
              {
                "system": "http://terminology.hl7.org/CodeSystem/measure-population",
                "code": "initial-population"
              }
            ]
          },
          "criteria": {
            "language": "text/cql",
            "expression": "InInitialPopulation"
          }
        }
      ]
    }
  ]
}'''

measure_config_template = '{"resourceType": "Parameters", "parameter": [{"name": "periodStart", "value": "2000"}, {"name": "periodEnd", "value": "2030"}, {"name": "measure", "value": "urn:uuid:49f4c7de-3320-4208-8e60-ecc0d8824e08"}, {"name": "reportType", "value": "subject-list"}]}'

fhir_base_url = "http://localhost:8081/fhir"
cql_base64 = base64.b64encode(cql_input.encode('ascii'))

lib_uuid = f'urn:uuid:{str(uuid.uuid4())}'
measure_uuid = f'urn:uuid:{str(uuid.uuid4())}'

lib = json.loads(library_template)
lib['url'] = lib_uuid
lib['content'][0]['data'] = cql_base64.decode('ascii')

measure = json.loads(measure_template)
measure['url'] = measure_uuid
measure['library'] = lib_uuid

measure_config = json.loads(measure_config_template)
measure_config['parameter'][2]['value'] = measure_uuid


print("Creating Library Resource on fhir server...")
headers = {'Content-Type': "application/fhir+json"}
resp = requests.post(f'{fhir_base_url}/Library', data=json.dumps(lib), headers=headers)
print(resp)

print("Creating Measure Resource on fhir server...")
resp = requests.post(f'{fhir_base_url}/Measure', data=json.dumps(measure), headers=headers)
print(resp)

#resp = requests.get(f'{fhir_base_url}/Measure/$evaluate-measure?measure={measure_uuid}&periodStart=2000&periodEnd=2030')
#print(resp.json())

print("Evaluating Measure Resource on fhir server...")
resp = requests.post(f'{fhir_base_url}/Measure/$evaluate-measure', data=json.dumps(measure_config), headers=headers)
print(resp)

print("Reading subject list, which resulted from the evaluation of the Measure")
subject_list = resp.json()['group'][0]['population'][0]['subjectResults']['reference']
print("subject List is :", subject_list)

print("Extracting subjects from subject list...")
subjects = extract_subjects(requests.get(f'{fhir_base_url}/{subject_list}').json())
print("---- BEGIN SUBJECT LIST ----")
print(subjects)
print("---- END SUBJECT LIST ----")



headers = {'Content-Type': "application/x-www-form-urlencoded"}

print("Search for feature = weight (http://loinc.org|29463-7) > 10 for all patients and count them...")
payload = {'code': 'http://loinc.org|29463-7', 'value': 'gt10', '_summary': 'count'}
resp = requests.post(f'{fhir_base_url}/Observation/_search', data=payload)
print("Number of patients found:", resp.json()['total'])

print("Search for feature = weight (http://loinc.org|29463-7) > 10 for our previously selected patients and count them...")
payload = {'code': 'http://loinc.org|29463-7', 'value': 'gt10', 'subject': subjects, '_summary': 'count'}
resp = requests.post(f'{fhir_base_url}/Observation/_search', data=payload)
print("Number of patients found:", resp.json()['total'])

print("Search for feature = weight (http://loinc.org|29463-7) > 10 for our previously selected patients and print found resources (features)...")
payload = {'code': 'http://loinc.org|29463-7', 'value': 'gt10', 'subject': subjects}
resp = requests.post(f'{fhir_base_url}/Observation/_search', data=payload)

result_list = page_through_results_and_collect(resp)
print("------------------------ BEGIN RESULT LIST ------------------------")
print(json.dumps(result_list, indent=4, sort_keys=True))
print("------------------------ END RESULT LIST ------------------------")


keys = result_list[0].keys()

with open('data-extraction-result.csv', 'w', newline='') as output_file:
    dict_writer = csv.DictWriter(output_file, keys)
    dict_writer.writeheader()
    dict_writer.writerows(result_list)