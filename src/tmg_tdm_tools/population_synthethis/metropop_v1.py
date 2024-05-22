import numpy as np
import pandas as pd
from pathlib import Path
from typing import Type

import tmg_tdm_tools.common.spatial_aggregator as sa
import tmg_tdm_tools.enums.population_synthesis.metropop_v1 as empv1

class MetroPopV1Inputs():
    """ Class to summarize MetroPopv1 inputs and help input file creation.
    
    This class is to help guide the users to create high-quality and 
    internally consistent input files used by MetroPop(v1) to create
    synthetic populations. 

    This help is primarily by provided summary tools, that a user can
    use to compare against external data sources or against other input files.
    This class also contains methods to help input file creation, especially
    for the households and persons files. 
    
    Attributes:
        self.zs: pandas.DataFrame 
            Zone system input from ZoneSystem.csv file.
        self.seeds: pandas.DataFrame 
            Seed data input from SeedData/SeedPopulation.csv.
        self.seed_pdgroups: pandas.Series 
            Planning District groups used to define IPU regions, 
            read in from SeedData/PDGroups.csv.
        self.scen_hhld_controls: pandas.DataFrame 
            Household control data, from Scenario HouseholdControls.csv file.
        self.scen_pers_controls: pandas.DataFrame
            Person control data, from Scenario PersonControls.csv file.
        self.scen_zone_attrs: pandas.DataFrame
            Scenario zone attribute population and employment data, from 
            Zone Attributes.csv file.

    """
    PD_COLUMN = 'PDfinal'
    ZONE_COLUMN = 'TAZ'
    
    def __init__(self):
        pass

    def read_input_files(
            self, 
            input_dir: Path | str, 
            scenario_dir: Path | str
        ) -> None:
        """ Reads all MetroPopv1 inputs, saving to the object instance.
        
        Args:
            input_dir: Path to MetroPop input directory
            scenario_dir: Path to MetroPop scenario directory
        
        """
        input_dir = Path(input_dir)
        scenario_dir = Path(scenario_dir)
        
        # Files in the root directory
        self.pd_map = pd.read_csv(
                input_dir / empv1.FN_PDMAP, 
                dtype=empv1.PDMAP_DTYPES, 
                usecols=empv1.PDMAP_DTYPES.keys(), 
                index_col=empv1.PDMAP_FROM
            )
        zs = pd.read_csv(
            input_dir / empv1.FN_ZS, 
            dtype=empv1.ZS_DTYPES, 
            usecols=empv1.ZS_DTYPES.keys(), 
            index_col=empv1.ZS_ZONEID
        )
        # Create zone planning district maps, 
        # Use the original map if blank
        zs = zs.merge(
            self.pd_map, 
            left_on=empv1.ZS_PD, 
            right_index=True, 
            how="left"
        )
        # There are likely PDs that are not mapped in self.PD_map file
        # Copy these over to the new zone system field
        fltr = pd.isna(zs[empv1.PDMAP_TO])
        zs.loc[fltr, empv1.PDMAP_TO] = zs.loc[fltr, empv1.ZS_PD]
        fltr = pd.isna(zs[empv1.PDMAP_TO])
        zs.loc[fltr, empv1.PDMAP_TO] = zs.loc[fltr, empv1.ZS_PD]
        zs = zs.rename({empv1.PDMAP_TO: self.PD_COLUMN}, axis=1)
        self.zs = zs.drop([empv1.ZS_PD], axis=1)
        self.zs.index.name = self.ZONE_COLUMN
        # Files in the Seed directory
        seed_dir = input_dir / empv1.DN_SEEDDATA
        self.seed_pdgroups = pd.read_csv(
            seed_dir / empv1.FN_PDGROUPS, 
            dtype=empv1.PDGR_DTYPES, 
            usecols=empv1.PDGR_DTYPES.keys(), 
            index_col=empv1.PDGR_INDEX
        )
        self.seeds = pd.read_csv(
            seed_dir / empv1.FN_SEEDS, 
            dtype=empv1.SD_DTYPES, 
            usecols=empv1.SD_DTYPES.keys(),
            index_col=[empv1.SD_HHLD_ID, empv1.SD_PERS_ID]
        )
        self.seeds = self.seeds.merge(
            self.seed_pdgroups, 
            how="inner", 
            left_on=empv1.SD_HHLD_HOMEPD, 
            right_index=True
        )

        # Files in the Scenario directory
        self.scen_hhld_controls = pd.read_csv(
            scenario_dir / empv1.FN_SCEN_HHLD_CNTRLS, 
            dtype=empv1.HHLDCNTRLS_DTYPES, 
            usecols=empv1.HHLDCNTRLS_DTYPES.keys()
        )
        self.scen_hhld_controls = self.scen_hhld_controls.merge(
            self.seed_pdgroups, 
            how="inner", 
            left_on=empv1.HHLDCNTRLS_PD, 
            right_index=True
        )
        self.scen_pers_controls = pd.read_csv(
            scenario_dir / empv1.FN_SCEN_PERS_CNTRLS, 
            dtype=empv1.PERSCNTRLS_DTYPES, 
            usecols=empv1.PERSCNTRLS_DTYPES.keys()
        )
        self.scen_pers_controls = self.scen_pers_controls.merge(
            self.seed_pdgroups, 
            how="inner", 
            left_on=empv1.PERSCNTRLS_PD, 
            right_index=True
        )
        self.scen_zone_attrs = pd.read_csv(
            scenario_dir / empv1.FN_SCEN_ZNATTRS, 
            dtype=empv1.ZA_DTYPES, 
            usecols=empv1.ZA_DTYPES.keys(), 
            index_col=empv1.ZA_ZONEID
        )

