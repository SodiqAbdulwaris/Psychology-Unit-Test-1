from datetime import datetime
from typing import Dict, Optional
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile
from pydantic import BaseModel
from groq import Groq

from dotenv import load_dotenv
import os

load_dotenv()


client = Groq(api_key=os.getenv("GROQ_API_KEY"))
app = FastAPI(title="Session API")

# In-memory storage
sessions: Dict[str, dict] = {}


# ------------------ MODELS ------------------

class SessionCreate(BaseModel):
    appointment_id: str
    client_name: str
    notes: Optional[str] = None


class SessionUpdate(BaseModel):
    client_name: Optional[str] = None
    notes: Optional[str] = None
    status: Optional[str] = None


# ------------------ ROUTES ------------------

@app.get("/")
def home():
    return {"message": "Session API is running"}


@app.post("/sessions")
def create_session(data: SessionCreate):
    session_id = str(uuid4())

    session = {
        "id": session_id,
        "appointment_id": data.appointment_id,
        "client_name": data.client_name,
        "notes": data.notes,
        "status": "scheduled",
        "audio_files": [],
        "transcript": None,
        "summary": None,
        "created_at": datetime.utcnow().isoformat(),
    }

    sessions[session_id] = session
    return session


@app.get("/sessions")
def get_all_sessions():
    return list(sessions.values())


@app.get("/sessions/{appointment_id}")
def get_session_by_appointment_id(appointment_id: str):
    for session in sessions.values():
        if session["appointment_id"] == appointment_id:
            return session

    raise HTTPException(status_code=404, detail="Session not found")


@app.patch("/sessions/{id}")
def update_session(id: str, data: SessionUpdate):
    if id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[id]
    updates = data.model_dump(exclude_unset=True)

    for key, value in updates.items():
        session[key] = value

    return session


# ------------------ AUDIO UPLOAD ------------------

@app.post("/sessions/{id}/audio")
async def upload_audio(id: str, file: UploadFile = File(...)):
    if id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    # ✅ Accept only good formats
    allowed_types = [
        "audio/mpeg",
        "audio/wav",
        "audio/mp4",
        "audio/mp3",
        "video/mp4"
    ]

    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format: {file.content_type}. Use mp3, wav, or mp4."
        )

    file_path = f"{id}_{file.filename}"

    with open(file_path, "wb") as f:
        content = await file.read()
        f.write(content)

    audio_info = {
        "filename": file.filename,
        "file_path": file_path,
        "content_type": file.content_type
    }

    sessions[id]["audio_files"].append(audio_info)
    sessions[id]["status"] = "in_progress"

    return {
        "message": "Audio uploaded successfully",
        "session_id": id,
        "audio": audio_info,
    }


# ------------------ TRANSCRIPTION (GROQ) ------------------

@app.post("/ai/transcribe/{session_id}")
def transcribe_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    if not session["audio_files"]:
        raise HTTPException(status_code=400, detail="No audio uploaded")

    file_path = session["audio_files"][-1]["file_path"]

    try:
        with open(file_path, "rb") as audio_file:
            transcription = client.audio.transcriptions.create(
                file=audio_file,
                model="whisper-large-v3"
            )

        text = transcription.text.strip()

        if not text or len(text) < 5:
            raise Exception("Transcription too short or empty")

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Transcription failed. Use a clean WAV or MP3 file. Error: {str(e)}"
        )

    session["transcript"] = text

    return {
        "message": "Transcription completed",
        "transcript": text
    }


# ------------------ SUMMARY ------------------

@app.post("/ai/summarise/{session_id}")
def summarise_session(session_id: str):
    if session_id not in sessions:
        raise HTTPException(status_code=404, detail="Session not found")

    session = sessions[session_id]

    if not session["transcript"]:
        raise HTTPException(status_code=400, detail="Transcript not available")

    try:
        response = client.chat.completions.create(
            model="llama-3.1-8b-instant",
            messages=[
                {
                    "role": "user",
                    "content": f"""
                    You are a professional therapist assistant.

                    Summarize the following session into structured clinical notes:

                    Include:
                    - Overview (brief summary of the session)
                    - Key Issues Discussed
                    - Observations (emotions, tone, behavior if noticeable)
                    - Action Items / Next Steps

                    Keep it clear, concise, and professional.

                    Transcript:
                    {session["transcript"]}
                    """
                }
            ]
        )

        summary_text = response.choices[0].message.content.strip()

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Summary generation failed: {str(e)}"
        )

    session["summary"] = summary_text
    session["status"] = "completed"

    return {
        "message": "Summary created",
        "summary": summary_text
    }


# ------------------ DEBUG ------------------

@app.get("/debug/sessions")
def list_sessions():
    return {
        "count": len(sessions),
        "sessions": list(sessions.values())
    }