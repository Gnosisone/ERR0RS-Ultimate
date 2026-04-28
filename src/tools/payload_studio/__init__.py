"""ERR0RS Payload Studio — package init"""
try:
    from .payload_engine import (
        detect_platform, detect_category, get_line_explanation,
        get_suggestions, index_existing_payloads, DUCKY_COMMANDS,
    )
    from .snippets import SNIPPETS
except ImportError:
    pass
