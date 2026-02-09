# Chapter 3: Getting Started

## Launching the Application

Open a terminal in the LocalSoundsAPI directory and run:

```
python main.py
```

Then open your browser and go to:

```
http://127.0.0.1:5006
```

## The Main Interface

The entire application lives on a single page. Each feature is organized into a collapsible section that you can expand or collapse by clicking its header bar. From top to bottom, the sections are:

1. **Toolbar** -- Shutdown button and settings preset management
2. **Upload & Transcribe** -- Upload voice reference files and transcribe audio
3. **XTTS-v2 TTS** -- Voice cloning text-to-speech
4. **Fish Speech Voice** -- High-quality text-to-speech
5. **Kokoro Voice** -- Fast, lightweight text-to-speech
6. **Stable Audio Music/SFX** -- Sound effect and music generation
7. **ACE-Step Music** -- Full song generation with lyrics
8. **Video Production Studio** -- Create videos with subtitles
9. **Chatbot** -- AI chat with local or cloud LLMs
10. **Master Cheat Sheet** -- Quick reference for recommended settings
11. **Helpful Links** -- External documentation links

All sections start collapsed. Click on any section header to expand it.

## The Toolbar

The toolbar sits at the top of the page and contains two important features:

### Shutdown Button
The red **Shutdown** button gracefully stops the server. This properly unloads models and cleans up resources. Always use this instead of just closing the terminal window when possible.

### Settings Presets
Next to the shutdown button, you'll find the settings preset controls:

- **Preset dropdown** -- Select a previously saved preset to load
- **Preset name input** -- Type a name for a new preset
- **Save Settings** -- Saves all current parameters across every section into a named preset

This is extremely useful when you've dialed in the perfect combination of parameters for a particular voice or task and want to recall them later.

## The Three-Column Layout

Most feature sections follow a consistent three-column layout:

| Left Column | Center Column | Right Column |
|-------------|---------------|--------------|
| Model controls | Text input / prompts | Output controls |
| Voice selection | API payload view | Audio format |
| Device selection | | Project save path |
| Load/Unload buttons | | Generate/Stop buttons |
| Settings gear icon | | Results and playback |

### The Settings Gear

In the left column of most sections, you'll notice a small gear icon. Clicking it slides the panel over to reveal inference settings (temperature, accuracy, etc.). Click the back arrow to return to the main panel. This keeps the interface clean while still giving you full control.

### The API Payload Button

In the center column, most sections have an "API Payload" button. Clicking it shows you the exact JSON dictionary that would be sent to the API endpoint. This is useful for:

- **Developers** who want to call the API programmatically
- **Debugging** when something isn't working as expected
- **Copying** the payload to use in scripts or other tools

## Device Selection

Every model has a device dropdown that lets you choose where to load it:

| Option | Meaning |
|--------|---------|
| CPU | Run on your processor (slow but always available) |
| 0 | First GPU (usually your primary graphics card) |
| 1 | Second GPU |
| 2-10 | Additional GPUs if you have them |

If you only have one GPU, use **0**. If you don't have a GPU, use **CPU**.

**Tip:** You can spread models across multiple GPUs. For example, load XTTS on GPU 0 and Whisper on GPU 1 to run them simultaneously without competing for memory.

## The Load/Unload Workflow

Every AI model in LocalSoundsAPI follows the same pattern:

1. **Select your device** from the dropdown (CPU, 0, 1, etc.)
2. **Click Load** -- The model downloads (first time only) and loads into memory
3. **Use the model** -- Generate speech, music, transcriptions, etc.
4. **Click Unload** when done -- Frees the GPU/CPU memory

The status badge next to the Load/Unload buttons shows the current state:

- **NOT LOADED** (grey) -- Model is not in memory
- **LOADED** (green) -- Model is ready to use
- **LOADING** (yellow) -- Model is being loaded

**Important:** You don't need to unload before switching to another feature. But if you're running low on GPU memory, unloading models you're not currently using is the best way to free space.

## Project Save Paths

Several sections include a text input labeled with placeholder text like `'Project', 'Project\SubDirectory'`. This controls where generated files are saved:

- **Leave it blank** -- Files go to the temporary `output_tts/` directory (may be cleared on restart)
- **Enter a name** like `MyNovel` -- Files are saved to `projects_output/MyNovel/`
- **Enter a path** like `MyNovel\Chapter1` -- Files are saved to `projects_output/MyNovel/Chapter1/`

Project folders are persistent and are never automatically deleted.

## Output Formats

All TTS and audio generation sections let you choose the output audio format:

| Format | Best For |
|--------|----------|
| WAV | Highest quality, no compression, large files |
| FLAC | Lossless compression, good quality-to-size ratio |
| MP3 | Universal compatibility, lossy compression |
| OGG | Good quality, smaller than WAV, open format |
| M4A | Good quality, widely supported on Apple devices |

## Your First Generation (Quick Start)

Here's the fastest path to hearing your first AI-generated speech:

1. Launch the app and open it in your browser
2. Click **"Kokoro Voice"** to expand that section (it's the lightest model)
3. In the left column, select a voice from the dropdown (try `af_heart`)
4. Select device **0** (or CPU) and click **Load**
5. Wait for the status badge to turn green
6. In the center text area, type: `Hello! This is my first time using LocalSoundsAPI.`
7. In the right column, click **Generate**
8. An audio player will appear in the results area -- click play to listen

Congratulations! You've just generated your first AI speech.

---

> **Screenshot suggestion:** Take three screenshots:
> 1. The full page with all sections collapsed, showing the toolbar at top
> 2. One section expanded (like Kokoro) showing the three-column layout clearly
> 3. The settings gear panel slid open, showing inference parameters
