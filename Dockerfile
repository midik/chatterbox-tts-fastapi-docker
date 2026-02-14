FROM nvidia/cuda:12.1.0-base-ubuntu22.04

RUN apt-get update && apt-get install -y \
    python3-pip \
    ffmpeg \
    espeak-ng \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip3 install --upgrade pip setuptools wheel

RUN pip3 install --no-cache-dir \
    fastapi uvicorn python-multipart peft \
    torch torchaudio --extra-index-url https://download.pytorch.org/whl/cu121

    RUN git clone https://github.com/resemble-ai/chatterbox.git /tmp/chatterbox && \
    pip3 install /tmp/chatterbox && \
    rm -rf /tmp/chatterbox

COPY main.py .

EXPOSE 8000

CMD ["python3", "main.py"]