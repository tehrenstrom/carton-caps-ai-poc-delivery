import psycopg2
import psycopg2.extras
import os
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, UTC
from dotenv import load_dotenv
import logging
import contextlib

logger = logging.getLogger(__name__)
load_dotenv()

# DB Connection #
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    logger.critical("DATABASE_URL env var not set.")

# Context manager for DB connection and cursor #
@contextlib.contextmanager
def db_cursor(commit=False):
    """cursor for managed transactions"""
    conn = None
    cursor = None
    try:
        conn = psycopg2.connect(DATABASE_URL)
        cursor = conn.cursor()
        logger.debug(f"DB Connection opened. Commit={commit}")
        yield cursor
        if commit:
            conn.commit()
            logger.debug("DB Transaction committed.")
    except psycopg2.Error as e:
        logger.error(f"Database Error: {e}")
        if conn:
            conn.rollback()
            logger.warning("DB Transaction rolled back due to error.")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            logger.debug("DB Connection closed.")

# Helper to convert psycopg2 rows to dicts for Python dicts #
def map_row_to_dict(cursor, row) -> Dict[str, Any]:
    if not row:
        return None
    return dict(zip([col[0] for col in cursor.description], row))

# User POC funstions #
def get_user(user_id: int) -> Optional[Dict[str, Any]]:
    """Fetches user details via ID"""
    with db_cursor() as cur:
        cur.execute(
            """SELECT u.id, u.name, u.email, s.name as school_name 
               FROM Users u LEFT JOIN Schools s ON u.school_id = s.id 
               WHERE u.id = %s""", 
            (user_id,)
        )
        user = cur.fetchone()
        return map_row_to_dict(cur, user)

def get_all_users() -> List[Dict[str, Any]]:
    """Fetches all users from the DB"""
    with db_cursor() as cur:
        cur.execute("""
            SELECT u.id, u.name, s.name as school_name
            FROM Users u 
            LEFT JOIN Schools s ON u.school_id = s.id 
            ORDER BY u.name ASC
        """)
        users = cur.fetchall()
        return [map_row_to_dict(cur, user) for user in users if user]

# Conversation History Functions #
def add_conversation_message(user_id: int, conversation_id: str, sender: str, message: str):
    """Stores a message to the Conversation_History table"""
    with db_cursor(commit=True) as cur:
        timestamp = datetime.now(UTC)
        cur.execute(
            """INSERT INTO Conversation_History (user_id, conversation_id, sender, message, timestamp) 
               VALUES (%s, %s, %s, %s, %s)""",
            (user_id, conversation_id, sender, message, timestamp)
        )

def get_conversation_history_db(conversation_id: str) -> List[Dict[str, Any]]:
    """Retrieves chronologically ALL messages for a given conversation ID from the database"""
    with db_cursor() as cur:
        cur.execute(
            """SELECT sender, message, timestamp 
               FROM Conversation_History 
               WHERE conversation_id = %s 
               ORDER BY timestamp ASC""",
            (conversation_id,)
        )
        history = cur.fetchall()
        formatted_history = [
            {"role": ("assistant" if row[0] == 'bot' else 'user'), "content": row[1]}
            for row in history if row
        ]
        return formatted_history

# Product Functions #
def get_product_by_id(product_id: int) -> Optional[Dict[str, Any]]:
    """Fetch products by ID"""
    with db_cursor() as cur:
        cur.execute("SELECT id, name, description, price FROM Products WHERE id = %s", (product_id,))
        product = cur.fetchone()
        return map_row_to_dict(cur, product)

def get_products(limit: int = 5) -> List[Dict[str, Any]]:
    """Fetch a list of products"""
    with db_cursor() as cur:
        cur.execute("SELECT id, name, description, price FROM Products LIMIT %s", (limit,))
        products = cur.fetchall()
        return [map_row_to_dict(cur, p) for p in products if p]
    
