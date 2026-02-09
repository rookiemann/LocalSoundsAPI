# Chapter 12: Settings and Presets

LocalSoundsAPI provides a settings preset system that lets you save and recall the complete set of parameters across all sections. This is invaluable when you've found the perfect combination of settings for a particular voice, genre, or workflow.

## The Settings Toolbar

At the top of the main page, the toolbar contains the preset controls:

| Control | Purpose |
|---------|---------|
| Preset dropdown | Select a saved preset to load |
| Preset name input | Name for a new preset |
| Save Settings button | Save current settings to the named preset |

## Saving a Preset

1. Configure all sections to your liking (temperature, speed, voice selections, audio modes, etc.)
2. Type a name in the **preset name input** (e.g., `Audiobook_Voice_A`)
3. Click **Save Settings**

The preset saves all parameters across every section of the app, including:
- XTTS settings (temperature, repetition penalty, speed, de-reverb, de-ess, voice mode, output format, etc.)
- Fish Speech settings (temperature, top P, speed, reference prompt, etc.)
- Kokoro settings (creativity, diversity, speed, etc.)
- Stable Audio settings (steps, length, guidance, audio mode, etc.)
- ACE-Step settings (steps, duration, guidance, scheduler, all advanced parameters, etc.)
- Chatbot settings (temperature, max tokens, top P, top K, penalties, etc.)

## Loading a Preset

1. Click the **preset dropdown**
2. Select the preset you want
3. All settings across the app update instantly

## Default Preset

The `A_default` preset is included with the app and contains sensible starting values. You can use it as a baseline and create your own presets from there.

## Where Presets Are Stored

Presets are saved as JSON files in the `settings/` directory:

```
settings/
  A_default.json     -- The built-in default preset
  AA_notes.json      -- Notes about settings (reference file)
  My_Custom.json     -- Your saved presets
```

You can manually edit these JSON files, copy them between machines, or share them with others.

## Configuration File (config.py)

For deeper configuration that goes beyond the web UI presets, edit `config.py` directly. This file controls:

### Audio Post-Processing Parameters

Each TTS engine has its own set of post-processing parameters:

**XTTS Post-Processing:**
```
XTTS_PADDING_SECONDS    = 0.5    -- Silence padding added to chunks
XTTS_CLIPPING_THRESHOLD = 0.95   -- Peak level that triggers clipping protection
XTTS_TARGET_LUFS        = -23.0  -- Loudness normalization target
XTTS_TRIM_DB            = -35    -- Silence detection threshold for trimming
XTTS_MIN_SILENCE        = 500    -- Minimum silence duration (ms) to trim
XTTS_FRONT_PROTECT      = 100    -- Protected silence at start (ms)
XTTS_END_PROTECT        = 800    -- Protected silence at end (ms)
XTTS_FRONT_PAD          = 0.0    -- Additional padding at start (seconds)
XTTS_INTER_PAUSE        = 0.25   -- Pause between chunks (seconds)
```

**Fish Speech Post-Processing:**
```
FISH_PADDING_SECONDS    = 0.5
FISH_CLIPPING_THRESHOLD = 0.95
FISH_TARGET_LUFS        = -23.0
FISH_TRIM_DB            = -40
FISH_MIN_SILENCE        = 400
FISH_FRONT_PROTECT      = 80
FISH_END_PROTECT        = 600
FISH_FRONT_PAD          = 0.0
FISH_INTER_PAUSE        = 0.2
```

**Kokoro Post-Processing:**
```
KOKORO_PADDING_SECONDS    = 0.5
KOKORO_CLIPPING_THRESHOLD = 0.95
KOKORO_TARGET_LUFS        = -23.0
KOKORO_TRIM_DB            = -40
KOKORO_MIN_SILENCE        = 300
KOKORO_FRONT_PROTECT      = 250
KOKORO_END_PROTECT        = 1100
KOKORO_FRONT_PAD          = 0.15
KOKORO_INTER_PAUSE        = 0.3
```

### Understanding Post-Processing Settings

**TARGET_LUFS** -- The loudness normalization target. Standard broadcast is -23.0 LUFS. For Kokoro, some voices sound better with different targets:
- `-26.0` -- Recommended for most Kokoro voices (am_onyx, af_bella, etc.)
- `-25.0` -- Slightly cooler voices (am_adam, af_emma)
- `-23.0` -- Default, used for older voice styles

**TRIM_DB** -- How quiet audio must be to be considered "silence" and trimmed. Lower values (more negative) are more aggressive.

**MIN_SILENCE** -- How long a quiet section must be before it's trimmed (in milliseconds).

**FRONT_PROTECT / END_PROTECT** -- How much silence at the beginning and end of each chunk is protected from trimming (in milliseconds). This prevents cutting off the start or tail of words.

**INTER_PAUSE** -- How much silence is inserted between concatenated chunks (in seconds). Increase this if words between chunks feel too close together.

### Job Recovery Attempts

```
XTTS_AUTO_TRIGGER_JOB_RECOVERY_ATTEMPTS = 3
FISH_AUTO_TRIGGER_JOB_RECOVERY_ATTEMPTS = 3
KOKORO_AUTO_TRIGGER_JOB_RECOVERY_ATTEMPTS = 3
```

When a TTS chunk fails Whisper verification, the system retries up to this many times before marking the chunk as failed. Three attempts is the default and is usually sufficient.

### Other Config Options

- **DELETE_OUTPUT_ON_STARTUP** -- Set to `True` to clear the temporary `output_tts/` folder each time the app starts. Set to `False` to preserve temporary files.
- **WHISPER_PATH** -- Choose which Whisper model to use (base.en, medium.en, or large-v3)
- **LLM_DEVICE** -- GPU device for local Llama models
- **LLM_DIRECTORY** -- Path to your .gguf model files
- **LMSTUDIO_API_BASE** -- LM Studio API endpoint
- **OPENROUTER_API_KEY** -- Your OpenRouter API key

## Tips for Managing Settings

1. **Create presets for each use case.** An "Audiobook" preset, a "Quick Preview" preset, a "Sound Effects" preset, etc.

2. **Name presets descriptively.** `Audiobook_VoiceA_Slow` is more useful than `preset1`.

3. **Keep the default preset.** Don't overwrite `A_default.json` -- use it as a reference for starting values.

4. **Back up your settings folder.** Copy the `settings/` directory to keep your presets safe.

5. **Share presets.** JSON files can be shared with other LocalSoundsAPI users. Just copy the files into their `settings/` directory.

---

> **Screenshot suggestions:**
> 1. The toolbar area showing the preset dropdown, name input, and Save Settings button
> 2. The preset dropdown open showing multiple saved presets
> 3. A portion of the config.py file showing the post-processing parameters with comments
