"""End-to-end test for v3.7 Phase 2 — RAG retrieval wired into build_system_prompt.

Not part of test suite — one-off validation that the runtime wiring works."""
import sys
sys.path.insert(0, '.')

class FakeFinding:
    def __init__(self, severity, kind, value):
        self.severity, self.kind, self.value = severity, kind, value

class FakeRun:
    def __init__(self, tool):
        self.tool = tool
        self.command = f'{tool} -sV 127.0.0.1'
        self.target = '127.0.0.1'
        self.returncode = 0
        self.duration = 5.2
        self.findings = [FakeFinding('high', 'service', 'ssh on 22')]

class FakeOpState:
    def __init__(self, tool):
        self.target = '127.0.0.1'
        self.mode = 'lab'
        self.history = [FakeRun(tool)]
        self.findings = self.history[0].findings


from src.core.conversation_engine import get_engine
engine = get_engine()

print("=== TEST 1: reactive injection (rubeus — in RAG) ===")
state = FakeOpState('rubeus')
prompt = engine.build_system_prompt(state, user_msg='')
has_rag = 'ERR0RS teach: rubeus' in prompt
has_mitre = 'T1558' in prompt
print(f"  prompt size:        {len(prompt)} chars")
print(f"  contains RAG block: {has_rag}")
print(f"  contains MITRE IDs: {has_mitre}")
assert has_rag, 'RAG block missing from system prompt'
assert has_mitre, 'MITRE IDs should be in RAG content'
print("  ✓ Rubeus RAG content injected into system prompt")

print()
print("=== TEST 2: reactive injection (custom-tool — NOT in RAG) ===")
state = FakeOpState('definitely-not-a-real-tool')
prompt = engine.build_system_prompt(state, user_msg='')
has_rag = 'ERR0RS teach:' in prompt
print(f"  prompt size:        {len(prompt)} chars")
print(f"  contains RAG block: {has_rag}")
assert not has_rag, 'Unknown tool should NOT inject RAG content'
print("  ✓ Unknown tool path falls through cleanly")

print()
print("=== TEST 3: proactive PRIORITY — user's question wins over reactive ===")
# User just ran nmap but asks a DIFFERENT question (kerberoasting).
# The kerberoasting answer should win — it's what they want help with NOW.
state = FakeOpState('nmap')
prompt = engine.build_system_prompt(state, user_msg='How do I avoid being caught when running Kerberoasting?')
has_proactive = 'ERR0RS RAG context' in prompt        # proactive marker
has_reactive  = 'ERR0RS teach: nmap' in prompt        # reactive marker
print(f"  prompt size:           {len(prompt)} chars")
print(f"  has proactive (query): {has_proactive}")
print(f"  has reactive (nmap):   {has_reactive}")
assert has_proactive, 'Proactive RAG block missing'
assert not has_reactive, 'Reactive should be suppressed when proactive fires'
print("  ✓ User's question wins; reactive is suppressed")

print()
print("=== TEST 4: build_system_prompt with no operator_state ===")
prompt = engine.build_system_prompt(None, user_msg='')
no_active = 'No active engagement' in prompt
print(f"  prompt size: {len(prompt)} chars")
print(f"  has fallback msg: {no_active}")
assert no_active
print("  ✓ Graceful no-state path")

print()
print("=== TEST 5: budget discipline — only ONE RAG block per prompt ===")
# Rubeus reactive + Rubeus-related user_msg → should NOT double-inject.
# Reactive takes priority; proactive is suppressed.
state = FakeOpState('rubeus')
prompt = engine.build_system_prompt(state, user_msg='What does Rubeus do and how do I avoid detection?')
# Count RAG block markers — should be exactly 1 (the reactive one)
rag_marker_count = prompt.count('(from ERR0RS RAG)')
print(f"  full prompt: {len(prompt)} chars")
print(f"  RAG block count: {rag_marker_count} (expect exactly 1)")
assert rag_marker_count == 1, f'Expected 1 RAG block, got {rag_marker_count}'
# And total prompt size should be within gemma3:1b's interactive zone
assert len(prompt) < 9000, f'system prompt got too large: {len(prompt)} chars'
print(f"  ✓ exactly 1 RAG block, prompt within budget ({len(prompt)} chars)")

print()
print("=== ALL E2E RAG INJECTION TESTS PASS ===")
