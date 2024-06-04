from importlib.resources import files
import pandas.testing as tm

import tmg_tdm_tools.synthetic_population.synthetic_population as sp
import tmg_tdm_tools


def test_same_pop_v0_vs_v_1_2():
    """ Test v4.0 synthetic population matches that read using v4.1/v4.2.
    
    The test data has the same persons and households files, only differing 
    with version headers. Test that the imported populations are identical.

    """

    root_path = files(__package__)
    synthpop_root_path = root_path / "test_data/synthetic_population"
    v0_root_path = synthpop_root_path / "gtamodelv4_0"
    v1_2_root_path = synthpop_root_path / "gtamodelv4_1_2"
    sp_v0 = sp.SyntheticPopulation(
            tmg_tdm_tools.ModelVersion.GTAModelv4_0, 
            v0_root_path / "households.csv", 
            v0_root_path / "persons.csv"
        )
    
    sp_v1_2 = sp.SyntheticPopulation(
        tmg_tdm_tools.ModelVersion.GTAModelv4_0, 
        v1_2_root_path / "households.csv", 
        v1_2_root_path / "persons.csv"
    )
    tm.assert_frame_equal(sp_v0.households, sp_v1_2.households)
    tm.assert_frame_equal(sp_v0.persons, sp_v1_2.persons)
