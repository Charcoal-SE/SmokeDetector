import sys
import os
import sqlite3

from globalvars import GlobalVars


def initialize():
    if GlobalVars.local_db:
        # there's already a sqlite3.Connection
        return
    if 'pytest' in sys.modules:
        GlobalVars.local_db = sqlite3.connect("pytest.db")
    else:
        GlobalVars.local_db = sqlite3.connect("smokedetector.db")
    return GlobalVars.local_db


def execute(query_string: str, parameters: tuple=(), action: str=""):
    if not GlobalVars.local_db:
        raise ValueError("DB is not connected")
    cursor = GlobalVars.local_db.execute(query_string, parameters)
    if action == "all":
        return cursor.fetchall()
    elif action == "one":
        return cursor.fetchone()
    else:
        return cursor


def executemany(query_string: str, parameters=[()]):
    if not GlobalVars.local_db:
        raise ValueError("DB is not connected")
    return GlobalVars.local_db.executemany(query_string, parameters)


def commit():
    """
    Commit DB changes, similar to dumping a pickle
    """
    if not GlobalVars.local_db:
        raise ValueError("DB is not connected")
    return GlobalVars.local_db.commit()


def table_exists(table: str="sqlite_master"):
    if not GlobalVars.local_db:
        return False
    return (execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", [table], "one") is not None)


def create_table_if_not_exist(table, s):
    # Bad approach here, any better ideas?
    if table_exists(table):
        return
    result = execute("CREATE TABLE {table} ({cols})".format(table=table, cols=s))
    commit()
    return result


# Query here or in datahandling.py (?)


initialize()
