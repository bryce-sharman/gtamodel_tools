Readme for initial commit.

How to create the python environment.
```

conda create --name tmgacc python=3.11
conda install --name tmgacc --channel conda-forge jupyter-lab bokeh geopandas matplotlib numba numexpr numpy openmatrix openpyxl pandas pyarrow pydata-sphinx-theme pytest scipy xlrd  
```

Much of the code in this package was graciously provided by WSP Canada to allow other users to better use and take advantage of GTAModel outputs. 



Package structure:

gtamodel_tools:
-**calibration**:
    -synthetic_population_calibration: ...
-**common**:
-**enums**: Constants GTAModel
-**io**: 
-**microsim**:
-**network**:
-**network_results**:







