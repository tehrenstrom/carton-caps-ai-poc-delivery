from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from typing import List, Optional
import logging 
import traceback 
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from functools import wraps
import inspect
import psycopg2

from .models import ChatRequest, ChatResponse, UserInfo, Product, FAQ, ReferralRule, MessageResponse
from pydantic import BaseModel

from . import conversation
from . import llm_integration
from . import crud

# Logging #
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# FastAPI Info #
app = FastAPI(
    title="Capper - Carton Caps AI Product and Referral Assistant",
    description="API for the AI-powered chat agent for Carton Caps",
    version="0.1.0"
)

# Mount the static directory to serve frontend files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Error Handling #
def handle_endpoint_errors(func):
    @wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            if inspect.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except HTTPException as http_exc:
            logger.warning(f"HTTPException in {func.__name__}: {http_exc.status_code} - {http_exc.detail}")
            raise http_exc
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            logger.error(traceback.format_exc())
            raise HTTPException(status_code=500, detail=f"Internal server error in {func.__name__}.")
    return wrapper

# Frontend Endpoints #
@app.get("/")
async def read_index():
    """Serves the index.html file for the chat interface"""
    return FileResponse('static/index.html')

@app.get("/documentation.html")
async def read_documentation():
    """Serves the documentation.html file"""
    return FileResponse('static/documentation.html')

# User Management Endpoints / For POC Testing Purposes Only / Auth is assumed #
@app.get("/users", response_model=List[UserInfo])
@handle_endpoint_errors
def get_users_list():
    """Returns a list of all users with their ID and name"""
    logger.info("Fetching all users")
    users = crud.get_all_users()
    logger.info(f"Found {len(users)} users")
    return users

@app.get("/user/{user_id}", response_model=UserInfo)
@handle_endpoint_errors
async def get_user_info(user_id: int):
    """Returns the ID, name, and school_name for a specific user"""
    logger.info(f"Fetching user info for user_id: {user_id}")
    user = crud.get_user(user_id)
    if not user:
        logger.warning(f"User not found for user_id: {user_id}")
        raise HTTPException(status_code=404, detail=f"User with ID {user_id} not found.")
    logger.info(f"Found user: {user.get('name')}")
    return UserInfo(
        id=user['id'],
        name=user['name'],
        school_name=user.get('school_name')
    )

# Chat Endpoints #
@app.post("/chat")
@handle_endpoint_errors
async def chat(request: Request, chat_request: ChatRequest) -> ChatResponse:
    """Primary chat endpoint"""
    logger.info(f"Received chat request for user_id: {chat_request.user_id}, conv_id: {chat_request.conversation_id}")
    logger.info(f"Validating user {chat_request.user_id}")
    user = crud.get_user(chat_request.user_id)
    if not user:
        logger.warning(f"Chat request failed: User {chat_request.user_id} not found.")
        raise HTTPException(status_code=404, detail=f"User with ID {chat_request.user_id} not found.")
    logger.info(f"User {chat_request.user_id} validated.")

    logger.info(f"Getting conversation history for conv_id: {chat_request.conversation_id}")
    conversation_id, history = conversation.get_conversation_history(chat_request.conversation_id)
    logger.info(f"Using conversation_id: {conversation_id}, history length: {len(history)}")

    logger.info(f"Saving user message to DB for conv_id: {conversation_id}")
    conversation.add_message_to_history(user_id=chat_request.user_id, conversation_id=conversation_id, role='user', content=chat_request.message)
    logger.info("User message saved.")

    logger.info(f"Generating LLM response for conv_id: {conversation_id}")
    ai_response_text = llm_integration.generate_response(
        user_id=chat_request.user_id,
        history=history,
        user_message=chat_request.message
    )
    logger.info(f"LLM response generated for conv_id: {conversation_id}. Length: {len(ai_response_text)}")

    logger.info(f"Saving AI response to DB for conv_id: {conversation_id}")
    conversation.add_message_to_history(user_id=chat_request.user_id, conversation_id=conversation_id, role='assistant', content=ai_response_text)
    logger.info("AI response saved.")

    response_payload = ChatResponse(response=ai_response_text, conversation_id=conversation_id)
    logger.info(f"Returning successful chat response for conv_id: {conversation_id}")
    return response_payload

