# Chapter 6: Fish Speech TTS

Fish Speech (OpenAudio S1-Mini) is a high-quality text-to-speech engine that excels at producing natural, realistic speech. While it's slower than XTTS, it often produces superior audio quality, making it the go-to choice when quality matters more than speed.

## When to Use Fish Speech

- You need the **highest possible voice cloning quality**
- You have a **GPU with sufficient VRAM** (~8 GB)
- You're producing **final output** where quality justifies longer generation times
- You want **near-perfect voice similarity** from a reference sample

## How Fish Speech Differs from XTTS

| Feature | XTTS-v2 | Fish Speech |
|---------|---------|-------------|
| Voice cloning quality | Good | Excellent |
| Speed | Moderate | Slow (3-8x real-time) |
| Built-in voices | 59 presets | None (reference only) |
| VRAM required | ~6 GB | ~8 GB |
| CPU support | Yes | Yes (very slow) |
| Multilingual | Yes | Yes |
| Reference audio | Any length | Best at 8-29 seconds |

## Section Layout

The layout matches the XTTS section's three-column design:

| Left Column | Center Column | Right Column |
|-------------|---------------|--------------|
| Voice selection | Text to speak | Speed control |
| Device selection | API Payload view | Clean / De-reverb |
| Load/Unload | | De-ess |
| Gear icon for settings | | Output format |
| | | Save path |
| | | Generate/Stop |
| | | Results |

## Loading the Model

1. Select your **device** (GPU recommended)
2. Click **Load**
3. First load downloads the model files from Hugging Face

## Selecting a Voice

Fish Speech uses your uploaded voice references from the `voices/` directory. It does not have built-in speaker presets.

1. Select a voice from the **Fish Speech Voice** dropdown
2. Click **Refresh** if you've recently uploaded new voices
3. The audio player lets you preview the reference

**Important:** Fish Speech automatically trims reference audio to a maximum of 29 seconds. For best results, use clean reference audio between 8 and 20 seconds long.

## Inference Settings (Gear Panel)

Click the gear icon to access Fish Speech-specific settings:

### Temperature (default: 0.7)
Controls output randomness. Fish Speech is more sensitive to temperature than XTTS.

| Value | Effect |
|-------|--------|
| 0.55-0.65 | Stable, controlled output |
| 0.65-0.75 | Recommended -- natural with good stability |
| > 0.75 | May cause accent drift or unnatural inflection |

### Top P (default: 0.7)
Nucleus sampling threshold. Controls the diversity of generated speech.

| Value | Effect |
|-------|--------|
| 0.60-0.70 | Focused, predictable |
| 0.70-0.85 | Recommended range |
| > 0.90 | More varied but less controlled |

### Accuracy / Tolerance (default: 0.80)
Same as XTTS -- sets the Whisper verification threshold.

### Verify with Whisper (default: on)
Enables quality checking of generated audio.

### Skip Audio Processing
Bypasses post-processing for raw output.

### Reference Style Prompt (optional)
A text description that guides the speaking style. For example:

- `A clear, professional speaker.`
- `A warm, conversational narrator with a calm tone.`
- `An energetic announcer with enthusiasm.`

This prompt influences how Fish Speech interprets the voice reference and renders the speech.

## Audio Output Controls

The right column controls are identical to XTTS:

- **Speed** -- Playback speed with pitch correction (default: 1.0)
- **Clean / De-Reverb** -- Room reverb reduction (default: 70%)
- **De-Ess** -- Sibilance reduction (default: 0%)
- **Output Format** -- WAV, FLAC, MP3, OGG, M4A
- **Save Path** -- Project folder name or leave blank for temp

## Generating Speech

1. Load the model and select a voice
2. Type your text in the center area
3. Optionally set a reference style prompt in the settings
4. Click **Generate**
5. Wait for completion -- Fish Speech is slower but produces high-quality output

### Generation Status
The status text below the Generate button shows real-time progress:
- Which chunk is being processed
- Whether Whisper verification passed or if retries are needed
- Total elapsed time

### Stopping and Recovery
Click **Stop** to cancel. Job recovery works the same as XTTS -- type `##recover##` in the text area with the same save path set to retry failed chunks.

## Tips for Best Results

1. **Reference audio quality is paramount.** Clean, noise-free reference audio between 8-20 seconds produces the best clones.

2. **Keep temperature conservative.** Fish Speech can drift with higher temperatures more than other engines.

3. **Use the reference style prompt.** A brief style description can significantly improve output consistency.

4. **Allow for longer generation times.** Fish Speech prioritizes quality over speed. On an RTX 4090, expect 3-8x real-time (a 10-second clip takes 30-80 seconds to generate).

5. **Monitor Whisper verification.** If you see many retries, try lowering the accuracy threshold slightly, or adjust the temperature downward.

---

> **Screenshot suggestions:**
> 1. Fish Speech section expanded with a voice selected and model loaded
> 2. The gear settings panel showing Temperature, Top P, Accuracy slider, and the Reference Style Prompt text area
> 3. A generation in progress showing the status text with chunk progress
> 4. The results area with a completed audio player after generation
