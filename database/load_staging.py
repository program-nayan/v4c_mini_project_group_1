import os
import pandas as pd
import urllib.parse
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

# Load environment variables from .env file
load_dotenv()

class StagingLoader:
    """Handles the ingestion of raw synthesized CSV data into MySQL Staging without exposing passwords."""

    def __init__(self):
        # Fetch values from environment variables with safe defaults
        self.db_user = os.getenv("DB_USER", "root")
        self.db_pass = os.getenv("DB_PASS", "")
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = os.getenv("DB_PORT", "3306")
        self.db_name = os.getenv("DB_NAME", "hr_staging_db")
        
        if not self.db_pass:
            raise ValueError("❌ Database password not found in .env file!")
            
        self.engine = self._create_engine()

    def _create_engine(self):
        """Constructs an encoded SQLAlchemy connection engine."""
        encoded_pass = urllib.parse.quote_plus(self.db_pass)
        connection_url = f"mysql+pymysql://{self.db_user}:{encoded_pass}@{self.db_host}:{self.db_port}/{self.db_name}"
        return create_engine(connection_url)

    def load_csv_to_staging(
        self,
        csv_path: str = "data/processed/synthesized_employee_data.csv",
        table_name: str = "staging_employees",
        chunksize: int = 5000,
    ) -> bool:
        """Reads the synthesized CSV file and loads it into MySQL staging table in batches."""
        if not os.path.exists(csv_path):
            if os.path.exists("synthesized_employee_data.csv"):
                csv_path = "synthesized_employee_data.csv"
            else:
                raise FileNotFoundError(f"Dataset not found at: {csv_path}")

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