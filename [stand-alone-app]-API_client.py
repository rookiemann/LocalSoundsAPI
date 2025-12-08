# [stand-alone-app]-API_client.py
# Paste ANY payload from your web UI → perfect auto-detection, no errors

import requests
import time

class TTSClient:
    def __init__(self, base_url: str = "http://127.0.0.1:5006"):
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()

    # ─── Load / Unload (fixed signatures) ─────────────────────────────────
    def _load(self, endpoint: str, name: str, device: str = "0"):
        try:
            r = self.session.post(f"{self.base_url}{endpoint}", json={"device": device}, timeout=180)
            r.raise_for_status()
            print(f"{name} → LOADED on {device}")
            return True
        except Exception as e:
            print(f"Failed to load {name}: {e}")
            return False

    def _unload(self, endpoint: str, name: str):
        try:
            r = self.session.post(f"{self.base_url}{endpoint}", timeout=10)
            r.raise_for_status()
            print(f"{name} → UNLOADED")
            return True
        except Exception as e:
            print(f"Failed to unload {name}: {e}")
            return False

    # Fixed: now accept device= keyword properly
    def load_xtts(self, device="0"):      self._load("/load",           "XTTS",         device)
    def unload_xtts(self):                self._unload("/unload",       "XTTS")
    def load_fish(self, device="0"):      self._load("/fish_load",      "FishSpeech",   device)
    def unload_fish(self):                self._unload("/fish_unload",  "FishSpeech")
    def load_kokoro(self, device="0"):    self._load("/kokoro_load",    "Kokoro",       device)
    def unload_kokoro(self):              self._unload("/kokoro_unload","Kokoro")
    def load_whisper(self, device="0"):   self._load("/whisper_load",   "Whisper",      device)
    def unload_whisper(self):             self._unload("/whisper_unload","Whisper")
    def load_stable(self, device="0"):    self._load("/stable_load",    "Stable Audio", device)
    def unload_stable(self):              self._unload("/stable_unload","Stable Audio")
    def load_ace(self, device="0"):       self._load("/ace_load",       "ACE-Step",     device)
    def unload_ace(self):                 self._unload("/ace_unload",   "ACE-Step")

    # ─── Inference ───────────────────────────────────────────────────────
    def infer_xtts(self, **kw):     return self._infer("/infer",        "XTTS",        kw)
    def infer_fish(self, **kw):     return self._infer("/fish_infer",   "FishSpeech",  kw)
    def infer_kokoro(self, **kw):   return self._infer("/kokoro_infer", "Kokoro",      kw)
    def infer_stable(self, **kw):   return self._infer("/stable_infer", "Stable Audio",kw)
    def infer_ace(self, **kw):      return self._infer("/ace_infer",    "ACE-Step",    kw)

    def _infer(self, endpoint: str, name: str, payload: dict):
        payload = payload.copy()
        for k in ["text", "prompt"]:
            if k in payload: payload[k] = payload[k].strip()
        if payload.get("save_path") in (None, "", "null", "None"):
            payload["save_path"] = None

        main = payload.get("prompt") or payload.get("text", "")
        print(f"\n{'='*90}")
        print(f"{name} → {len(main):,} characters | Save → {payload.get('save_path') or 'temp'}")
        print("─" * 90)

        start = time.time()
        try:
            r = self.session.post(f"{self.base_url}{endpoint}", json=payload, timeout=2400)
            r.raise_for_status()
            result = r.json()
            elapsed = time.time() - start
            print(f"SUCCESS | {elapsed:.1f}s")

            if "saved_files" in result:
                print(f"   → {len(result['saved_files'])} file(s) saved")
                for f in result["saved_files"]:
                    best = " (BEST)" if f.get("is_best") else ""
                    print(f"     • {f['filename']}{best}")
            elif "audios" in result:
                print(f"   → {len(result['audios'])} variant(s) generated")
            return result
        except Exception as e:
            print(f"FAILED: {e}")
            if hasattr(e, "response") and e.response:
                try: print("Server:", e.response.json())
                except: print("Raw:", e.response.text[:500])
            return None


