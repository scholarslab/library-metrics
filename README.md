
# Library Metric Utilities

This repository contains scripts and utilities for generating numbers for
various library metrics that we're required to give every year.

This counts the number of features in PostGIS databases. 

# Setup

1. Python Dependencies

    Run `rake init`

    OR `pip install --requirement requirements.txt`

1. Create config.yml

    This needs a YAML configuration file to tell it how to connect to all of the
databases you need counts from.

    The config.yml file should be on the same level as the bin folder (not within
the bin folder).

```yaml
---
postgis:
  - host: postgis.server.com
    port: 5432
    user: postgis_user
    password: secret
  - host: postgis2.server.com
    port: 5432
    user: postgis2_user
    password: secret2
rasters:
  host: geo.server.com
  user: username
  geoserver-data-dir: /var/geodata/geoserver/data
geoserver:
  url: http://geo.server.com:8080/geoserver
  user: admin
  password: secret
```

# Run the script

Now you can call it like this:

```shell
./bin/geolayers.py --config config.yml --filter '^ESRI' --filter '^MLB'
```

OR

```shell
rake geoserver
```

# Options

Other options are available to control the output.

--config = The database configuration file.

--filter = Don't get counts for databases matching these. Can be given more than once.

--no-totals = Don't print totals.

--verbose = Extra output.


# Notes

- The user supplied in the config.yml for connecting to the host must be able to access the pg_hba.conf file (meaning the account will need sudo access).


