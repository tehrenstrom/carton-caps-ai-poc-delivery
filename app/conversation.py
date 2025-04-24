import uuid
from typing import List, Dict, TypedDict, Optional
from . import crud 

class Message(TypedDict):
    role: str
    content: str

def get_conversation_history(conversation_id: Optional[str]) -> tuple[str, List[Message]]:
    """Retrieves conversation session ID and FULL history from the DB, or creates a new one"""
    if conversation_id:
        history = crud.get_conversation_history_db(conversation_id)
        return conversation_id, history
    else:
        new_conversation_id = str(uuid.uuid4())
        return new_conversation_id, []

def add_message_to_history(user_id: int, conversation_id: str, role: str, content: str):
    """Stores messages to conversation history in the DB"""
    sender = 'bot' if role == 'assistant' else 'user'
    crud.add_conversation_message(user_id, conversation_id, sender, content)