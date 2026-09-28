# Chatbot empresarial para WhatsApp

Backend en Python y FastAPI para responder preguntas a partir de documentos de la empresa. Incluye integración con WhatsApp Cloud API; no utiliza inteligencia artificial.

## Requisitos

- Python 3.10 o posterior
- VS Code (opcional, recomendado para editar el proyecto)

## Instalación

Abre una terminal en la carpeta `whatsapp-chatbot` y crea un entorno virtual:

```powershell
py -m venv .venv
```

Actívalo en PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

En macOS o Linux, actívalo con:

```bash
source .venv/bin/activate
```

Instala las dependencias:

```bash
python -m pip install -r requirements.txt
```

Configura `COMPANY_NAME` en `.env`. Las respuestas de ejemplo y los textos entre corchetes se pueden editar en `app/responses.py`.

## Conectar WhatsApp Cloud API

1. Copia `.env.example` como `.env` y configura `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_VERIFY_TOKEN` y `WHATSAPP_APP_SECRET`. Usa un token vigente generado en Meta; si compartiste uno públicamente, revócalo y genera otro. No subas `.env` al repositorio.
2. Instala dependencias con `python -m pip install -r requirements.txt` y ejecuta el backend.
3. Publica el servidor detrás de una URL HTTPS accesible desde internet. En el panel de Meta, configura esa URL seguida de `/webhook`, usa el mismo `WHATSAPP_VERIFY_TOKEN` y suscribe el webhook al campo `messages`.
4. Envía un mensaje de texto al número de prueba o al número conectado. El backend busca la respuesta con el motor actual y contesta usando el Phone Number ID.

El endpoint `GET /webhook` realiza la verificación de Meta y `POST /webhook` valida `X-Hub-Signature-256` usando el secreto de la aplicación. Se procesan mensajes de texto; otros tipos de evento se reconocen y se ignoran. El identificador de la cuenta Business no se requiere para enviar mensajes: se usa el Phone Number ID.

## Interfaz web pública

La página disponible en `/` permite conversar con el bot desde un navegador y consume el endpoint `POST /chat` del mismo backend. Al desplegar en Vercel, se puede compartir directamente la URL raíz del proyecto. Las rutas de WhatsApp `/webhook` y `/webhook/whatsapp` siguen disponibles.

## Documentos de la empresa

Coloca los archivos Word `.docx` en `public/documents/`, en la raíz del proyecto (al mismo nivel que `app/`). No es necesario registrar sus nombres en el código. Se leen los párrafos no vacíos; archivos de otros formatos se ignoran. Un documento dañado se omite y se registra en el log, sin impedir que se lean los demás.

El backend conserva el texto completo de cada documento en memoria. Los endpoints muestran como máximo los primeros 1000 caracteres por documento e indican `"truncated": true` cuando se ha limitado el contenido.

El bot busca dentro del texto cargado y devuelve únicamente la oración o fragmento mejor relacionado con la intención detectada, con un máximo de 500 caracteres. La búsqueda normaliza mayúsculas, tildes y puntuación, contempla variantes habituales de palabras y puntúa coincidencias de la pregunta y de la intención. Solo responde si la puntuación supera el umbral configurado; no genera información ni devuelve documentos completos. Si se agregan, reemplazan o quitan documentos mientras el servidor está activo, usa `POST /documents/reload` para actualizar la información cargada.

## Ejecutar FastAPI

Desde la carpeta `whatsapp-chatbot`, ejecuta:

```bash
python -m uvicorn app.main:app --reload
```

La API estará disponible en `http://127.0.0.1:8000`. La documentación interactiva está en `http://127.0.0.1:8000/docs`.

## Probar `/health`

Abre `http://127.0.0.1:8000/health` o ejecuta:

```bash
curl http://127.0.0.1:8000/health
```

Respuesta esperada:

```json
{"status":"ok"}
```

## Probar `/chat`

En PowerShell, envía un POST con JSON UTF-8:

```powershell
$body = @{ message = '¿Cuál es el horario?' } | ConvertTo-Json
$utf8Body = [System.Text.Encoding]::UTF8.GetBytes($body)
Invoke-RestMethod -Uri 'http://127.0.0.1:8000/chat' `
  -Method Post -ContentType 'application/json' -Body $utf8Body
```

El bot busca la respuesta en los documentos cargados. Prueba estos mensajes:

- `¿Cuál es el horario?`
- `¿A qué horas atienden?`
- `¿Dónde están ubicados?`
- `¿Qué servicios ofrecen?`
- `¿Cuánto cuesta el almuerzo?` (si no aparece en los documentos, devuelve el fallback)

La respuesta tiene el formato `{"response":"..."}`. Si no se reconoce la intención o no hay un fragmento suficientemente relacionado en los documentos, el bot responde: `No encontré información sobre esa pregunta en los documentos disponibles. Por favor, comunícate con un asesor.` Las solicitudes vacías o con más de 2000 caracteres se rechazan mediante validación Pydantic.

Para ejecutar las pruebas locales de intención y búsqueda:

```bash
python -m unittest discover -s tests
```

## Probar los documentos

1. Desde la raíz `whatsapp-chatbot/`, crea `public/documents/` si todavía no existe.
2. Copia allí los archivos `.docx` de la empresa. Por ejemplo: `public/documents/horarios.docx`.
3. Ejecuta `python -m uvicorn app.main:app --reload`.
4. Abre `http://127.0.0.1:8000/docs`.
5. Ejecuta `GET /documents` para ver los archivos detectados y una vista limitada de cada uno.
6. Ejecuta `GET /documents/horarios.docx` para consultar uno. Para nombres con espacios o caracteres especiales, introdúcelos en el campo de Swagger; el navegador codifica la URL.
7. Después de añadir o cambiar archivos sin reiniciar el servidor, ejecuta `POST /documents/reload` y vuelve a consultar la lista.

Si no hay documentos o la carpeta no existe, `GET /documents` devuelve `{"documents": []}`. `GET /documents/{filename}` devuelve HTTP 404 si el nombre no está entre los documentos cargados.