#region input directory
    def summarize_number_of_seeds_by_hhld_ipu_segment(self) -> pd.Series:
        """ Find number of household IPU seeds, by segment. 

        Note:
            MetroPop IPU household segments are as follows: 
            PD Group, dwelling type, household type

        Returns:
            pd.Series: Number of households by segment

        """
        # Prepare a full index for the household and person summaries
        idx_hhldtype = (np.sort(self.seeds[empv1.SD_HHLD_HHLDTYPE].unique()))
        idx_dwellingtype = np.sort(
            self.seeds[empv1.SD_HHLD_DWELLINGTYPE].unique())
        idx_pdgroups = np.sort(self.seeds[empv1.PDGR_PDGROUP].unique())
        idx_hhldsegments = pd.MultiIndex.from_product(
            [idx_hhldtype, idx_dwellingtype, idx_pdgroups], 
            names=['HhldType', 'DwellingType', 'PDGroup']
        )

        # For the households, keep only one entry for each household.
        hhld_df = self.seeds.groupby(empv1.SD_HHLD_ID)[
            [empv1.SD_HHLD_HHLDTYPE, 
             empv1.SD_HHLD_DWELLINGTYPE, 
             empv1.PDGR_PDGROUP]
            ].first()
        hhld_df['one'] = 1.0
        hhld_pt = hhld_df.groupby(
            [empv1.SD_HHLD_HHLDTYPE, 
             empv1.SD_HHLD_DWELLINGTYPE, 
             empv1.PDGR_PDGROUP
            ], sort=True, observed=False)['one'].sum()
        final = hhld_pt.reindex(idx_hhldsegments, axis=0, fill_value=np.NaN)
        return final

    def calculate_expected_hhld_sizes_by_dtype_from_seeds(
            self, 
            min_entries: int
        ) -> pd.DataFrame:
        """ Find expected adults, seniors & children by IPU segment from seeds.
         
        IPU segmentation is by household type, dwelling type and PD Group .

        If number of (unexpanded) seed households for any combination of 
        household type, dwelling type and PD Group is below min_entries, then 
        calculation will be recomputed only by household type.

        This function was created as many housing types are specified as a 
        minimum number of people, e.g. 2+. Calculating representative sizes for 
        these types is key when summarizing inputs from the households input 
        file.

        Args:
        min_entries: integer
            minimum number of (unexpanded) households by household type, 
            dwelling type and PD group to use full segmentation when 
            calculating household sizes.

        Returns:
        pandas.Dataframe 
            rows are the combination of household type and dwelling type
            columns are number of adults (18-64), seniors (65+) 
            and children (0-17), respectively.

        """
        df_hhlds = self.seeds.groupby(empv1.SD_HHLD_ID)[[
            empv1.SD_HHLD_HHLDTYPE, 
            empv1.SD_HHLD_DWELLINGTYPE, 
            empv1.PDGR_PDGROUP, 
            empv1.SD_HHLD_EXPFACTOR
        ]].first()

        # Define adults, seniors and children
        df = self.seeds.copy()
        df['is_adult'] = 0
        df['is_senior'] = 0
        df['is_child'] = 0
        df.loc[(df[empv1.SD_PERS_AGE] >= 18) & 
               (df[empv1.SD_PERS_AGE] <= 64), 'is_adult'] = 1
        df.loc[df[empv1.SD_PERS_AGE] >= 65, 'is_senior'] = 1
        df.loc[df[empv1.SD_PERS_AGE] <= 17, 'is_child'] = 1
        df['exp_adult'] = df[empv1.SD_HHLD_EXPFACTOR] * df['is_adult']
        df['exp_senior'] = df[empv1.SD_HHLD_EXPFACTOR] * df['is_senior']
        df['exp_child'] = df[empv1.SD_HHLD_EXPFACTOR] * df['is_child']

        # Calculate the number of people per cell by age segment
        numerator = df.groupby([
            empv1.SD_HHLD_HHLDTYPE, 
            empv1.SD_HHLD_DWELLINGTYPE, 
            empv1.PDGR_PDGROUP
        ], observed=False)[['exp_adult', 'exp_senior', 'exp_child']].sum()
        numerator = numerator.rename(
            {'exp_adult': 'adult', 
             'exp_senior': 'senior', 
             'exp_child': 'child'
            }, axis=1)
        denominator = df_hhlds.groupby([
            empv1.SD_HHLD_HHLDTYPE, 
            empv1.SD_HHLD_DWELLINGTYPE, 
            empv1.PDGR_PDGROUP
        ], observed=False)[empv1.SD_HHLD_EXPFACTOR].sum()
        avg_cell = numerator.divide(denominator, axis=0)

        # Overwrite where insufficient seeds, only segmenting by household type
        # Recalculate mean household sizes by age category, this time only segmenting by household type
        numerator = df.groupby(
            [empv1.SD_HHLD_HHLDTYPE], observed=False)[[
                'exp_adult', 'exp_senior', 'exp_child']].sum()
        numerator = numerator.rename(
            {'exp_adult': 'adult', 
             'exp_senior': 'senior', 
             'exp_child': 'child'
            }, axis=1)
        denominator = df_hhlds.groupby(
            [empv1.SD_HHLD_HHLDTYPE], 
            observed=False)[empv1.SD_HHLD_EXPFACTOR].sum()
        avg_cell_hhtypeonly = numerator.divide(denominator, axis=0)

        # Overwrite where filter is true
        n_hhldseeds_cell = self.summarize_number_of_seeds_by_hhld_ipu_segment()
        min_hhlds_per_cell = n_hhldseeds_cell.unstack(
            [-2, -1], fill_value=0).min(axis=1)
        fltr = min_hhlds_per_cell.loc[(min_hhlds_per_cell < min_entries)].index
        print(f"The following household types have insufficient records for "
              f"full segmentation {fltr}. "
              f"Only segmenting these using household type")
        
        # We need to overwrite the values in avg_cell when insufficient records 
        # are unavailable. This is a bit tricky as we are writing from a 
        # dataframe with a single-level index to one with a multiple-level 
        # index. We can use the reindex method for this, specifying the level 
        # argument to define broadcasting.
        full_index = n_hhldseeds_cell.index
        avg_cell_hhtypeonly2 = avg_cell_hhtypeonly.reindex(
            full_index, axis=0, level=0)
        avg_cell.loc[fltr] = avg_cell_hhtypeonly2.loc[fltr]
        return avg_cell
