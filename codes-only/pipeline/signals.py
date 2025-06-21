import signal
from typing import Dict, Optional

# Ensure the platform supports real-time signals
if not hasattr(signal, "SIGRTMIN") or not hasattr(signal, "SIGRTMAX"):
    raise RuntimeError("Platform does not support real-time signals")

RTMIN, RTMAX = signal.SIGRTMIN, signal.SIGRTMAX
MAX_OFFSET = RTMAX - RTMIN - 1  # highest allowed offset

# Helper to safely allocate real-time signal offsets
def rt(offset: int) -> int:
    """
    Compute RTMIN + offset, ensuring it does not exceed RTMAX-1.
    Raises RuntimeError if out of range.
    """
    if offset > MAX_OFFSET:
        raise RuntimeError(f"Offset {offset} too large: max allowed is {MAX_OFFSET}")
    return RTMIN + offset

# Define all signal keys in order; extend this list to add new signals.
ALL_SIGNALS = [
    # feeder.py
    ('FEEDER_SIG_CARD', 'Card loaded'),
    ('FEEDER_SIG_USER', 'User loaded'),
    ('FEEDER_SIG_MCC', 'MCC loaded'),
    ('FEEDER_SIG_LABELS', 'Labels loaded'),
    ('FEEDER_SIG_DB', 'DB written'),
    ('FEEDER_SIG_DONE', 'Feeder done'),
    # preprocessing.py
    ('PREPROC_SIG_RAW', 'Raw data ready'),
    ('PREPROC_SIG_DB', 'Preproc DB written'),
    ('PREPROC_SIG_DONE', 'Preprocessing done'),
    # datamarts.py
    ('DM_SIG_CLIENT_FEATURES', 'Client features computed'),
    ('DM_SIG_CARD_FEATURES',   'Card features computed'),
    ('DM_SIG_VELOCITY',        'Velocity metrics computed'),
    ('DM_SIG_MCC_RISK',        'MCC fraud risk computed'),
    ('DM_SIG_TIME_DISTRIBUTION','Time-of-day distribution computed'),
    ('DM_SIG_DONE',            'Datamarts done'),
    # ml.py
    ('ML_SIG_DONE', 'ML done')
]

# Dynamically assign signals
def _build_signal_map():
    FILE_SIGNALS: Dict[str,int] = {}
    for idx, (var_name, label) in enumerate(ALL_SIGNALS):
        sig = rt(idx)
        globals()[var_name] = sig
        FILE_SIGNALS[label] = sig
    return FILE_SIGNALS

FILE_SIGNALS = _build_signal_map()

# Print out the mapping for visibility
def print_signal_mapping(
    file_signals: Dict[str, int],
    extra_signals: Optional[Dict[str, int]] = None,
    title: str = "Signal Mapping"
) -> None:
    """
    Print a neat table of signal assignments.

    :param file_signals: mapping from item name to signal number
    :param extra_signals: optional mapping for additional labels
    :param title: heading to display
    """
    line_len = max(len(title) + 8, 40)
    print(f"=== {title} ===")
    for name, sig in file_signals.items():
        try:
            sig_name = signal.Signals(sig).name
        except ValueError:
            sig_name = str(sig)
        print(f"  • {name:<30} → {sig} ({sig_name})")
    if extra_signals:
        for name, sig in extra_signals.items():
            try:
                sig_name = signal.Signals(sig).name
            except ValueError:
                sig_name = str(sig)
            print(f"  • {name:<30} → {sig} ({sig_name})")
    print("=" * line_len)

# Expose full signal metadata for orchestrator (if needed)
SIGNAL_MAP = {
    var_name: {'signal': globals()[var_name], 'label': label}
    for var_name, label in ALL_SIGNALS
}
