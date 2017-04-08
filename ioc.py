class SchemaConflict(Exception):
    pass

class DatabaseProvider:
    def __init__(self, name):
        self.name = name
        self.tables = {}

    def table(self, **kwargs):
        def dec(func):
            return func

        for name, columns in kwargs.items():
            if name in self.tables and columns != self.tables['name']:
                raise SchemaConflict(name)
            else:
                self.tables[name] = columns

        return dec

    def setup(self, conn):
        q = conn.execute("SELECT name FROM sqlite_master WHERE type='table'");
        actual = set(r[0] for r in q.fetchall())
        expected = set(self.tables.keys())
        to_create = expected - actual
        # TODO: Verify existing tables:
        # to_verify = expected.intersection(actual)

        for table in to_create:
            cols = ', '.join(f"{key} {value}" for (key, value) in self.tables[table])
            conn.execute(f"CREATE TABLE {table} ({cols})")
        if to_create:
            conn.commit()

