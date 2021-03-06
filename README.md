![large lots logo](lots/static/images/large_lots.png)

# Large Lots

The City of Chicago is selling vacant lots for $1. Here's how you get one.

## Configuring and running locally

We recommend using [virtualenv](http://virtualenv.readthedocs.org/en/latest/virtualenv.html) and [virtualenvwrapper](http://virtualenvwrapper.readthedocs.org/en/latest/install.html) for working in a virtualized development environment. [Read how to set up virtualenv](http://docs.python-guide.org/en/latest/dev/virtualenvs/).

Once you have virtualenvwrapper set up, run the following commands in your terminal:

```bash
mkvirtualenv largelots -p /path/to/your/python3
git clone git@github.com:datamade/large-lots.git
cd large-lots
pip install -r requirements.txt
```

Set the environmental variables in [local_settings.py.example](https://github.com/datamade/large-lots/blob/master/lots/local_settings.py.example) (then drop the .example suffix):

  * ``SECRET_KEY`` - Django’s [Secret Key](https://docs.djangoproject.com/en/1.10/ref/settings/#secret-key) used by the project. Can be any relatively hard to guess string.

  * ``AWS_STORAGE_BUCKET_NAME`` - the name of the AWS bucket where deed uploads (PDFs, images) reside; for local development you can use: largelots-test-uploads

  * ``AWS_ACCESS_KEY`` - AWS key used by the file storage mechanism to store files in S3.

  * ``AWS_SECRET_ACCESS_KEY`` - The secret that goes with the key above.

  * ``CARTODB_API_KEY`` - [Carto](https://carto.com/) API key

  * ``EMAIL_HOST, EMAIL_PORT, EMAIL_USE_TLS, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD`` - These are used to configure the email settings for Django. See [Django docs](https://docs.djangoproject.com/en/1.6/topics/email/) for more info.

  * ``SENTRY_DSN`` - This is a connection string for [Sentry](http://getsentry.com).

Note that the example local settings sets `START_DATE` and `END_DATE` to now and two weeks from now, respectively, so you'll default to an "active" application period for local development. In production, these should correspond to the start and end dates of the current round's application period.

Make a database, `largelots`, and run migrations:

```bash
createdb largelots
python manage.py migrate
```

Now you're ready to run the app:

```bash
python manage.py runserver
```

Navigate to [http://localhost:8000/](http://localhost:8000/).

## Sending emails

We have a management command that facilitates sending emails in bulk. It takes several arguments, including an option to send emails to applicants needing to complete the Economic Disclosure Statement:

```bash
python manage.py send_emails --eds_email=87
```

The arguments after `--eds_email` refer to the number of applications who should receive emails.

## Testing

Export your settings:

```bash
export DJANGO_SETTINGS_MODULE=lots_admin.tests.test_config
```

Run the tests:
```bash
pytest lots_admin/tests
```

## Data

Our map was built using open data from Chicago and Cook County:

* [Chicago - City Owned Land Inventory](https://data.cityofchicago.org/Community-Economic-Development/City-Owned-Land-Inventory/aksk-kvfp)
* [Chicago - Wards](https://data.cityofchicago.org/Facilities-Geographic-Boundaries/Boundaries-Wards/bhcv-wqkf)
* [Cook County - 2012 Parcels](https://datacatalog.cookcountyil.gov/GIS-Maps/ccgisdata-Parcel-2012/e62c-6rz8)

## Dependencies
We used the following open source tools:

* [QGIS](http://www.qgis.org/en/site/) - graphic information system (GIS) desktop application
* [PostGIS](http://postgis.net/) - geospatial database
* [Bootstrap](http://getbootstrap.com/) - Responsive HTML, CSS and Javascript framework
* [Leaflet](http://leafletjs.com/) - javascript library interactive maps
* [jQuery Address](https://github.com/asual/jquery-address) - javascript library creating RESTful URLs

## Logging 

The `send_emails` management command employs the Python `logging` facility. The `file` handler directs output to log files in `/var/log/largelots` on the LargeLots server.

## Team

* Demond Drummer - idea, content, outreach
* Derek Eder - developer, content
* Eric van Zanten - developer, GIS data merging
* Forest Gregg - process design, content

## Contributors

* Aya O'Connor - logo
* Juan-Pablo Velez - content

## Errors / Bugs

If something is not behaving intuitively, it is a bug, and should be reported.
Report it here: https://github.com/datamade/large-lots/issues

## Note on Patches/Pull Requests

* Fork the project.
* Make your feature addition or bug fix.
* Commit, do not mess with rakefile, version, or history.
* Send me a pull request. Bonus points for topic branches.

## Copyright

Copyright (c) 2014 DataMade and LISC Chicago. Released under the [MIT License](https://github.com/datamade/large-lots/blob/master/LICENSE).
