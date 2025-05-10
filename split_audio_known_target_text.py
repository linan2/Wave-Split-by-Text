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

# ---------- 1. 读取 CTM，支持数字 ID 或符号，并去除位置标签 ----------
def load_phone_ctm(ctm_path, phone_map=None):
    phn_ctm = defaultdict(list)
    with open(ctm_path, 'r', encoding='utf-8') as f:
        for line in f:
            utt, ch, st, dur, ph = line.strip().split()
            ph_sym = phone_map.get(ph, ph) if phone_map else ph
            base = ph_sym.split('_')[0]
            phn_ctm[utt].append((float(st), float(dur), base))
    return phn_ctm

# ---------- 2. 加载发音词典，保留所有发音版本 ----------
def load_lexicon_all_prons(lexicon_path):
    lex = defaultdict(list)
    with open(lexicon_path, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split()
            if len(parts) < 2: continue
            raw_word, phones = parts[0], parts[1:]
            clean = re.sub(r'[^A-Za-z0-9]', '', raw_word).lower()
            if clean:
                lex[clean].append(phones)
    return lex

# ---------- 3. 匹配任意音素序列并获取时间段 ----------
def find_sequence_times(phones, seq):
    window = deque(maxlen=len(seq))
    for st, dur, ph in phones:
        window.append((st, dur, ph))
        if len(window) == window.maxlen:
            if [p for (_, _, p) in window] == seq:
                start = window[0][0]
                end = window[-1][0] + window[-1][1]
                return start, end
    return None

# ---------- 4. 切分多个连续单词并将非语音部分设为静默 ----------
#    匹配时忽略 SIL，提取时将 SIL 置零
def extract_multiword_segment(wav_path, phones, words, lexicon):
    # 1) 为匹配构建不含 SIL 的音素流
    content_phones = [(st, dur, ph) for (st, dur, ph) in phones if ph.lower() != 'sil']
    # 2) 获取所有发音组合的时间段
    pron_lists = [lexicon[w] for w in words]
    match = None
    for combo in product(*pron_lists):
        seq = [ph for pron in combo for ph in pron]
        match = find_sequence_times(content_phones, seq)
        if match:
            break
    if not match:
        return None, None, None
    start_t, end_t = match
    # 3) 构建输出片段：逐原始 phones 拼接，silence 部分用静默填充
    audio = AudioSegment.from_file(wav_path)
    out = AudioSegment.empty()
    for st, dur, ph in phones:
        if st < start_t: continue
        if st + dur > end_t: break
        if ph.lower() == 'sil':
            out += AudioSegment.silent(duration=int(dur*1000))
        else:
            out += audio[int(st*1000):int((st+dur)*1000)]
    return out, start_t, end_t
# ---------- 主流程：支持多个连续单词 ----------
if __name__ == '__main__':
    utt_id = 'c02c0202'
    # 目标单词列表，大小写无关
    target_words = ['REVISED', 'TAX', 'CODE', 'POSSIBLY']
    target_clean = [re.sub(r'[^A-Za-z0-9]', '', w).lower() for w in target_words]

    audio_dir = './'
    ctm_path = 'phones_readable.ctm'
    lexicon_path = './data/local/dict/lexicon.txt'
    phones_txt = './data/lang/phones.txt'

    phone_map = load_phone_map(phones_txt)
    phn_ctm = load_phone_ctm(ctm_path, phone_map)
    lexicon = load_lexicon_all_prons(lexicon_path)

    phones = phn_ctm.get(utt_id)
    if not phones:
        raise ValueError(f"No phones for utterance {utt_id}")
    for w in target_clean:
        if w not in lexicon:
            raise ValueError(f"Word '{w}' not in lexicon")

    wav_path = os.path.join(audio_dir, f"{utt_id}.wav")
    print(phones)
    segment, start_t, end_t = extract_multiword_segment(wav_path, phones, target_clean, lexicon)
    if segment is None:
        raise ValueError(f"Cannot match sequence {' '.join(target_words)} in utterance")

    out_wav = f"{utt_id}_{'_'.join(target_clean)}.wav"
    segment.export(out_wav, format='wav')
    print(f"Saved segment with silent gaps zeroed to {out_wav} (from {start_t:.3f}s to {end_t:.3f}s)")