#endregion

#region Scenario directory
    def summarize_forecast_hhldcontrols(
            self, 
            add_dwellingtype_segmentation: bool, 
            seed_segmentation_min_entries: int
        ) -> pd.DataFrame:
        """ Summarize children, adults and seniors from household controls.

        This can be used to test consistency of the age pyramid defined by the 
        households and the persons control files.

        Note that the forecast population is set in the zone attributes file, 
        hence the totals coming out of the household and person control files 
        are not important, only the proportions.
        
        Args:
        add_dwellingtype_segmentation: bool
            If True, segment by planning destrict and dwelling type, otherwise 
            segment by planning district only.
        seed_segmentation_min_entries: int
            minimum number of (unexpanded) households by household type, 
            dwelling type and PD group to use full segmentation when calculating 
            household sizes.

        Returns:
        pandas.DataFrame 
            Contains proportion of children, adults and seniors by PD and 
            dwelling type:
            index: planning districts, dwelling type
            columns: 'child', 'adult', 'senior'
        """
        # Using the seed file, we can calculate the expected number of children, adults and seniors 
        # by housetype, dwelling type and PDGroup. Merge into the HHLD control file
        exp_hhld_sizes = self.calculate_expected_hhld_sizes_by_dtype_from_seeds(seed_segmentation_min_entries)
        df = self.scen_hhld_controls.merge(exp_hhld_sizes, left_on=[empv1.HHLDCNTRLS_HHLDTYPE, empv1.HHLDCNTRLS_DWELLINGTYPE, empv1.PDGR_PDGROUP], right_index=True)
        df['exp_adult'] = df[empv1.HHLDCNTRLS_FREQ] * df['adult']
        df['exp_child'] = df[empv1.HHLDCNTRLS_FREQ] * df['child']
        df['exp_senior'] = df[empv1.HHLDCNTRLS_FREQ] * df['senior']
        if add_dwellingtype_segmentation:
            pt = df.groupby([empv1.HHLDCNTRLS_PD, empv1.HHLDCNTRLS_DWELLINGTYPE], observed=False)[['exp_child', 'exp_adult', 'exp_senior']].sum()
        else:
            pt = df.groupby(empv1.HHLDCNTRLS_PD, observed=False)[['exp_child', 'exp_adult', 'exp_senior']].sum()
        pt['total'] = pt.sum(axis=1)
        pt['child'] = pt['exp_child'] / pt['total']
        pt['adult'] = pt['exp_adult'] / pt['total']
        pt['senior'] = pt['exp_senior'] / pt['total']
        return pt[['child', 'adult', 'senior']].copy()
    
    def summarize_forecast_perscontrols(
            self, 
            add_dwellingtype_segmentation: bool
        ) -> pd.DataFrame:
        """ Summarize children, adults and seniors from person controls file.
    
        This can be used to test age pyramid consistency between households 
        and the persons control files.
    
        Note that the forecast population is set in the zone attributes file, 
        hence it is not the totals coming out of the household and person 
        control files that are important, but the proportions.
    
        Args:
        add_dwellingtype_segmentation: bool
            If True, segment by planning destrict and dwelling type, otherwise 
            segment by planning district only.

        Returns:
        pandas.DataFrame 
            Contains proportion of children, adults and seniors by PD and 
            dwelling type:
            index: planning districts, dwelling type
            columns: 'child', 'adult', 'senior'
            
        """
        df = self.scen_pers_controls.copy()
        df['age_cat'] = df['AgeGroup'].map(empv1.IPU_AGE_SEGMENTS)
        df['is_child'] = 0
        df['is_adult'] = 0
        df['is_senior'] = 0
        df.loc[df['age_cat'] == 'child', 'is_child']= 1
        df.loc[df['age_cat'] == 'adult', 'is_adult'] = 1
        df.loc[df['age_cat'] == 'senior', 'is_senior'] = 1
        df['exp_adult'] = df[empv1.PERSCNTRLS_FREQ] * df['is_adult']
        df['exp_child'] = df[empv1.PERSCNTRLS_FREQ] * df['is_child']
        df['exp_senior'] = df[empv1.PERSCNTRLS_FREQ] * df['is_senior']
        if add_dwellingtype_segmentation:
            pt = df.groupby(
                [empv1.PERSCNTRLS_PD, empv1.PERSCNTRLS_DWELLILNGTYPE], 
                observed=False)[['exp_child', 'exp_adult', 'exp_senior']].sum()
        else:
            pt = df.groupby(
                empv1.PERSCNTRLS_PD, 
                observed=False)[['exp_child', 'exp_adult', 'exp_senior']].sum()
        pt['total'] = pt.sum(axis=1)
        pt['child'] = pt['exp_child'] / pt['total']
        pt['adult'] = pt['exp_adult'] / pt['total']
        pt['senior'] = pt['exp_senior'] / pt['total']
        return pt[['child', 'adult', 'senior']].copy()
    
    def summarize_forecast_zone_attributes_population(
            self, 
            home_sa: Type[sa.SpatialAggregator],
            aggregation_base: str,  
        ) -> pd.Series:
        """ Summarizes population from the Scenario zone attributes input file.
        
        Args:
        home_sa: Subclass of sa.SpatialAggregator
            Spatial aggregator. 
        aggregation_base: str, must be either 'taz' or 'pd'
            States if the aggregation is to be performed on the TAZ column or
            on the planning district, which is defined in the input directory.

        Returns: 
        pandas Series 
            Population, by spatial aggregation region

        """
        if home_sa is None:
            raise RuntimeError("'home_sa' must be defined.")
        if aggregation_base  == 'taz':
            df = self.scen_zone_attrs.copy()
            zone_col = empv1.ZA_ZONEID
        elif aggregation_base == 'pd':
            df = self.scen_zone_attrs.merge(
                self.zs[[self.PD_COLUMN]], 
                how="left", 
                left_index=True, 
                right_index=True
            )
            zone_col = self.PD_COLUMN
        else:
            raise RuntimeError("'aggregation_base' must be 'taz' or 'pd'.")

        return sa.summarize_table_with_spatial_aggregation(
            df=df, 
            values='population', 
            geom_id=zone_col, 
            spatial_aggregations=home_sa
        )

    def summarize_forecast_zone_attributes_employment(
            self, 
            home_sa: Type[sa.SpatialAggregator],
            aggregation_base: str,  
        ) -> pd.Series | pd.DataFrame:
        """ Summarizes employment from the Scenario zone attributes input file.

        Separate summaries (totals) are returned for each NAICS employment
        code in the zone attributes file.
        
        Args:
        home_sa: Subclass of sa.SpatialAggregator
            Spatial aggregator. 
        aggregation_base: str, must be either 'taz' or 'pd'
            States if the aggregation is to be performed on the TAZ column or
            on the planning district, which is defined in the input directory.
            
        Returns: 
        pandas.DataFrame
            Employment segmented by regions as the index and NAICS categories as 
            the columns.

        """
        if home_sa is None:
            raise RuntimeError("'home_sa' must be defined.")
        if aggregation_base  == 'taz':
            df = self.scen_zone_attrs.copy()
            zone_col = empv1.ZA_ZONEID
        elif aggregation_base == 'pd':
            df = self.scen_zone_attrs.merge(
                self.zs[[self.PD_COLUMN]], 
                how="left", 
                left_index=True, 
                right_index=True
            )
            zone_col = self.PD_COLUMN
        else:
            raise RuntimeError("'aggregation_base' must be 'taz' or 'pd'.")
        return sa.summarize_table_with_spatial_aggregation(
            df=df, 
            values=empv1.ZA_EMP_COLS, 
            geom_id=zone_col, 
            spatial_aggregations=home_sa
        )

#endregion