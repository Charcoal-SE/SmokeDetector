import os
import sqlite3

from globalvars import GlobalVars


def initialize():
    if GlobalVars.local_db:
        # there's already a sqlite3.Connection
        return
    GlobalVars.local_db = sqlite3.connect("smokedetector.db")


def execute(query_string: str, parameters: tuple, action="all"):
    if not GlobalVars.local_db:
        raise ValueError("DB is not connected")
    cursor = GlobalVars.local_db.execute(query_string, parameters)
    if action == "all":
        return cursor.fetchall()
    elif action == "one":
        return cursor.fetchone()
    else:
        return cursor


def executemany(query_string: str, parameters: Iterable):
    if not GlobalVars.local_db:
        raise ValueError("DB is not connected")
    cursor = GlobalVars.local_db.executemany(query_string, parameters)
    if fetchall:
        return cursor.fetchall()
    else:
        return cursor


def commit():
    """
    Commit DB changes, similar to dumping a pickle
    """
    if not GlobalVars.local_db:
        raise ValueError("DB is not connected")
    return GlobalVars.local_db.commit()


def table_exists(table):
    if not GlobalVars.local_db:
        return False
    return bool(db_exec)


def create_table_if_not_exist(table, s):
    # Bad approach here, any better ideas?
    if table_exists(table):
        return
    return execute("CREATE TABLE {table} ({cols})".format(table=table, cols=s))


# Query here or in datahandling.py (?)


initialize()