client = TTSClient()

# ==================================================================
# PASTE YOUR FULL PAYLOAD FROM THE WEB UI BELOW
# ==================================================================

payload = payload = {
    "text": "The old house stood at the edge of a quiet town, where the streetlights ended and the fields began to roll out like a dark green ocean under the moon. Its windows were mostly broken, and the paint had peeled away in long curls that hung like dead vines. No one had lived there for years, but every autumn the porch light flickered on by itself for a few hours after midnight, as if someone inside still paid the bill and waited for company.\n\nA boy from the town decided one October evening that he would find out why the light came on. He was the kind who collected strange facts the way others collected stones or stamps. He carried a small flashlight, a notebook, and a pocket full of batteries. The air smelled of frost and wood smoke as he crossed the empty field toward the house. His shoes made soft crunching sounds on the dry grass.\n\nWhen he reached the porch, the light was already glowing, a weak yellow bulb behind cracked glass. The front door hung open just enough to slip through without touching it. Inside, the air felt thick and cool, like the inside of a cave. Dust floated in slow motion through the beam of his flashlight. The floorboards sighed under his weight, but nothing else moved.\n\nHe walked through the front hall and into what had once been a living room. A single couch remained, its fabric rotted into gray threads. On a small table beside it sat an old record player, the kind with a heavy arm and a dusty stack of black discs. One record still rested on the turntable, the label long since faded to nothing. The boy brushed the dust away with his sleeve and saw a faint groove where the needle had rested for decades.\n\nHe turned the switch. Nothing happened at first. Then, with a soft pop, the platter began to spin. The needle dropped on its own, scratching across the surface until it found the groove. A low hum filled the room, followed by the slow, crackling sound of music from another time. It was a slow dance tune, gentle and sad, the kind of song people played when they wanted to remember better days.\n\nThe boy stood listening, unsure what to do next. The music seemed to pull the dust into patterns in the air. Shadows stretched and swayed along the walls as if invisible couples moved across the floor. He felt the hair on his arms rise, but he did not leave. Instead he opened his notebook and began to write down everything he saw and heard.\n\nMinutes passed, or maybe hours. Time felt soft inside the house. The song played again and again, never skipping, never ending. The boy wrote until his hand cramped. He described the peeling wallpaper with its tiny faded roses, the way the moonlight came through the broken windows in silver bars, the smell of old wood and faint perfume that lingered in corners.\n\nThen he noticed something odd. Each time the song began again, the room looked a little different. The couch cushions were less sunken. The wallpaper roses looked brighter. A vase appeared on the mantel, holding flowers that had not been there before. The changes were small, but they kept coming. A rug unrolled itself across the floor. Pictures returned to the walls, showing people smiling in clothes from long ago.\n\nThe boy understood then that the house was remembering itself, note by note. Every turn of the record brought back another piece of what it had been when people still lived and laughed inside its walls. He felt like an intruder watching a private dream come true.\n\nHe stepped back toward the hall, meaning to leave before the house finished waking up. But the floorboards no longer creaked. They felt solid and warm under his shoes. The front door had closed without a sound and now looked freshly painted, bright red against white trim. Through the window he could see the porch light burning steady and strong.\n\nThe music changed. The slow dance became something faster, full of horns and clapping hands. Laughter spilled out of the record player, bright and real. The boy turned and saw that the living room was no longer empty. People filled the space, men in suits and women in long dresses, all moving together in perfect time. They did not look like ghosts. They looked alive, cheeks pink, eyes shining. None of them noticed the boy standing by the doorway with his notebook clutched to his chest.\n\nHe watched for a long time. He saw a tall man lift a woman high into the air and spin her until her dress flared like a flower. He saw old couples sitting on the couch holding hands and tapping their feet. He saw children sneaking cookies from a tray on the table, crumbs falling onto the clean rug. The room smelled of cake and coffee and wood polish.\n\nThe boy felt something inside him loosen, like a knot he had carried for years without knowing it. He thought of his own house, quiet and dark since his mother left and his father worked late every night. He thought of the empty chairs at their table and the way the television always stayed on too loud to fill the silence.\n\nWithout deciding to do it, he stepped forward into the light and the music. One of the women saw him and smiled the way adults smile at children who wander into grown-up parties. She held out her hand. The boy took it. Her skin was warm. She guided him into the dance, showing him where to put his feet. He was clumsy at first, but the rhythm was patient, and soon he moved with everyone else.\n\nHours slipped by like minutes. The boy danced until his legs ached and his face hurt from smiling. When the music finally slowed again, the woman led him to the couch and gave him a glass of something sweet and fizzy. The tall man ruffled his hair and told him he had done well for his first time. The children brought him cookies shaped like stars.\n\nAt some point the record reached its final note and did not start again. The people began to fade, not all at once but gently, like smoke drifting out an open window. The woman squeezed his hand once more before she too became part of the moonlight. The room grew quiet. The rug rolled itself away. The flowers in the vase withered and fell. The wallpaper peeled again, roses fading back to gray.\n\nThe boy stood alone in the dusty living room. The record player was silent, the needle lifted and still. His notebook lay open on the floor, pages filled with writing he no longer needed to read. He knew every moment by heart.\n\nHe walked to the front door, which now hung open the way it had when he arrived. The porch light flickered once, twice, then went dark. Outside, the field waited under cold stars. The air smelled only of frost now, sharp and clean.\n\nThe boy crossed the grass back toward town. When he reached his own street, he saw that the windows of his house were lit. His father stood on the porch, looking out into the night, worry clear on his face even from far away. The boy ran the last stretch and threw his arms around his father’s waist. They stood like that for a long time, neither speaking.\n\nYears later, when the boy had grown into a man, he sometimes drove past the old house on the edge of town. The windows stayed broken and the paint kept peeling, but every autumn, for a few hours after midnight, the porch light came on. He never went inside again. He did not need to. Some nights he would park his car across the field and sit with the window down, listening. If the wind was right, he could hear the faint sound of music carried across the grass, slow and sad and beautiful.\n\nHe would close his eyes and smile, remembering warm hands and star-shaped cookies and the way a house could choose to remember the best parts of itself, if only for one more dance.\n\nThe boy kept the notebook for the rest of his life. Its pages turned soft and brown at the edges, and the ink faded to the color of weak tea, but he never threw it away. When he moved into his first small apartment after school, the notebook sat on the shelf above his desk. When he married and bought a little house with blue shutters, it went into a drawer in the bedroom. When his own children were born, he sometimes pulled it out on quiet evenings and read a few lines while they slept.\n\nHis wife noticed the way he touched the cover, careful, almost reverent. She asked once what was inside. He told her it was just an old story from when he was young. She smiled and never asked again, but she always knew when he had been reading it because he would hum the same slow tune under his breath for days afterward.\n\nYears rolled on the way seasons do. The town grew a little bigger, the fields shrank, and new houses went up where corn used to sway. The old house at the edge stayed empty, though people stopped telling scary stories about it. Children dared each other to run up and touch the porch, but they no longer ran away screaming. They said the place felt more sad than frightening, like a book left open on the last page.\n\nOne November evening, when the first real cold had settled in and the sky looked like polished steel, the man (no longer a boy) drove out to the field with his daughter. She was ten, all elbows and questions, with hair the color of late-autumn maple leaves. She had heard bits of the story over the years and wanted to see the house for herself. He had never taken anyone before, but something about the way she asked, quiet and serious, made him say yes.\n\nThey parked where the gravel ended and walked across the stiff grass together. Frost crunched under their boots. The porch light was already on, glowing the same weak yellow it had always been. His daughter slipped her hand into his without thinking. Her fingers were cold, but she did not let go.\n\nInside, everything looked exactly the same and completely different. The dust was thicker. The couch had finally collapsed into a pile of springs and gray cloth. The record player sat under a blanket of cobwebs so fine they looked like lace. The man felt his chest tighten the way it used to when he was small and the world still held pockets of real magic.\n\nHis daughter let go of his hand and walked straight to the record player. She brushed the webs away with the sleeve of her coat, the way he once had. She turned the switch. Nothing happened. She tried again, frowning the small determined frown she wore when puzzles refused to solve themselves.\n\n“It’s broken,” she said.\n\n“Maybe,” he answered. “Or maybe it’s waiting.”\n\nShe looked at him, waiting for the rest. He almost told her everything right then, the dancing, the warm hands, the star cookies, but the words felt too big for the dusty room. Instead he knelt and opened the cabinet beneath the turntable. Inside lay a small wooden box he had never noticed before. The lid was carved with tiny roses.\n\nHe lifted it out and set it on the floor between them. His daughter opened it carefully. Inside were three things: a single black record in a plain paper sleeve, a silver needle still bright after all the years, and a folded square of heavy cream-colored paper. The paper had turned yellow, but the ink was dark and perfect.\n\nThe man unfolded it and read aloud.\n\n“If you have come this far, you already know the song. Play it when the night feels too heavy and the house needs company. One night only. Then let it rest again. Some doors should stay closed most of the time, but none should stay locked forever.”\n\nHis daughter looked up at him, eyes wide. “Are we going to play it?”\n\nHe thought about it for a long time. He thought about the quiet house he and his wife kept, how the children filled it with noise and mess and joy, but how some nights he still woke up reaching for something he could not name. He thought about the way his father had stood on their porch all those years ago, searching the dark for a small boy who came home changed.\n\n“Yes,” he said. “Just this once.”\n\nThey worked together. He showed her how to slide the record from its sleeve without touching the grooves. She fitted the new needle into the arm with steady fingers. When the platter began to turn, the sound it made was clean and new, not the tired scratch of memory. The needle dropped.\n\nThe same slow dance filled the room, gentle and sad and perfect. Dust rose and swirled into shapes that almost looked like people. The wallpaper straightened. The roses bloomed again. The couch lifted itself and grew plump cushions the color of summer sky.\n\nHis daughter gasped when the first couple appeared, solid and real, spinning slowly in the center of the floor. More came after, men and women and children in clothes from another time. The tall man was there, and the woman with the warm hands. They smiled when they saw the girl, the same welcoming smile they had once given a lonely boy.\n\nThe man stayed near the door and watched his daughter step forward. She did not hesitate. One of the women took her hands and showed her the steps. Soon she was laughing, bright loud laughter that bounced off the walls and made the candles appear in their holders, flames steady and gold.\n\nHe felt tears on his cheeks but did not wipe them away. The room smelled of cake again, and coffee, and the sharp sweet tang of oranges. Someone pressed a warm cookie into his hand. He bit into it and tasted childhood and forgiveness and every good thing that refuses to stay lost.\n\nThe night stretched the way it had the first time. They danced until feet hurt and hearts felt light enough to float. When the final note came, the people began to fade. The woman who had taught his daughter the steps hugged her close, then walked to the man and kissed his forehead the way a mother might. She whispered something he could not quite catch, but he felt it settle in his bones like warm sunlight.\n\nThen the room was empty again, dust and moonlight and silence. The record lifted itself, slid back into the wooden box, and the lid closed. The new needle dulled and crumbled into silver dust.\n\nHis daughter stood in the middle of the floor, cheeks red, eyes shining. She looked at him for a long moment, then ran and threw her arms around him. They held each other while the house settled back into sleep around them.\n\nOn the drive home she fell asleep against his shoulder, mouth slightly open, one hand still curled as if holding a partner that was no longer there. He carried her inside and tucked her into bed. His wife raised an eyebrow at the grass stains on the knees of the girl’s jeans and the faint smell of wood smoke in her hair, but she only smiled and said nothing.\n\nMuch later, when the house was dark and everyone slept, the man went back to the bedroom drawer and took out the old notebook. He opened to the last blank page and wrote a single line in his careful adult handwriting:\n\n“She danced better than I ever did.”\n\nThen he closed the book, slid it back into place, and went to bed. Outside, the frost thickened on the windows, and somewhere far away an old porch light flickered once, twice, and stayed dark for another year.\n\nBut every autumn after that, on the clearest, coldest nights, father and daughter would sometimes drive out to the edge of town with a thermos of cocoa and sit in the car with the windows down. They never went inside again. They did not need to. If they listened hard enough, they could hear the faint sound of music across the empty field, slow and patient, waiting for the next lonely heart that needed to remember how good it felt to be welcomed home.\n\nAnd the house, patient as stone and twice as kind, kept its light ready, just in case.",
    "voice": "af_heart",
    "language": "en",
    "speed": 1,
    "temperature": 0.7,
    "top_p": 0.9,
    "tolerance": 80,
    "de_reverb": 0.7,
    "de_ess": 0,
    "output_format": "wav",
    "save_path": "projects_output/mmmmmmm",
    "verify_whisper": True,
    "whisperDeviceSelect": "0",
    "kokoroDeviceSelect": "0",
    "skip_post_process": False
}



