# Chapter 15: Troubleshooting

## Model Loading Issues

### Model won't load -- "Out of memory" error

**Cause:** Not enough GPU VRAM to fit the model.

**Solutions:**
1. Unload other models first to free VRAM
2. Check available VRAM: open a terminal and run `nvidia-smi`
3. Try loading on a different GPU (if you have multiple)
4. Use CPU mode (slower but always works)
5. For Whisper, switch to a smaller model in `config.py` (base.en instead of medium.en)

### Model won't load -- download fails

**Cause:** Network issue preventing model download from Hugging Face.

**Solutions:**
1. Check your internet connection
2. If behind a proxy, configure Python's proxy settings
3. Try again -- Hugging Face may be temporarily unavailable
4. Manually download model files and place them in the correct `models/` subdirectory

### Status badge stuck on "LOADING"

**Cause:** Model loading is taking a long time or has hung.

**Solutions:**
1. Wait longer -- first-time loads include downloads which can be slow
2. Check the terminal for error messages
3. Restart the app and try again

---

## TTS Generation Issues

### Generated speech sounds garbled or slurred

**Cause:** Temperature too high, or poor voice reference quality.

**Solutions:**
1. Lower the temperature (try 0.60-0.70)
2. Increase repetition penalty (try 3.0-5.0 for XTTS)
3. Use a cleaner voice reference (no background noise, no music)
4. Try a shorter text -- break long text into smaller pieces

### Words are skipped or missing in the output

**Cause:** Common with Kokoro when encountering unknown words; or Whisper verification is rejecting chunks.

**Solutions:**
1. For Kokoro: spell out unusual words phonetically or switch to XTTS/Fish
2. Lower the Whisper tolerance threshold
3. Disable Whisper verification temporarily to see if the raw output is acceptable
4. Check the terminal for retry messages

### Audio has echo or room reverb

**Cause:** Voice reference has room reverb, or de-reverb is too low.

**Solutions:**
1. Increase the Clean/De-Reverb slider (try 80-100%)
2. Use a better voice reference recorded in a quiet, treated room
3. Re-record the reference closer to the microphone

### Audio has harsh "S" sounds (sibilance)

**Cause:** Some voices and TTS engines produce prominent sibilance.

**Solutions:**
1. Increase the De-Ess slider (try 30-60%)
2. Post-process with external audio tools for more precise control

### Generation is extremely slow

**Cause:** Running on CPU, or model is too large for available VRAM (causing swap).

**Solutions:**
1. Make sure the model is loaded on GPU, not CPU
2. Check that CUDA is properly installed: run `python -c "import torch; print(torch.cuda.is_available())"`
3. Unload other models to ensure full VRAM is available
4. For previews, use Kokoro (fastest) instead of Fish Speech (slowest)

### Whisper verification keeps failing (retries endlessly)

**Cause:** Tolerance threshold too high, or the TTS output doesn't closely match the input text.

**Solutions:**
1. Lower the tolerance (try 0.72-0.78)
2. For Kokoro: turn off Whisper verification or set it to 0.92+
3. Simplify the input text -- remove complex punctuation, abbreviations
4. Edit the `job.json` file and set `"verify_whisper": false` for the problematic chunk
5. If all else fails, disable Whisper verification entirely

---

## Job Recovery

### How to recover a failed TTS job

1. Make sure the same model is loaded
2. Set the same save path as the original job
3. Type `##recover##` in the text area
4. Click Generate

The app reads `job.json` from the project directory and retries only failed chunks.

### job.json doesn't exist

The job tracking file is only created when you use a save path. If you generated without a save path (temp output), there's no recovery file.

### Some chunks keep failing after recovery

1. Open `job.json` in a text editor
2. Find the failing chunk entries
3. Try: lower the temperature, disable Whisper verification, or simplify the text for that chunk
4. Save the file and run recovery again

---

## Video Production Issues

