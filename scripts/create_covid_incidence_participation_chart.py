import os
import json
import argparse
from utils import read_yaml
import base64
from datetime import datetime
import pandas as pd
from datetime import datetime, timedelta
import pytz
import copy

utc=pytz.UTC
regions_in_country = {}
participant_region_info = {}
map_schema, slider_schema, covid_incidence_schema, participation_schema = {}, {}, {}, {}

# Method to create the configuration for the slider that represents 
# which weeks data is currently displayed on the map chart 
def load_slider_conf():
    print("Creating configurations for the slider")
    return {
        "minLabel": slider_schema["startDate"],
        "maxLabel": slider_schema["endDate"],
        "labels": generate_labels(slider_schema["startDate"], slider_schema["endDate"], slider_schema["period"]),
        "hideTicks": slider_schema["hideTicks"] if slider_schema["hideTicks"] else False
    }

# Generate the series information for both the Reported covid chart and the participation chart
def generate_series(language, slider_configuration, metrics):
    series = []
    print("Calculating Covid Incidence and Participation Rates")
    chart_data = calculate_chart_data(metrics)
    incidence_rates_per_1000 = chart_data["incidenceRates"]
    participation_rates_per_100000 = chart_data["participationRates"]

    # Create fields for Covid Incidence chart 
    series.append(create_chart_fields(map_schema["covidIncidenceChart"], language, incidence_rates_per_1000))
    # Create fields for Participation Chart
    series.append(create_chart_fields(map_schema["participantChart"], language, participation_rates_per_100000))
    return series

# Create the major fields of each series in a map chart
def create_chart_fields(schema, language, data):
    return {
        "name": schema["name"][language],
        "title": schema["title"][language],
        "legend": create_chart_legend(schema["legend"], language),
        "colorScale": generate_color_scale(schema["colorScale"], data["min"], data["max"]),
        "data": data["value"]
    }

# Create the color palette used to display regions in the map chart.
def generate_color_scale(color_scale_schema, min_value, max_value):
    return {
        "min": min_value,
        "max": max_value,
        "hoverStrokeColor": color_scale_schema["hoverStrokeColor"] if "hoverStrokeColor" in color_scale_schema else "#FD4",
        "colors": color_scale_schema["colors"]
    }

# Method to take the evaluated metrics per week per region (covid count, and participation count), and use it 
# to calculate the regional_weekly_incidence and regional_weekly_participation.
#
# Returns a dict containing incidence rates and participation rates of every region per week as well as the min and max values.
def calculate_chart_data(metrics):
    # Calculate (reported_count_in_region / active_participants_in_region) * 1000 
    # Calculate (active_participants_in_region / population_in_region) * 100000
    rates_per_region, participants_per_region = [], []
    collective_rate, collective_participants = [], []

    # Iterate through each region
    for index, region in enumerate(regions_in_country):
        region_name = region["name"]
        region_incidence_data = {
            "name": region_name,
            "sequence": []
        }
        region_participation_data = copy.deepcopy(region_incidence_data)

        # For each region get calculate for every week.
        for current_week_data in metrics:
            weekly_metric = metrics[current_week_data]
            weekly_participants_in_region = weekly_metric["active_participants"][region_name] if region_name in weekly_metric["active_participants"] else 0
            weekly_covid_reports_in_region = weekly_metric["covid_symptoms"][region_name] if region_name in weekly_metric["covid_symptoms"] else 0

            regional_weekly_incidence = (weekly_covid_reports_in_region / weekly_participants_in_region) * 1000 if weekly_participants_in_region > 5 else 0.0
            #regional_weekly_participation = (weekly_participants_in_region / region["population"]) * 100000
            regional_weekly_participation = weekly_participants_in_region

            region_incidence_data["sequence"].append(regional_weekly_incidence)
            region_participation_data["sequence"].append(regional_weekly_participation)
            collective_rate.append(regional_weekly_incidence)
            collective_participants.append(regional_weekly_participation)
        
        # Aggregate results for all regions
        rates_per_region.append(region_incidence_data)
        participants_per_region.append(region_participation_data)
    return { 
        "incidenceRates": {"min": min(collective_rate), "max": max(collective_rate), "value": rates_per_region},
        "participationRates": {"min": min(collective_participants), "max": max(collective_participants), "value": participants_per_region}
    }

# Genrates the data to determine where the legend of the chart is displayed
def create_chart_legend(legend, language):
    return {
        "title": legend["title"][language],
        "show": legend["show"] if legend["show"] else True,
        "position": {
            "x": legend["position"]["x"] if legend["position"]["x"]  else "left",
            "y": legend["position"]["y"] if legend["position"]["y"]  else "top"
        }
    }

# Method to create labels for every week from the start date to the end date.
def generate_labels(start_date, end_date, period):
    labels = []
    date_start = datetime.strptime(start_date, "%d-%m-%Y")
    date_end = datetime.strptime(end_date, '%d-%m-%Y')
    one_week = timedelta(weeks = 1)
    one_day = timedelta(days = 1)
    if period == "weekly":
        current_label_end = date_start
        while(current_label_end + one_week < date_end):
            labels.append("" + current_label_end.strftime("%d-%m-%Y") + " - " + (current_label_end + one_week - one_day).strftime("%d-%m-%Y"))
            current_label_end = current_label_end + one_week
        labels.append("" + current_label_end.strftime("%d-%m-%Y") + " - " + date_end.strftime("%d-%m-%Y"))
    return labels

