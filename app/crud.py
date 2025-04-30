import psycopg2
import psycopg2.extras
import os
from typing import List, Dict, Optional, Any, Tuple
from datetime import datetime, timezone
from dotenv import load_dotenv
import logging
import contextlib

# Imports for async
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

logger = logging.getLogger(__name__)

# --- Refactored Async Functions --- 
async def get_user(session: AsyncSession, user_id: int) -> Optional[Dict[str, Any]]:
    """Fetches user details via ID using async session"""
    query = text("""
        SELECT u.id, u.name, u.email, s.name as school_name 
        FROM Users u LEFT JOIN Schools s ON u.school_id = s.id 
        WHERE u.id = :user_id
    """)
    result = await session.execute(query, {"user_id": user_id})
    user_row = result.mappings().first() 
    return dict(user_row) if user_row else None

async def add_conversation_message(
    session: AsyncSession, user_id: int, conversation_id: str, sender: str, message: str
):
    """Stores a message to the Conversation_History table using async session"""
    query = text("""
        INSERT INTO Conversation_History (user_id, conversation_id, sender, message, timestamp) 
        VALUES (:user_id, :conversation_id, :sender, :message, :timestamp)
    """)
    timestamp = datetime.now(timezone.utc)
    await session.execute(
        query, 
        {
            "user_id": user_id, 
            "conversation_id": conversation_id, 
            "sender": sender, 
            "message": message, 
            "timestamp": timestamp
        }
    )
 
async def get_conversation_history_db(session: AsyncSession, conversation_id: str) -> List[Dict[str, Any]]:
    """Retrieves chronologically ALL messages for a given conversation ID using async session"""
    query = text("""
        SELECT sender, message, timestamp 
        FROM Conversation_History 
        WHERE conversation_id = :conversation_id 
        ORDER BY timestamp ASC
    """)
    result = await session.execute(query, {"conversation_id": conversation_id})
    history_rows = result.fetchall() 
    
    formatted_history = [
        {"role": ("assistant" if row.sender == 'bot' else 'user'), "content": row.message}
        for row in history_rows
    ]
    return formatted_history

