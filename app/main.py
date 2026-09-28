import json

from fastapi import FastAPI, HTTPException, Query, Request
from pydantic import BaseModel, Field, field_validator
from starlette.responses import PlainTextResponse

from app.bot import get_bot_response
from app.config import (
    DOCUMENT_PREVIEW_LENGTH,
    WHATSAPP_ACCESS_TOKEN,
    WHATSAPP_APP_SECRET,
    WHATSAPP_PHONE_NUMBER_ID,
    WHATSAPP_VERIFY_TOKEN,
)
from app.documents import load_documents
from app.whatsapp import (
    handle_incoming_messages,
    is_valid_webhook_signature,
    is_valid_webhook_verification,
)

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


@app.get("/webhook/whatsapp")
@app.get("/webhook")
def verify_whatsapp_webhook(
    mode: str | None = Query(default=None, alias="hub.mode"),
    token: str | None = Query(default=None, alias="hub.verify_token"),
    challenge: str | None = Query(default=None, alias="hub.challenge"),
) -> PlainTextResponse:
    if not is_valid_webhook_verification(mode, token, WHATSAPP_VERIFY_TOKEN):
        raise HTTPException(status_code=403, detail="Verificación de webhook inválida.")
    return PlainTextResponse(challenge or "")


@app.post("/webhook/whatsapp")
@app.post("/webhook")
async def receive_whatsapp_webhook(request: Request) -> dict[str, str]:
    if not WHATSAPP_APP_SECRET:
        raise HTTPException(
            status_code=503, detail="Falta configurar WHATSAPP_APP_SECRET."
        )
    if not WHATSAPP_ACCESS_TOKEN or not WHATSAPP_PHONE_NUMBER_ID:
        raise HTTPException(
            status_code=503, detail="Faltan las credenciales de WhatsApp Cloud API."
        )

    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256")
    if not is_valid_webhook_signature(payload, signature, WHATSAPP_APP_SECRET):
        raise HTTPException(status_code=403, detail="Firma de webhook inválida.")

    try:
        event = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise HTTPException(status_code=400, detail="JSON de webhook inválido.") from error
    if not isinstance(event, dict):
        raise HTTPException(status_code=400, detail="JSON de webhook inválido.")

    await handle_incoming_messages(event, app.state.documents)
    return {"status": "ok"}