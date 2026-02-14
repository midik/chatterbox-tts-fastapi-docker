from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
import torchaudio as ta
from chatterbox.mtl_tts import ChatterboxMultilingualTTS
import torch
import os
import re
import uvicorn
import gc

app = FastAPI()

print(f"CUDA Available: {torch.cuda.is_available()}", flush=True)
device = "cuda" if torch.cuda.is_available() else "cpu"
print(f"Using device: {device}", flush=True)

# load model
print("Loading model... this might take a minute.", flush=True)
model = ChatterboxMultilingualTTS.from_pretrained(device=device)
print("Model loaded successfully!", flush=True)

# split text into sentences
SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?…])\s+')

def split_into_sentences(text: str) -> list[str]:
    """split text into sentences"""
    parts = SENTENCE_SPLIT_RE.split(text.strip())
    return [s.strip() for s in parts if s.strip()]


class TTSRequest(BaseModel):
    text: str
    voice: str = "french-mornings.wav"
    language_id: str = "fr"
    pause_after_sentence: bool = False

@app.post("/generate")
async def generate_tts(request: TTSRequest):
    ref_path = f"/voices/{request.voice}"
    
    if not os.path.exists(ref_path):
        print(f"File not found: {ref_path}", flush=True)
        raise HTTPException(status_code=400, detail=f"Voice file not found at {ref_path}")

    try:
        out_path = "/tmp/output.wav"
        
        sentences = split_into_sentences(request.text)
        print(f"Split text into {len(sentences)} sentence(s), pause={request.pause_after_sentence}", flush=True)
        
        chunks = []
        
        for i, sentence in enumerate(sentences):
            print(f"  [{i+1}/{len(sentences)}] Generating: {sentence[:60]}...", flush=True)
            
            with torch.inference_mode():
                wav = model.generate(
                    sentence,
                    language_id=request.language_id,
                    audio_prompt_path=ref_path
                )
            
            wav_cpu = wav.cpu()
            chunks.append(wav_cpu)
            
            # insert silence after each sentence
            if request.pause_after_sentence:
                silence = torch.zeros_like(wav_cpu)
                chunks.append(silence)
            
            # clear VRAM after each sentence
            del wav
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
            gc.collect()
        
        # concatenate all chunks into one audio file
        result = torch.cat(chunks, dim=-1)
        ta.save(out_path, result, model.sr)
        
        del result, chunks
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