def create_product(name: str, description: str, price: float) -> Dict[str, Any]:
    """Create a new product in the DB"""
    with db_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO Products (name, description, price)
               VALUES (%s, %s, %s)
               RETURNING id, name, description, price""",
            (name, description, price)
        )
        product = cur.fetchone()
        return map_row_to_dict(cur, product)
    
def update_product(product_id: int, name: str, description: str, price: float) -> Optional[Dict[str, Any]]:
    """Update an existing product in the DB"""
    with db_cursor(commit=True) as cur:
        cur.execute(
            """UPDATE Products 
               SET name = %s, description = %s, price = %s
               WHERE id = %s
               RETURNING id, name, description, price""",
            (name, description, price, product_id)
        )
        product = cur.fetchone()
        return map_row_to_dict(cur, product)

def delete_product(product_id: int) -> bool:
    """Delete a product from the DB"""
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM Products WHERE id = %s", (product_id,))
        deleted = cur.rowcount > 0
        return deleted

# KB Management Functions #
def get_faq_by_id(faq_id: int) -> Optional[Dict[str, Any]]:
    """Fetch an FAQ by Id"""
    with db_cursor() as cur:
        cur.execute("SELECT id, question, answer FROM Referral_FAQs WHERE id = %s", (faq_id,))
        faq = cur.fetchone()
        return map_row_to_dict(cur, faq)
    
def create_faq(question: str, answer: str) -> Dict[str, Any]:
    """Creates a new FAQ in the DB"""
    with db_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO Referral_FAQs (question, answer)
               VALUES (%s, %s)
               RETURNING id, question, answer""",
            (question, answer)
        )
        faq = cur.fetchone()
        return map_row_to_dict(cur, faq)
    
def update_faq(faq_id: int, question: str, answer: str) -> Optional[Dict[str, Any]]:
    """Update an existing FAQ in the DB"""
    with db_cursor(commit=True) as cur:
        cur.execute(
            """UPDATE Referral_FAQs 
               SET question = %s, answer = %s
               WHERE id = %s
               RETURNING id, question, answer""",
            (question, answer, faq_id)
        )
        faq = cur.fetchone()
        return map_row_to_dict(cur, faq)

def delete_faq(faq_id: int) -> bool:
    """Deletes a FAQ from the DB"""
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM Referral_FAQs WHERE id = %s", (faq_id,))
        deleted = cur.rowcount > 0
        return deleted

def get_referral_faqs() -> List[Dict[str, Any]]:
    """Fetches all referral FAQs"""
    with db_cursor() as cur:
        cur.execute("SELECT id, question, answer FROM Referral_FAQs")
        faqs = cur.fetchall()
        return [map_row_to_dict(cur, faq) for faq in faqs if faq]
    
def get_referral_rules() -> List[str]:
    """Fetches all referral rules"""
    with db_cursor() as cur:
        cur.execute("SELECT rule_description FROM Referral_Rules")
        rules = cur.fetchall()
        return [row[0] for row in rules if row]

def create_referral_rule(rule: str) -> str:
    """Creates a new referral rule in the DB"""
    with db_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO Referral_Rules (rule_description)
               VALUES (%s)
               RETURNING rule_description""",
            (rule,)
        )
        rule_desc = cur.fetchone()[0]
        return rule_desc

def update_referral_rule(rule_id: int, rule: str) -> Optional[str]:
    """Update an existing referral rule in the DB"""
    with db_cursor(commit=True) as cur:
        cur.execute(
            """UPDATE Referral_Rules 
               SET rule_description = %s 
               WHERE id = %s
               RETURNING rule_description""",
            (rule, rule_id)
        )
        result = cur.fetchone()
        return result[0] if result else None

def delete_referral_rule(rule_id: int) -> bool:
    """Delete a referral rule from the DB"""
    with db_cursor(commit=True) as cur:
        cur.execute("DELETE FROM Referral_Rules WHERE id = %s", (rule_id,))
        deleted = cur.rowcount > 0
        return deleted 