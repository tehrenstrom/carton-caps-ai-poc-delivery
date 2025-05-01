#!/usr/bin/env python3
"""
Database Seeding Script

This script seeds the database with sample data for local development.
It uses the application's async API directly to ensure compatibility and test the API.
"""

import os
import sys
import asyncio
import random
from datetime import datetime
from typing import List, Dict, Any, Optional

# Add parent directory to path so we can import app modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import app modules
from app.database import get_async_session, AsyncSession
from app import crud
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Sample data
SAMPLE_SCHOOLS = [
    {"name": "Cedar Grove Elementary"},
    {"name": "Oakwood High School"},
    {"name": "Riverside Middle School"},
    {"name": "St. Mary's Academy"},
    {"name": "Westlake Preparatory"}
]

SAMPLE_USERS = [
    {"name": "David Jones", "email": "david.jones@example.com", "school_id": 1},
    {"name": "Emily Smith", "email": "emily.smith@example.com", "school_id": 2},
    {"name": "Michael Brown", "email": "michael.brown@example.com", "school_id": 3},
    {"name": "Sarah Wilson", "email": "sarah.wilson@example.com", "school_id": 4},
    {"name": "James Miller", "email": "james.miller@example.com", "school_id": 5},
    {"name": "Jennifer Davis", "email": "jennifer.davis@example.com", "school_id": 1},
    {"name": "Robert Taylor", "email": "robert.taylor@example.com", "school_id": 2},
    {"name": "Lisa Anderson", "email": "lisa.anderson@example.com", "school_id": 3},
    {"name": "William Thomas", "email": "william.thomas@example.com", "school_id": 4},
    {"name": "Jessica Martinez", "email": "jessica.martinez@example.com", "school_id": 5}
]

SAMPLE_PRODUCTS = [
    {"name": "Basic Cap", "description": "Simple and comfortable everyday cap", "price": 19.99},
    {"name": "Premium Cap", "description": "High-quality cap with embroidered logo", "price": 29.99},
    {"name": "Athletic Cap", "description": "Moisture-wicking cap perfect for sports", "price": 24.99},
    {"name": "Winter Cap", "description": "Warm beanie for cold weather", "price": 22.99},
    {"name": "Sun Hat", "description": "Wide-brimmed hat for sun protection", "price": 27.99},
    {"name": "Custom School Cap", "description": "Cap with your school's colors and logo", "price": 34.99},
    {"name": "Graduation Cap", "description": "Ceremonial cap for graduation events", "price": 39.99},
    {"name": "Kids Cap", "description": "Smaller size cap for children", "price": 17.99},
    {"name": "Adjustable Cap", "description": "One-size-fits-all adjustable cap", "price": 21.99},
    {"name": "Vintage Cap", "description": "Classic design with retro styling", "price": 32.99}
]

SAMPLE_FAQS = [
    {"question": "How does the referral program work?", 
     "answer": "When you refer someone to Carton Caps, they receive a 10% discount on their first purchase, and your school receives 15% of their purchase value."},
    {"question": "How much of my purchase goes to schools?", 
     "answer": "20% of every purchase is directed to your associated school."},
    {"question": "Can I change my associated school?", 
     "answer": "Yes, you can change your associated school once every 6 months through your profile settings."},
    {"question": "How do schools receive the funds?", 
     "answer": "Schools receive quarterly disbursements via check or direct deposit."},
    {"question": "Is there a limit to how much a school can earn?", 
     "answer": "No, there's no upper limit. The more purchases associated with a school, the more they earn."},
    {"question": "Can I refer multiple people?", 
     "answer": "Yes, you can refer as many people as you want. There's no limit to referrals."},
    {"question": "How do I track my referrals?", 
     "answer": "You can see all your referrals and their status in the 'My Referrals' section of your account."},
    {"question": "What if I don't have a school to support?", 
     "answer": "You can select from our list of partner schools or choose our general education fund."}
]

SAMPLE_RULES = [
    "Referrals must be new customers who haven't previously made a purchase.",
    "Each referral is eligible for one 10% discount on their first purchase.",
    "Referred customers must make a purchase within 30 days of referral to count.",
    "School disbursements are made quarterly to eligible institutions.",
    "Schools must be accredited educational institutions to receive funds.",
    "Customers can change their associated school once every 6 months.",
    "All purchases made through the referral link must comply with our terms of service."
]

SAMPLE_CONVERSATIONS = [
    {
        "user_id": 1,
        "conversation_id": "conv-1001",
        "messages": [
            {"sender": "user", "message": "Hi, I'm looking for a cap for my son's school."},
            {"sender": "bot", "message": "Hello David! I'd be happy to help you find a cap for your son at Cedar Grove Elementary. We have several options, including our Kids Cap for $17.99 or our Custom School Cap with your school's colors for $34.99. Would you like more details about either of these?"},
            {"sender": "user", "message": "Tell me more about the Custom School Cap."},
            {"sender": "bot", "message": "The Custom School Cap features your school's colors and logo, and is made of high-quality breathable materials. It's adjustable to fit most sizes and is very durable for everyday wear. Remember, 20% of your purchase will go directly to Cedar Grove Elementary through our school support program. Would you like to know about any other products?"}
        ]
    },
    {
        "user_id": 2,
        "conversation_id": "conv-1002",
        "messages": [
            {"sender": "user", "message": "How does the referral program work?"},
            {"sender": "bot", "message": "Hello Emily! The referral program is a great way to support Oakwood High School. When you refer someone to Carton Caps, they receive a 10% discount on their first purchase, and your school receives 15% of their purchase value. This is in addition to the standard 20% that goes to your school from your own purchases. Would you like to know how to refer someone?"}
        ]
    }
]

