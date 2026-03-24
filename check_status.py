import sys; sys.path.insert(0,'.')
try:
    from src.ui.errorz_launcher import _status
    s = _status()
    print("_status() keys:", list(s.keys()))
    missing = [k for k in ['campaign_engine','killchain_engine','pro_reporter','cred_engine','se_engine','ai_threat_engine'] if k not in s]
    print("Missing keys:", missing if missing else "NONE - all present!")
except Exception as e:
    print("Error:", e)
    import traceback; traceback.print_exc()
