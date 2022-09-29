from utility.sql_alchemy import initialize as model_initialize
from utility.sql_alchemy.model import SQLAlchemy_Manager


def initialize(app, echo: bool = False):
    """Initialize SQL Alchemy with application."""
    # get application config.
    sql_alchemy_database_uri = app.config['SQLALCHEMY_DATABASE_URI']

    from sqlalchemy import create_engine
    # an Engine, which the Session will use for connection resources.
    engine = create_engine(sql_alchemy_database_uri)

    # create sqlalchemy manager.
    mock_sql_alchemy_manager = SQLAlchemy_Manager(Engine=engine)

    # execute create test database command.
    mock_sql_alchemy_manager.Engine.execute("CREATE DATABASE IF NOT EXISTS test_db;")

    # initialize model.
    app.config['SQLALCHEMY_DATABASE_URI'] = f"{sql_alchemy_database_uri}test_db"
    model_initialize(app, echo)


def terminate(echo: bool = False):
    """Drop test database."""
    from testing.globals import app
    # get application config.
    sql_alchemy_database_uri = app.config['SQLALCHEMY_DATABASE_URI']

    from sqlalchemy import create_engine
    # an Engine, which the Session will use for connection resources.
    engine = create_engine(sql_alchemy_database_uri, echo=echo)

    # create sqlalchemy manager.
    mock_sql_alchemy_manager = SQLAlchemy_Manager(Engine=engine)

    # drop test database.
    mock_sql_alchemy_manager.Engine.execute("DROP DATABASE IF EXISTS test_db;")
