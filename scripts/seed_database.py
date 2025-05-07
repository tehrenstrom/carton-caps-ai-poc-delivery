"""
Database Seeding Script

This script seeds the database with sample data for local development.
It uses the application's async API directly in some scenarios to ensure compatibility and test the API.
"""

import os
import sys
import asyncio
import random
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy import text

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.database import get_async_session, AsyncSession
from app import crud
from dotenv import load_dotenv

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

# Updated sample products to reflect food items
SAMPLE_PRODUCTS = [
    {"name": "Honey Nut Cheerios", "description": "Sweetened whole grain oat cereal with real honey & almond flavor.", "price": 4.99},
    {"name": "Nature Valley Granola Bars", "description": "Crunchy Oats 'n Honey bars, perfect for on-the-go.", "price": 3.49},
    {"name": "Yoplait Go-GURT", "description": "Portable low fat yogurt tubes, kid-friendly flavors.", "price": 5.29},
    {"name": "Annie's Macaroni & Cheese", "description": "Classic cheddar mac & cheese made with organic pasta.", "price": 2.99},
    {"name": "Mott's Fruit Snacks", "description": "Assorted fruit flavored snacks made with real fruit juice.", "price": 3.99},
    {"name": "Pillsbury Toaster Strudel", "description": "Warm, flaky pastry with sweet filling and icing.", "price": 4.19},
    {"name": "Progresso Chicken Noodle Soup", "description": "Classic homestyle chicken noodle soup, ready to heat.", "price": 3.79},
    {"name": "Fiber One Brownies", "description": "Chocolate fudge brownie with 90 calories and fiber.", "price": 4.49},
    {"name": "Chex Mix Traditional", "description": "Savory snack mix with Corn Chex, Wheat Chex, pretzels, and more.", "price": 3.99},
    {"name": "Old El Paso Taco Dinner Kit", "description": "Kit includes taco shells, seasoning, and taco sauce.", "price": 5.99}
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

# Updated sample conversations to use food products
SAMPLE_CONVERSATIONS = [
    {
        "user_id": 1,
        "conversation_id": "conv-1001",
        "messages": [
            {"sender": "user", "message": "Hi, I'm looking for some easy breakfast options for my kids.", "timestamp": datetime.now(timezone.utc).isoformat()},
            {"sender": "bot", "message": "Hello David! For easy breakfasts for the kids at Cedar Grove Elementary, how about Honey Nut Cheerios ($4.99) or Pillsbury Toaster Strudel ($4.19)? Both are popular choices!", "timestamp": (datetime.now(timezone.utc) + timedelta(seconds=5)).isoformat()},
            {"sender": "user", "message": "Are the Cheerios gluten-free?", "timestamp": (datetime.now(timezone.utc) + timedelta(seconds=10)).isoformat()},
            {"sender": "bot", "message": "Yes, Honey Nut Cheerios are gluten-free. They're made with whole grain oats. Remember, 20% of your purchase supports Cedar Grove Elementary! Would you like to add them to your cart or see other options?", "timestamp": (datetime.now(timezone.utc) + timedelta(seconds=15)).isoformat()}
        ]
    },
    {
        "user_id": 2,
        "conversation_id": "conv-1002",
        "messages": [
            {"sender": "user", "message": "How does the referral program work?", "timestamp": datetime.now(timezone.utc).isoformat()},
            {"sender": "bot", "message": "Hello Emily! The referral program is a great way to support Oakwood High School. When you refer someone to Carton Caps, they get a 10% discount on their first order (maybe some yummy Mott's Fruit Snacks?), and your school receives 15% of their purchase value. This is on top of the 20% your school gets from your own purchases. Do you need help finding your referral link?", "timestamp": (datetime.now(timezone.utc) + timedelta(seconds=5)).isoformat()}
        ]
    }
]

async def create_schools(session: AsyncSession) -> List[Dict[str, Any]]:
    """Create sample schools in the database."""
    print("Creating schools...")
    schools = []
    
    for school in SAMPLE_SCHOOLS:
        try:
            # First check if school exists by name
            check_query = text("""
            SELECT id, name FROM schools WHERE name = :name
            """)
            result = await session.execute(check_query, {"name": school["name"]})
            existing = result.mappings().first()
            
            if existing:
                print(f"Found existing school: {school['name']}")
                schools.append(dict(existing))
            else:
                # If not exists, insert new school letting PostgreSQL handle the ID
                insert_query = text("""
                INSERT INTO schools (name) 
                VALUES (:name)
                RETURNING id, name
                """)
                result = await session.execute(insert_query, {"name": school["name"]})
                school_record = result.mappings().one()
                schools.append(dict(school_record))
                print(f"Created school: {school['name']}")
            
            await session.commit()
        except Exception as e:
            await session.rollback()
            print(f"Error processing school {school['name']}: {str(e)}")
            # Try to get the existing school one more time after rollback
            try:
                result = await session.execute(check_query, {"name": school["name"]})
                existing = result.mappings().first()
                if existing:
                    print(f"Found existing school after error: {school['name']}")
                    schools.append(dict(existing))
                    await session.commit()
                    continue
            except Exception as inner_e:
                print(f"Error getting existing school after rollback: {str(inner_e)}")
            raise
    
    return schools

async def create_users(session: AsyncSession) -> List[Dict[str, Any]]:
    """Create sample users in the database"""
    print("Creating users...")
    users = []
    
    # Create using custom SQL since we don't have a specific create_user CRUD function #
    for user in SAMPLE_USERS:
        query = text("""
        INSERT INTO Users (name, email, school_id) 
        VALUES (:name, :email, :school_id)
        ON CONFLICT (email) DO UPDATE SET 
            name = EXCLUDED.name,
            school_id = EXCLUDED.school_id
        RETURNING id, name, email, school_id
        """)
        result = await session.execute(query, user)
        user_record = result.mappings().one()
        users.append(dict(user_record))
        print(f"Created user: {user['name']}")
    
    return users

async def create_products(session: AsyncSession) -> List[Dict[str, Any]]:
    """Create sample products in the database"""
    print("Creating products...")
    products = []
    
    for product in SAMPLE_PRODUCTS:
        query = text("""
        SELECT id FROM Products WHERE name = :name
        """)
        result = await session.execute(query, {"name": product["name"]})
        existing = result.scalar_one_or_none()
        
        if existing:
            product_data = await crud.update_product(
                session, 
                existing, 
                product["name"], 
                product["description"], 
                product["price"]
            )
            print(f"Updated product: {product['name']}")
        else:
            product_data = await crud.create_product(
                session,
                product["name"],
                product["description"],
                product["price"]
            )
            print(f"Created product: {product['name']}")
        
        products.append(product_data)
    
    return products

async def create_faqs(session: AsyncSession) -> List[Dict[str, Any]]:
    """Create sample FAQs in the database"""
    print("Creating FAQs...")
    faqs = []
    
    for faq in SAMPLE_FAQS:
        # Check if FAQ already exists
        query = text("""
        SELECT id FROM Referral_FAQs WHERE question = :question
        """)
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
            print(f"Updated FAQ: {faq['question'][:30]}...")
        else:
            # Create new FAQ
            faq_data = await crud.create_faq(
                session,
                faq["question"],
                faq["answer"]
            )
            print(f"Created FAQ: {faq['question'][:30]}...")
        
        faqs.append(faq_data)
    
    return faqs

async def create_rules(session: AsyncSession) -> List[str]:
    """Create sample referral rules in the database"""
    print("Creating referral rules...")
    rules = []
    
    # Clear existing rules to avoid duplicates (since there's no easy way to detect them)
    await session.execute(text("DELETE FROM Referral_Rules"))
    await session.commit()
    
    for rule in SAMPLE_RULES:
        # Create new rule
        rule_data = await crud.create_referral_rule(session, rule)
        rules.append(rule_data)
        print(f"Created rule: {rule[:30]}...")
    
    return rules

async def create_conversations(session: AsyncSession) -> None:
    """Create sample conversation history in the database."""
    print("Creating sample conversations...")
    
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
        
        print(f"Created conversation {conversation_id} with {len(conversation_data['messages'])} messages")

async def create_tables(session: AsyncSession) -> None:
    """Create database tables if they don't exist"""
    print("Ensuring database tables exist...")
    
    # Read schema from schema.sql file
    schema_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'database', 'schema.sql')
    try:
        with open(schema_path, 'r') as f:
            schema_sql = f.read()
        
        # Execute schema SQL
        statements = schema_sql.split(';')
        for statement in statements:
            if statement.strip():
                # Skip comments and empty lines
                if not statement.strip().startswith('--') and statement.strip():
                    print(f"Executing SQL: {statement.strip()}")
                    try:
                        await session.execute(text(statement))
                    except Exception as e:
                        print(f"Error executing statement: {statement.strip()}")
                        print(f"Error details: {str(e)}")
                        raise
        
        # Reset sequences one at a time
        sequences = [
            ('schools_id_seq', 'schools'),
            ('users_id_seq', 'users'),
            ('products_id_seq', 'products'),
            ('referral_faqs_id_seq', 'referral_faqs'),
            ('referral_rules_id_seq', 'referral_rules'),
            ('conversation_history_id_seq', 'conversation_history'),
            ('purchase_history_id_seq', 'purchase_history')
        ]
        
        for seq_name, table_name in sequences:
            reset_query = text(f"""
            SELECT setval(:seq_name, COALESCE((SELECT MAX(id) FROM {table_name}), 0) + 1, false)
            """)
            try:
                await session.execute(reset_query, {"seq_name": seq_name})
                print(f"Reset sequence {seq_name}")
            except Exception as e:
                print(f"Error resetting sequence {seq_name}: {str(e)}")
                # Continue with other sequences even if one fails
                continue
        
        await session.commit()
        print("Database schema applied successfully")
    except Exception as e:
        print(f"Error applying database schema: {e}")
        raise

async def seed_database():
    """Main function to seed the database with sample data"""
    print("Starting database seeding...")
    
    try:
        async for session in get_async_session():
            await create_tables(session)
            
            # Seed data in correct order due to foreign key constraints
            await create_schools(session)
            await create_users(session)
            await create_products(session)
            await create_faqs(session)
            await create_rules(session)
            await create_conversations(session)
            
            print("Database seeded successfully!")
            break
    except Exception as e:
        print(f"Error seeding database: {e}")
        raise

if __name__ == "__main__":
    asyncio.run(seed_database()) 