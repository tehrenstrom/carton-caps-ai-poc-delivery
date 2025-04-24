import google.generativeai as genai
import os
from dotenv import load_dotenv
from typing import List, Dict, Optional, Any
import logging 
import traceback

from .conversation import Message
from . import crud

logger = logging.getLogger(__name__)

load_dotenv()

API_KEY = os.getenv("GOOGLE_API_KEY")
if not API_KEY:
    logger.critical("GOOGLE_API_KEY environment variable not set.")
    raise ValueError("GOOGLE_API_KEY environment variable not set.")

try:
    genai.configure(api_key=API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    logger.info("Gemini API configured successfully.")
except Exception as e:
    logger.critical(f"Failed to configure Gemini API: {e}")
    logger.critical(traceback.format_exc())

# Comments are expanded in this section to help with understanding the LLM path and decision
# making process as this is a POC. See unit test "test_llm_integration"
# for testing the these functions #
def generate_response(user_id: int, history: List[Message], user_message: str) -> str:
    """Generates a response using the Gemini API based on context and history"""
    logger.info(f"Starting generate_response for user_id: {user_id}")

    if not model:
        logger.error("Gemini model not initialized due to configuration error.")
        return "Error: AI Service not configured correctly."

    try:
        # Fetch Dynamic Context from DB/Future dev should consider leveraging a vector/embedding DB or similarity search for this purpose at scale #
        logger.info(f"Fetching DB context for user_id: {user_id}")
        user_info = crud.get_user(user_id)
        products = crud.get_products()
        faqs = crud.get_referral_faqs()
        rules = crud.get_referral_rules()
        logger.info("DB context fetched.")

        # System prompt defines persona (Capper), goals, and constraints, including fallback instruction / Future dev should consider using a more dynamic system prompt that can be updated as the conversation progresses and more data becomes available to the LLM / Consider using langchain for agnostic provider prompt management for A/B testing and fallback #
        system_prompt = (
            "You are Capper, a friendly and helpful assistant for the Carton Caps app."
            "Carton Caps helps users raise money for schools by buying products."
            "Your main goals are to help users find products and understand the referral program."
            "using ONLY the information provided in the 'Relevant Knowledge' section below."
            "Be concise, mission driven, and conversational."
            "If you cannot answer a question based on the provided Relevant Knowledge or your capabilities,"
            "politely state that you cannot assist with that specific request and suggest the user contact support@cartoncaps.com for further assistance."
        )
        # User-specific and general knowledge base context #
        user_context = f"User Info:\n- Name: {user_info['name'] if user_info else 'N/A'}\n- Email: {user_info['email'] if user_info else 'N/A'}\n- Linked School: {user_info['school_name'] if user_info and user_info.get('school_name') else 'N/A'}\n"
        product_context = "Available Products:\n" + ("\n".join([f"- {p['name']}: {p['description']} (${p['price']:.2f})" for p in products]) if products else "No products listed.")
        referral_context = "Referral Program Info:\nFAQs:\n" + ("\n".join([f" Q: {faq['question']}\n A: {faq['answer']}" for faq in faqs]) if faqs else "No FAQs available.") + "\nRules:\n" + ("\n".join([f"- {rule}" for rule in rules]) if rules else "No rules available.")
        relevant_knowledge = f"\n{user_context}\n\n{product_context}\n\n{referral_context}"

        # Format Conversation History for Gemini API #
        logger.info("Formatting history for Gemini API")
        gemini_history = []
        # Prepend the system prompt and knowledge as the initial user message context #
        initial_context_message = f"{system_prompt}\n\nRelevant Knowledge:\n{relevant_knowledge}"
        gemini_history.append({'role': 'user', 'parts': [initial_context_message]})
        # Add an initial model turn to ensure the history alternates user/model roles, 
        # as suggested by the Gemini API after the initial context is provided as a user turn.
        gemini_history.append({'role': 'model', 'parts': ["Okay, I understand my role and the context. How can I help?"]})

        # Apply conversation history conetxt / truncation strategy ('First + Last N') #
        # Keeps the first 'turn' and the most recent N-1 turns to manage context size #
        MAX_HISTORY_TURNS = 10 # Total turns (user + assistant), including the first turn #
        if len(history) > MAX_HISTORY_TURNS:
            # Calculate how many 'last' turns to keep (total max - the first one) #
            num_last_turns = MAX_HISTORY_TURNS - 1 
            logger.warning(f"History length ({len(history)}) exceeds max ({MAX_HISTORY_TURNS}). Truncating to first 1 + last {num_last_turns}.")
            # Combine the first message with the last N-1 messages #
            truncated_history = [history[0]] + history[-num_last_turns:]
        else:
            truncated_history = history

        # Append the processed conversation history #
        for msg in truncated_history:
            # Map internal role names ('assistant') to Gemini API role names ('model') #
            role = 'model' if msg.get('role') == 'assistant' else msg.get('role', 'user') 
            # Ensure content exists and is a string
            content = msg.get('content', '')
            if not isinstance(content, str):
                logger.warning(f"History message content is not a string: {content}. Skipping.")
                continue
            gemini_history.append({'role': role, 'parts': [content]}) 

        logger.info(f"Final history length being sent to LLM (excluding current user message): {len(gemini_history)}")

        # Call the Gemini API #
        logger.info("Starting Gemini API call")
        # Start chat with the prepared history #
        chat = model.start_chat(history=gemini_history) 
        # Send only the current user message for this turn #
        response = chat.send_message(user_message) 
        logger.info("Gemini API call finished")

        # Process and Return Response #
        response_text = response.text

        if not response_text:
            logger.warning("Gemini API returned empty response text.")
            return "Sorry, I received an empty response from the AI. Please try again."

        logger.info(f"Successfully generated response. Length: {len(response_text)}")
        return response_text

    except Exception as e:
        logger.error(f"Error during generate_response for user_id {user_id}: {e}")
        logger.error(traceback.format_exc())
        return "Sorry, I encountered an internal error while generating a response." 