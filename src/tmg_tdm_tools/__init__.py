""" High-level enumerations that apply regardless of GTA model version """
import tmg_tdm_tools.calibration
import tmg_tdm_tools.common
import tmg_tdm_tools.enums
import tmg_tdm_tools.io
import tmg_tdm_tools.population_synthesis
import tmg_tdm_tools.synthetic_population
import tmg_tdm_tools.validation

from enum import Enum

class ModelVersion(Enum):
    GTAModelv4_0 = 0
    GTAModelv4_1_2 = 1
