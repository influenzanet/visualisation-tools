import os
import json
import argparse
from utils import read_yaml
import base64
from datetime import datetime
import pandas as pd
from datetime import datetime, timedelta

def lookup_region(postal_code, nuts_lookup, nuts_to_region, country):
    searched_zip = nuts_lookup[(nuts_lookup["zip_code"] == postal_code) & (nuts_lookup["country"] == country)]
    return find_regions_from_code(nuts_to_region, searched_zip.iloc[0]["nuts_code"]) if searched_zip["nuts_code"].any() else ""

def find_regions_from_code(nuts_to_region, nuts_code):
    filtered_regions = nuts_to_region[nuts_to_region["nuts2"].str.contains(nuts_code)]
    return filtered_regions.iloc[0]["name"] if filtered_regions["name"].any() else ""


if __name__ == "__main__":
    parser = argparse.ArgumentParser()  
    parser.add_argument(
        "--configuration_file_path", help="Complete file path of the configurations to create the json", default=os.path.join('resources', 'participant_region', 'convert.yaml'))
    parser.add_argument(
        "--intake_responses_csv_path", help="Complete file path of the downloaded intake responses", default=os.path.join('resources', 'participant_region', 'intake_responses.csv'))
    parser.add_argument(
        "--nuts_lookup_csv_path", help="Complete file path of the csv to match postal code to nuts code", default=os.path.join('resources', 'participant_region', 'lookup_nuts.csv'))
    parser.add_argument(
        "--nuts_to_region_json", help="Complete file path of the json that matches nuts code to regions", default=os.path.join('resources', 'charts', 'maps', '0', 'region-data.json'))

    args = parser.parse_args()

    configuration = read_yaml(args.configuration_file_path)

    intake_responses = pd.read_csv(args.intake_responses_csv_path, dtype=str)
    nuts_lookup = pd.read_csv(args.nuts_lookup_csv_path)
    nuts_to_region = pd.read_json(args.nuts_to_region_json)

    try:
        participant_region_json = {}
        id_column = configuration['userIdColumn']
        postal_column = configuration['postalCodeColumn']
        for i, u in intake_responses.iterrows():
            if u[id_column] not in participant_region_json or participant_region_json[u[id_column]] == "":
                participant_region_json[u[id_column]] = lookup_region(u[postal_column], nuts_lookup, nuts_to_region, configuration["countryCode"])

        output_file = "participant_per_region.json"
        with open(output_file, 'w') as f:
            json.dump(participant_region_json, f)
    except Exception as e:
        print("Error: " + str(e))
