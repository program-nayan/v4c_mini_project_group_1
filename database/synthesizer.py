import datetime
import os
import random
import yaml
from faker import Faker
import numpy as np
import pandas as pd


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

        self.config = self._load_config(config_path)
        
        # Fallback to YAML config path if base_csv_path is not explicitly provided
        self.base_csv_path = base_csv_path or self.config["paths"]["raw_data"]
        self.target_unique_employees = target_unique_employees

        if not os.path.exists(self.base_csv_path):
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
            raise FileNotFoundError(f"❌ Configuration file not found at: {config_path}")

        with open(config_path, "r") as file:
            return yaml.safe_load(file)

    def load_and_clean_base(self) -> pd.DataFrame:
        """Loads IBM HR dataset and drops uninformative constant columns."""
        df = pd.read_csv(self.base_csv_path)
        redundant_cols = ["EmployeeCount", "StandardHours", "Over18"]
        return df.drop(
            columns=[col for col in redundant_cols if col in df.columns]
        )

    def generate_personal_details(self, count: int) -> pd.DataFrame:
        """Generates synthetic employee identity profiles using Faker."""
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
        return pd.DataFrame(profiles)

    def scale_base_dataset(self) -> pd.DataFrame:
        """Scales base records up to target unique employee count."""
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

        return scaled_df

    def engineer_scd2_history(self, df: pd.DataFrame) -> pd.DataFrame:
        """Engineers historical SCD Type 2 state changes for a ~60% subset of employees."""
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

        return pd.DataFrame(all_records)

    def run_pipeline(
        self,
        output_csv_path: str = None,
    ) -> pd.DataFrame:
        """Executes full synthesis pipeline and saves dataset using config paths."""
        # Fallback to YAML config output path if not explicitly provided
        output_csv_path = output_csv_path or self.config["paths"]["processed_data"]

        print("🚀 Step 1: Scaling base dataset...")
        scaled_df = self.scale_base_dataset()

        print("⚙️ Step 2: Generating SCD Type 2 history...")
        final_df = self.engineer_scd2_history(scaled_df)

        os.makedirs(os.path.dirname(output_csv_path), exist_ok=True)

        print(
            f"💾 Step 3: Saving {len(final_df):,} rows to {output_csv_path}..."
        )
        final_df.to_csv(output_csv_path, index=False)

        print("\n✅ Synthesis Complete!")
        print(f"• Total Records: {len(final_df):,}")
        return final_df


if __name__ == "__main__":
    synthesizer = DataSynthesizer()
    synthesizer.run_pipeline()