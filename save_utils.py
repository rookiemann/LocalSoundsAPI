# save_utils.py
import os
import uuid
from pathlib import Path
from config import OUTPUT_DIR

def handle_save(
    temp_path: str,
    user_path: str | None,
    prefix: str,
    *,
    always_save_fails: bool = False,
) -> tuple[str | None, str | None]:
    """
    Save a temporary file and return (final_path, saved_rel).

    Returns:
        (absolute_path, posix_ui_path) or (None, None)
    """
    if user_path is None and not always_save_fails:
        return None, None

    if user_path:
        user_p = Path(user_path).expanduser()
        if user_p.is_absolute():
            final_path = user_p.resolve()
        else:
            final_path = (Path.cwd() / user_p).resolve()
    else:
        final_path = OUTPUT_DIR / f"{prefix}_fail_{uuid.uuid4().hex}.wav"

    final_path.parent.mkdir(parents=True, exist_ok=True)

    os.replace(temp_path, str(final_path))

    try:
        rel_path = final_path.relative_to(Path.cwd())
        saved_rel = str(rel_path).replace("\\", "/")
    except ValueError:
        saved_rel = f"{final_path.drive}{final_path.as_posix()[1:]}"

    return str(final_path), saved_rel