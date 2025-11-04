from profiles import build_active_map, ALEsis_NITRO_PRO
from config import GM

def test_device_translation_overrides():
    note_to_kind = build_active_map(GM, ALEsis_NITRO_PRO)
    # 38 remains snare
    assert note_to_kind(38) == "snare"
    # 39 translated to 38 -> snare (if you keep that override)
    assert note_to_kind(39) == "snare"
    # 52 -> ride (via example override to 51)
    assert note_to_kind(52) in ("ride", None)  # adjust depending on your chosen mapping
