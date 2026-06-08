#!/bin/bash
# 🧬 Auto Evolution - runs periodically
cd /root/telegram-bot
/root/telegram-bot/env/bin/python3 -c "
import sys, json
sys.path.insert(0, '/root/codex-brain')
from brain import brain
brain.evolve()
# Log it
with open('/root/telegram-bot/evolution.log', 'a') as f:
    import time
    f.write(f\"{time.strftime('%Y-%m-%d %H:%M')} Evolved to level {brain.evolution_level}\\n\")
print(f'🧬 Evolved to level {brain.evolution_level}')
" >> /root/telegram-bot/auto_evolve.log 2>&1
