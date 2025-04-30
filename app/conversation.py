import uuid
from typing import List, Dict, TypedDict, Optional
from . import crud 
from sqlalchemy.ext.asyncio import AsyncSession

class Message(TypedDict):
    role: str
    content: str

async def get_conversation_history(session: AsyncSession, conversation_id: Optional[str]) -> tuple[str, List[Message]]:
    """Retrieves conversation session ID and FULL history from the DB, or creates a new one"""
    if conversation_id:
        history = await crud.get_conversation_history_db(session, conversation_id)
        return conversation_id, history
    else:
        new_conversation_id = str(uuid.uuid4())
        return new_conversation_id, []

async def add_message_to_history(session: AsyncSession, user_id: int, conversation_id: str, role: str, content: str):
    """Stores messages to conversation history in the DB"""
    sender = 'bot' if role == 'assistant' else 'user'
    await crud.add_conversation_message(session, user_id, conversation_id, sender, content)