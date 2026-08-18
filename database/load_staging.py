import os
import sys
import urllib.parse
import yaml
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

# Ensure parent directory is on sys.path for logger imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from backend.logger import get_logger
except ImportError:
    from logger import get_logger

logger = get_logger(__name__)
load_dotenv()


class StagingLoader:
    """Handles raw synthesized CSV ingestion into MySQL Staging using external YAML configs."""

    def __init__(self, config_path: str = None):
        # Resolve config.yaml in the root folder if not explicitly provided
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, "config.yaml")

        logger.info("Initializing StagingLoader with config: %s", config_path)
        self.config = self._load_config(config_path)

        # Database credentials fetched from .env
        self.db_user = os.getenv("DB_USER", "root")
        self.db_pass = os.getenv("DB_PASS", "")
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = os.getenv("DB_PORT", "3306")
        self.db_name = os.getenv("DB_NAME", "hr_staging_db")

        if not self.db_pass:
            logger.error("Database password not found in .env file!")
            raise ValueError("❌ Database password not found in .env file!")

        self.engine = self._create_engine()
        logger.info("StagingLoader initialized successfully for database: %s", self.db_name)

    def _load_config(self, config_path: str) -> dict:
        """Reads and parses the YAML configuration file."""
        if not os.path.exists(config_path):
            logger.error("Configuration file not found at: %s", config_path)
            raise FileNotFoundError(f"❌ Configuration file not found at: {config_path}")

        with open(config_path, "r") as file:
            cfg = yaml.safe_load(file)
            logger.debug("Config YAML parsed: %s", cfg)
            return cfg

    def _create_engine(self):
        """Constructs an encoded SQLAlchemy connection engine."""
        logger.info("Creating SQLAlchemy connection engine for %s@%s:%s/%s", self.db_user, self.db_host, self.db_port, self.db_name)
        encoded_pass = urllib.parse.quote_plus(self.db_pass)
        connection_url = f"mysql+pymysql://{self.db_user}:{encoded_pass}@{self.db_host}:{self.db_port}/{self.db_name}"
        return create_engine(connection_url)

    def load_csv_to_staging(
        self,
        csv_path: str = None,
        table_name: str = None,
        chunksize: int = None,
    ) -> bool:
        """Loads dataset into MySQL staging table using values from config.yaml as defaults."""
        # Fall back to YAML config if parameters are not explicitly passed
        csv_path = csv_path or self.config["paths"]["processed_data"]
        table_name = table_name or self.config["database"]["staging_table"]
        chunksize = chunksize or self.config["database"]["chunksize"]

        if not os.path.exists(csv_path):
            logger.error("Dataset not found at: %s", csv_path)
            raise FileNotFoundError(f"❌ Dataset not found at: {csv_path}")

        try:
            logger.info("Reading dataset from %s...", csv_path)
            df = pd.read_csv(csv_path)

            logger.info("Inserting %d rows into '%s.%s' (chunksize: %s)...", len(df), self.db_name, table_name, chunksize)
            df.to_sql(
                name=table_name,
                con=self.engine,
                if_exists="replace",
                index=False,
                chunksize=chunksize,
            )
            logger.info("Successfully loaded %d rows into '%s'!", len(df), table_name)
            return True

        except SQLAlchemyError as e:
            logger.error("Database error during staging ingestion: %s", e, exc_info=True)
            return False
        except Exception as e:
            logger.error("Unexpected error loading staging data: %s", e, exc_info=True)
            return False


if __name__ == "__main__":
    loader = StagingLoader()
    loader.load_csv_to_staging()