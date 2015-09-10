VPATH=raw:build
include config.mk
county_shp=$(notdir $(shell ls raw/cook-county/*.shp))

LAND_HEADER = "pin14,street_number,street_dir,street_name,street_type,sq_ft,ward,community_area,zoning_classification,tif_district"

all: community-areas.table city-owned-residential-lots.table land-inventory-parcels.zip rp_lots.zip

clean:
	@rm -Rf build/*

full_clean:
	@rm -Rf build/*
	@rm -Rf finished/*

land-inventory.csv:
	wget https://data.cityofchicago.org/api/views/aksk-kvfp/rows.csv?accessType=DOWNLOAD -qO- | \
		python processors/remove_dashes.py 0 | \
		(echo $(LAND_HEADER) ; tail -n +2) > build/$@

cook-county-parcels.zip:
	@wget "https://datacatalog.cookcountyil.gov/api/geospatial/5i2c-y2u6?method=export&format=Shapefile" -O raw/$@

land-inventory.table: land-inventory.csv
	@psql -h $(PG_HOST) -U $(PG_USER) -p $(PG_PORT) -d $(PG_DB) -c "DROP TABLE IF EXISTS land_inventory;"
	@csvsql build/land-inventory.csv \
			--db "postgresql://$(PG_USER):@$(PG_HOST):$(PG_PORT)/$(PG_DB)" --table land_inventory --insert
	@touch build/land-inventory.table

cook-county-parcels.table: cook-county-parcels.zip
	@mkdir -p raw/cook-county
	@unzip -d raw/cook-county raw/cook-county-parcels.zip
	ogr2ogr -overwrite -t_srs EPSG:4326 \
		build/$(notdir $(shell ls raw/cook-county/*.shp)) \
		raw/cook-county/$(notdir $(shell ls raw/cook-county/*.shp))
	shp2pgsql -I -s 4326 -d build/$(notdir $(shell ls raw/cook-county/*.shp)) \
		cook_county_parcels | \
		psql -d $(PG_DB) -U $(PG_USER) -h $(PG_HOST) -p $(PG_PORT)
	psql -d $(PG_DB) -U $(PG_USER) -h $(PG_HOST) -p $(PG_PORT) -c \
	   "CREATE INDEX county_pin_idx ON cook_county_parcels (PIN14)"
	touch build/cook-county-parcels.table

community-areas.zip: 
	@wget "https://data.cityofchicago.org/api/geospatial/cauq-8yn6?method=export&format=Original" -O raw/$@

community-areas.table: community-areas.zip
	mkdir -p raw/community-areas
	unzip -d raw/community-areas raw/community-areas.zip
	ogr2ogr -overwrite -t_srs EPSG:4326 build/$(notdir $(shell ls raw/community-areas/*.shp)) \
	   raw/community-areas/$(notdir $(shell ls raw/community-areas/*.shp))
	psql -h $(PG_HOST) -U $(PG_USER) -p $(PG_PORT) -d $(PG_DB) -c \
	   "DROP TABLE IF EXISTS community_areas;"
	shp2pgsql -I -s 4326 -d build/$(notdir $(shell ls raw/community-areas/*.shp)) community_areas | \
	   psql -d $(PG_DB) -U $(PG_USER) -h $(PG_HOST) -p $(PG_PORT)
	touch build/community-areas.table

land-inventory-parcels.shp: cook-county-parcels.table land-inventory.table
	@pgsql2shp -f build/land-inventory-parcels.shp -h $(PG_HOST) -u $(PG_USER) -p $(PG_PORT) $(PG_DB) \
		"SELECT cook_county_parcels.geom, land_inventory.* \
			FROM cook_county_parcels \
			JOIN land_inventory ON cast(cook_county_parcels.PIN14 as bigint) = land_inventory.pin14"

land-inventory-parcels.zip: land-inventory-parcels.shp
	@ls build/land-inventory-parcels.* | zip finished/land-inventory-parcels.zip -@ 


city-owned-residential-lots.table: land-inventory.table cook-county-parcels.table
	@psql -h $(PG_HOST) -U $(PG_USER) -p $(PG_PORT) -d $(PG_DB) -c "DROP TABLE IF EXISTS city_owned_residential_lots;"
	@psql -d $(PG_DB) -U $(PG_USER) -h $(PG_HOST) -p $(PG_PORT) -c \
		"CREATE TABLE city_owned_residential_lots AS \
			SELECT cook_county_parcels.geom, land_inventory.* \
			FROM cook_county_parcels \
			JOIN land_inventory \
			ON cast(cook_county_parcels.PIN14 as bigint) = land_inventory.pin14 \
			WHERE zoning_classification LIKE 'R%' \
				OR zoning_classification IS NULL"
	@psql -d $(PG_DB) -U $(PG_USER) -h $(PG_HOST) -p $(PG_PORT) -c \
		"ALTER TABLE city_owned_residential_lots ADD COLUMN city_owned boolean"
	@psql -d $(PG_DB) -U $(PG_USER) -h $(PG_HOST) -p $(PG_PORT) -c \
		"ALTER TABLE city_owned_residential_lots ADD COLUMN residential boolean"
	@psql -d $(PG_DB) -U $(PG_USER) -h $(PG_HOST) -p $(PG_PORT) -c \
		"ALTER TABLE city_owned_residential_lots ADD COLUMN alderman_hold boolean"
	@touch build/$@

RP_HEADER = "pin14,from_street_number,to_street_number,street_dir,street_name,street_type,zoning_classification"

eligable_lots.csv: Roseland_Pullman_FINAL_LLP_List.xlsx
	@in2csv raw/Roseland_Pullman_FINAL_LLP_List.xlsx | \
		csvcut -C 1,8,9,11,12 | \
		python processors/remove_dashes.py 0 | \
		(echo $(RP_HEADER) ; tail -n +2) > build/$@

eligable_lots.table: eligable_lots.csv
	@psql -h $(PG_HOST) -U $(PG_USER) -p $(PG_PORT) -d $(PG_DB) -c "DROP TABLE IF EXISTS eligable_lots;"
	@csvsql build/eligable_lots.csv \
			--db "postgresql://$(PG_USER):@$(PG_HOST):$(PG_PORT)/$(PG_DB)" --table eligable_lots --insert
	@touch build/eligable_lots.table

rp_lots.table: community-areas.table cook-county-parcels.table
	@psql -d $(PG_DB) -U $(PG_USER) -h $(PG_HOST) -p $(PG_PORT) -c \
		"DROP TABLE IF EXISTS rp_lots"
	@psql -d $(PG_DB) -U $(PG_USER) -h $(PG_HOST) -p $(PG_PORT) -c \
		"CREATE TABLE rp_lots AS \
			SELECT \
				CAST(p.pin14 AS bigint) as display_pin, \
				CAST(p.pin14 AS bigint) as pin14, \
				CAST(p.shape_area as int) as sq_ft, \
				c.community as community_area, \
				FALSE as eligable, \
				FALSE as city_owned, \
				FALSE as residential, \
				FALSE as alderman_hold, \
				p.geom as geom, \
				ST_X(ST_Centroid(p.geom)) as longitude, \
				ST_Y(ST_Centroid(p.geom)) as latitude, \
				0 as status \
			FROM cook_county_parcels AS p \
			JOIN community_areas as c \
				ON ST_Within(p.geom, c.geom) \
			WHERE c.area_num_1 IN ('49', '50')"
	@psql -d $(PG_DB) -U $(PG_USER) -h $(PG_HOST) -p $(PG_PORT) -c \
		"ALTER TABLE rp_lots ADD COLUMN street_number int"
	@psql -d $(PG_DB) -U $(PG_USER) -h $(PG_HOST) -p $(PG_PORT) -c \
		"ALTER TABLE rp_lots ADD COLUMN street_dir varchar"
	@psql -d $(PG_DB) -U $(PG_USER) -h $(PG_HOST) -p $(PG_PORT) -c \
		"ALTER TABLE rp_lots ADD COLUMN street_name varchar"
	@psql -d $(PG_DB) -U $(PG_USER) -h $(PG_HOST) -p $(PG_PORT) -c \
		"ALTER TABLE rp_lots ADD COLUMN street_type varchar"
	@psql -d $(PG_DB) -U $(PG_USER) -h $(PG_HOST) -p $(PG_PORT) -c \
		"ALTER TABLE rp_lots ADD COLUMN ward varchar"
	@psql -d $(PG_DB) -U $(PG_USER) -h $(PG_HOST) -p $(PG_PORT) -c \
		"ALTER TABLE rp_lots ADD COLUMN zoning_classification varchar"
	@touch build/rp_lots.table

rp_lots.defaults: rp_lots.table eligable_lots.table
	@psql -d $(PG_DB) -U $(PG_USER) -h $(PG_HOST) -p $(PG_PORT) -c \
		"UPDATE rp_lots SET \
			street_number=s.street_number, \
			street_dir=s.dir, \
			street_name=s.street_name, \
			street_type=s.type, \
			ward=s.ward, \
			zoning_classification=s.zoning_classification, \
			eligable=TRUE, \
			city_owned=TRUE, \
			residential=TRUE, \
			status=0 FROM ( \
				SELECT \
					COALESCE(l.pin14, e.pin14) as pin14, \
					COALESCE(l.street_number, e.from_street_number) as street_number, \
					COALESCE(l.street_dir, e.street_dir) as dir, \
					COALESCE(l.street_name, e.street_name) as street_name, \
					COALESCE(l.street_type, e.street_type) as type, \
					l.ward, \
					COALESCE(l.zoning_classification, e.zoning_classification) as zoning_classification \
				FROM eligable_lots AS e \
				LEFT JOIN city_owned_residential_lots AS l \
					ON e.pin14 = l.pin14 \
			) as s \
			WHERE rp_lots.pin14 = s.pin14"
	@touch build/rp_lots.defaults

rp_lots.shp: rp_lots.defaults
	@pgsql2shp -f finished/rp_lots.shp -h $(PG_HOST) -u $(PG_USER) -p $(PG_PORT) $(PG_DB) rp_lots

rp_lots.zip: rp_lots.shp
	@ls finished/rp_lots.* | zip finished/rp_lots.zip -@ 
