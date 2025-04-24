import requests
import os
import sys
import sqlite3
from dotenv import load_dotenv
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

load_dotenv()

SQLITE_DB_PATH = "database/Carton Caps Data.sqlite" # Source for products/schools
API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000")
PRODUCTS_ENDPOINT = f"{API_BASE_URL}/products"
FAQS_ENDPOINT = f"{API_BASE_URL}/faqs"
RULES_ENDPOINT = f"{API_BASE_URL}/referral-rules"

# Note: API endpoints to create Schools or Users not implemented in this POC

# Seed Data Definition (FAQs and Rules hardcoded from PDF
# Products data will be fetched from SQLite below
# Schools data will be fetched from SQLite but only logged

FAQS_DATA = [
    {'question': 'What is the Carton Caps Referral Program?', 'answer': 'The Carton Caps Referral Program allows you to invite your friends to join the Carton Caps app. When your friend signs up using your unique referral link and completes onboarding, both of you receive a special bonus in your Carton Caps accounts.'},
    {'question': 'How do I refer a friend?', 'answer': 'You can refer a friend directly from the Carton Caps app. Simply tap on the account icon, tap “Invite Friends”, copy the referral code or share a link using the buttons.'},
    {'question': 'What does my friend experience when they join via my link?', 'answer': 'Referred users get a customized onboarding experience that introduces them to Carton Caps and highlights how the program supports schools. They\'ll also be notified about the bonus they and you will receive.'},
    {'question': 'When do we receive the bonus?', 'answer': 'Both you and your referred friend will receive the bonus after your friend completes onboarding and links their Carton Caps account to a preferred school to support.'},
    {'question': 'What kind of bonus do we get?', 'answer': 'The bonus may vary. It could be additional Carton Caps points or a special in-app reward. The current bonus will be displayed on the referral page in the app.'},
    {'question': 'Can I refer more than one person?', 'answer': 'Absolutely! There\'s no limit to how many friends you can invite. You’ll earn a bonus for each successful referral!'},
    {'question': 'My friend forgot to use my link. Can we still get the bonus?', 'answer': 'Unfortunately, referrals must be tracked through your unique link. If your friend signs up without it, the referral won’t be credited automatically.'},
    {'question': 'Can I refer someone who already uses Carton Caps?', 'answer': 'The referral program is only available for new users. Existing users or users who uninstall and reinstall the app are not eligible for referral bonuses.'},
    {'question': 'How can I track my referrals?', 'answer': 'In the “Refer a Friend” section of the app, you can view the status of each referral - whether your friend has signed up, completed onboarding, and whether your bonus has been awarded.'},
    {'question': 'Why haven’t I received my bonus yet?', 'answer': 'There may be a delay if your referred friend hasn’t completed onboarding or hasn’t linked to a school. If it’s been more than 48 hours and you believe there\'s an issue, contact our support team via the app.'},
    {'question': 'Are there any restrictions or abuse policies?', 'answer': 'Yes. Carton Caps reserves the right to withhold bonuses or disable accounts if we detect fraudulent or abusive behavior, including self-referrals, spamming, or fake accounts.'}
]

RULES_DATA = [
    {'rule': 'Eligibility: All existing Carton Caps users with a verified account are eligible to refer friends.'},
    {'rule': 'Eligibility: Referred users must be new to the Carton Caps program.'},
    {'rule': 'Eligibility: Each user must be a legal resident of the United States.'},
    {'rule': 'Referral Process: Users can share a unique referral code or link via the Carton Caps app.'},
    {'rule': 'Referral Process: The referred user must use the referral code or link during the sign-up process or within a defined window after first installing the app (e.g., within 48 hours).'},
    {'rule': 'Reward Structure: Referrer receives bonus (e.g., $5 credit) when referred user completes onboarding and performs a qualifying action (first scan or links school).'},
    {'rule': 'Reward Structure: Referred User receives bonus (e.g., $5) upon successful sign-up and qualifying action.'},
    {'rule': 'Reward Structure: Bonuses are credited to Carton Caps accounts and may be limited to school donations.'},
    {'rule': 'Limitations & Abuse: Self-referrals are not allowed.'},
    {'rule': 'Limitations & Abuse: Carton Caps may use fraud detection to block suspicious referrals.'},
    {'rule': 'Limitations & Abuse: Referrals may not be paid for or promoted via misleading methods.'},
    {'rule': 'Program Changes: Carton Caps reserves the right to modify or terminate the referral program at any time.'},
    {'rule': 'Program Changes: Carton Caps reserves the right to withhold rewards for suspected abuse.'}
]

# Helper Functions #
def check_api_status():
    """Check if the API server is running before attempting to seed."""
    try:
        ping_url = f"{API_BASE_URL}/docs"
        response = requests.get(ping_url, timeout=5) # Add timeout
        response.raise_for_status() # Raise an exception for bad status codes (4xx or 5xx)
        logger.info(f"API server is reachable at {API_BASE_URL}")
        return True
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection Error: Could not connect to API server at {API_BASE_URL}. Is it running?")
    except requests.exceptions.Timeout:
        logger.error(f"Connection Timed Out trying to reach {API_BASE_URL}.")
    except requests.exceptions.RequestException as e:
        logger.error(f"Error checking API status at {ping_url}: {e}")
    return False

