
# Library Metric Utilities

This repository contains scripts and utilities for generating numbers for
various library metrics that we're required to give every year.

This counts the number of features in PostGIS databases. 

## Setup

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

## Options

Other options are available to control the output.

--config = The database configuration file.

--filter = Don't get counts for databases matching these. Can be given more than once.

--no-totals = Don't print totals.

--verbose = Extra output.


## Notes

- The user supplied in the config.yml for connecting to the host must be able to access the pg_hba.conf file (meaning the account will need sudo access).

# Website Metrics

The `server-logs` directory also contains some resources for analyzing server logs. Currently, this is just a `Makefile` that installed the needed dependencies and tools and then generates summary statistics from a log file.

## Tools

The tools that it uses are:

* [GoAccess](https://goaccess.io/) to parse the logs, aggregate their data, and dump out the report as JSON, which means we need to process that with ...
* [jq](https://stedolan.github.io/jq/), which pulls out the data we need from the log summary and write it out as CSV, which we process using ...
* [csvkit](https://csvkit.readthedocs.io/en/1.0.1/) to get summary statistics for the fields we're interested in (unique visitors and page views).

The `Makefile` will install these using [homebrew](https://brew.sh/) and [pip](https://pip.pypa.io/en/stable/):

```bash
make install
```

## Preparing the Logs

The logs have to be downloaded separately. These are found on our servers in the `/etc/httpd/logs` directory, and are usually named after their sites (e.g., `prosody_access.log`).

Generally, we keep about a month's worth of logs in five files: the current file and four numbered rotated logs (`prosody_access.log.1` through `prosody_access.log.4`).

These tools assume that there's one file containing all of these files with a *very* specific name: **`PROJECT_access.log`**. You can easily generate this file with these two short shell command:

```bash
mv prosody_access.log prosody_access.log.0
cat prosody_access.log.* > prosody_access.log
```

The first command backs up the current file by renaming it, and then the second command uses `cat` to join all the files into one. Notice that the logs are redirected into a file whose name matches the pattern required.

## Generating Statistics

Once the logs are in shape, the `Makefile` will generate the statistical summary for a project:

```bash
make prosody.summary
```

If the tools can find the file `prosody_access.log`, it will use the [tools](#tools) to generate a file called `prosody.summary`. Its contents will look something like this:

```
  2. "visitors"

	Type of data:          Number
	Contains null values:  False
	Unique values:         31
	Smallest value:        103
	Largest value:         594
	Sum:                   16,022
	Mean:                  485.515
	Median:                519
	StDev:                 102.473
	Most common values:    501 (2x)
	                       521 (2x)
	                       103 (1x)
	                       581 (1x)
	                       565 (1x)

  3. "hits"

	Type of data:          Number
	Contains null values:  False
	Unique values:         33
	Smallest value:        1,174
	Largest value:         10,814
	Sum:                   268,436
	Mean:                  8,134.424
	Median:                8,661
	StDev:                 2,412.637
	Most common values:    1,174 (1x)
	                       9,929 (1x)
	                       7,674 (1x)
	                       8,127 (1x)
	                       8,574 (1x)

Row count: 33
```

