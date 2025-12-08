import os, gc
from pathlib import Path
import torch
from transformers import ClapModel, ClapProcessor
from huggingface_hub import snapshot_download

os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

MODEL_DIR = Path(__file__).parent.parent / "models" / "clap-htsat-unfused"

# This PR adds the real model.safetensors (600 MB) to laion’s repo
REPO_ID = "laion/clap-htsat-unfused"
REVISION = "refs/pr/3"      # contains model.safetensors + everything else

_clap_model = None
_processor = None

def load_clap(device="cuda:0"):  # Changed: Accept dynamic device
    global _clap_model, _processor
    if _clap_model is not None:
        return _clap_model, _processor

    MODEL_DIR.mkdir(parents=True, exist_ok=True)
    print(f"[CLAP] Checking {MODEL_DIR} ...")

    # Only trigger download if the big file is missing (fast check)
    if not (MODEL_DIR / "model.safetensors").exists():
        print("[CLAP] Downloading full model (with safetensors) – this can take 20–90 seconds ...")
        snapshot_download(
            repo_id=REPO_ID,
            revision=REVISION,
            local_dir=str(MODEL_DIR),
            local_dir_use_symlinks=False,
            max_workers=8,          # faster + resume support
            tqdm_class=None,        # we print our own messages
        )
        print("[CLAP] Download complete")

    _clap_model = ClapModel.from_pretrained(str(MODEL_DIR)).to(device).eval()
    _processor = ClapProcessor.from_pretrained(str(MODEL_DIR))
    print(f"[CLAP] Loaded on {device}")
    return _clap_model, _processor


def unload_clap() -> None:
    """Unload the CLAP model and processor from GPU memory.

    Deletes the objects, clears PyTorch cache. Safe to call even if nothing is loaded.
    """
    global _clap_model, _processor
    if _clap_model is not None:
        del _clap_model
        _clap_model = None
    if _processor is not None:
        del _processor
        _processor = None
    gc.collect()
    if torch.cuda.is_available():
        torch.cuda.empty_cache()
        torch.cuda.ipc_collect()
    print("[UNLOAD] CLAP unloaded.")