def fetch_sqlite_data(query: str):
    """Generic function to fetch data from SQLite."""
    if not os.path.exists(SQLITE_DB_PATH):
        logger.error(f"SQLite database file not found at: {SQLITE_DB_PATH}")
        return []

    conn = None
    data = []
    try:
        conn = sqlite3.connect(SQLITE_DB_PATH)
        conn.row_factory = sqlite3.Row # Access columns by name
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        data = [dict(row) for row in rows] # Convert sqlite3.Row to dict
    except sqlite3.Error as e:
        logger.error(f"Error reading from SQLite database {SQLITE_DB_PATH}: {e}")
    finally:
        if conn:
            conn.close()
    return data

def fetch_sqlite_products():
    """Fetches product data (name, description, price) from SQLite."""
    # Ensure column names match the Products table in the SQLite file
    query = "SELECT name, description, price FROM Products"
    products = fetch_sqlite_data(query)
    logger.info(f"Fetched {len(products)} products from SQLite DB.")
    return products

def fetch_sqlite_schools():
    """Fetches school names from SQLite."""
    # Ensure column names match the Schools table in the SQLite file
    query = "SELECT name FROM Schools ORDER BY name"
    schools = fetch_sqlite_data(query)
    logger.info(f"Fetched {len(schools)} schools from SQLite DB.")
    return schools

def post_data(endpoint: str, data: dict, item_type: str):
    """Sends a single item to a POST endpoint."""
    item_name = data.get('name') or data.get('question') or data.get('rule') or 'Unknown Item'
    try:
        # Ensure price is float if it exists and is not None
        if 'price' in data and data['price'] is not None:
            try:
                data['price'] = float(data['price'])
            except (ValueError, TypeError):
                logger.error(f"Invalid price value '{data['price']}' for {item_type} '{item_name[:50]}...'. Skipping.")
                return False

        response = requests.post(endpoint, json=data, timeout=10) # Add timeout

        # Check for HTTP errors (4xx or 5xx)
        response.raise_for_status()

        # Check for successful creation (e.g., 200 OK or 201 Created)
        if response.status_code == 200:
            logger.info(f"Successfully seeded {item_type}: {item_name[:50]}...")
            return True
        else:
            logger.warning(f"Received unexpected status code {response.status_code} for {item_type}: {item_name[:50]}... - Response: {response.text}")
            return False

    except requests.exceptions.HTTPError as http_err:
        # Log HTTP errors (like 422 validation or 500 server error)
        logger.warning(f"HTTP error seeding {item_type} '{item_name[:50]}...': {http_err} - Response: {http_err.response.text}")
        return False # Count as failed/skipped
    except requests.exceptions.ConnectionError:
        logger.error(f"Connection error seeding {item_type} '{item_name[:50]}...'. Is the API server running?")
        sys.exit(1) # Exit script if connection fails during seeding
    except requests.exceptions.RequestException as req_err:
        logger.error(f"Error seeding {item_type} '{item_name[:50]}...': {req_err}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error seeding {item_type} '{item_name[:50]}...': {e}")
        return False

def seed_items(endpoint: str, data_list: list, item_type: str):
    """Iterates through a list of data and posts each item."""
    if not data_list:
        logger.info(f"No {item_type} data provided to seed.")
        return

    logger.info(f"Attempting to seed {len(data_list)} {item_type}s via API ({endpoint})...")
    success_count = 0
    fail_count = 0
    for item_data in data_list:
        if not post_data(endpoint, item_data, item_type):
            fail_count += 1
            # Optional: break on first failure?
        else:
            success_count += 1

    logger.info(f"{item_type} seeding complete. Success: {success_count}, Failed/Skipped: {fail_count}")

# --- Main Execution ---
def main():
    """Main function to check API, fetch SQLite data, and seed via API."""
    logger.info("--- Starting API Seeding Script ---")

    if not check_api_status():
        sys.exit(1)

    # 1. Fetch data from SQLite
    products_to_seed = fetch_sqlite_products()
    schools_from_sqlite = fetch_sqlite_schools() # Fetch schools

    # Log fetched schools (cannot seed via API in this POC)
    if schools_from_sqlite:
        school_names = [s.get('name', 'N/A') for s in schools_from_sqlite]
        logger.info(f"Schools found in SQLite (cannot seed via API): {school_names}")
    else:
        logger.warning("No schools found in SQLite DB.")

    # 2. Seed Products via API using fetched data
    seed_items(PRODUCTS_ENDPOINT, products_to_seed, "Product")

    # 3. Seed FAQs & Rules via API using hardcoded data
    seed_items(FAQS_ENDPOINT, FAQS_DATA, "FAQ")
    seed_items(RULES_ENDPOINT, RULES_DATA, "Referral Rule")

    logger.info("--- Seeding Script Finished ---")

if __name__ == "__main__":
    main()