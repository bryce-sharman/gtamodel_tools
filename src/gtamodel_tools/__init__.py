""" High-level enumerations that apply regardless of GTA model version """
import gtamodel_tools.calibration
import gtamodel_tools.common
import gtamodel_tools.enums
import gtamodel_tools.io
import gtamodel_tools.network_results

__version__ = "0.0.1"

from enum import Enum

class ModelVersion(Enum):
    GTAModelv4_0 = 0
    GTAModelv4_1 = 1
    GTAModelv4_2 = 2
