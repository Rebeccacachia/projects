from typing import Any

import numpy as np
import pandas as pd


def concatenate_dublin_postal_districts_and_county_dublin(
    upstream: Any, product: Any
) -> None:
    county = pd.read_csv(
        upstream["download_county_residential_networked_gas_consumption"], index_col=0
    )
    postal_district = pd.read_csv(
        upstream[
            "download_dublin_postal_district_residential_networked_gas_consumption"
        ],
        index_col=0,
    )
    dublin = pd.concat([county.loc[["Dublin County"], :], postal_district])
    dublin.to_csv(product)


def amalgamate_synthetic_bers_to_postcode_gas(upstream: Any, product: Any) -> None:
    bers = pd.read_parquet(upstream["download_synthetic_bers"])
    gas_bers = bers.query("main_sh_boiler_fuel == 'Mains Gas'")
    gas_consumption = (
        gas_bers["main_sh_demand"]
        + np.where(
            gas_bers["main_hw_boiler_fuel"] == "Mains Gas",
            gas_bers["main_hw_demand"],
            0,
        )
        + np.where(
            gas_bers["suppl_sh_boiler_fuel"] == "Mains Gas",
            gas_bers["suppl_sh_demand"],
            0,
        )
    )
    postcode_gas_consumption = (
        pd.concat([gas_bers["countyname"], gas_consumption], axis=1)
        .groupby("countyname")
        .sum()
        .squeeze()
        .divide(1e6)
        .round()
        .rename("ber_gas_consumption")
    )
    postcode_gas_consumption.to_csv(product)


def adapt_ber_postcode_names_to_same_format_as_cso_gas(
    upstream: Any, product: Any
) -> None:
    ber_gas = pd.read_csv(
        upstream["amalgamate_synthetic_bers_to_postcode_gas"], index_col=0
    )
    ber_gas_standardised = pd.concat(
        [
            pd.Series(ber_gas.index)
            .replace({"CO. DUBLIN": "Dublin County"})
            .str.title()
            .str.replace(
                r"^(Dublin )(\dW?)$",
                lambda m: m.group(1) + "0" + m.group(2),
                regex=True,
            ),
            ber_gas.reset_index(drop=True),
        ],
        axis=1,
    ).set_index("countyname")
    ber_gas_standardised.to_csv(product)