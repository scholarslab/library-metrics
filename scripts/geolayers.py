#!/usr/bin/env python3


"""\
This walks over a collection of PostGIS tables and reports on the number of
rows in each database.

## Database Configuration File

This is a YAML file formatted like this:

```yaml
---
postgis:
  - host: postgis.host.edu
    port: 5432
    user: postgis_user
    password: secret
  - host: postgis2.host.edu
    user: post_user_2
    password: hushhush
rasters:
  host: geo.server.com
  user: username
  geoserver-data-dir: /var/geodata/geoserver/data
geoserver:
  url: http://geo.server.com:8080/geoserver
  user: admin
  password: secret
```

This will connect to each database server and walk over the databases and their
tables. For each PostGIS table it encounters, it will get the number of rows
and write them out. Finally, it will output the total number of rows.

"""


from __future__ import (
    division, absolute_import, print_function, unicode_literals,
    )

import argparse
from contextlib import closing, contextmanager
import os
# from pprint import pprint
import re
import stat
import sys

import paramiko
import psycopg2
import requests
import yaml


# Utilities


@contextmanager
def db_cursor(config):
    """\
    Connect to a database and return the connection and a cursor. Then clean
    up.
    """
    cxn = psycopg2.connect(**config)
    c = cxn.cursor()
    try:
        yield (cxn, c)
    finally:
        c.close()
        cxn.close()


def db_fetch(config, sql, *params):
    """Connect to a database and return the results of a SQL query."""
    with db_cursor(config) as (_, c):
        c.execute(sql, *params)
        return c.fetchall()


class MetricsBase(object):

    def __init__(self, config, filters, verbose=False):
        self.config = config
        self.filters = filters
        self.verbose = verbose
        self.set_logger()
        self.set_filter_fn()

    def set_logger(self):
        if self.verbose:
            self.log = print
        else:
            self.log = lambda x: None

    def set_filter_fn(self):
        if self.filters is None:
            self.filter_fn = lambda _: False
        else:
            regexes = [re.compile(regex) for regex in self.filters]
            self.filter_fn = lambda n: any(regex.search(n) is not None
                                           for regex in regexes)

    def get_counts(self):
        raise NotImplementedError(
            '{}.get_counts'.format(self.__class__.__name__),
            )


class PostGISMetrics(MetricsBase):

    def get_counts(self):
        """\
        This queries the database repeatedly to get the number of PostGIS
        resources.
        """
        table_total = layer_total = 0

        for host_config in self.config:
            for (db_name, _) in self.list_databases(host_config):
                if self.filter_fn(db_name):
                    continue

                db_config = host_config.copy()
                db_config['dbname'] = db_name

                with db_cursor(db_config) as (cxn, c):
                    self.cursor = c
                    for (schema, table) in self.list_tables():
                        if self.is_postgis(table):
                            count = self.count_rows(schema, table)
                            if count:
                                table_total += 1
                                self.log('{}.{}.{}\t{}'.format(db_name, schema,
                                                               table, count))
                            layer_total += count

        return {'table': table_total, 'layer': layer_total}

    @staticmethod
    def list_databases(db_config):
        """This lists the databases on a server."""
        # From
        # http://www.postgresql.org/message-id/3E318553.7050101@incentre.net
        dbs = db_fetch(db_config, '''
            SELECT d.datname as "Name", u.usename as "Owner"
                FROM pg_catalog.pg_database d
                    LEFT JOIN pg_catalog.pg_user u ON d.datdba = u.usesysid
                WHERE NOT d.datistemplate AND d.datname != 'postgres'
                  AND d.datname != u.usename;
            ''')
        return dbs

    def list_tables(self):
        """This lists the tables on a database."""
        # From
        # http://stackoverflow.com/questions/2276644/list-all-tables-in-postgresql-information-schema
        self.cursor.execute('''
            SELECT table_schema, table_name
                FROM information_schema.tables
                WHERE table_type='BASE TABLE'
                  AND table_name NOT LIKE 'pg_%'
                  AND table_name NOT LIKE 'sql_%';
            ''')
        return self.cursor.fetchall()

    def list_columns(self, table_name):
        """\
        This returns a list of the column names, data types, and UDT names.
        """
        self.cursor.execute('''
            SELECT column_name, data_type, udt_name
                FROM information_schema.columns
                WHERE table_name=%s;
            ''', (table_name,))
        columns = self.cursor.fetchall()
        return columns

    def is_postgis(self, table_name, columns=None):
        """Tests whether this is a PostGIS table."""
        if columns is None:
            columns = self.list_columns(table_name)
        return 'geometry' in set(udt_name for (_, _, udt_name) in columns)

    def count_rows(self, schema, table_name):
        """Returns the count of rows for a table."""
        self.cursor.execute(
            'SELECT COUNT(*) FROM "{}"."{}";'.format(schema, table_name),
            )
        return self.cursor.fetchone()[0]


