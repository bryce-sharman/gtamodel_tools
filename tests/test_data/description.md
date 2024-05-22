# Test data description 

The test data consists of a three-zone system (with two station zones), 
designed as follows:
- Zone 1: (primarily suburban)
    - PD: 1, PG Group 2
    - 40 households
    - dwelling type: 
        30 ground, 8 apartment, 2 unknown
    - 126 persons (highest population)    
        primarily ground dwelling (30 house, 8 townhouse, 2 apartment)
    - higher auto ownership: (see table below)
    - higher income: (see table below)
    - employment:  30 total, primarily service and professional
    - Nearby GO Rail station: zone 4


- Zone 2: (primarily urban)
    - PD: 2, , PG Group 1
    - 40 households
    - 85 persons (lowest population)
    - primarily apartment dwellings
        5 house, 26 apartment, 6 townhouse, 3 unknown
    - lower auto owndership: (see table below)
    - lower income: (see table below)
    - employment 90 total:
    - mix including all NAICS
    - Nearby GO, urban and LRT station: zone 5

- Zone 3: (mixed) 
    - PD: defined as 3 in the ZoneSystem file, switched to 2 in the PD_map file
    - PD Group 1
    - 40 households
    - 105 personse: (middle)
    - mixed dwelling types
        14 house, 12 apartment, 10 townhouse, 4 unknown
    - mixed auto ownership (see table below)
    - mixed income: (see table below)
    - employment: 60 total
    - mix including all NAICS

    




## Auto ownership table

| Zone |  0  |  1  |  2  |  3  |  4  |  5  |
| ---  | --- | --- | --- | --- | --- | --- |
|  1   |   3 |  13 | 18  |  3  |  2  | 1   |
|  2   |  20 |  15 |  5  |  0  |  0  | 0   |
|  3   |  12 |  14 |  9  |  2  |  1  |  2  |

## Income table

| Zone |  1  |  2  |  3  |  4  |  5  |  6  |  7  | 
| ---  | --- | --- | --- | --- | --- | --- | --- |
|  1   |   2 |  3  |  5  |  8  | 10  |  9  |  3  |
|  2   |   5 |  6  |  7  |  7  |  5  |  6  |  4  |
|  3   |   3 |  7  |  8  |  5  |  4  |  7  |  6  |


## Zone aggregrations
The following zone aggregations are created to test the spatial
aggregation operations:

- model_region: zones 1, 2, 3
- zone_aggregation: 
    1: 1, 2
    2: 3
- mapped_collection:
    1: 1, 2
    2: 3

## Person and household control files
The person control files was developed from the artificial synthetic population 
that was created for this test data by taking the "observed" people 
by age category, and then summing by PD and dwelling type. Proportions were
not distinguished by gender.






**Synthetic Population data**
Note that household and person weights are intentionally non-sensical
floats, aimed primarily for testing purposes. When comparing against
other inputs, non-weighted values should be used.