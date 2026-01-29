#!/usr/bin/python3
# -*- coding: utf-8 -*-
from alembic import config as alembic_config
from alembic import command

from config import Config
import logging
logging.basicConfig()

def downgrade_to_base():
    alembic_Config = alembic_config.Config(Config.ALEMBIC_INI_PATH)
    alembic_Config.set_main_option("script_location", str(Config.ALEMBIC_SCRIPT_PATH))
    command.downgrade(alembic_Config, "base")

def run_migrations(conn_url:str):
    alembic_Config = alembic_config.Config(Config.ALEMBIC_INI_PATH)
    alembic_Config.set_main_option("script_location", str(Config.ALEMBIC_SCRIPT_PATH))
    alembic_Config.set_main_option("sqlalchemy.url", conn_url)
    command.upgrade(alembic_Config, Config.ALEMBIC_REVISION)

