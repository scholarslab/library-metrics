#!/usr/bin/env python2.7


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
```

This will connect to each database server and walk over the databases and their
tables. For each PostGIS table it encounters, it will get the number of rows
and write them out. Finally, it will output the total number of rows.

"""


from __future__ import (
    division, absolute_import, print_function, unicode_literals,
    )

import argparse
from contextlib import contextmanager
# from pprint import pprint
import re
import sys

import psycopg2
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


class PostGISMetrics(object):

    def __init__(self, host_configs, filters, verbose=False):
        self.host_configs = host_configs
        self.filters = filters
        self.verbose = verbose
        self.set_logger()
        self.set_filter_fn()

    def get_layer_count(self):
        """\
        This queries the database repeatedly to get the number of PostGIS
        resources.
        """
        layer_total = 0

        for host_config in self.host_configs:
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
                            self.log('{}.{}.{}\t{}'.format(db_name, schema,
                                                           table, count))
                            layer_total += count

        return layer_total

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


class Script(object):

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
            print('layers\t{}'.format(self.layer_total))

    def main(self, argv=None):
        postgis = PostGISMetrics(
            self.config['postgis'],
            self.opts.filter,
            self.opts.verbose,
            )
        self.layer_total = postgis.get_layer_count()
        self.do_totals()


if __name__ == '__main__':
    Script().main()
