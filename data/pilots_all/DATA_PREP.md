# Preparing the Data

The index page displays all the properties sold and currently under review. Getting that data requires a little effort: the following explains what you need to do.

### Process data sources 

First, you need a Postgress database with all city parcels, communities, and wards. Please see `DATA_PREP.md` at the root of the large-lots repo for information on creating a database with the necessary tables. Alternatively, you may set-up an `lis` database, given the instructions provided in [this repo](https://github.com/datamade/lis).

Then, request a list of all properties sold in previous pilots from the Department of Planning and Development (contact: Jeanne Chandler). Add that file to `pilots_all/raw/`. 

Finally, run the Makefile. It will accomplish two things: (1) create a table in your postgres database called `lots_sold_all_pilots`, and (2) query your database to create a Carto-friendly CSV file with lot PINs, addresses, communities, wards, and geoms.

Look inside `pilots_all/processed` to see the newly generated file. You are ready to upload it to Carto!