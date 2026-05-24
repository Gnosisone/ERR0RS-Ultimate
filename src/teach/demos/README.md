# ERR0RS Demo Recipes

Each YAML file in this directory defines a curated, hand-vetted demo
sequence for one tool. These power the `teach <tool>` interactive demo
mode when the user is at LEARN tier or higher AND has lab mode active.

## Why curated, not LLM-authored

A 1-billion-parameter local LLM (gemma3:1b) is excellent at narrating
and explaining, but it's not reliable at authoring shell commands. A
hallucinated flag combination — `nmap --max-rate=10000` against the
wrong target, `hashcat -m 0` when the user wanted `-m 1000` — can
silently corrupt the student's learning and, in OPERATE tier without
the safety gate engaged, cause real harm.

Hand-curated recipes are predictable, audited, and pedagogically
sound. The LLM still does all the *narration* — what changes is that
the *command* comes from a YAML file maintained by humans.

OPERATE tier still allows LLM-authored commands when the user
explicitly invokes that mode. LEARN tier is curated-only.

## Recipe format

```yaml
tool: nmap                         # canonical tool key (matches registry)
display_name: Nmap                 # human-readable
default_target: 127.0.0.1          # the target used in LEARN demo. Always
                                   # localhost or an explicit lab range.
description: |
  Multi-line description shown before the demo starts. Sets context
  for the learner about what they're about to see.

steps:
  - name: Identify interfaces
    intent: "First, see what network interfaces are available on this host."
    command: "ip -4 -o addr show"  # safe, read-only command
    timeout: 3                      # seconds
    requires_root: false
    explain_after: |
      Optional canned explanation. If absent, gemma3:1b narrates
      the actual output through the chunked-RAG engine.

  - name: Scan localhost (TCP top-100)
    intent: "Run an nmap top-100 TCP scan against your own machine."
    command: "nmap -sV --top-ports 100 {USER_IP}"
    timeout: 60
    requires_root: false
    teach_chunks:                  # optional: chunks of the RAG to
      - rubeus                     #   prefer when narrating. If absent,
      - nmap                       #   semantic search picks.

next_steps:                        # offered after the demo completes
  - "If you found web ports, try `teach nikto`"
  - "If you found SMB, try `teach enum4linux`"
  - "Save the output and ask me 'explain the open ports'"

# Tier gates — minimum tier required to run this demo. Recipes that
# touch the network beyond localhost should require LEARN+lab or OPERATE.
min_tier: LEARN
requires_lab_mode: true
```

## Placeholder substitution

`{USER_IP}`, `{LHOST}`, `{HOSTNAME}` etc. in `command:` fields are
substituted using `src.ai.host_context.substitute_placeholders()` at
demo-run time. The user sees the FINAL command before it executes.

## Safety contract

Every recipe in this directory must:

1. Only target `127.0.0.1`, `::1`, `localhost`, or another RFC1918
   address that's the user's own machine. NEVER hard-code a remote
   target.
2. Use read-only or non-destructive flags. No `rm`, no `dd`, no
   `--script vuln,exploit` (the safety gate would block these anyway,
   but defense in depth).
3. Include `requires_root: true` if the command needs sudo. The
   launcher will warn and offer to use a non-root alternative.
4. Set `min_tier:` correctly. Demos that read system info → EXPLORE.
   Demos that send any packets → LEARN. Demos that need OPERATE-only
   features (listeners, working payloads) → OPERATE.

## Adding a new recipe

1. Copy an existing recipe in this directory as a template
2. Hand-verify every command works as expected on a clean Pi 5 install
3. Run it through the demo system: `teach <tool>` and walk the steps
4. Open a PR
