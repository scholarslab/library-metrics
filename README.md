
# Library Metric Utilities

This repository contains scripts and utilities for generating numbers for
various library metrics that we're required to give every year.

## Setup

### Python Dependencies

Run `rake init:dependencies`

OR `pip install --requirement requirements.txt`

### Python Environment

Run `rake init:virtualenv` then `source bin/activate`

OR ` virtualenv .` then `source bin/activate`

### Copy geolayers.py

Copy geolayers.py from scripts to bin directory

`cp scripts/geolayers.py bin`



## bin/geolayers.py

This counts the number of features in PostGIS databases. This needs a YAML
configuration file to tell it how to connect to all of the databases you need
counts from.

```yaml
---
postgis:
  - host: postgis.server.com
    port: 5432
    user: postgis_user
    password: secret
rasters:
  host: geo.server.com
  user: username
  geoserver-data-dir: /var/geodata/geoserver/data
geoserver:
  url: http://geo.server.com:8080/geoserver
  user: admin
  password: secret
```

Now you can call it like this:

```shell
./bin/geolayers.py --config config.yml --filter '^ESRI' --filter '^MLB'
```

OR

```shell
rake geoserver
```

Other options are available to control the output.

