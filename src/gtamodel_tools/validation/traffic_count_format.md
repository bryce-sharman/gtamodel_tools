# Traffic count validation

## Description

Traffic count data are available from the different regions. This code
provides the following tools:
1. Tools to read traffic counts provided by different jurisdictions into 
   the database format that will be used by the rest of the validation tools.
2. Tools to link the traffic counts to network links.
3. Tools to validate assignment volumes against count data, by screenline
   or by producing scatterplots. 

## Traffic count sources:

Tools are provided to read traffic counts from the following data sources. It is
envisioned that more data count sources can be included at a later date.
- City of Toronto Midblock Vehicle Speed, Volume and Classification Counts: 
  available on the [City of Toronto OpenData website](
    https://open.toronto.ca/dataset/traffic-volumes-midblock-vehicle-speed-volume-and-classification-counts/)
- Cordon Count Program: available through iDRS


## Processed Mid-block Traffic Count Data Format

### Station table

|   Field Name  | Field Type | Description |
| ------------- | ---------- | ----------- |
| source        | text(4)    | Count source (see below for possible codes) |
| station_id    | text(10)    | Unique ID describing count station |
| direction     | text(2)    | Cartesian direction |
| description   | Unicode    | Text description of location
| longitude     | Float      | Longitude coordinates of count station, EPSG:4326 |
| latitude      | Float      | Latitude coordinates of count station, EPSG:4326 |
| geometry      | shapely.LineString | Centreline of the road link on which count station is located, , EPSG:4326 |

The combination of `source`, `station_id` and `direction` form a unique key to the station. 


### Count table

|    Field Name   | Field Type | Description |
| --------------- | ---------- | ----------- |
| source          | text(12)   | Unique id of traffic count record, see below for details |
| station_id      | text(10)   | Count station id, links to stations table, see below for details |
| direction       | str(2)     | one of 'NB', 'EB', 'SB' or 'WB' |
| date            | str        | Count date -- Set to Jan 1st of the year for cordon counts |
| vtot_amper      | float(4)   | 
| vtot_ampkhr     | float(4)   | 
| vtot_mdper      | float(4)   | 
| vtot_mdpkhr     | float(4)   | 
| vtot_pmper      | float(4)   | 
| vtot_pmpkhr     | float(4)   | 
| vtot_evper      | float(4)   | 
| vtot_evpkhr     | float(4)   | 
| vtot_onper      | float(4)   | 
| vtot_onpkhr     | float(4)   | 
| vtot_weekday    | float(4)   | 
| vtot_weeken'    | float(4)   | 
| vcar_amper      | float(4)   | 
| vcar_ampkhr     | float(4)   | 
| vcar_mdper      | float(4)   | 
| vcar_mdpkhr     | float(4)   | 
| vcar_pmper      | float(4)   | 
| vcar_pmpkhr     | float(4)   | 
| vcar_evper      | float(4)   | 
| vcar_evpkhr     | float(4)   | 
| vcar_onper      | float(4)   | 
| vcar_onpkhr     | float(4)   | 
| vcar_weekday    | float(4)   | 
| vcar_weekend    | float(4)   | 
| vbus_amper      | float(4)   | 
| vbus_ampkhr     | float(4)   | 
| vbus_mdper      | float(4)   | 
| vbus_mdpkhr     | float(4)   | 
| vbus_pmper      | float(4)   | 
| vbus_pmpkhr     | float(4)   | 
| vbus_evper      | float(4)   | 
| vbus_evpkhr     | float(4)   | 
| vbus_onper      | float(4)   | 
| vbus_onpkhr     | float(4)   | 
| vbus_weekday    | float(4)   | 
| vbus_weekend    | float(4)   | 
| vtrk_amper      | float(4)   | 
| vtrk_ampkhr     | float(4)   | 
| vtrk_mdper      | float(4)   | 
| vtrk_mdpkhr     | float(4)   | 
| vtrk_pmper      | float(4)   | 
| vtrk_pmpkhr     | float(4)   | 
| vtrk_evper      | float(4)   | 
| vtrk_evpkhr     | float(4)   | 
| vtrk_onper      | float(4)   | 
| vtrk_onpkhr     | float(4)   | 
| vtrk_weekday    | float(4)   | 
| vtrk_weekend    | float(4)   | 
| vtot_max15min   | float(4)   | Maximum observed 15-minute count volume. Primarily used to assess road capacities. |


The combination of `source`, `station_id`, `direction` and `date` form a 
unique key to the station. 

Using floats for all counts as they include NaNs.
### Vehicle Types

### Data Sources

Cordon count data: The 4 digit year is appended to the back of cordon counts
- CCDR: Durham
- CCHL: Halton Region
- CCHM: Hamilton Region 
- CCPL: Peel Region
- CCTO: Toronto
- CCYK: York Region

Other data sources:
- TMBK: Toronto Midblock vcounts


### Count IDs

- Cordon count:
    - Region: see [Data Sources](#data-sources)
    - year: 4 digit number with the count year
    - Integer count
- City of Toronto Midblock Vehicle Speed, Volume and Classification Counts
  - It appears that the City of Toronto uses a unique 'counter id' in their
    data (confirm this), hence the count ID is just TMBK + the City of Toronto
    counter id.