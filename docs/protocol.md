**`docs/protocol.md`:** (Basic notes on the conceptual protocol)

```markdown
# Meshtastic Protocol Implementation Notes

The `main.py` daemon includes a basic, conceptual implementation of the Meshtastic protocol. **This implementation is simplified and needs to be fully aligned with the actual Meshtastic serial protocol specification.**

**Packet Structure (Conceptual):**

Packets are framed with `!` as a preamble, `<` as the start delimiter, and `>` as the end delimiter. Fields within the packet are separated by `:`. The payload is separated from the header by `|`.
