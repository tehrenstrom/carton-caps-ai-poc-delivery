import uuid
import logging
from typing import List, Dict, TypedDict, Optional, Tuple
from . import crud 
from sqlalchemy.ext.asyncio import AsyncSession
from .crud import DatabaseError

logger = logging.getLogger(__name__)

class Message(TypedDict):
    role: str
    content: str

async def get_conversation_history(session: AsyncSession, conversation_id: Optional[str]) -> Tuple[str, List[Message]]:
    """Retrieves conversation session ID and FULL history from the DB, or creates a new one"""
    try:
        if conversation_id:
            logger.info(f"Retrieving history for existing conversation: {conversation_id}")
            history = await crud.get_conversation_history_db(session, conversation_id)
            return conversation_id, history
        else:
            new_conversation_id = str(uuid.uuid4())
            logger.info(f"Created new conversation with ID: {new_conversation_id}")
            return new_conversation_id, []
    except DatabaseError as e:
        logger.error(f"Database error while retrieving conversation history: {str(e)}")
        if conversation_id:
            logger.warning(f"Returning empty history for conversation: {conversation_id} due to database error")
            return conversation_id, []
        else:
            new_conversation_id = str(uuid.uuid4())
            logger.warning(f"Creating new conversation with ID: {new_conversation_id} after database error")
            return new_conversation_id, []
    except Exception as e:
        logger.error(f"Unexpected error in get_conversation_history: {str(e)}")
        fallback_id = str(uuid.uuid4())
        logger.warning(f"Using fallback conversation ID: {fallback_id} after error")
        return fallback_id, []

async def add_message_to_history(session: AsyncSession, user_id: int, conversation_id: str, role: str, content: str):
    """Stores messages to conversation history in the DB"""
    try:
        sender = 'bot' if role == 'assistant' else 'user'
        logger.info(f"Adding {sender} message to conversation: {conversation_id}")
        await crud.add_conversation_message(session, user_id, conversation_id, sender, content)
        logger.debug(f"Successfully added message to history")
    except DatabaseError as e:
        logger.error(f"Database error while adding message to history: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error in add_message_to_history: {str(e)}")
        raise