# Method to call evaluate metrics (covid count, active participants)
def calculate_response_metrics(weekly_responses, labels):
    participant_metadata = participation_schema["data"]
    covid_chart_metadata = covid_incidence_schema["data"]
    return evaluate_metrics(weekly_responses, labels, participant_metadata, covid_chart_metadata)

# Method to iterate through weekly responses, filter them according to weeks (defined by chart labels) and then calculate
# active participant count, and covid report count per region.
def evaluate_metrics(weekly_responses, labels, participant_data, covid_chart_metadata):
    metrics = {} # list of active participants and covid reports per week, per region.
    time_column_name = participant_data["timeInfo"]["columnName"]
    time_format = participant_data["timeInfo"]["timeFormat"]
    user_id_column_name = participant_data["participantId"]["columnName"]
    times = pd.to_datetime(weekly_responses[time_column_name], infer_datetime_format=True)
    # Label is the weekly stamp - i.e. 12-03-2021 - 19-03-2021
    for label in labels:
        print("Calculating metrics for time: " + label)
        split_label = label.split(" ")
        start = utc.localize(datetime.strptime(split_label[0], "%d-%m-%Y"))
        end = utc.localize(datetime.strptime(split_label[2], "%d-%m-%Y"))

        # Filter by week
        responses_by_label = weekly_responses[
           (end >= times) & (times >= start)
        ]

        # Remove duplicates and keep only latest response
        responses_by_label = responses_by_label.drop_duplicates(subset=[user_id_column_name], keep="last")
        current_week_participation = {}
        current_week_covid_reports = {}

        # Iterate through weekly response and update counts per region
        for i, u in responses_by_label.iterrows():
            region = get_region_by_user(u[user_id_column_name])
            current_week_participation = update_participation_count(region, current_week_participation)
            current_week_covid_reports = update_report_count(region, current_week_covid_reports, u, covid_chart_metadata["symptomFields"], covid_chart_metadata["truthValues"])
            
        metrics[label] = {"active_participants": current_week_participation, "covid_symptoms": current_week_covid_reports}
    return metrics

# Create a dict with key region and update the active participant count        
def update_participation_count(region, current_week_participation): 
    if region in current_week_participation:
        current_week_participation[region] += 1
    else:
        current_week_participation[region] = 1
    return current_week_participation

# Create a dict with key region and update the covid report count
def update_report_count(region, current_week_covid_reports, weekly_response, symtoms_to_check, truth_values):
    for key in symtoms_to_check:
        if weekly_response[symtoms_to_check[key]] is truth_values['checked']:
            if region in current_week_covid_reports:
                current_week_covid_reports[region] += 1
            else:
                current_week_covid_reports[region] = 1
            return current_week_covid_reports
    return current_week_covid_reports

# From the participant_Region json get region of participant by ID
def get_region_by_user(user_id):
    return participant_region_info[user_id] if participant_region_info[user_id] else "unknown"
    

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--chart_number", help="Index of the chart being configured", default='0')
    parser.add_argument(
        "--chart_data_folder", help="path to the folder containing map-schema and region data", default=os.path.join('resources', 'charts', 'maps', '0'))
    parser.add_argument(
        "--weekly_responses_csv_path", help="Complete file path of the downloaded weekly responses", default=os.path.join('resources', 'charts', 'maps', '0', 'weekly_responses.csv'))

    args = parser.parse_args()

    chart_data_folder = args.chart_data_folder

    print("Loading Required configuration files")
    # Main chart generation schema
    map_schema = read_yaml(
        os.path.join(chart_data_folder, 'map-schema.yaml'))
    # Weekly Responses from the platform
    weekly_responses = pd.read_csv(args.weekly_responses_csv_path, dtype=str)
    # JSON containing region info of participants
    participant_region_info = json.load(open(os.path.join(chart_data_folder, 'participant_region.json'), 'r', encoding='UTF-8'))
    # JSON containing regions of the country and it's population count
    regions_in_country = json.load(open(os.path.join(chart_data_folder, 'region-data.json'), 'r', encoding='UTF-8'))

    try:
        if not map_schema["languages"]: raise Exception("languages field missing in Map Schema") 
        languages = map_schema["languages"]

        slider_schema = map_schema["sliderConfiguration"]
        covid_incidence_schema = map_schema["covidIncidenceChart"]
        participation_schema = map_schema["participantChart"]   

        slider_configuration = load_slider_conf()

        # Calculate active participants, and count reported covid symptoms
        metrics = calculate_response_metrics(
            weekly_responses, slider_configuration["labels"])
        
        # Generate charts for each language
        for language in languages:
            chart = {}
            chart["slider"] = slider_configuration
            chart["series"] = generate_series(language, slider_configuration, metrics)
            output_file = "map_chart_" + datetime.now().strftime('%Y-%m-%d-%H-%M-%S') + "_" + language + ".json"

            print("===========================================================================================")
            print("CHART CREATED WITH NAME: " + output_file)
            print("To use this chart plug this file into the data section of the participant webapp and refer to it in a markdown");
            with open(os.path.join(output_file), 'w') as f:
                json.dump(chart, f)

    except Exception as e:
        print("Error: " + str(e))

