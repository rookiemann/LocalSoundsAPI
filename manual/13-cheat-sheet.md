# Chapter 13: Recommended Settings Cheat Sheet

This chapter reproduces and expands on the "Master Cheat Sheet" built into the app. Use it as a quick reference for dialing in good parameters.

## XTTS-v2 -- Daily Driver

**Best for:** General-purpose TTS, voice cloning, multilingual content

| Parameter | Recommended | Notes |
|-----------|-------------|-------|
| Temperature | 0.65 - 0.75 | Above 0.85 causes slurring; below 0.55 sounds robotic |
| Speed | 0.90 - 1.15 | RubberBand handles pitch correction at extreme values |
| Repetition Penalty | 3.0 - 6.0 | Too low causes stuttering on long text |
| Top P / Top K | Default | Only change if you hear gibberish |
| Whisper Tolerance | 78% - 84% | Above 90% is too strict; below 70% lets bad output through |
| Clean (De-Reverb) | 60% - 80% | Good for removing room sound |
| De-Ess | 0% - 30% | Only increase if sibilance is distracting |

**Strengths:** Fast, works on CPU, any language, reliable
**Weaknesses:** Voice cloning is good but not perfect

---

## Fish Speech -- Highest Quality Cloning

**Best for:** Premium voice cloning, final production output

| Parameter | Recommended | Notes |
|-----------|-------------|-------|
| Temperature | 0.60 - 0.70 | Above 0.75 causes accent drift |
| Top P | 0.80 - 0.90 | Avoid below 0.70 |
| Reference audio | 8-20 seconds, clean | No background music or noise |
| Whisper Tolerance | 70% - 80% | Can be stricter than XTTS |
| Reference Style Prompt | Short, descriptive | "A clear, professional speaker with calm tone" |

**Strengths:** Near-perfect voice cloning
**Weaknesses:** 3-8x real-time on RTX 4090, occasional failures (use `##recover##`)

---

## Kokoro 82M -- Fast CPU Inference

**Best for:** Quick previews, real-time applications, low-VRAM systems

| Parameter | Recommended | Notes |
|-----------|-------------|-------|
| Speed | 1.3 - 1.6 | Above 1.7 sounds like a chipmunk |
| Creativity (Temp) | 0.5 - 0.8 | Keep moderate for natural output |
| Diversity (Top P) | 0.7 - 0.9 | Standard range |
| Whisper Verify | Off or 92%+ | Lower thresholds cause many false failures |

**Strengths:** 30-40x real-time on CPU, minimal VRAM
**Weaknesses:** Unknown words may produce silence

---

## Stable Audio Open 1.0 -- SFX and Short Music

**Best for:** Sound effects, ambient textures, musical clips up to 47 seconds

| Parameter | Recommended | Notes |
|-----------|-------------|-------|
| Length | 5-12s (SFX), 30-47s (music) | Long complex prompts get muddy |
| Steps | 80 - 100 | Below 60 is noisy |
| CFG / Guidance Scale | 3.5 - 5.0 | Higher = better prompt adherence |
| Waveforms (batch) | 3 - 4 | Use CLAP scoring to pick the best result |
| Eta | 0.0 | Usually best left at zero |

**Strengths:** Excellent sound effects, good music clips
**Weaknesses:** Max 47 seconds, no vocals

---

## ACE-Step -- Full-Length Songs

**Best for:** Music with lyrics, genre-specific tracks, longer compositions

| Parameter | Recommended | Notes |
|-----------|-------------|-------|
| Steps | 45 - 55 | Higher gives minimal quality improvement |
| Guidance | 4.5 - 6.0 | Too low = incoherent output |
| Duration | 10 - 30 seconds | 60s possible but may lose structure |
| Prompt format | First line = genre/style, rest = lyrics | No special tags needed |
| Variants | 3 - 4 | High variance, pick the best |
| Scheduler | euler | Default, reliable |
| CFG Type | cfg | Standard guidance |

**Strengths:** Lyrics-aware generation, genre flexibility
**Weaknesses:** Quality acceptable but not studio-grade

---

## Golden Rules and Essential Tips

These tips apply across all modules:

1. **Save path blank = preview only.** No file is permanently saved.

2. **Enter a folder name = auto-save.** Files go to `projects_output/YourFolder/`.

3. **`##recover##` = instant job resume.** Type this in the text area with the same save path to retry failed chunks.

4. **Whisper keeps failing?** Edit the `job.json` file in your project directory and set `"verify_whisper": false` for the problematic chunk.

5. **Kill a stuck job.** Close the app entirely (use the Shutdown button or close the terminal).

6. **Need true parallel processing?** Run multiple instances on different ports (5006, 5007, 5008...).

7. **Post-processing matters.** For professional results, run your output through external tools (RubberBand, EQ, compression) after generation.

8. **Unload models when switching tasks.** Free GPU memory for the next model.

9. **Use GPU for quality, CPU for previews.** GPU is dramatically faster for all models except Kokoro (which runs great on CPU).

10. **Back up your projects folder.** `projects_output/` contains all your saved work.

---

> **Screenshot suggestion:** Take a screenshot of the built-in "Master Cheat Sheet" section expanded in the app, showing the parameter tables and golden rules. This is already designed as a quick-reference and looks good in the app's dark theme.
