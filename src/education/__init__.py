# ERR0RS ULTIMATE - education package
# teach_engine.py handles all offline teaching - no Ollama needed
try:
    from .education_engine import EducationContent
except Exception:
    pass

try:
    from .teach_engine import handle_teach_request, find_lesson
except Exception:
    pass