class RasterMetrics(MetricsBase):

    def get_counts(self):
        raster_counts = 0

        with self.connect() as ssh:
            with closing(ssh.open_sftp()) as sftp:
                dirname = os.path.join(self.config['geoserver-data-dir'],
                                       'coverages')
                for (root, dirs, files) in self.walk(sftp, dirname):
                    dirs[:] = [
                        d for d in dirs if not self.filter_fn(d.filename)
                        ]
                    dir_count = len([
                        f for f in files if self.is_tiff(f.filename)
                        ])
                    if dir_count:
                        self.log('{}\t{}'.format(root, dir_count))
                    raster_counts += dir_count

        return {'raster': raster_counts}

    @contextmanager
    def connect(self):
        ssh = paramiko.SSHClient()
        ssh.load_system_host_keys()
        ssh.connect(
            hostname=self.config['host'],
            port=self.config.get('port', 22),
            username=self.config['user'],
            password=self.config.get('password'),
            )
        try:
            yield ssh
        finally:
            ssh.close()

    def walk(self, sftp, basedir):
        ls = sftp.listdir_attr(basedir)
        dirs = [
            dirname for dirname in ls
            if stat.S_ISDIR(dirname.st_mode) or stat.S_ISLNK(dirname.st_mode)
            ]
        files = [
            filename for filename in ls if not stat.S_ISDIR(filename.st_mode)
            ]

        yield (basedir, dirs, files)

        for dirname in dirs:
            full_dir_name = os.path.join(basedir, dirname.filename)
            for dir_info in self.walk(sftp, full_dir_name):
                yield dir_info

    def is_tiff(self, filename):
        (_, ext) = os.path.splitext(filename)
        ext = ext.lower()
        return ext == '.tif' or ext == '.tiff'


class LayerMetrics(MetricsBase):

    def get_counts(self):
        self.auth = (self.config['user'], self.config['password'])
        return {'named': self.get_layer_count() + self.get_group_count()}

    def get_layer_count(self):
        return self._get_count(self.config['url'] + '/rest/layers.json',
                               'layers', 'layer')

    def get_group_count(self):
        return self._get_count(self.config['url'] + '/rest/layergroups.json',
                               'layerGroups', 'layerGroup')

    def _get_count(self, url, key0, key1):
        req = requests.get(url, auth=self.auth)
        items = [
            obj for obj in req.json()[key0][key1]
            if not self.filter_fn(str(obj['name']))
            ]
        return len(items)


class Script(object):
    METRIC_ARGS = [(PostGISMetrics, 'postgis'),
                   (RasterMetrics, 'rasters'),
                   (LayerMetrics, 'geoserver')]

    def __init__(self, argv=None):
        self.argv = sys.argv[1:] if argv is None else argv
        self.parse_args()
        self.read_config()

    def read_config(self):
        """\
        This reads a YAML configuration file and returns the data structures it
        contains.
        """
        with open(self.opts.config) as f:
            self.config = yaml.load(f)
        return self.config

    def parse_args(self):
        parser = argparse.ArgumentParser(
            description=__doc__,
            formatter_class=argparse.RawDescriptionHelpFormatter,
            )

        parser.add_argument('-c', '--config', metavar='CONFIG_FILE',
                            help='The database configuration file.')
        parser.add_argument('-F', '--filter', metavar='FILTER_REGEX',
                            action='append',
                            help="Don't get counts for databases matching "
                                 "these. Can be given more than once.")
        parser.add_argument('-T', '--no-totals', action='store_false',
                            dest='do_totals', help="Don't print totals.")
        parser.add_argument('-v', '--verbose', action='store_true',
                            help='Extra output.')

        self.opts = parser.parse_args(self.argv)
        return self.opts

    def do_totals(self):
        if self.opts.do_totals:
            metrics = self.metrics
            print('layers\t{}'.format(metrics['layer']))
            print('raster\t{}'.format(metrics['raster']))
            print('titles\t{}'.format(metrics['raster'] + metrics['table']))
            print('named layers\t{}'.format(metrics['named']))

    def main(self, argv=None):
        self.metrics = metrics = {}
        for (klass, key) in self.METRIC_ARGS:
            m = klass(self.config[key], self.opts.filter, self.opts.verbose)
            metrics.update(m.get_counts())

        self.do_totals()


if __name__ == '__main__':
    Script().main()
