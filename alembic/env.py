from logging.config import fileConfig
from sqlalchemy import engine_from_config, pool
from alembic import context
import os
import importlib
import pkgutil

# --- Load Configurations ---
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- Dynamically Load Models ---
def import_models_from_package(package_name):
    """Import all models from a given package."""
    package = importlib.import_module(package_name)
    for _, module_name, is_pkg in pkgutil.walk_packages(package.__path__, package.__name__ + "."):
        if not is_pkg:
            importlib.import_module(module_name)

# Load all models in the app.models directory
import_models_from_package("app.models")

# Import Base metadata after loading models
from app.database import Base
target_metadata = Base.metadata

# --- Offline Migrations ---
def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()

# --- Online Migrations ---
def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()

# --- Determine Migration Mode ---
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