async def get_products(session: AsyncSession, limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch a list of products using async session"""
    query = text("SELECT id, name, description, price FROM Products LIMIT :limit")
    result = await session.execute(query, {"limit": limit})
    product_rows = result.mappings().all() 
    return [dict(p) for p in product_rows]

async def get_referral_faqs(session: AsyncSession) -> List[Dict[str, Any]]:
    """Fetches all referral FAQs using async session"""
    query = text("SELECT id, question, answer FROM Referral_FAQs")
    result = await session.execute(query)
    faq_rows = result.mappings().all()
    return [dict(faq) for faq in faq_rows]

async def get_referral_rules(session: AsyncSession) -> List[str]:
    """Fetches all referral rules using async session"""
    query = text("SELECT rule_description FROM Referral_Rules")
    result = await session.execute(query)
    rules = result.scalars().all()
    return rules

async def get_all_users(session: AsyncSession) -> List[Dict[str, Any]]:
    """Fetches all users from the DB using async session"""
    query = text("""
        SELECT u.id, u.name, s.name as school_name
        FROM Users u 
        LEFT JOIN Schools s ON u.school_id = s.id 
        ORDER BY u.name ASC
    """)
    result = await session.execute(query)
    user_rows = result.mappings().all()
    return [dict(u) for u in user_rows]

async def get_product_by_id(session: AsyncSession, product_id: int) -> Optional[Dict[str, Any]]:
    """Fetch a product by ID using async session"""
    query = text("SELECT id, name, description, price FROM Products WHERE id = :product_id")
    result = await session.execute(query, {"product_id": product_id})
    product_row = result.mappings().first()
    return dict(product_row) if product_row else None

async def create_product(session: AsyncSession, name: str, description: str, price: float) -> Dict[str, Any]:
    """Create a new product in the DB using async session"""
    query = text("""
        INSERT INTO Products (name, description, price)
        VALUES (:name, :description, :price)
        RETURNING id, name, description, price
    """)
    result = await session.execute(query, {"name": name, "description": description, "price": price})
    new_product = result.mappings().one()
    await session.commit() # Commit after insert/update/delete
    return dict(new_product)

async def update_product(session: AsyncSession, product_id: int, name: str, description: str, price: float) -> Optional[Dict[str, Any]]:
    """Update an existing product in the DB using async session"""
    query = text("""
        UPDATE Products 
        SET name = :name, description = :description, price = :price
        WHERE id = :product_id
        RETURNING id, name, description, price
    """)
    result = await session.execute(
        query, 
        {"name": name, "description": description, "price": price, "product_id": product_id}
    )
    updated_product = result.mappings().first()
    if updated_product:
        await session.commit()
        return dict(updated_product)
    return None

async def delete_product(session: AsyncSession, product_id: int) -> bool:
    """Delete a product from the DB using async session"""
    query = text("DELETE FROM Products WHERE id = :product_id RETURNING id")
    result = await session.execute(query, {"product_id": product_id})
    deleted_id = result.scalar_one_or_none()
    if deleted_id is not None:
        await session.commit()
        return True
    return False

async def get_faq_by_id(session: AsyncSession, faq_id: int) -> Optional[Dict[str, Any]]:
    """Fetch an FAQ by ID using async session"""
    query = text("SELECT id, question, answer FROM Referral_FAQs WHERE id = :faq_id")
    result = await session.execute(query, {"faq_id": faq_id})
    faq_row = result.mappings().first()
    return dict(faq_row) if faq_row else None

async def create_faq(session: AsyncSession, question: str, answer: str) -> Dict[str, Any]:
    """Creates a new FAQ in the DB using async session"""
    query = text("""
        INSERT INTO Referral_FAQs (question, answer)
        VALUES (:question, :answer)
        RETURNING id, question, answer
    """)
    result = await session.execute(query, {"question": question, "answer": answer})
    new_faq = result.mappings().one()
    await session.commit()
    return dict(new_faq)

async def update_faq(session: AsyncSession, faq_id: int, question: str, answer: str) -> Optional[Dict[str, Any]]:
    """Update an existing FAQ in the DB using async session"""
    query = text("""
        UPDATE Referral_FAQs 
        SET question = :question, answer = :answer
        WHERE id = :faq_id
        RETURNING id, question, answer
    """)
    result = await session.execute(query, {"faq_id": faq_id, "question": question, "answer": answer})
    updated_faq = result.mappings().first()
    if updated_faq:
        await session.commit()
        return dict(updated_faq)
    return None

async def delete_faq(session: AsyncSession, faq_id: int) -> bool:
    """Deletes a FAQ from the DB using async session"""
    query = text("DELETE FROM Referral_FAQs WHERE id = :faq_id RETURNING id")
    result = await session.execute(query, {"faq_id": faq_id})
    deleted_id = result.scalar_one_or_none()
    if deleted_id is not None:
        await session.commit()
        return True
    return False

async def create_referral_rule(session: AsyncSession, rule: str) -> str:
    """Creates a new referral rule in the DB using async session"""
    query = text("""
        INSERT INTO Referral_Rules (rule_description)
        VALUES (:rule)
        RETURNING rule_description
    """)
    result = await session.execute(query, {"rule": rule})
    new_rule = result.scalar_one()
    await session.commit()
    return new_rule

async def update_referral_rule(session: AsyncSession, rule_id: int, rule: str) -> Optional[str]:
    """Update an existing referral rule in the DB using async session"""
    query = text("""
        UPDATE Referral_Rules 
        SET rule_description = :rule 
        WHERE id = :rule_id
        RETURNING rule_description
    """)
    result = await session.execute(query, {"rule_id": rule_id, "rule": rule})
    updated_rule = result.scalar_one_or_none()
    if updated_rule is not None:
        await session.commit()
        return updated_rule
    return None

async def delete_referral_rule(session: AsyncSession, rule_id: int) -> bool:
    """Delete a referral rule from the DB using async session"""
    query = text("DELETE FROM Referral_Rules WHERE id = :rule_id RETURNING id")
    result = await session.execute(query, {"rule_id": rule_id})
    deleted_id = result.scalar_one_or_none()
    if deleted_id is not None:
        await session.commit()
        return True
    return False