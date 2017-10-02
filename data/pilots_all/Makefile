# Variables
PG_DB=lis
SOLD_LOTS=raw/Large\ Lot\ Sold\ GHN\ EGP\ and\ Austin\ Roseland\ and\ Auburn\ Gresham.csv

# Non-file targets
.PHONY: clean all

clean:
	rm processed/*
	psql -d $(PG_DB) -c 'DROP TABLE lots_sold_all_pilots' 

all: lots_sold_all_pilots.table all_sold_lots.csv

# Create table with necessary columns in database
lots_sold_all_pilots.table: $(SOLD_LOTS)
	csvsql --db postgresql:///$(PG_DB) --insert $(SOLD_LOTS) --table lots_sold_all_pilots
	psql -d $(PG_DB) -c "ALTER TABLE lots_sold_all_pilots ADD COLUMN status varchar(30)"
	psql -d $(PG_DB) -c "UPDATE lots_sold_all_pilots SET status='sold'"
	touch processed/$@

# Query database and make a csv
all_sold_lots.csv: processed/lots_sold_all_pilots.table
	psql -d $(PG_DB) -c \
	"COPY (SELECT \
		pin14 as pin_nbr, pins.pin, \
		ST_AsGeoJSON(ST_transform(pins.geom, 4326)) as the_geom, \
		low_address, high_address, street_direction, street_name, street_type, \
    community, ward, status \
    FROM (SELECT pin14, \"PIN number\" as pin, status, \
    	parcel.geom as geom, \"Lot Address\" as full_address \
    	FROM parcel \
      JOIN lots_sold_all_pilots \
      ON trim(replace(\"PIN number\", '-', ''))=parcel.pin14 \
      UNION \
      SELECT pin14, \"PIN number\" as pin, status, \
      parcel.geom as geom, \"Lot Address\" as full_address \
      FROM parcel \
      JOIN lots_sold_all_pilots \
      ON trim(replace(\"PIN number\", '-', ''))=parcel.pin10 \
    ) as pins \
    INNER JOIN community_areas \
    ON ST_Intersects(pins.geom, community_areas.geom) \
    INNER JOIN wards \
    ON ST_Intersects(pins.geom, wards.geom) \
    LEFT JOIN raw_address \
    ON pin14=replace(raw_address.pin, '-', '') \
  ) TO STDOUT WITH CSV HEADER" > processed/$@