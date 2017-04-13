"""
Some conveniece methods for accessing databases and declaritivly specifying schemata.
"""

class SchemaConflict(Exception):
    pass

class DatabaseProvider:
    def __init__(self, name):
        self.name = name
        self.tables = {}

    def table(self, **kwargs):
        """
        Decorator for declaratively specifying table schemata.

        Usage:
        @db.table(foo=(("bar", "TEXT"), ("bin", "TEXT")))
        def whatev(db): pass

        This will ensure that the `db` object passed to `whatev` will have a table named `foo` and two `TEXT` columns named `bar` and `bin`.
        """
        def dec(func):
            return func
        for name, columns in kwargs.items():
            if name in self.tables and columns != self.tables['name']:
                raise SchemaConflict(name)
            else:
                self.tables[name] = columns
        return dec

    def setup(self, conn):
        """
        Creates tables from `table` decorator invocations.
        """
        # Get a list of tables.
        q = conn.execute("SELECT name FROM sqlite_master WHERE type='table'");
        actual = set(r[0] for r in q.fetchall())
        expected = set(self.tables.keys())
        # Get names of tables that have been declared but that do not yet exist.
        to_create = expected - actual
        # TODO: Verify existing tables:
        # to_verify = expected.intersection(actual)

        # Create the missing tables.
        for table in to_create:
            cols = ', '.join(f"{key} {value}" for (key, value) in self.tables[table])
            conn.execute(f"CREATE TABLE {table} ({cols})")
        if to_create:
            conn.commit()

