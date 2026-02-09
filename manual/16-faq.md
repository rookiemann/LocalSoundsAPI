# Chapter 16: Frequently Asked Questions

## General

### Q: Can I use LocalSoundsAPI without a GPU?

**A:** Yes. Every model supports CPU mode. Select "CPU" from the device dropdown before loading. Expect significantly slower generation times (roughly 10-50x slower than GPU for most models). Kokoro is the exception -- it runs at 30-40x real-time even on CPU, making it a great choice for GPU-free setups.

### Q: Is my data private?

**A:** Yes, when using local models or LM Studio. All processing happens on your machine and nothing leaves it. The only exception is the **OpenRouter** chatbot backend, which sends your conversation to external cloud servers. The TTS engines, audio generators, and transcription always run locally.

### Q: Can I host this publicly / on a server?

**A:** The app is designed for local use on `127.0.0.1`. While it listens on `0.0.0.0` (all interfaces), it lacks authentication, rate limiting, and other security features needed for public deployment. If you want to use it on a local network, understand that anyone on your network can access it. Do not expose it to the open internet without adding proper security.

### Q: How do I update the models to newer versions?

**A:** Delete the model folder (e.g., `models/XTTS-v2/`) and restart the app. The next time you click "Load," it will download the latest version from Hugging Face.

### Q: Can I run multiple instances at the same time?

**A:** Yes. Start each instance on a different port:
```
python main.py --port 5006
python main.py --port 5007
```
Each instance is fully independent. Be careful about GPU memory -- two instances loading the same model will use double the VRAM.

---

## Text-to-Speech

### Q: What's the difference between XTTS, Fish Speech, and Kokoro?

**A:**

| | XTTS-v2 | Fish Speech | Kokoro |
|-|---------|-------------|--------|
| **Speed** | Medium | Slow | Very fast |
| **Quality** | Very good | Excellent | Good |
| **Voice cloning** | Yes | Yes (best quality) | No |
| **Preset voices** | 59 | None | 19 |
| **VRAM** | ~6 GB | ~8 GB | ~2 GB |
| **CPU usable** | Yes (slow) | Yes (very slow) | Yes (fast!) |
| **Best for** | General use | Final production | Quick previews |

**Quick guide:**
- Need voice cloning? Start with **XTTS**, use **Fish Speech** for final output
- Need speed? Use **Kokoro**
- Need quality? Use **Fish Speech**
- Need flexibility? Use **XTTS**

### Q: How long should my voice reference file be?

**A:** 10-30 seconds for XTTS, 8-20 seconds for Fish Speech. The reference should be:
- Clean speech without background noise or music
- Natural conversational tone (not monotone reading)
- Single speaker only
- Clear recording quality

### Q: Why does generation keep retrying the same chunk?

**A:** Whisper verification is rejecting the output. Try:
1. Lowering the tolerance threshold (e.g., from 0.80 to 0.74)
2. Lowering the temperature
3. Simplifying the text for that section
4. Disabling Whisper verification if speed matters more than perfect accuracy

### Q: What does `##recover##` do?

**A:** When you type `##recover##` in the text area and click Generate, the app looks for a `job.json` file in your project directory. This file tracks the status of each text chunk. The recovery process retries only the chunks that failed, keeping all successful chunks intact. It's like resuming a download instead of starting over.

### Q: Can I generate speech in languages other than English?

**A:** XTTS-v2 supports multiple languages. Fish Speech also has multilingual support. Kokoro is English-only (it uses eSpeak-ng for phoneme conversion). For non-English text, XTTS is your best bet.

---

## Audio Generation

### Q: How do I get better sound effects from Stable Audio?

**A:**
1. Be specific in your prompts (describe instruments, texture, tempo, mood)
2. Use negative prompts to exclude unwanted elements
3. Generate 3-4 variants and let CLAP pick the best one
4. Keep SFX short (5-12 seconds)
5. Use 80-100 steps for good quality
6. Experiment with the audio mode (Impact vs Ambient vs Music)

### Q: Can ACE-Step generate full songs with vocals?

**A:** ACE-Step can generate music with sung or rapped lyrics. Write the first line as a style description and the remaining lines as lyrics. The quality is acceptable but not studio-grade. For instrumental music, omit the lyrics or include "instrumental" in the style line.

### Q: What is the CLAP score?

**A:** CLAP (Contrastive Language-Audio Pretraining) is a model that scores how well an audio clip matches a text description. When you generate multiple variants, CLAP scores each one and ranks them. Higher scores mean the audio better matches your prompt. It's not perfect, but it's a useful automatic quality filter.

---

## Video Production

### Q: What video formats are supported?

**A:** Output is MP4 (for solid color and image backgrounds) or WebM (for transparent background). Input media can be any format FFmpeg supports, including MP4, WebM, MOV, AVI, MKV for video and JPG, PNG, GIF, BMP, WebP for images.

### Q: Can I edit the subtitles before creating the video?

**A:** The SRT file is a standard text file that you can edit with any text editor. After editing, create the video as normal -- it will use the modified SRT file. The transcription display in the app is read-only, but the underlying file is fully editable.

### Q: How does the "Cycle Images" background mode work?

**A:** It takes all image and video files in your project folder and uses them as rotating backgrounds behind the subtitles. Images are displayed in sequence, each for an equal portion of the audio duration. This creates a slideshow-style video automatically.

---

## Chatbot

### Q: What .gguf models work with the local Llama backend?

**A:** Any GGUF format model compatible with llama-cpp-python. Popular options include Llama, Mistral, Phi, and other open-source models in GGUF format. The GPU Layers slider lets you control how much of the model is offloaded to your GPU.

### Q: Can I use the chatbot while generating TTS?

**A:** Yes, if they're on different devices or using different backends. For example, run TTS on GPU 0 and the chatbot via LM Studio or OpenRouter. Running both on the same GPU may cause memory issues.

### Q: Where are my conversations stored?

**A:**
- Current conversation: `brain/context_history/current.json`
- Archived conversations: `brain/context_history/archives/`
- System prompts: `brain/system_prompt.json` and `brain/[preset_name].json`

All files are standard JSON and can be backed up, edited, or transferred.

---

## Performance

### Q: How much disk space do I need?

**A:**
- Application code: ~50 MB
- All models (if downloaded): ~30-40 GB
- Projects and output: varies by usage
- **Total recommended:** 100-200 GB free

### Q: How can I make generation faster?

**A:**
1. Use GPU instead of CPU
2. Use Kokoro for quick previews, Fish Speech for final output
3. Unload unused models to free VRAM
4. Reduce inference steps (for Stable Audio / ACE-Step)
5. Disable Whisper verification when speed matters more than perfect accuracy
6. Use a smaller Whisper model (base.en instead of medium.en)

### Q: Can I use AMD GPUs?

**A:** PyTorch has experimental ROCm support for AMD GPUs on Linux. On Windows, AMD GPU support is limited. Check the PyTorch documentation for the latest AMD compatibility.

---

> **Screenshot suggestion:** No screenshots needed for the FAQ -- this is a text-reference chapter. However, you could include a screenshot of the app's built-in "Helpful Links" section, which points to external documentation.