@app.get("/history/{conversation_id}", response_model=List[MessageResponse])
@handle_endpoint_errors
async def get_history(conversation_id: str):
    """Retrieve the message history for a given conversation ID"""
    logger.info(f"Fetching history for conversation_id: {conversation_id}")
    history = crud.get_conversation_history_db(conversation_id)
    logger.info(f"Found {len(history)} messages for conversation_id: {conversation_id}")
    return history

# Product Endpoints #
@app.get("/products", response_model=List[Product])
@handle_endpoint_errors
async def get_products(limit: int = 100):
    """Get all products with optional limit"""
    products = crud.get_products(limit)
    return products

@app.get("/products/{product_id}", response_model=Product)
@handle_endpoint_errors
async def get_product(product_id: int):
    """Get a single product by ID"""
    product = crud.get_product_by_id(product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.post("/products", response_model=Product)
@handle_endpoint_errors
async def create_product(product: Product):
    """Creates a new product"""
    created_product = crud.create_product(
        name=product.name,
        description=product.description,
        price=product.price
    )
    return Product(**created_product)

@app.put("/products/{product_id}", response_model=Product)
@handle_endpoint_errors
async def update_product(product_id: int, product: Product):
    """Updates an existing product"""
    updated_product = crud.update_product(
        product_id=product_id,
        name=product.name,
        description=product.description,
        price=product.price
    )
    if not updated_product:
        raise HTTPException(status_code=404, detail="Product not found")
    return Product(**updated_product)

@app.delete("/products/{product_id}")
@handle_endpoint_errors
async def delete_product(product_id: int):
    """Deletes a product"""
    success = crud.delete_product(product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}

# KB Endpoints #
@app.get("/faqs", response_model=List[FAQ])
@handle_endpoint_errors
async def get_faqs():
    """Get all referral FAQs."""
    faqs = crud.get_referral_faqs()
    return faqs

@app.post("/faqs", response_model=FAQ)
@handle_endpoint_errors
async def create_faq(faq: FAQ):
    """Create a new FAQ."""
    created_faq_dict = crud.create_faq(
        question=faq.question,
        answer=faq.answer
    )
    return FAQ(
        id=created_faq_dict.get("id"),
        question=created_faq_dict.get("question"),
        answer=created_faq_dict.get("answer")
    )

@app.put("/faqs/{faq_id}", response_model=FAQ)
@handle_endpoint_errors
async def update_faq(faq_id: int, faq: FAQ):
    """Update an existing FAQ"""
    updated_faq = crud.update_faq(
        faq_id=faq_id,
        question=faq.question,
        answer=faq.answer
    )
    if not updated_faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return FAQ(**updated_faq)

@app.delete("/faqs/{faq_id}")
@handle_endpoint_errors
async def delete_faq(faq_id: int):
    """Delete a FAQ"""
    success = crud.delete_faq(faq_id)
    if not success:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return {"message": "FAQ deleted successfully"}

@app.get("/referral-rules", response_model=List[ReferralRule])
@handle_endpoint_errors
async def get_referral_rules():
    """Get all referral rules"""
    rules = crud.get_referral_rules()
    return [ReferralRule(rule=r) for r in rules]

@app.post("/referral-rules", response_model=ReferralRule)
@handle_endpoint_errors
async def create_referral_rule(rule: ReferralRule):
    """Create a new referral rule"""
    created_rule = crud.create_referral_rule(rule.rule)
    return ReferralRule(rule=created_rule)

@app.put("/referral-rules/{rule_id}", response_model=ReferralRule)
@handle_endpoint_errors
async def update_referral_rule(rule_id: int, rule: ReferralRule):
    """Update an existing referral rule"""
    updated_rule = crud.update_referral_rule(
        rule_id=rule_id,
        rule=rule.rule
    )
    if not updated_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return ReferralRule(rule=updated_rule)

@app.delete("/referral-rules/{rule_id}")
@handle_endpoint_errors
async def delete_referral_rule(rule_id: int):
    """Delete a referral rule"""
    success = crud.delete_referral_rule(rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"message": "Rule deleted successfully"}

@app.get("/faqs/{faq_id}", response_model=FAQ)
@handle_endpoint_errors
async def get_faq(faq_id: int):
    """Get a single FAQ by ID"""
    faq = crud.get_faq_by_id(faq_id)
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return faq