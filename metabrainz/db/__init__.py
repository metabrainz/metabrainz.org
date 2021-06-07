import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.pool import NullPool

engine: sqlalchemy.engine.Engine = None


def init_db_engine(connect_str):
    global engine
    engine = create_engine(connect_str, poolclass=NullPool)


def run_sql_script(sql_file_path):
    with open(sql_file_path) as sql:
        with engine.connect() as connection:
            connection.execute(sql.read())


def run_sql_script_without_transaction(sql_file_path):
    with open(sql_file_path) as sql:
        connection = engine.connect().execution_options(isolation_level="AUTOCOMMIT")
        lines = sql.read().splitlines()
        try:
            # If we try to execute multiple statements at once, postgres wraps them in a transaction.
            # see https://www.psycopg.org/docs/usage.html#transactions-control for details.
            for line in lines:
                # TODO: Not a great way of removing comments. The alternative is to catch
                # the exception sqlalchemy.exc.ProgrammingError "can't execute an empty query"
                if line and not line.startswith("--"):
                    connection.execute(line)
        except sqlalchemy.exc.ProgrammingError as e:
            print("Error: {}".format(e))
        finally:
            connection.close()
