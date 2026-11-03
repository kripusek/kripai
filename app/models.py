from datetime import datetime
from typing import Literal
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field, SecretStr

class Strict(BaseModel):
    model_config = ConfigDict(extra='forbid')

class UploadStart(Strict):
    id:UUID
    name:str=Field(min_length=1,max_length=180)
    size:int=Field(ge=1,le=8388608,strict=True)
    sha256:str=Field(pattern=r'^[a-f0-9]{64}$')

class Login(Strict):
    username: str = Field(min_length=1,max_length=128)
    password: str = Field(min_length=1,max_length=1024)

class ConversationCreate(Strict):
    title: str = Field(default='',max_length=200)

class ConversationRename(Strict):
    title:str=Field(min_length=1,max_length=200)

class ConversationBranch(Strict):
    message_id:UUID

class MessageCreate(Strict):
    text: str = Field(min_length=1,max_length=4000)
    client_message_id: UUID
    attachment_id: UUID | None = None
    document_ids: list[UUID] = Field(default_factory=list,max_length=5)
    allow_web: bool = False
    allow_github: bool = False
    allow_mcp: bool = False

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

class McpFilesConnect(Strict):
    root:str=Field(min_length=1,max_length=1024)
    label:str=Field(default='Moje dokumenty',min_length=1,max_length=60)

class MediaPage(Strict):
    page: int = Field(ge=1,le=50)

class ImageQuestion(Strict):
    mode: Literal['ocr','question'] = 'question'
    question: str = Field(default='Opisz ten obraz.',min_length=1,max_length=1000)

class RagIndex(Strict):
    rebuild: bool = False

class GithubConnect(Strict):
    repositories:list[str]=Field(min_length=1,max_length=5)
    token:SecretStr=Field(min_length=1,max_length=512)
    write:bool=False
