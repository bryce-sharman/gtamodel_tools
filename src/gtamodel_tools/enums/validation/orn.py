""" Enumerations for Ontario Road Network GeoDatabase. """
import numpy as np


GEOM_LAYERNAME = 'ORN_ROAD_NET_ELEMENT'
GEOM_ELEMID_COL = 'OGF_ID'
GEOM_LENGTH_COL = 'LENGTH'
GEOM_TRAFFICDIR_COL = 'DIRECTION_OF_TRAFFIC_FLOW'
GEOM_ELEMTYPE_COL = 'ROAD_ELEMENT_TYPE'
GEOM_TOLLRDIND_COL = 'TOLL_ROAD_IND'
GEOM_COL = 'geometry'
GEOM_USECOLS = [
    GEOM_ELEMID_COL, GEOM_LENGTH_COL, GEOM_TRAFFICDIR_COL, GEOM_ELEMTYPE_COL,
    GEOM_TOLLRDIND_COL, GEOM_COL
]

RDCLS_LAYERNAME = 'ORN_ROAD_CLASS'
RDCLS_INDEX_COL = 'EVENT_ID'
RDCLS_ELEMID_COL = 'ORN_ROAD_NET_ELEMENT_ID'
RDCLS_RDCLS_COL = 'ROAD_CLASS'
RDCLS_USECOLS = [
    RDCLS_INDEX_COL, RDCLS_ELEMID_COL, RDCLS_RDCLS_COL
]

CLASSES_FREEWAY = ['Expressway / Highway', 'Freeway', 'Ramp']
CLASSES_ARTERIAL = ['Arterial']
CLASSES_COLLECTOR = ['Collector']
CLASSES_LOCAL = ['Local / Street', 'Local / Strata', 'Local / Unknown', 'Service']
CLASSES_SERVICE = ['Alleyway / Laneway']
CLASSES_OTHER = ['Winter', 'Resource / Recreation']
CLASSES_TRANSIT = ['Rapid Transit']


JURDICTN_LAYERNAME = 'ORN_JURISDICTION'
JURDICTN_INDEX_COL = 'EVENT_ID'
JURDICTN_ELEMID_COL = 'ORN_ROAD_NET_ELEMENT_ID'
JURDICTN_STSIDE_COL = 'STREET_SIDE'
JURDICTN_JURDICTN_COL = 'JURISDICTION'
JURDICTN_AGNCY_COL = 'AGENCY_NAME'
JURDICTN_USECOLS = [
    JURDICTN_INDEX_COL, JURDICTN_ELEMID_COL, JURDICTN_STSIDE_COL,
    JURDICTN_JURDICTN_COL, JURDICTN_AGNCY_COL
]


JURISDICTIONS_GTHA = [
    # Toronto
    'City of Toronto',
    # Durham
    'City of Pickering',
    'Town of Ajax', 
    'Town of Whitby',
    'City of Oshawa',
    'Municipality of Clarington',
    'Township of Scugog',
    "Mississauga's of Scugog Island",
    'Township of Uxbridge',
    # York
    'Town of Georgina',
    'Chippewas of Georgina Island First Nation 33a',
    'Town of East Gwillimbury',
    'Town of Newmarket',
    'Town of Aurora', 
    'Township of King',
    'Town of Whitchurch-Stouffville', 
    'City of Richmond Hill',
    'City of Vaughan',
    'City of Markham',
    # Peel
    'City of Brampton',
    'City of Mississauga',
    'Town of Caledon',
    # Halton
    'Town of Milton',
    'Town of Oakville',
    'City of Burlington',
    'Town of Halton Hills', 
    # Hamilton
    'City of Hamilton'
]

JURISDICTIONS_GGH = JURISDICTIONS_GTHA + [
    # Kawartha Lakes
    'City of Kawartha Lakes',
    # Peterborough County
    'City of Peterborough',
    'Township of Douro-Dummer',
    'Township of Cavan Monaghan',
    'Township of Otonabee-South Monaghan',
    'Township of Selwyn',
    'Township of Asphodel-Norwood',
    'Curve Lake First Nation 35',
    'Hiawatha First Nation 36',
    # Simcoe
    'Town of Innisfil',
    'Town of Bradford West Gwillimbury',
    'Township of Essa',
    'Township of Adjala-Tosorontio',
    'Town of New Tecumseth',
    'Cfb Borden',
    'Township of Clearview',
    'City of Barrie',
    'Town of Collingwood',
    'Town of Wasaga Beach',
    'Township of Springwater',
    'Township of Tiny',
    'Township of Oro-Medonte',
    'Township of Severn',
    'Township of Ramara',
    'Township of Tay',
    'Christian Island 30', 
    'Christian Island 30a',
    'City of Orillia',
    'Mnjikaning First Nation 32',
    'Town of Penetanguishene',
    'Town of Midland',
    # Wellington County
    'Township of Guelph/Eramosa',
    'City of Guelph',
    'Township of Puslinch',
    'Township of Centre Wellington',
    'Town of Erin',
    'Township of Mapleton',
    'Township of Wellington North',
    # Dufferin County
    'Town of Orangeville',
    'Township of Mulmur',
    'Town of Mono',
    'Township of East Garafraxa',
    'Township of Melancthon',
    'Town of Grand Valley',
    'Town of Shelburne',
    'Township of Amaranth',
    # Region of Waterloo
    'City of Kitchener',
    'City of Waterloo',
    'City of Cambridge',
    'Township of Woolwich',
    'Township of Wellesley',
    'Township of North Dumfries',
    'Township of Wilmot',
    # Niagara      
    'City of St. Catharines',
    'City of Niagara Falls', 
    'Town of Niagara-On-The-Lake',
    'Town of Lincoln',
    'Town of Fort Erie',
    'Township of West Lincoln',
    'City of Thorold',
    'Town of Grimsby',
    'Township of Wainfleet',
    'Town of Pelham',
    'City of Welland',
    'City of Port Colborne',
    # Brant County
    'City of Brantford', 
    'County of Brant'
]

JURISDICTIONS_TTS_2022 = JURISDICTIONS_GGH + [
    # Grey County
    'Town of the Blue Mountains',
    'Municipality of West Grey',
    'Municipality of Grey Highlands',
    'Township of Georgian Bluffs',
    'Town of Hanover',
    'Township of Southgate',
    'City of Owen Sound',
    'Municipality of Meaford',
    'Township of Chatsworth',
    # Haldimand County
    'Haldimand County',
    'Six Nations 40'
]