async def create_schools(session: AsyncSession) -> List[Dict[str, Any]]:
    """Create sample schools in the database."""
    print("➡️ Creating schools...")
    schools = []
    
    # Create using custom SQL since we don't have a specific CRUD function for schools
    for school in SAMPLE_SCHOOLS:
        query = """
        INSERT INTO Schools (name) 
        VALUES (:name)
        ON CONFLICT (name) DO UPDATE SET name = EXCLUDED.name
        RETURNING id, name
        """
        result = await session.execute(query, {"name": school["name"]})
        school_record = result.mappings().one()
        schools.append(dict(school_record))
        print(f"  ✅ Created school: {school['name']}")
    
    return schools

async def create_users(session: AsyncSession) -> List[Dict[str, Any]]:
    """Create sample users in the database."""
    print("➡️ Creating users...")
    users = []
    
    # Create using custom SQL since we don't have a specific create_user CRUD function
    for user in SAMPLE_USERS:
        query = """
        INSERT INTO Users (name, email, school_id) 
        VALUES (:name, :email, :school_id)
        ON CONFLICT (email) DO UPDATE SET 
            name = EXCLUDED.name,
            school_id = EXCLUDED.school_id
        RETURNING id, name, email, school_id
        """
        result = await session.execute(query, user)
        user_record = result.mappings().one()
        users.append(dict(user_record))
        print(f"  ✅ Created user: {user['name']}")
    
    return users

async def create_products(session: AsyncSession) -> List[Dict[str, Any]]:
    """Create sample products in the database."""
    print("➡️ Creating products...")
    products = []
    
    for product in SAMPLE_PRODUCTS:
        # Check if product already exists
        query = """
        SELECT id FROM Products WHERE name = :name
        """
        result = await session.execute(query, {"name": product["name"]})
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing product
            product_data = await crud.update_product(
                session, 
                existing, 
                product["name"], 
                product["description"], 
                product["price"]
            )
            print(f"  ✅ Updated product: {product['name']}")
        else:
            # Create new product
            product_data = await crud.create_product(
                session,
                product["name"],
                product["description"],
                product["price"]
            )
            print(f"  ✅ Created product: {product['name']}")
        
        products.append(product_data)
    
    return products

async def create_faqs(session: AsyncSession) -> List[Dict[str, Any]]:
    """Create sample FAQs in the database."""
    print("➡️ Creating FAQs...")
    faqs = []
    
    for faq in SAMPLE_FAQS:
        # Check if FAQ already exists
        query = """
        SELECT id FROM Referral_FAQs WHERE question = :question
        """
        result = await session.execute(query, {"question": faq["question"]})
        existing = result.scalar_one_or_none()
        
        if existing:
            # Update existing FAQ
            faq_data = await crud.update_faq(
                session, 
                existing, 
                faq["question"], 
                faq["answer"]
            )
            print(f"  ✅ Updated FAQ: {faq['question'][:30]}...")
        else:
            # Create new FAQ
            faq_data = await crud.create_faq(
                session,
                faq["question"],
                faq["answer"]
            )
            print(f"  ✅ Created FAQ: {faq['question'][:30]}...")
        
        faqs.append(faq_data)
    
    return faqs

async def create_rules(session: AsyncSession) -> List[str]:
    """Create sample referral rules in the database."""
    print("➡️ Creating referral rules...")
    rules = []
    
    # Clear existing rules to avoid duplicates (since there's no easy way to detect them)
    await session.execute("DELETE FROM Referral_Rules")
    await session.commit()
    
    for rule in SAMPLE_RULES:
        # Create new rule
        rule_data = await crud.create_referral_rule(session, rule)
        rules.append(rule_data)
        print(f"  ✅ Created rule: {rule[:30]}...")
    
    return rules

async def create_conversations(session: AsyncSession) -> None:
    """Create sample conversation history in the database."""
    print("➡️ Creating sample conversations...")
    
    for conversation_data in SAMPLE_CONVERSATIONS:
        user_id = conversation_data["user_id"]
        conversation_id = conversation_data["conversation_id"]
        
        # Create messages in this conversation
        for message in conversation_data["messages"]:
            await crud.add_conversation_message(
                session,
                user_id,
                conversation_id,
                message["sender"],
                message["message"]
            )
        
        print(f"  ✅ Created conversation {conversation_id} with {len(conversation_data['messages'])} messages")

async def create_tables(session: AsyncSession) -> None:
    """Create database tables if they don't exist."""
    print("➡️ Ensuring database tables exist...")
    
    # Read schema from schema.sql file
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'schema.sql')
    try:
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        # Execute schema SQL
        statements = schema_sql.split(';')
        for statement in statements:
            if statement.strip():
                await session.execute(statement)
        
        await session.commit()
        print("  ✅ Database schema applied successfully")
    except Exception as e:
        print(f"  ❌ Error applying database schema: {e}")
        raise

async def seed_database():
    """Main function to seed the database with sample data."""
    print("🌱 Starting database seeding...")
    
    try:
        # Get database session
        async for session in get_async_session():
            # Create tables if they don't exist
            await create_tables(session)
            
            # Seed data in correct order due to foreign key constraints
            await create_schools(session)
            await create_users(session)
            await create_products(session)
            await create_faqs(session)
            await create_rules(session)
            await create_conversations(session)
            
            print("✅ Database seeded successfully!")
            break  # Exit after one iteration
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(seed_database()) 