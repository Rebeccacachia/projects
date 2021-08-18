from os import getenv
from pathlib import Path

import prefect
from prefect.engine import results
from prefect.engine import serializers
from prefect.tasks.jupyter import ExecuteNotebook

import functions
from globals import BASE_DIR
from globals import DATA_DIR
from serializers import GeoPandasSerializer


def check_if_s3_keys_are_defined() -> None:
    message = f"""

        Please create a .env file
        
        In this directory: {BASE_DIR.resolve()}

        With the following contents:
        
        AWS_ACCESS_KEY_ID=YOUR_KEY
        AWS_SECRET_ACCESS_KEY=YOUR_SECRET_KEY
    """
    assert getenv("AWS_ACCESS_KEY_ID") is not None, message
    assert getenv("AWS_SECRET_ACCESS_KEY") is not None, message


def get_json_result(data_dir: Path) -> results.LocalResult:
    return results.LocalResult(
        dir=data_dir,
        serializer=serializers.JSONSerializer(),
    )


def get_parquet_result(data_dir: Path) -> results.LocalResult:
    return results.LocalResult(
        dir=data_dir,
        serializer=serializers.PandasSerializer("parquet"),
    )


def get_geoparquet_result(data_dir: Path) -> results.LocalResult:
    return results.LocalResult(
        dir=data_dir,
        serializer=GeoPandasSerializer("parquet"),
    )


load_valuation_office = prefect.task(
    functions.read_parquet,
    target="raw_valuation_office.parquet",
    checkpoint=True,
    result=get_parquet_result(DATA_DIR / "external"),
    name="Load Dublin Valuation Office",
)

load_bers = prefect.task(
    functions.read_parquet,
    target="small_area_bers.parquet",
    checkpoint=True,
    result=get_parquet_result(DATA_DIR / "external"),
    name="Load Dublin Small Area BERs",
)

load_benchmark_uses = prefect.task(
    functions.read_benchmark_uses,
    target="benchmark_uses.json",
    checkpoint=True,
    result=get_json_result(DATA_DIR / "external"),
    name="Load Valuation Office Benchmark Uses",
)

load_benchmarks = prefect.task(
    functions.read_excel,
    target="benchmarks.parquet",
    checkpoint=True,
    result=get_parquet_result(DATA_DIR / "external"),
    name="Load Energy Benchmarks",
)

load_small_area_boundaries = prefect.task(
    functions.read_geoparquet,
    target="small_area_boundaries.parquet",
    checkpoint=True,
    result=get_geoparquet_result(DATA_DIR / "external"),
    name="Load Dublin Small Area Boundaries",
)

load_local_authority_boundaries = prefect.task(
    functions.read_zipped_shp,
    target="local_authority_boundaries.parquet",
    checkpoint=True,
    result=get_geoparquet_result(DATA_DIR / "external"),
    name="Load Dublin Local Authority Boundaries",
)

link_small_areas_to_local_authorities = prefect.task(
    functions.link_small_areas_to_local_authorities,
    name="Link Each Small Areas to their Corresponding Local Authority",
)

extract_non_residential_emissions = prefect.task(
    functions.extract_non_residential_emissions,
    name="Use Energy Benchmarks on Valuation Office Floor Areas to Estimate Emissions",
)

link_valuation_office_to_small_areas = prefect.task(
    functions.link_valuation_office_to_small_areas,
    target="valuation_office_small_areas.parquet",
    checkpoint=True,
    result=get_geoparquet_result(DATA_DIR / "interim"),
    name="Link Valuation Office to Small Area Boundaries",
)

drop_small_areas_not_in_boundaries = prefect.task(
    functions.drop_small_areas_not_in_boundaries, name="Drop Invalid Small Areas"
)

extract_residential_emissions = prefect.task(
    functions.extract_residential_emissions,
    name="Extract DEAP Residential Emissions",
)

amalgamate_emissions_to_small_areas = prefect.task(
    functions.amalgamate_emissions_to_small_areas,
    target="dublin_small_area_demand_mwh_per_y.parquet",
    checkpoint=True,
    result=get_parquet_result(DATA_DIR / "processed"),
    name="Amalgamate Emissions to Small Areas",
)

link_emissions_to_boundaries = prefect.task(
    functions.link_emissions_to_boundaries,
    name="Link Emissions to Boundaries for Mapping",
)

save_demand_map = prefect.task(
    functions.save_demand_map,
    name="Save Small Area Heat Demand Map",
)

convert_plotting_script_to_ipynb = prefect.task(
    functions.convert_file_to_ipynb,
    name="Convert Heat Demand Density Map Script to ipynb",
)

execute_plot_ipynb = ExecuteNotebook()