# ==================================================================
# BULLETPROOF AUTO-DETECTION (order matters!)
# ==================================================================

if __name__ == "__main__":
    print("Detecting model...\n")

    # 1. FishSpeech — ANY fish-specific key wins immediately
    if any(k in payload for k in ["fishTemp", "fishTopP", "ref_text", "fishDeviceSelect"]):
        print("→ FishSpeech detected")
        client.load_fish(device=payload.get("fishDeviceSelect", "0"))
        client.infer_fish(**payload)
        client.unload_fish()

    # 2. XTTS — only if no fish keys were present
    elif any(k in payload for k in ["xttsDeviceSelect", "mode", "repetition_penalty"]):
        print("→ XTTS v2 detected")
        client.load_xtts(device=payload.get("xttsDeviceSelect", "0"))
        client.infer_xtts(**payload)
        client.unload_xtts()

    # 3. Kokoro — explicit device key OR built-in voice name
    elif "kokoroDeviceSelect" in payload or (
        payload.get("voice") in {
            "af_heart","af_alloy","af_aoede","af_bella","af_jessica","af_kore",
            "af_nova","af_river","af_sarah","af_sky",
            "am_adam","am_echo","am_eric","am_fenrir","am_liam","am_michael",
            "am_onyx","am_puck","am_santa"
        }
    ):
        print("→ Kokoro detected")
        client.load_kokoro(device=payload.get("kokoroDeviceSelect", "0"))
        client.infer_kokoro(**payload)
        client.unload_kokoro()

    # 4. Stable Audio — requires audio_mode
    elif payload.get("prompt") and payload.get("audio_mode") in ("sfx_impact", "sfx_ambient", "music"):
        print("→ Stable Audio detected")
        client.load_stable(device="0")
        client.infer_stable(**payload)
        client.unload_stable()

    # 5. ACE-Step — requires guidance or other ACE-specific keys
    elif payload.get("prompt") and any(k in payload for k in ["guidance", "min_guidance", "scheduler", "cfg_type", "omega", "oss_steps"]):
        print("→ ACE-Step detected")
        client.load_ace(device="0")
        client.infer_ace(**payload)
        client.unload_ace()

    # 6. Safe fallback
    else:
        print("→ No unique keys → defaulting to Kokoro (safest)")
        client.load_kokoro(device="0")
        client.infer_kokoro(**payload)
        client.unload_kokoro()

    client.unload_whisper()
    print("\nFinished!")