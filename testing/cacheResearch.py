import psycopg2
import os
from psycopg2 import sql
from datetime import date
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# --- Database Configuration (Now loaded from environment variables) ---
# Ensure DB_HOST, DB_USER, DB_PASSWORD, DB_PORT are set in your .env file or environment
NEW_DB_NAME = "research"
TABLE_NAME = "research_entries"

# --- Sample Data ---
research_text = """
{
  "portfolio": [
    {
      "asset_class": "semiconductors",
      "allocation": 14,
      "reason": "Secular AI and data center chip growth, industry leadership, and strong capex/R&D spending drive outsized return potential."
    },
    {
      "asset_class": "application_software",
      "allocation": 5,
      "reason": "Digital transformation, SaaS growth, and defensive/recurring revenue models enhance stability and upside."
    },
    {
      "asset_class": "technology_hardware_storage_and_peripherals",
      "allocation": 5,
      "reason": "Cloud/server hardware, storage, and device demand from AI and enterprise digitization."
    },
    {
      "asset_class": "beverages",
      "allocation": 3,
      "reason": "Strong brands, pricing power, and resilience in inflationary periods."
    },
    {
      "asset_class": "packaged_foods_and_meats",
      "allocation": 4,
      "reason": "Defensive demand, pricing power, and margin stability in volatile markets."
    },
    {
      "asset_class": "household_products",
      "allocation": 3,
      "reason": "Essential goods, stable cash flows, and innovation-led growth."
    },
    {
      "asset_class": "investment_grade_corporate_bond_etfs",
      "allocation": 11,
      "reason": "Attractive yields, low default risk, and strong credit quality for core fixed income allocation."
    },
    {
      "asset_class": "high_yield_junk_bond_etfs",
      "allocation": 4,
      "reason": "Tactical income boost with focus on quality to manage default risk."
    },
    {
      "asset_class": "treasury_and_inflation_bond_etfs",
      "allocation": 8,
      "reason": "Diversification, safe haven, and inflation protection amid uncertain macro backdrop."
    },
    {
      "asset_class": "precious_metals_etfs",
      "allocation": 6,
      "reason": "Gold as a hedge against inflation, geopolitical risk, and central bank demand."
    },
    {
      "asset_class": "industrial_reits",
      "allocation": 5,
      "reason": "Logistics and cold storage REITs benefit from e-commerce and supply chain trends."
    },
    {
      "asset_class": "data_center_reits",
      "allocation": 3,
      "reason": "Secular growth in AI and cloud computing drives demand for data centers."
    },
    {
      "asset_class": "multi_utilities",
      "allocation": 3,
      "reason": "Stable dividends and regulatory support in a defensive sector."
    },
    {
      "asset_class": "renewable_electricity",
      "allocation": 3,
      "reason": "Clean energy transition and ESG demand provide growth and resilience."
    },
    {
      "asset_class": "single_country_and_regional_etfs_in_emerging_markets",
      "allocation": 4,
      "reason": "Exposure to IT/tech leaders and commodity producers in Asia, Latin America, and Africa."
    },
    {
      "asset_class": "industrial_metals",
      "allocation": 2,
      "reason": "Long-term demand from electrification, infrastructure, and EVs; copper, nickel, and lithium in focus."
    },
    {
      "asset_class": "cash",
      "allocation": 7,
      "reason": "Liquidity for tactical rebalancing and risk management in volatile markets."
    }
  ]
}
"""

def setup_research_table_and_insert_data(db_name, table_name, content):
    """Connects to the specific database using env vars, creates schema/table if needed, and inserts data."""
    conn = None
    cursor = None
    try:
        # Get connection details from environment variables
        host = os.environ.get("DB_HOST")
        user = os.environ.get("DB_USER")
        password = os.environ.get("DB_PASSWORD")
        port = os.environ.get("DB_PORT")

        if not all([host, user, password, port]):
            print("Error: Database connection details (DB_HOST, DB_USER, DB_PASSWORD, DB_PORT) not found in environment variables.")
            return

        # Get current date for schema name
        today_str = date.today().strftime("%Y_%m_%d")
        schema_identifier = sql.Identifier(today_str)
        table_identifier = sql.Identifier(table_name)

        # Connect to the newly created or existing research database
        conn = psycopg2.connect(
            host=host,
            user=user,
            password=password,
            port=port,
            dbname=db_name
        )
        cursor = conn.cursor()

        # Create schema if it doesn't exist
        create_schema_query = sql.SQL("CREATE SCHEMA IF NOT EXISTS {}").format(schema_identifier)
        cursor.execute(create_schema_query)
        print(f"Schema '{today_str}' ensured to exist in database '{db_name}'.")

        # Create table if it doesn't exist within the date-based schema
        # Use TEXT data type for potentially large research content
        create_table_query = sql.SQL("""
            CREATE TABLE IF NOT EXISTS {}.{} (
                id SERIAL PRIMARY KEY,
                content TEXT,
                inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """).format(schema_identifier, table_identifier)
        cursor.execute(create_table_query)
        print(f"Table '{table_name}' ensured to exist in schema '{today_str}'.")

        # Insert the research data into the schema-qualified table
        insert_query = sql.SQL("INSERT INTO {}.{} (content) VALUES (%s)").format(schema_identifier, table_identifier)
        cursor.execute(insert_query, (content,))
        conn.commit() # Commit the transaction to save the data
        print(f"Successfully inserted research text into '{today_str}.{table_name}'.")

    except psycopg2.Error as e:
        print(f"Error connecting to '{db_name}', creating table, or inserting data: {e}")
        if conn:
            conn.rollback() # Roll back in case of error during insertion
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
        print(f"Connection to '{db_name}' closed.")

if __name__ == "__main__":
    print("Starting script...")
    setup_research_table_and_insert_data(NEW_DB_NAME, TABLE_NAME, research_text)
    print("Script finished.")
