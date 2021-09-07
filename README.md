# Visualization Tool

This repository consists of scripts that help generate data for the charts that can be plugged into the Influenzanet platform or supporting visualization platforms.

This document is structured into sections based on the different functionalities supported

## 1. Generate Country Specific Map - Covid Incidence & Participation Rates.

This script allows you to generate the data for the map chart present in the results page. This involves the executions of two scripts, first to generate region information for each participant in the system (i.e. get the region from their intake responses), and the second to generate the chart data json to be plugged into the participant-webapp.

**Note**: This section does not interact with the live platform, but instead generates files to be added to the platform.

### Step 1: Generate Participant Region information

Create a folder within resources (central-resource-management/country/resources) called **participant_region** that contains the following:
1. Configuration file called convert.yaml with the following contents  
    ```
    userIdColumn: <column_name_containing_user_id_in_intake_responses>
    postalCodeColumn: <column_name_containing_postal_code_in_intake_responses>
    countryCode: <your_country_code>
    ```
2. intake_responses.csv : CSV file containing the intake responses from the platform
3. lookup_nuts.csv: CSV file containing the NUTS code for every postal code. This is used to map postal code to a unique NUTS code. See central-resource-management/italy/resources-it/participant_region/lookup_nuts.csv for reference.
4. region-data.json: JSON file containing a list of regions in your country, and the NUTS code for each of the regions. See central-resource-management/italy/resources-it/participant_region/region-data.json for reference.

To generate the JSON containing the regions of each participant, run the following command:
```
python3 create_participant_region_json.py --configuration_file_path <path_to_convert.yaml> --intake_responses_csv_path <path_to_intake_response_csv> --nuts_lookup_csv_path <path_to_nuts_lookup_csv> --nuts_to_region_json <path_to_nuts_to_region_json>
```

This generates a json called participant_region.json which is needed for step 2.

### Step 2: Generate data for the Map chart

Create a folder called charts/maps/0 in your resources folder. The index 0 is used to accomodate multiple charts if needed. In this folder which we call chart data folder, ensure that the following files exist:
1. **map-schema.yaml**: Yaml that defines how the chart is to be created. Including info about the legend, color schemes, titles, as well as the fields in the weekly responses used to generate the data.
2. **participant_region.json**: This is the json generated in the Step 1 containing the regions for each of the participants.
3. **region-data.json**: This is a json containing the list of all regions in your country, along with the population counts for each of them.
4. **weekly_responses.csv**: This is the CSV downloaded from the live platform containing participant responses for the weekly survey.

For the map schema in particular, it contains several fields that you need to configure: 
    
    languages:
      - 'en'
    countryCode: IT
    sliderConfiguration:
      startDate: 02-11-2020 # labels for the slider start from this date
      endDate: 23-05-2021 # labels for the slider end at this date 
      hideTicks: false # Remove markers on the slider axis
      period: weekly # Calculate labels from start date on a weekly basis upto the end date
    covidIncidenceChart: #Contains configurations for the incidence chart
      name:
          en: "COVID19-like complaints per 1000 participants" #Name of the chart
      title:
        en: "COVID19-like complaints per 1000 participants" #Title of the chart
      colorScale:
        hoverStrokeColor: "#FD4" # Outline of regions when hovered over them
        colors: 
          - "#FDEDEC"
          - "#FADBD8"  # Different color shades to be used
          - "#F5B7B1"  # in the chart
          - "#F1948A"
          - "#EC7063"
          - "#CB4335"
      legend:
        show: true
        title:
          en: "COVID19-like complaints per 1000 participants"
        position:     # Position where the legend shows up
          x: "left"   # left | right | top | bottom
          y: "bottom"
      data:
        # Column Id's for relevant symtoms in Weekly Response csv
        symptomFields:
          cough: Q1_6
          fever: Q1_1
          breath: Q1_7
          smell: Q1_23
          taste: Q1_21
        truthValues:
          checked: t
          unchecked: f
    participantChart: # CHART INFO for the participant chart
      name:
        en: "Participants per 100000 inhabitants"
      title:
        en: "Number of Participants per 100000 inhabitants per region"
      colorScale:
        hoverStrokeColor: "#FD4"
        colors:
          - "#FDEDEC"
          - "#FADBD8"
          - "#F5B7B1"
          - "#F1948A"
          - "#EC7063"
          - "#CB4335"
      legend:
        show: true
        title:
          en: "participants per 100000 inhabitants"
        position:
          x: "left"
          y: "bottom"
      data:
        # Column ID, and format of the time when individual responses in weekly surveys were submitted
        timeInfo:
          columnName: timestamp
          timeFormat: "%Y-%m-%d %H:%M:%S.%f%z"
        participantId:
          columnName: global_id
Take care to configure these correctly before running the following command to generate the chart files:

```
python3 create_covid_incidence_participation_chart.py --chart_data_folder <path_to_the folder_containing_configuration_files> --weekly_responses_csv_path <path_to_downloaded_weekly_responses>
```

This generates chart files for each language supported. These need to be then plugged into the public/assets/data folder in the participant-webapp to be used in the front-end.