### "Create Video" button is disabled

**Cause:** No audio file is selected, or the audio file doesn't have an SRT subtitle file.

**Solutions:**
1. Select an audio file from the project files list
2. Transcribe it first (click "Transcribe with Whisper")
3. Verify that a `.srt` file exists alongside the audio file

### Video creation fails with FFmpeg error

**Cause:** FFmpeg binary not found or misconfigured.

**Solutions:**
1. Verify `bin/ffmpeg/bin/` contains `ffmpeg.exe` and `ffprobe.exe`
2. Check the `FFMPEG_BIN` path in `config.py`
3. Check the terminal for the specific FFmpeg error message
4. Try a different resolution or background mode

### Subtitles don't appear in the video

**Cause:** SRT file is empty or malformed.

**Solutions:**
1. Check the transcription text in the Production Studio -- is it empty?
2. Re-transcribe the audio file
3. Open the `.srt` file in a text editor to verify it has valid content

---

## Chatbot Issues

### Local Llama model won't load

**Cause:** Model file is corrupted, too large for memory, or wrong format.

**Solutions:**
1. Verify the file is a valid `.gguf` format
2. Try a smaller model
3. Reduce GPU layers to offload some work to CPU
4. Check `LLM_DIRECTORY` in `config.py` points to the correct folder

### LM Studio connection fails

**Cause:** LM Studio isn't running, or the API address is wrong.

**Solutions:**
1. Make sure LM Studio is running and has a model loaded
2. Check that `LMSTUDIO_API_BASE` in `config.py` matches LM Studio's settings (default: `http://127.0.0.1:1234/v1`)
3. Try loading a model in LM Studio and refreshing the status

### OpenRouter returns an error

**Cause:** Invalid API key, insufficient credits, or selected model unavailable.

**Solutions:**
1. Verify your API key in `config.py`
2. Check your OpenRouter account balance
3. Try a different model from the dropdown
4. Check OpenRouter's status page for outages

### Chatbot response is cut off

**Cause:** Max tokens setting is too low.

**Solutions:**
1. Open the gear settings panel
2. Increase the Max Tokens slider
3. For local models, also ensure the Context Length is sufficient

---

## Stable Audio / ACE-Step Issues

### Generated audio is noisy or low quality

**Solutions:**
1. Increase the Steps parameter (try 80-100 for Stable Audio, 50-60 for ACE-Step)
2. Adjust the Guidance Scale (try 4-6)
3. Write a more specific prompt
4. Generate more variants and use CLAP scoring to pick the best

### Output doesn't match the prompt

**Solutions:**
1. Increase the Guidance Scale for stronger prompt adherence
2. Be more specific in your prompt description
3. Use negative prompts to exclude unwanted elements
4. Try different seeds

---

## General Issues

### App won't start

**Common causes and solutions:**
1. **Port in use:** Another process is using port 5006. Use `--port 5007` or kill the other process.
2. **Missing dependencies:** Run `pip install -r requirements.txt` again
3. **Python version:** Ensure Python 3.9+
4. **CUDA mismatch:** PyTorch CUDA version must match your NVIDIA driver

### Browser shows a blank page

1. Clear browser cache and refresh
2. Check the terminal for JavaScript errors
3. Try a different browser (Chrome, Firefox, Edge)

### Files aren't being saved

1. Check that the save path is correct
2. Verify `projects_output/` directory exists and is writable
3. Check available disk space

### App crashes during generation

1. Check the terminal for error messages
2. Most likely cause is GPU out of memory -- unload unused models
3. If the crash is reproducible, try the same text with different settings
4. For TTS, use `##recover##` to resume

---

> **Screenshot suggestions:**
> 1. The terminal showing a typical error message (e.g., CUDA out of memory) to help users recognize common errors
> 2. The nvidia-smi output showing GPU memory usage
> 3. A job.json file open in a text editor showing chunk entries
