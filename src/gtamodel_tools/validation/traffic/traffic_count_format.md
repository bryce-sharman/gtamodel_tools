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
| source        | text(8)   | Count source |
| station_id    | text(10)   | Unique ID describing count station, see below for details
| direction     | text(2)    | Cartesian direction |
| description   | text(50)   | Text description of location
| longitude     | Float      | Longitude coordinates of count station, EPSG:4326
| latitude      | Float      | Latitude coordinates of count station, EPSG:4326
| geometry      | shapely.LineString | Centreline of the road link on which count station is located, , EPSG:4326

 
### Count table

|    Field Name     |      Field Type   | Description |
| ----------------- | ----------------- | ----------- |
| count_id          | text(12)          | Unique id of traffic count record, see below for details
| 
| station_id        | text(10)          | Count station id, links to stations table, see below for details
| direction         | str(2)            | one of 'NB', 'EB', 'SB' or 'WB'
| date              | datetime.date     | Count date -- Set to Jan 1st of the year for cordon counts
| time_start        | datetime.time     | Start time of count interval (inclusive)
| time_end          | datetime.time     | End time of count interval (exclusive)
| vol_passenger     | int               | Counted volume of light (passenger) vehicles            
| vol_buses         | int               | Counted volume of buses            
| vol_straighttruck | int               | Counted volume of straight trucks            
| vol_singletrailer | int               | Counted volume of trucks with a single trailer
| vol_multitrailer  | int               | Counted volume of trucks with multiple trailers
| vol_truck         | int               | Counted volume of all trucks
| vol_heavy         | int               | Counted volume of heavy vehicles (trucks + buses)
| vol_total         | int               | Counted volume of all vehicles

### Vehicle Types

**FWHA classes of vehicle types:**
- vol_passenger: fwha1(motorbike) + fwha2(cars) + fhwa3(pickups)
- vol_buses: fwha4(buses)
- vol_straighttruck: fwha5 + fwha6 + fwha7
- vol_singletrailer: fwha8 + fwha9 + fwha10
- vol_multitrailer: fwha11 + fwha12 + fwha13

**Aggregate vehicle classes:**
- vol_truck: vol_straight_truck + vol_single_trailer + vol_single_trailer
- vol_heavy: vol_truck + vol_buses (or all - vol_passenger)
- vol_total: all vehicles (vol_passenger + vol_heavy)


### Data Sources

Cordon count data: The 4 digit year is appended to the back of cordon counts
- CCDR: Durham
- CCHL: Halton Region
- CCHM: Hamilton Region 
- CCPL: Peel Region
- CCTO: Toronto
- CCYK: York Region

Other data sources:
- TOCL: Toronto Midblock vehicle class-specific counts

### Station IDs

To ensure uniqueness, station IDS are defined as follows:
- Cordon count:
    - Cordon count station (in region), without the direction label
- City of Toronto Midblock Vehicle Speed, Volume and Classification Counts

### Count IDs

- Cordon count:
    - Region: see [Data Sources](#data-sources)
    - year: 4 digit number with the count year
    - Integer count
- City of Toronto Midblock Vehicle Speed, Volume and Classification Counts
  - It appears that the City of Toronto uses a unique 'counter id' in their
    data (confirm this), hence the count ID is just TMBK + the City of Toronto
    counter id.