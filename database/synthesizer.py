import datetime
import os
import sys
import random
import yaml
from faker import Faker
import numpy as np
import pandas as pd

# Ensure parent directory is on sys.path for logger imports
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
try:
    from backend.logger import get_logger
except ImportError:
    from logger import get_logger

logger = get_logger(__name__)


class DataSynthesizer:
    """Synthesizes and scales base HR dataset to 100,000+ rows with SCD Type 2 history using YAML config."""

    def __init__(
        self,
        config_path: str = None,
        base_csv_path: str = None,
        target_unique_employees: int = 65000,
    ):
        # Resolve config.yaml path dynamically relative to project root
        if config_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            config_path = os.path.join(base_dir, "config.yaml")
            if not os.path.exists(config_path):
                config_path = "config.yaml"

        logger.info("Initializing DataSynthesizer with config path: %s", config_path)
        self.config = self._load_config(config_path)
        
        # Fallback to YAML config path if base_csv_path is not explicitly provided
        self.base_csv_path = base_csv_path or self.config["paths"]["raw_data"]
        self.target_unique_employees = target_unique_employees
        logger.info("Base CSV Path: %s, Target Unique Employees: %d", self.base_csv_path, self.target_unique_employees)

        if not os.path.exists(self.base_csv_path):
            logger.error("Base CSV not found at: %s", self.base_csv_path)
            raise FileNotFoundError(f"❌ Base CSV not found at: {self.base_csv_path}")

        self.fake = Faker()

        # Seed for reproducible synthetic data
        Faker.seed(42)
        np.random.seed(42)
        random.seed(42)

        self.dept_map = {
            "Sales": 1,
            "Research & Development": 2,
            "Human Resources": 3,
        }

    def _load_config(self, config_path: str) -> dict:
        """Reads and parses the YAML configuration file."""
        if not os.path.exists(config_path):
            logger.error("Configuration file not found at: %s", config_path)
            raise FileNotFoundError(f"❌ Configuration file not found at: {config_path}")

        with open(config_path, "r") as file:
            cfg = yaml.safe_load(file)
            logger.debug("Parsed synthesizer configuration: %s", cfg)
            return cfg

    def load_and_clean_base(self) -> pd.DataFrame:
        """Loads IBM HR dataset and drops uninformative constant columns."""
        logger.info("Loading and cleaning raw dataset from %s", self.base_csv_path)
        df = pd.read_csv(self.base_csv_path)
        redundant_cols = ["EmployeeCount", "StandardHours", "Over18"]
        cleaned_df = df.drop(
            columns=[col for col in redundant_cols if col in df.columns]
        )
        logger.info("Base dataset loaded with %d rows and %d columns", len(cleaned_df), len(cleaned_df.columns))
        return cleaned_df

    def generate_personal_details(self, count: int) -> pd.DataFrame:
        """Generates synthetic employee identity profiles using Faker."""
        logger.info("Generating %d synthetic identity profiles via Faker...", count)
        profiles = []
        for _ in range(count):
            first_name = self.fake.first_name()
            last_name = self.fake.last_name()
            email = f"{first_name.lower()}.{last_name.lower()}{random.randint(10, 99)}@company.com"
            phone = self.fake.phone_number()

            profiles.append(
                {
                    "first_name": first_name,
                    "last_name": last_name,
                    "email": email,
                    "phone_number": phone,
                }
            )
        logger.info("Finished generating %d identity profiles", count)
        return pd.DataFrame(profiles)

    def scale_base_dataset(self) -> pd.DataFrame:
        """Scales base records up to target unique employee count."""
        logger.info("Step 1: Scaling base dataset up to %d records...", self.target_unique_employees)
        base_df = self.load_and_clean_base()
        repeat_factor = (self.target_unique_employees // len(base_df)) + 1

        scaled_df = (
            pd.concat([base_df] * repeat_factor, ignore_index=True)
            .iloc[: self.target_unique_employees]
            .copy()
        )
        scaled_df["employee_id"] = np.arange(
            10001, 10001 + self.target_unique_employees
        )

        faker_df = self.generate_personal_details(self.target_unique_employees)
        scaled_df = pd.concat([scaled_df, faker_df], axis=1)

        scaled_df["department_id"] = (
            scaled_df["Department"]
            .map(self.dept_map)
            .fillna(1)
            .astype(int)
        )

        today = datetime.date(2026, 8, 15)
        scaled_df["hire_date"] = [
            today - datetime.timedelta(days=int(365 * np.random.uniform(1, 10)))
            for _ in range(self.target_unique_employees)
        ]

        logger.info("Step 1 complete: Scaled dataset has %d unique employees", len(scaled_df))
        return scaled_df

    def engineer_scd2_history(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineers historical SCD Type 2 state changes for a ~60% subset of employees."""
        logger.info("Step 2: Engineering SCD Type 2 history across %d employees...", len(df))
        all_records = []
        today = datetime.date(2026, 8, 15)

        for _, row in df.iterrows():
            has_history = random.random() < 0.60

            if has_history:
                days_since_hire = (today - row["hire_date"]).days
                if days_since_hire > 365:
                    change_days = random.randint(
                        180, min(days_since_hire - 30, 1095)
                    )
                    change_date = row["hire_date"] + datetime.timedelta(
                        days=change_days
                    )
                else:
                    change_date = row["hire_date"] + datetime.timedelta(
                        days=180
                    )

                # Historical Record (Expired)
                hist_row = row.copy()
                hist_row["MonthlyIncome"] = int(
                    row["MonthlyIncome"] * random.uniform(0.75, 0.90)
                )
                hist_row["JobLevel"] = max(1, row["JobLevel"] - 1)

                if random.random() < 0.30:
                    hist_row["department_id"] = (
                        row["department_id"] % 3
                    ) + 1

                hist_row["effective_start_date"] = row["hire_date"]
                hist_row["effective_end_date"] = change_date
                hist_row["is_current"] = 0
                hist_row["change_reason"] = random.choice(
                    [
                        "Promotion & Salary Hike",
                        "Department Transfer",
                        "Annual Merit Increase",
                    ]
                )
                all_records.append(hist_row)

                # Active Current Record
                curr_row = row.copy()
                curr_row["effective_start_date"] = change_date
                curr_row["effective_end_date"] = datetime.date(9999, 12, 31)
                curr_row["is_current"] = 1
                curr_row["change_reason"] = "Current Active State"
                all_records.append(curr_row)

            else:
                curr_row = row.copy()
                curr_row["effective_start_date"] = row["hire_date"]
                curr_row["effective_end_date"] = datetime.date(9999, 12, 31)
                curr_row["is_current"] = 1
                curr_row["change_reason"] = "Initial Onboarding"
                all_records.append(curr_row)

        history_df = pd.DataFrame(all_records)
        logger.info("Step 2 complete: Engineered SCD Type 2 history resulting in %d total rows", len(history_df))
        return history_df

    def run_pipeline(
        self,
        output_csv_path: str = None,
    ) -> pd.DataFrame:
        """Executes full synthesis pipeline and saves dataset using config paths."""
        output_csv_path = output_csv_path or self.config["paths"]["processed_data"]

        logger.info("Starting synthesis pipeline. Output target: %s", output_csv_path)
        scaled_df = self.scale_base_dataset()
        final_df = self.engineer_scd2_history(scaled_df)

        os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)

        logger.info("Step 3: Saving %d rows to %s...", len(final_df), output_csv_path)
        final_df.to_csv(output_csv_path, index=False)

        logger.info("✅ Synthesis Complete! Total Records Generated: %d", len(final_df))
        return final_df


if __name__ == "__main__":
    synthesizer = DataSynthesizer()
    synthesizer.run_pipeline()