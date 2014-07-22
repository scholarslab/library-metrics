
# Library Metric Utilities

This repository contains scripts and utilities for generating numbers for
various library metrics that we're required to give every year.

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
```

Now you can call it like this:

```shell
./bin/geolayers.py --config config.yml --filter '^ESRI' --filter '^MLB'
```

Other options are available to control the output.

