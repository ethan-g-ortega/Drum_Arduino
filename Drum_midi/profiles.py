# Simple per-device overrides to translate device notes -> GM notes.
# Only include diffs from GM. Add/fix here as you discover mismaps.

from typing import Optional

ALEsis_NITRO_PRO = {
    # examples:
    # 39=Hand Clap -> treat as snare
    39: 38,
    # 52=Chinese cymbal -> treat as ride (depends on your kit layout)
    52: 51,
    # 59 sometimes is crash2 on some kits; keep as ride by default (config already maps 59: "ride")
    # Add YOUR real mismaps here as you detect them:
    # <incoming_device_note>: <target_gm_note>
}

def build_active_map(gm_map: dict[int, str], device_overrides: Optional[dict[int, int]]):
    """
    Returns a function that translates device note -> GM kind or None.
    If override maps a note->new_note, we resolve the kind via gm_map[new_note].
    """
    def note_to_kind(note: int) -> Optional[str]:
        if device_overrides and note in device_overrides:
            note = device_overrides[note]
        return gm_map.get(note)
    return note_to_kind
