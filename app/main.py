from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from typing import List, Optional, Dict, Any
import logging 
import traceback 
from fastapi.middleware.cors import CORSMiddleware
import asyncio
from functools import wraps
import inspect
import psycopg2
from dotenv import load_dotenv
import os

from .models import ChatRequest, ChatResponse, UserInfo, Product, FAQ, ReferralRule, MessageResponse
from pydantic import BaseModel

from . import conversation
from . import llm_integration
from . import crud
from .database import get_async_session
from sqlalchemy.ext.asyncio import AsyncSession

# Load environment variables
load_dotenv()

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

# CORS Middleware
origins = [
    "*",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Error Handling #
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception for request {request.url}: {exc}")
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal server error occurred."},
    )

def handle_endpoint_errors(func):
    """Decorator to handle common endpoint errors like DB issues or validation"""
    async def wrapper(*args, **kwargs):
        try:
            session = next((v for v in kwargs.values() if isinstance(v, AsyncSession)), None)
            if not session and 'session' in kwargs and isinstance(kwargs['session'], AsyncSession):
                session = kwargs['session']

            if asyncio.iscoroutinefunction(func):
                return await func(*args, **kwargs)
            else:
                return func(*args, **kwargs)
        except HTTPException as http_exc:
            logger.warning(f"HTTP Exception in {func.__name__}: {http_exc.status_code} - {http_exc.detail}")
            raise http_exc
        except Exception as e:
            logger.error(f"Unexpected error in endpoint {func.__name__}: {e}")
            logger.error(traceback.format_exc())
            if session:
                try:
                    await session.rollback() 
                    logger.warning("Rolled back session due to unhandled exception in endpoint decorator.")
                except Exception as rollback_err:
                    logger.error(f"Failed to rollback session after error: {rollback_err}")
            raise HTTPException(status_code=500, detail="Internal Server Error")
    if asyncio.iscoroutinefunction(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            try:
                session = next((v for v in kwargs.values() if isinstance(v, AsyncSession)), None)
                if not session and 'session' in kwargs and isinstance(kwargs['session'], AsyncSession):
                    session = kwargs['session']

                return await func(*args, **kwargs)
            except HTTPException as http_exc:
                logger.warning(f"HTTP Exception in {func.__name__}: {http_exc.status_code} - {http_exc.detail}")
                raise http_exc
            except Exception as e:
                logger.error(f"Unexpected error in endpoint {func.__name__}: {e}")
                logger.error(traceback.format_exc())
                if session:
                    try:
                        await session.rollback()
                        logger.warning("Rolled back session due to unhandled exception in endpoint decorator.")
                    except Exception as rollback_err:
                        logger.error(f"Failed to rollback session after error: {rollback_err}")
                raise HTTPException(status_code=500, detail="Internal Server Error")
        return async_wrapper
    else:
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except HTTPException as http_exc:
                logger.warning(f"HTTP Exception in {func.__name__}: {http_exc.status_code} - {http_exc.detail}")
                raise http_exc
            except Exception as e:
                logger.error(f"Unexpected error in endpoint {func.__name__}: {e}")
                logger.error(traceback.format_exc())
                raise HTTPException(status_code=500, detail="Internal Server Error")
        return sync_wrapper

# Frontend Endpoints #
@app.get("/")
async def read_index():
    """Serves the index.html file for the chat interface"""
    if not os.path.exists('static/index.html'):
        logger.error("static/index.html not found")
        raise HTTPException(status_code=404, detail="Frontend index file not found.")
    return FileResponse('static/index.html')

@app.get("/static/{filepath:path}")
async def serve_static(filepath: str):
    """Serves static files (CSS, JS, images)"""
    static_file_path = os.path.join('static', filepath)
    if not os.path.exists(static_file_path):
        logger.error(f"Static file not found: {static_file_path}")
        raise HTTPException(status_code=404, detail="Static file not found.")
    return FileResponse(static_file_path)

@app.get("/documentation.html")
async def read_documentation():
    """Serves the documentation.html file"""
    return FileResponse('static/documentation.html')

# User Management Endpoints / For POC Testing Purposes Only / Auth is assumed #
@app.get("/users", response_model=List[UserInfo])
@handle_endpoint_errors
async def get_users_list(session: AsyncSession = Depends(get_async_session)):
    """Returns a list of all users with their ID and name (now async)"""
    logger.info("Fetching all users")
    users = await crud.get_all_users(session) # Use async version
    logger.info(f"Found {len(users)} users")
    return users

@app.get("/user/{user_id}", response_model=UserInfo)
@handle_endpoint_errors
async def get_user_info(user_id: int, session: AsyncSession = Depends(get_async_session)):
    """Returns the ID, name, and school_name for a specific user"""
    logger.info(f"Fetching user info for user_id: {user_id}")
    user = await crud.get_user(session, user_id)
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
async def chat(
    request: Request, 
    chat_request: ChatRequest, 
    session: AsyncSession = Depends(get_async_session)
) -> ChatResponse:
    """Primary chat endpoint (now async)"""
    logger.info(f"Received chat request for user_id: {chat_request.user_id}, conv_id: {chat_request.conversation_id}")
    logger.info(f"Validating user {chat_request.user_id}")
    user = await crud.get_user(session, chat_request.user_id)
    if not user:
        logger.warning(f"Chat request failed: User {chat_request.user_id} not found.")
        raise HTTPException(status_code=404, detail=f"User with ID {chat_request.user_id} not found.")
    logger.info(f"User {chat_request.user_id} validated.")

    logger.info(f"Getting conversation history for conv_id: {chat_request.conversation_id}")
    conversation_id, history = await conversation.get_conversation_history(session, chat_request.conversation_id)
    logger.info(f"Using conversation_id: {conversation_id}, history length: {len(history)}")

    logger.info(f"Saving user message to DB for conv_id: {conversation_id}")
    await conversation.add_message_to_history(
        session=session, 
        user_id=chat_request.user_id, 
        conversation_id=conversation_id, 
        role='user', 
        content=chat_request.message
    )
    logger.info("User message saved.")

    # Fetch KB context data asynchronously using the same session
    logger.info(f"Fetching KB context for conv_id: {conversation_id}")
    # Use the new async crud functions directly
    products = await crud.get_products(session, limit=100) 
    faqs = await crud.get_referral_faqs(session)
    rules = await crud.get_referral_rules(session)
    logger.info(f"KB context fetched for conv_id: {conversation_id}")

    # Add user message to history *before* sending to LLM
    history.append({"role": "user", "content": chat_request.message})

    logger.info(f"Generating LLM response for conv_id: {conversation_id}")
    from fastapi.concurrency import run_in_threadpool
    ai_response_text = await run_in_threadpool(
        llm_integration.generate_response,
        user_info=user,
        history=history, 
        user_message=chat_request.message,
        products=products,
        faqs=faqs,
        rules=rules
    )
    
    logger.info(f"LLM response generated for conv_id: {conversation_id}. Length: {len(ai_response_text)}")

    logger.info(f"Saving AI response to DB for conv_id: {conversation_id}")
    await conversation.add_message_to_history(
        session=session, 
        user_id=chat_request.user_id, 
        conversation_id=conversation_id, 
        role='assistant', 
        content=ai_response_text
    )
    logger.info("AI response saved.")

    response_payload = ChatResponse(response=ai_response_text, conversation_id=conversation_id)
    logger.info(f"Returning successful chat response for conv_id: {conversation_id}")
    return response_payload

@app.get("/history/{conversation_id}", response_model=List[MessageResponse])
@handle_endpoint_errors
async def get_history(
    conversation_id: str, 
    session: AsyncSession = Depends(get_async_session)
):
    """Retrieve the message history for a given conversation ID (now async)"""
    logger.info(f"Fetching history for conversation_id: {conversation_id}")
    _conv_id, history = await conversation.get_conversation_history(session, conversation_id)
    logger.info(f"Found {len(history)} messages for conversation_id: {conversation_id}")
    return history

# Product Endpoints #
@app.get("/products", response_model=List[Product])
@handle_endpoint_errors
async def get_products(limit: int = 100, session: AsyncSession = Depends(get_async_session)):
    """Get all products with optional limit (now async)"""
    products = await crud.get_products(session, limit=limit)
    return products

@app.get("/products/{product_id}", response_model=Product)
@handle_endpoint_errors
async def get_product(product_id: int, session: AsyncSession = Depends(get_async_session)):
    """Get a single product by ID (now async)"""
    product = await crud.get_product_by_id(session, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product

@app.post("/products", response_model=Product)
@handle_endpoint_errors
async def create_product(product: Product, session: AsyncSession = Depends(get_async_session)):
    """Creates a new product (now async)"""
    created_product = await crud.create_product(
        session=session,
        name=product.name,
        description=product.description,
        price=product.price
    )
    return Product(**created_product)

@app.put("/products/{product_id}", response_model=Product)
@handle_endpoint_errors
async def update_product(product_id: int, product: Product, session: AsyncSession = Depends(get_async_session)):
    """Updates an existing product (now async)"""
    updated_product = await crud.update_product(
        session=session,
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
async def delete_product(product_id: int, session: AsyncSession = Depends(get_async_session)):
    """Deletes a product (now async)"""
    success = await crud.delete_product(session, product_id)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"message": "Product deleted successfully"}

# KB Endpoints #
@app.get("/faqs", response_model=List[FAQ])
@handle_endpoint_errors
async def get_faqs(session: AsyncSession = Depends(get_async_session)):
    """Get all referral FAQs (now async)."""
    faqs = await crud.get_referral_faqs(session)
    return faqs

@app.get("/faqs/{faq_id}", response_model=FAQ)
@handle_endpoint_errors
async def get_faq(faq_id: int, session: AsyncSession = Depends(get_async_session)):
    """Get a single FAQ by ID (now async)"""
    faq = await crud.get_faq_by_id(session, faq_id) 
    if not faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return faq

@app.post("/faqs", response_model=FAQ)
@handle_endpoint_errors
async def create_faq(faq: FAQ, session: AsyncSession = Depends(get_async_session)):
    """Create a new FAQ (now async)."""
    created_faq_dict = await crud.create_faq( 
        session=session,
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
async def update_faq(faq_id: int, faq: FAQ, session: AsyncSession = Depends(get_async_session)):
    """Update an existing FAQ (now async)"""
    updated_faq = await crud.update_faq( 
        session=session,
        faq_id=faq_id,
        question=faq.question,
        answer=faq.answer
    )
    if not updated_faq:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return FAQ(**updated_faq)

@app.delete("/faqs/{faq_id}")
@handle_endpoint_errors
async def delete_faq(faq_id: int, session: AsyncSession = Depends(get_async_session)):
    """Delete a FAQ (now async)"""
    success = await crud.delete_faq(session, faq_id) 
    if not success:
        raise HTTPException(status_code=404, detail="FAQ not found")
    return {"message": "FAQ deleted successfully"}

@app.get("/referral-rules", response_model=List[ReferralRule])
@handle_endpoint_errors
async def get_referral_rules(session: AsyncSession = Depends(get_async_session)):
    """Get all referral rules (now async)"""
    rules = await crud.get_referral_rules(session) 
    return [ReferralRule(rule=r) for r in rules]

@app.post("/referral-rules", response_model=ReferralRule)
@handle_endpoint_errors
async def create_referral_rule(rule: ReferralRule, session: AsyncSession = Depends(get_async_session)):
    """Create a new referral rule (now async)"""
    created_rule = await crud.create_referral_rule(session, rule.rule)
    return ReferralRule(rule=created_rule)

@app.put("/referral-rules/{rule_id}", response_model=ReferralRule)
@handle_endpoint_errors
async def update_referral_rule(rule_id: int, rule: ReferralRule, session: AsyncSession = Depends(get_async_session)):
    """Update an existing referral rule (now async)"""
    updated_rule = await crud.update_referral_rule(session, rule_id=rule_id, rule=rule.rule)
    if not updated_rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    return ReferralRule(rule=updated_rule)

@app.delete("/referral-rules/{rule_id}")
@handle_endpoint_errors
async def delete_referral_rule(rule_id: int, session: AsyncSession = Depends(get_async_session)):
    """Delete a referral rule (now async)"""
    success = await crud.delete_referral_rule(session, rule_id=rule_id)
    if not success:
        raise HTTPException(status_code=404, detail="Rule not found")
    return {"message": "Rule deleted successfully"}

@app.on_event("startup")
async def startup_event():
    logger.info("Performing startup checks...")
    
    logger.info("Checking environment variables...")
    required_env_vars = ["DATABASE_URL", "GOOGLE_API_KEY"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    
    if missing_vars:
        error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
        logger.critical(error_msg)
        raise ValueError(error_msg)
    else:
        logger.info("Required environment variables found.")

    logger.info("Testing database connection...")
    from .database import test_connection
    if await test_connection():
        logger.info("Database connection verified.")
    else:
        logger.error("Database connection failed on startup. Check DATABASE_URL and connectivity.")

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting Uvicorn server...")
    uvicorn.run(app, host="0.0.0.0", port=8000)