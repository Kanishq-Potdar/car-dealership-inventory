# SAMPLE catalogue — not real dealership listings

`sample_vehicles.csv` contains 60 fictional demonstration listings across Indian and international brands. Prices are illustrative **INR amounts**, not current quotations, on-road prices, valuations or availability claims. Years, conditions and stock counts are invented for development and demonstrations. A `new` sample indicates unused stock, not necessarily the latest model year.

Every row has a stable `sample_id`. The seed utility stores `sample-v1:<sample_id>` in the internal unique `vehicles.sample_key` column. It inserts missing sample keys only; it never updates existing prices, stock, conditions, user accounts or user-created vehicles. Changing a sample ID means adding a different sample, so keep IDs stable. A manually deleted sample will be recreated if the seed is run again. A similar user-created listing is a separate record and is never adopted or overwritten.

The dataset label applies to every row in this file. The API's existing price field remains unchanged; the dataset's INR convention does not convert or relabel prices in existing listings. The unchanged frontend does not yet display condition or sample provenance.
