from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
import torch
import os
import uvicorn
import gc

app = FastAPI()

print(f"CUDA Available: {torch.cuda.is_available()}", flush=True)
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}", flush=True)

# Загружаем модель
print("Loading model... this might take a minute.", flush=True)
model = ChatterboxMultilingualTTS.from_pretrained(device=device)
print("Model loaded successfully!", flush=True)

class TTSRequest(BaseModel):
    text: str
    voice: str = "french-mornings.wav"
    language_id: str = "fr"

@app.post("/generate")
async def generate_tts(request: TTSRequest):
    ref_path = f"/voices/{request.voice}"
    
    if not os.path.exists(ref_path):
        print(f"File not found: {ref_path}", flush=True)
        raise HTTPException(status_code=400, detail=f"Voice file not found at {ref_path}")

    try:
        out_path = "/tmp/output.wav"
        print(f"Generating audio for text: {request.text[:50]}...", flush=True)
        
        with torch.inference_mode():
            wav = model.generate(
                request.text, 
                language_id=request.language_id, 
                audio_prompt_path=ref_path
            )
        
        ta.save(out_path, wav.cpu(), model.sr)
        
        del wav
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
        
        print("Generation finished and saved. VRAM cleared.", flush=True)
        
        return FileResponse(out_path, media_type="audio/wav")
        
    except Exception as e:
        print(f"GEN ERROR: {e}", flush=True)
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        gc.collect()
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)