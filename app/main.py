from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.bot import get_bot_response
from app.config import DOCUMENT_PREVIEW_LENGTH
from app.documents import load_documents

app = FastAPI(title="Chatbot empresarial para WhatsApp")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)

    @field_validator("message")
    @classmethod
    def message_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("El mensaje no puede estar vacío.")
        return value


class ChatResponse(BaseModel):
    response: str


class DocumentPreview(BaseModel):
    name: str
    content: str
    truncated: bool


class DocumentsResponse(BaseModel):
    documents: list[DocumentPreview]


class DocumentReloadResponse(BaseModel):
    count: int
    names: list[str]


app.state.documents = load_documents()


def _make_document_preview(name: str, content: str) -> DocumentPreview:
    return DocumentPreview(
        name=name,
        content=content[:DOCUMENT_PREVIEW_LENGTH],
        truncated=len(content) > DOCUMENT_PREVIEW_LENGTH,
    )


@app.get("/health")
def health_check() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/documents", response_model=DocumentsResponse)
def list_documents() -> DocumentsResponse:
    documents = [
        _make_document_preview(name, content)
        for name, content in app.state.documents.items()
    ]
    return DocumentsResponse(documents=documents)


@app.get("/documents/{filename}", response_model=DocumentPreview)
def get_document(filename: str) -> DocumentPreview:
    content = app.state.documents.get(filename)
    if content is None:
        raise HTTPException(status_code=404, detail="Documento no encontrado.")
    return _make_document_preview(filename, content)


@app.post("/documents/reload", response_model=DocumentReloadResponse)
def reload_documents() -> DocumentReloadResponse:
    app.state.documents = load_documents()
    names = list(app.state.documents)
    return DocumentReloadResponse(count=len(names), names=names)


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    return ChatResponse(
        response=get_bot_response(request.message, app.state.documents)
    )