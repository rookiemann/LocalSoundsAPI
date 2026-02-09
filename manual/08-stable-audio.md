# Chapter 8: Stable Audio -- Music and Sound Effects

Stable Audio (by Stability AI) generates music clips and sound effects from text descriptions. Describe what you want to hear, and the model creates original audio up to 47 seconds long. Combined with the CLAP scoring model, it can generate multiple variants and automatically rank them by quality.

## When to Use Stable Audio

- You need **sound effects** (impacts, ambient sounds, foley, explosions)
- You want **short music clips** (jingles, intros, background music)
- You need **original audio** that doesn't come from a sample library
- You want to **experiment with creative sound design**

## Section Layout

| Left Column | Center Column | Right Column |
|-------------|---------------|--------------|
| Quick prompt templates | Prompt text area | Waveforms count (1-4) |
| Device selection | Negative prompt | Audio mode |
| Load/Unload | API Payload view | Output format |
| Gear icon for settings | | Save path |
| | | Generate/Stop |
| | | Results |

## Loading the Model

1. Select your **device** (GPU only -- Stable Audio is GPU-intensive)
2. Click **Load**
3. First load downloads the model (~10 GB VRAM required)

**Note:** Stable Audio also loads the CLAP model for quality scoring. This adds approximately 1 GB of VRAM.

## Quick Prompt Templates

The left column provides one-click prompt templates to get you started:

| Template | Description |
|----------|-------------|
| Deep House | Electronic deep house music with drums and bass |
| Hip-Hop | Hip-hop beat with samples and rhythm |
| Cinematic | Orchestral cinematic score |
| Impact | Punchy impact sound effect |
| Ambient | Atmospheric ambient soundscape |
| Explosion | Explosion and blast sound effect |
| Clear | Clears the prompt fields |

These templates fill in both the prompt and appropriate settings. You can use them as-is or modify them as a starting point.

## Writing Prompts

### Main Prompt
The top text area is where you describe the sound you want. Be specific and descriptive:

**Good prompts:**
- `Warm deep house loop, 120 bpm, rolling bassline, crisp hi-hats, vinyl crackle`
- `Thunder crack followed by heavy rain on a tin roof, close distance`
- `Upbeat acoustic guitar strumming, major key, happy summer feeling`

**Less effective prompts:**
- `Music` (too vague)
- `A sound` (not descriptive enough)
- `Something cool` (no useful information for the model)

### Negative Prompt
The bottom text area tells the model what to avoid:

- `vocals, singing, voice, speech`
- `distortion, clipping, noise`
- `drums, percussion` (for a drums-free track)

Leave this empty if you don't have specific exclusions.

## Audio Modes

The **Audio Mode** dropdown in the right column controls how the model processes and normalizes the output:

| Mode | Best For | Characteristics |
|------|----------|----------------|
| Impact / Foley | Short, punchy sound effects | Tight, quick sounds |
| Ambient / Field | Background textures, loops | Smooth, continuous audio |
| Jingle / Intro | Music clips | Full, polished sound |

Choose the mode that best matches your intended use.

## Advanced Settings (Gear Panel)

Click the gear icon to access the diffusion parameters:

### Steps (default: 100)
The number of inference steps. More steps = better quality but slower generation.

| Value | Effect |
|-------|--------|
| 10-50 | Fast but noisy/low quality |
| 60-80 | Decent quality, reasonable speed |
| 80-120 | Recommended -- good quality |
| 120-200 | Diminishing returns, mostly for experimentation |

### Length (default: 30.0 seconds)
Duration of the generated audio. Range: 10 to 47 seconds.

- **Sound effects:** 5-12 seconds usually sufficient
- **Music clips:** 20-47 seconds for a full passage
- **Longer clips** with complex prompts may lose coherence

### Guidance Scale (default: 7.0)
How closely the model follows your prompt (also called CFG scale).

| Value | Effect |
|-------|--------|
| 1-3 | Very loose interpretation |
| 3.5-5.0 | Good prompt adherence (recommended for SFX) |
| 5-8 | Strong prompt following |
| 8-15 | Very strict, may sound forced |
| > 15 | Often over-constrained |

### Eta (default: 0.0)
Adds controlled noise to the generation process. Usually best left at 0.

### Seed (default: -1)
Set a specific seed number for reproducible results. -1 means random. If you get a result you like, note the seed to recreate it later.

## Waveform Variants

The **Waveforms** slider (1 to 4) in the right column controls how many variants are generated per request. The app generates all variants, then uses the **CLAP model** to score each one against your prompt. Results are displayed ranked from best to worst match.

**Recommended:** Generate 3-4 variants and pick the best one. Audio generation has inherent randomness, so multiple attempts often yield one standout result.

## Generating Audio

1. Load the model
2. Write your prompt (and optionally a negative prompt)
3. Select the audio mode
4. Set the number of waveforms (variants)
5. Click **Generate**

### Results

Each generated variant appears as an audio player in the results area, along with its CLAP quality score. The variants are ranked best-to-worst. You can:

- **Play** each variant to listen
- **Compare** scores to identify the best match
- Files are automatically saved if you specified a save path

### Stopping Generation
Click **Stop** to cancel. Completed variants are preserved.

## Tips for Better Results

1. **Be specific in your prompts.** Describe instruments, tempo (BPM), mood, and genre.

2. **Use negative prompts.** If you keep getting unwanted vocals, add `vocals, singing, voice` to the negative prompt.

3. **Generate multiple variants.** The CLAP scoring does a good job of identifying the best outputs.

4. **Keep SFX short.** Sound effects work best at 5-12 seconds. Longer durations tend to drift.

5. **Experiment with guidance scale.** Lower values (3-5) give more creative results; higher values (6-8) follow the prompt more closely.

6. **Note good seeds.** When you find a result you love, remember the seed for reproducibility.

---

> **Screenshot suggestions:**
> 1. Stable Audio section expanded showing the prompt templates on the left and the prompt text areas in the center
> 2. The gear settings panel open showing Steps, Length, Guidance, Eta, and Seed controls
> 3. Multiple generated variants in the results area with CLAP scores visible, showing the ranked output
> 4. The Audio Mode dropdown expanded showing the SFX and Music options
