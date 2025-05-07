from pydantic import BaseModel
from typing import Optional, List

class ChatRequest(BaseModel):
    user_id: int
    message: str
    conversation_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    is_suggestion_prompt: bool = False 
    original_user_message: Optional[str] = None

class MessageResponse(BaseModel):
    role: str
    content: str

class ReferralRule(BaseModel):
    id: Optional[int] = None
    rule: str

class Product(BaseModel):
    id: Optional[int] = None
    name: str
    description: str
    price: float

class FAQ(BaseModel):
    id: Optional[int] = None
    question: str
    answer: str

class UserInfo(BaseModel):
    id: int
    name: str
    school_name: Optional[str] = None