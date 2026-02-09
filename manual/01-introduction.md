# Chapter 1: Introduction

## What Is LocalSoundsAPI?

LocalSoundsAPI is a self-hosted audio production platform that brings together several powerful AI models under one roof. Instead of juggling separate tools, signing up for cloud services, or writing scripts to glue things together, you get a single web interface that handles:

- **Text-to-Speech (TTS)** -- Three different engines (XTTS-v2, Fish Speech, Kokoro) each with their own strengths
- **Voice Cloning** -- Upload a short audio sample of any voice and generate new speech in that voice
- **Music Generation** -- Create original music tracks from text descriptions
- **Sound Effects** -- Generate impacts, ambient textures, foley, and more from text prompts
- **Transcription** -- Convert speech to text with word-level timestamps
- **Video Production** -- Combine audio with images or video, add auto-generated subtitles
- **AI Chatbot** -- Chat with local or cloud-based language models

Everything runs on your local machine. Your audio, your voices, and your conversations stay private. The only exception is if you choose to use the optional OpenRouter cloud backend for the chatbot.

## Who Is This For?

- **Content creators** who need voiceovers, narration, or background music
- **Game developers** looking for sound effects and character voices
- **Podcasters and video makers** who want automated transcription and subtitled videos
- **Hobbyists and tinkerers** who want to explore AI audio generation
- **Developers** who need a local TTS/audio API for their projects

## How It Works

LocalSoundsAPI is a Flask web application written in Python. When you run it, a local web server starts on your machine. You open your browser, navigate to the address (usually `http://127.0.0.1:5006`), and interact with everything through the web interface.

Behind the scenes, AI models are loaded onto your GPU (or CPU) on demand. You only load what you need, and you can unload models when you're done to free up memory. This "lazy loading" approach means the app starts quickly and you control your GPU memory usage.

### Architecture at a Glance

```
Your Browser
    |
    v
Flask Web Server (main.py, port 5006)
    |
    +-- Routes (API endpoints for each feature)
    |     +-- TTS: XTTS, Fish Speech, Kokoro
    |     +-- Audio: Stable Audio, ACE-Step
    |     +-- Production: Upload, Transcribe, Video
    |     +-- Chatbot: Local LLM, LM Studio, OpenRouter
    |
    +-- Models (loaded/unloaded on demand)
    |     +-- XTTS-v2, Fish Speech, Kokoro, Whisper
    |     +-- Stable Audio, ACE-Step, CLAP
    |     +-- Llama.cpp (local LLM)
    |
    +-- Storage
          +-- voices/          (your reference voice samples)
          +-- output_tts/      (temporary working files)
          +-- projects_output/ (saved project files)
          +-- brain/           (chatbot memory and prompts)
          +-- settings/        (saved parameter presets)
```

## Key Design Principles

1. **Local-first privacy** -- All processing happens on your hardware. No data leaves your machine unless you explicitly use the OpenRouter cloud backend.

2. **Load only what you need** -- Models consume significant GPU memory. LocalSoundsAPI lets you load and unload each model independently, so you're never forced to have everything in memory at once.

3. **Multi-GPU support** -- If you have multiple GPUs, you can assign different models to different devices. Run XTTS on GPU 0 and Whisper on GPU 1, for example.

4. **Project-based workflow** -- Generated audio is organized into project folders under `projects_output/`. Each project keeps its audio files, transcriptions, subtitles, and videos together.

5. **Recovery built in** -- Long TTS jobs track their progress. If something fails mid-way, you can recover and continue from where it left off rather than starting over.

---

> **Screenshot suggestion:** Take a wide screenshot of the full web interface with all sections collapsed, showing the section headers (Upload & Transcribe, XTTS-v2 TTS, Fish Speech Voice, Kokoro Voice, Stable Audio Music/SFX, ACE-Step Music, Video Production Studio, Chatbot). This gives readers an immediate sense of the app's scope and layout.
