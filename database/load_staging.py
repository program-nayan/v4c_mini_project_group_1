import os
import urllib.parse
import yaml
import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()

class StagingLoader:
    """Handles raw synthesized CSV ingestion into MySQL Staging using external YAML configs."""

    def __init__(self, config_path: str = None):
        # Resolve config.yaml in the root folder if not explicitly provided
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, "config.yaml")

        self.config = self._load_config(config_path)

        # Database credentials fetched from .env
        self.db_user = os.getenv("DB_USER", "root")
        self.db_pass = os.getenv("DB_PASS", "")
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = os.getenv("DB_PORT", "3306")
        self.db_name = os.getenv("DB_NAME", "hr_staging_db")

        if not self.db_pass:
            raise ValueError("❌ Database password not found in .env file!")

        self.engine = self._create_engine()

    def _load_config(self, config_path: str) -> dict:
        """Reads and parses the YAML configuration file."""
        if not os.path.exists(config_path):
            raise FileNotFoundError(f"❌ Configuration file not found at: {config_path}")

        with open(config_path, "r") as file:
            return yaml.safe_load(file)

    def _create_engine(self):
        """Constructs an encoded SQLAlchemy connection engine."""
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
            raise FileNotFoundError(f"❌ Dataset not found at: {csv_path}")

        try:
            print(f"⏳ Reading dataset from {csv_path}...")
            df = pd.read_csv(csv_path)

            print(f"🚀 Inserting {len(df):,} rows into '{self.db_name}.{table_name}'...")
            df.to_sql(
                name=table_name,
                con=self.engine,
                if_exists="replace",
                index=False,
                chunksize=chunksize,
            )
            print(f"✅ Successfully loaded {len(df):,} rows into '{table_name}'!")
            return True

        except SQLAlchemyError as e:
            print(f"❌ Database error during staging ingestion: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error loading staging data: {e}")
            return False

if __name__ == "__main__":
    loader = StagingLoader()
    loader.load_csv_to_staging()