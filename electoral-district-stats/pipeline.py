from dotenv import load_dotenv

load_dotenv(".prefect")
from prefect import Flow

import tasks
from globals import DATA_DIR
from globals import HERE

URLS = {
    "commercial": "s3://codema-dev/valuation_office_dublin_april_2021.parquet",
    "residential": "s3://codema-dev/bers_dublin_june_2021.parquet",
    "public_sector": "s3://codema-dev/monitoring_and_reporting_dublin_21_1_20.parquet",
    "small_area_boundaries": "s3://codema-dev/dublin_small_area_boundaries_in_routing_keys.gpkg",
}


with Flow("Amalgamate Buildings to Electoral Districts") as flow:
    create_folder_structure = tasks.create_folder_structure(DATA_DIR)
    commercial = tasks.load_commercial(URLS["commercial"])
    raw_public_sector = tasks.load_public_sector(URLS["public_sector"])
    residential = tasks.load_residential(URLS["residential"])
    small_area_boundaries = tasks.load_small_area_boundaries(
        URLS["small_area_boundaries"]
    )

    public_sector = tasks.convert_to_geodataframe(
        raw_public_sector,
        x="longitude",
        y="latitude",
        from_crs="EPSG:4326",
        to_crs="EPSG:2157",
    )
    small_areas_to_electoral_districts = tasks.extract_columns(
        small_area_boundaries, columns=["small_area", "cso_ed_id"]
    )
    commercial_with_eds = tasks.merge(
        commercial, small_areas_to_electoral_districts, on="small_area"
    )
    residential_with_eds = tasks.merge(
        residential, small_areas_to_electoral_districts, on="small_area"
    )

    public_sector_with_eds = tasks.sjoin(
        public_sector, small_area_boundaries, op="within"
    )

    # Manually specify missing links
    commercial.set_upstream(create_folder_structure)
    public_sector.set_upstream(create_folder_structure)
    residential.set_upstream(create_folder_structure)
    small_area_boundaries.set_upstream(create_folder_structure)


state = flow.run()
flow.visualize(flow_state=state, filename=HERE / "flow", format="png")
