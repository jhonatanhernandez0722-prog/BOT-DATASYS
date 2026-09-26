# Chatbot empresarial para WhatsApp

Backend local en Python y FastAPI para probar respuestas predeterminadas. No conecta con WhatsApp ni utiliza inteligencia artificial.

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