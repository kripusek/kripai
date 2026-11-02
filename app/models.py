from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class Login(Strict):
    username: str = Field(min_length=1,max_length=128)
    password: str = Field(min_length=1,max_length=1024)

class ConversationCreate(Strict):
    title: str = Field(default='',max_length=200)

class MessageCreate(Strict):
    text: str = Field(min_length=1,max_length=4000)
    client_message_id: UUID
    attachment_id: UUID | None = None

class Mode(Strict):
    mode: Literal['normal','gaming']

class Speech(Strict):
    text: str = Field(min_length=1, max_length=1200)
    language: Literal['pl','en'] = 'pl'

class GPUReport(Strict):
    state: Literal['ready','stopped','unverified']
    gpu_process_absent: bool | None
    vram_bytes_free: int | None = Field(ge=0)
    measured_at: datetime

class MediaPage(Strict):
    page: int = Field(ge=1,le=50)

class ImageQuestion(Strict):
    mode: Literal['ocr','question'] = 'question'
    question: str = Field(default='Opisz ten obraz.',min_length=1,max_length=1000)
