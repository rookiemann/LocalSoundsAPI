# models/llama.py
import gc
import os
import threading
from llama_cpp import Llama
import torch
import time
from config import LLM_DEVICE
LLM_GPU_ID = int(LLM_DEVICE.strip())

if not (0 <= LLM_GPU_ID < torch.cuda.device_count()):
    raise RuntimeError(
        f"LLM_DEVICE={LLM_GPU_ID} is invalid. "
        f"You have {torch.cuda.device_count()} GPUs (0–{torch.cuda.device_count()-1})"
    )

tensor_split = [100 if i == LLM_GPU_ID else 0 for i in range(torch.cuda.device_count())]

print(f"[LLAMA] LLM will be forced onto GPU {LLM_GPU_ID} "
      f"→ {torch.cuda.get_device_name(LLM_GPU_ID)}")
#print(f"[LLAMA] tensor_split = {tensor_split}")

# Global state
llm = None
current_model_path = None
model_loaded = False
loading_in_progress = False
model_lock = threading.Lock()

def load_llama(model_path: str, n_ctx: int = 8192, n_gpu_layers: int = 999) -> str:
    global llm, current_model_path, model_loaded, loading_in_progress

    print("\n" + "="*80)
    print("[LLAMA] load_llama() CALLED")
    print(f"[LLAMA] Model path: {model_path}")
    print(f"[LLAMA] n_ctx: {n_ctx} | n_gpu_layers: {n_gpu_layers}")
    print(f"[LLAMA] Thread: {threading.current_thread().name}")
    print("="*80)

    with model_lock:
        if loading_in_progress:
            print("[LLAMA] REJECTED: Already loading in another thread!")
            raise RuntimeError("Model loading already in progress")
        loading_in_progress = True
        print("[LLAMA] Lock acquired — starting load sequence")

    try:
        print("[LLAMA] Step 1 → Unloading any previous model...")
        unload_llama()

        if not os.path.isfile(model_path):
            print(f"[LLAMA] ERROR: File not found → {model_path}")
            raise FileNotFoundError(model_path)

        print(f"[LLAMA] File exists → {os.path.getsize(model_path) / 1e9:.2f} GB")
        print("[LLAMA] Step 2 → About to call Llama() constructor...")
        print("[LLAMA] If you see this and nothing after → it's stuck in CUDA/driver init")
        print(f"[LLAMA] n_gpu_layers = {n_gpu_layers} → 0 = CPU, >0 = GPU")

        start_time = time.time()
        llm = Llama(
            model_path=model_path,
            n_ctx=n_ctx,
            n_batch=512,
            n_gpu_layers=n_gpu_layers,
            main_gpu=LLM_GPU_ID,
            tensor_split=tensor_split,    # e.g. [0, 100] or [0, 0, 100]
            rpc_tensor=True,              # mandatory when using tensor_split            
            verbose=True,
            logits_all=True,
        )
        load_time = time.time() - start_time
        print(f"[LLAMA] CONSTRUCTOR RETURNED SUCCESSFULLY in {load_time:.1f}s!")

        current_model_path = model_path
        model_loaded = True
        mode = "CPU" if n_gpu_layers == 0 else "GPU"
        print(f"[LLAMA] MODEL FULLY LOADED on {mode} — READY FOR INFERENCE")
        print("="*80 + "\n")
        return f"Loaded on {mode} ({load_time:.1f}s)"

    except Exception as e:
        print("[LLAMA] EXCEPTION DURING LOAD:")
        print(f"[LLAMA] Type: {type(e).__name__}")
        print(f"[LLAMA] Message: {str(e)}")
        
        error_lower = str(e).lower()
        if any(kw in error_lower for kw in ["cuda", "driver", "out of memory", "failed to", "invalid", "unsupported"]):
            print("[LLAMA] → This is almost certainly a CUDA/VRAM/driver issue")
        raise

    finally:
        with model_lock:
            loading_in_progress = False
            print("[LLAMA] loading_in_progress = False (lock released)")

def unload_llama(force=False) -> None:
    global llm, current_model_path, model_loaded
    print("[LLAMA] >>> ENTERING unload_llama()")
    if llm is not None:
        try:
            print("[LLAMA] Deleting llm object...")
            del llm
            print("[LLAMA] del llm → success")
        except Exception as e:
            print(f"[LLAMA] del llm failed: {e}")
        llm = None

    current_model_path = None
    model_loaded = False
    torch.cuda.empty_cache()
    gc.collect()
    print("[LLAMA] VRAM cleared + GC done")

def infer_llama(
    messages: list,
    temperature: float = 0.8,
    max_tokens: int = 8192,
    top_p: float = 0.95,
    top_k: int = 40,
    presence_penalty: float = 0.0,
    frequency_penalty: float = 0.0
):
    with model_lock:
        if not model_loaded or llm is None:
            raise RuntimeError("No model loaded")
        if loading_in_progress:
            raise RuntimeError("Still loading model")

        print(f"[LLAMA] Starting inference → {len(messages)} messages")
        print(f"  temp={temperature} max_tokens={max_tokens} top_p={top_p} top_k={top_k} "
              f"presence={presence_penalty} freq={frequency_penalty}")

        completion = llm.create_chat_completion(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            top_k=top_k,
            presence_penalty=presence_penalty,
            frequency_penalty=frequency_penalty,
            stop=["<|end_of_text|>", "<|eot_id|>", "<|im_end|>", "</s>"],
            stream=True,
        )

        for chunk in completion:
            delta = chunk["choices"][0]["delta"].get("content", "")
            if delta:
                yield delta