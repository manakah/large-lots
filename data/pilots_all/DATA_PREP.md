# Preparing the Data

The index page displays all the properties sold and currently under review. Getting that data requires a little effort: the following explains what you need to do.

### Process data sources 

First, you need a Postgress database with all city parcels, communities, and wards. Please see `DATA_PREP.md` at the root of the large-lots repo for information on creating a database with the necessary tables. Alternatively, you may set-up an `lis` database, given the instructions provided in [this repo](https://github.com/datamade/lis).

Then, request a list of all properties sold in previous pilots from the Department of Planning and Development (contact: Jeanne Chandler). Add that file to `pilots_all/raw/`, and transform it into a Postgres table using csvsql.

```bash
pip install csvkit 

csvsql --db postgresql:///<database name> --insert data/pilots_all/raw/Large\ Lot\ Sold\ GHN\ EGP\ and\ Austin\ Roseland\ and\ Auburn\ Gresham.csv --table lots_sold_all_pilots
```

Finally, add a status column to the table:

```
psql -d <database name>

ALTER TABLE lots_sold_all_pilots ADD COLUMN status varchar(30);

UPDATE lots_sold_all_pilots SET status='sold';
```

### Create a dataset for Carto

Query your database to create a file with lot PINs, addresses, communities, wards, and geoms.

```
COPY (
  SELECT pin14 as pin_nbr, pins.pin, ST_AsGeoJSON(ST_transform(pins.geom, 4326)) as the_geom, low_address, high_address, street_direction, street_name, street_type, community, ward, status 
  FROM (
    select pin14, "PIN number" as pin, status, parcel.geom as geom, "Lot Address" as full_address from parcel
    join lots_sold_all_pilots
    on trim(replace("PIN number", '-', ''))=parcel.pin14
    UNION
    select pin14, "PIN number" as pin, status, parcel.geom as geom, "Lot Address" as full_address from parcel
    join lots_sold_all_pilots
    on trim(replace("PIN number", '-', ''))=parcel.pin10
    ) as pins
  INNER JOIN community_areas
  ON ST_Intersects(pins.geom, community_areas.geom)
  INNER JOIN wards 
  ON ST_Intersects(pins.geom, wards.geom)
  LEFT JOIN raw_address
  ON pin14=replace(raw_address.pin, '-', '')
) TO '<path to repo>/large-lots/data/pilots_all/all_sold_lots.csv' 
DELIMITER ',' CSV HEADER;
```

Now, you have a Carto-friendly csv of all sold lots!


