# Preparing the Data

The index page displays all the properties sold and currently under review. Getting that data requires a little effort: the following explains what you need to do.

### Process data sources 

First, you need a Postgress database with all city parcels. Please see `DATA_PREP.md` at the root of the large-lots repo for information on creating a database with the necessary tables. Alternatively, you may set-up an `lis` database, given the instructions provided in [this repo](https://github.com/datamade/lis).

Then, request a list of all properties sold in previous pilots from the Department of Planning and Development (contact: Jeanne Chandler). Add that file to `pilots_all/raw/`, and transform it into a Postgres table using csvsql.

```bash
pip install csvkit 

csvsql --db postgresql:///<database name> --insert data/pilots_all/raw/Large\ Lot\ Sold\ GHN\ EGP\ and\ Austin\ Roseland\ and\ Auburn\ Gresham.csv --table lots_sold_all_pilots
```

### Create a dataset for Carto

Query your database to create a file with lot PINs, addresses, communities, wards, and geoms.

```
COPY (
  SELECT pin14, pin, pins.geom, full_address, community, ward 
  FROM (
    select pin14, "PIN number" as pin, parcel.geom as geom, "Lot Address" as full_address from parcel
    join lots_sold_all_pilots
    on trim(replace("PIN number", '-', ''))=parcel.pin14
    UNION
    select pin14, "PIN number" as pin, parcel.geom as geom, "Lot Address" from parcel
    join lots_sold_all_pilots
    on trim(replace("PIN number", '-', ''))=parcel.pin10
    ) as pins
  INNER JOIN community_areas
  ON ST_Intersects(pins.geom, community_areas.geom)
  INNER JOIN wards 
  ON ST_Intersects(pins.geom, wards.geom)
) TO '<path to repo>/large-lots/data/pilots_all/all_sold_lots_.csv' 
DELIMITER ',' CSV HEADER;
```

Then, import this data to Carto, using the `datamade` account. 


