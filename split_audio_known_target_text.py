#!/usr/bin/env python3
import os
import re
from collections import defaultdict, deque
from itertools import product
from pydub import AudioSegment

# ---------- 0. 加载 phone ID 到符号映射 ----------
def load_phone_map(phones_txt):
    id2sym = {}
    with open(phones_txt, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) >= 2:
                sym, idx = parts[0], parts[1]
                id2sym[idx] = sym
    return id2sym


    out_wav = f"{utt_id}_{'_'.join(target_clean)}.wav"
    segment.export(out_wav, format='wav')
    print(f"Saved segment with silent gaps zeroed to {out_wav} (from {start_t:.3f}s to {end_t:.3f}s)")
