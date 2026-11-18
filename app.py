import os
import sys
import uuid
import re
import json
import time
import asyncio
import urllib.request
import urllib.error
import subprocess
from pathlib import Path
from flask import Flask, render_template, request, jsonify, send_file, Response
import edge_tts

app = Flask(__name__)

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
OUTPUT_DIR = BASE_DIR / "output"
BROLL_DIR = STATIC_DIR / "broll"
MUSIC_DIR = STATIC_DIR / "music"
OUTPUT_DIR.mkdir(exist_ok=True)
BROLL_DIR.mkdir(parents=True, exist_ok=True)
MUSIC_DIR.mkdir(parents=True, exist_ok=True)

# CORS Headers
@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        res = Response()
        res.headers["Access-Control-Allow-Origin"] = "*"
        res.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization,X-Requested-With"
        res.headers["Access-Control-Allow-Methods"] = "GET,PUT,POST,DELETE,OPTIONS"
        return res

@app.after_request
def add_cors_headers(response):
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization,X-Requested-With"
    response.headers["Access-Control-Allow-Methods"] = "GET,PUT,POST,DELETE,OPTIONS"
    return response

# Human Emotion Presets (আবেগ ও অনুভূতির স্টাইল)
EMOTION_PRESETS = [
    {
        "id": "thoughtful",
        "name": "🧠 Thoughtful & Deep",
        "name_bn": "দার্শনিক ও গভীর বিবেক",
        "desc": "Calm, contemplative, deep chest resonance with deliberate pauses. Perfect for life lessons & wisdom.",
        "default_rate": "-6%",
        "default_pitch": "-2Hz",
        "pause_sec": 0.55,
        "badge": "✨ Deep Wisdom",
        "badge_color": "purple"
    },
    {
        "id": "storyteller",
        "name": "🎭 Emotional Storyteller",
        "name_bn": "আবেগঘন হৃদয়স্পর্শী গল্প",
        "desc": "Warm, sensitive human empathy with rich room presence. Touches the heart.",
        "default_rate": "-4%",
        "default_pitch": "+0Hz",
        "pause_sec": 0.45,
        "badge": "💖 Emotional",
        "badge_color": "rose"
    },
    {
        "id": "motivational",
        "name": "🔥 Motivational & Power",
        "name_bn": "উত্তেজক ও বজ্রকণ্ঠ",
        "desc": "Energetic, powerful broadcast punch with punchy dynamic compression. Commands respect.",
        "default_rate": "+3%",
        "default_pitch": "+1Hz",
        "pause_sec": 0.35,
        "badge": "⚡ High Energy",
        "badge_color": "amber"
    },
    {
        "id": "mystery",
        "name": "🌌 Cinematic Mystery",
        "name_bn": "রহস্যময় ডার্ক ডকুমেন্টারি",
        "desc": "Slow, suspenseful, dark sub-bass with dramatic silence. Viral TikTok & YouTube mystery hooks.",
        "default_rate": "-9%",
        "default_pitch": "-4Hz",
        "pause_sec": 0.65,
        "badge": "🎬 Dark Cinema",
        "badge_color": "cyan"
    },
    {
        "id": "conversational",
        "name": "💬 Natural Conversational",
        "name_bn": "সহজ ও সাবলীল মানুষের কণ্ঠ",
        "desc": "Relaxed everyday human speech with natural breath cadence and balanced clarity.",
        "default_rate": "-1%",
        "default_pitch": "+0Hz",
        "pause_sec": 0.30,
        "badge": "🌟 Natural Human",
        "badge_color": "emerald"
    }
]

# Voice Catalog: Ultra-Human Neural + ElevenLabs Cloud
VOICES = [
    # Bengali (Bangladesh) Neural
    {
        "id": "bn-BD-PradeepNeural",
        "name": "প্রদীপ (Pradeep - Deep Male)",
        "lang": "Bangla (BD)",
        "flag": "🇧🇩",
        "gender": "Male",
        "engine": "neural",
        "tag": "👑 Bengali Master",
        "desc": "গম্ভীর ও আকর্ষণীয় পুরুষ কণ্ঠ • গল্প, মোটিভেশন ও ডকুমেন্টারি"
    },
    {
        "id": "bn-BD-NabanitaNeural",
        "name": "নবনীতা (Nabanita - Sweet Female)",
        "lang": "Bangla (BD)",
        "flag": "🇧🇩",
        "gender": "Female",
        "engine": "neural",
        "tag": "🌸 Bengali Female",
        "desc": "মিষ্টি, সাবলীল ও স্পষ্ট নারী কণ্ঠ • শর্টস ও রিলস"
    },
    # Bengali (India)
    {
        "id": "bn-IN-BashkarNeural",
        "name": "ভাস্কর (Bashkar - Deep Narrator)",
        "lang": "Bangla (IN)",
        "flag": "🇮🇳",
        "gender": "Male",
        "engine": "neural",
        "tag": "🎙️ Deep Bangla",
        "desc": "গভীর ও স্পষ্ট আবৃত্তি ও জ্ঞানগর্ভ গল্প বলা"
    },
    {
        "id": "bn-IN-TanishaaNeural",
        "name": "তানিশা (Tanishaa - Modern Tone)",
        "lang": "Bangla (IN)",
        "flag": "🇮🇳",
        "gender": "Female",
        "engine": "neural",
        "tag": "✨ Modern Bangla",
        "desc": "স্মার্ট ও আধুনিক ভয়েস ওভার"
    },
    # English (US) Ultra-Human Neural
    {
        "id": "en-US-ChristopherNeural",
        "name": "Christopher (Viral Mystery)",
        "lang": "English (US)",
        "flag": "🇺🇸",
        "gender": "Male",
        "engine": "neural",
        "tag": "🔥 Viral Mystery",
        "desc": "Deep, authoritative, viral TikTok mystery & documentary narrator"
    },
    {
        "id": "en-US-AndrewNeural",
        "name": "Andrew (Viral Storyteller)",
        "lang": "English (US)",
        "flag": "🇺🇸",
        "gender": "Male",
        "engine": "neural",
        "tag": "🌟 Warm Storyteller",
        "desc": "Warm, engaging, fast-paced storytelling and viral reels"
    },
    {
        "id": "en-US-GuyNeural",
        "name": "Guy (Tech & Energetic)",
        "lang": "English (US)",
        "flag": "🇺🇸",
        "gender": "Male",
        "engine": "neural",
        "tag": "⚡ High Energy",
        "desc": "Crisp YouTube tech reviews, gaming, and energetic shorts"
    },
    {
        "id": "en-US-EricNeural",
        "name": "Eric (Deep Radio Master)",
        "lang": "English (US)",
        "flag": "🇺🇸",
        "gender": "Male",
        "engine": "neural",
        "tag": "🎙️ Radio Broadcaster",
        "desc": "Deep bass broadcast radio and cinema trailer voice"
    },
    {
        "id": "en-US-AvaNeural",
        "name": "Ava (Expressive Emotion)",
        "lang": "English (US)",
        "flag": "🇺🇸",
        "gender": "Female",
        "engine": "neural",
        "tag": "✨ Emotional Story",
        "desc": "Expressive, calm, cinematic female storyteller"
    },
    {
        "id": "en-US-JennyNeural",
        "name": "Jenny (Natural Conversational)",
        "lang": "English (US)",
        "flag": "🇺🇸",
        "gender": "Female",
        "engine": "neural",
        "tag": "💬 Conversational",
        "desc": "Natural lifestyle, vlog, and friendly explainer"
    },
    # Hindi
    {
        "id": "hi-IN-MadhurNeural",
        "name": "Madhur (Reels & Story)",
        "lang": "Hindi (IN)",
        "flag": "🇮🇳",
        "gender": "Male",
        "engine": "neural",
        "tag": "🔥 Hindi Viral",
        "desc": "Viral Hindi facts, stories and motivational shorts"
    },
    {
        "id": "hi-IN-SwaraNeural",
        "name": "Swara (Professional Narrative)",
        "lang": "Hindi (IN)",
        "flag": "🇮🇳",
        "gender": "Female",
        "engine": "neural",
        "tag": "🌟 Hindi Pro",
        "desc": "Clear professional Hindi commentary"
    },
    # ElevenLabs Cloud Voices (When ElevenLabs API Key is provided)
    {
        "id": "eleven_adam",
        "name": "ElevenLabs: Adam (Legacy Deep)",
        "voice_id": "pNInz6obpgDQGcFmaJgB",
        "lang": "Multilingual (ElevenLabs)",
        "flag": "💎",
        "gender": "Male",
        "engine": "elevenlabs",
        "tag": "💎 ElevenLabs Pro",
        "desc": "Official ElevenLabs Flagship Voice • Deep, narrative & expressive"
    },
    {
        "id": "eleven_rachel",
        "name": "ElevenLabs: Rachel (Calm Warm)",
        "voice_id": "21m00Tcm4TlvDq8ikWAM",
        "lang": "Multilingual (ElevenLabs)",
        "flag": "💎",
        "gender": "Female",
        "engine": "elevenlabs",
        "tag": "💎 ElevenLabs Pro",
        "desc": "Official ElevenLabs Flagship • Calm, warm & emotional narrator"
    },
    {
        "id": "eleven_antoni",
        "name": "ElevenLabs: Antoni (Passionate)",
        "voice_id": "ErXwobaYiN019PkySvjV",
        "lang": "Multilingual (ElevenLabs)",
        "flag": "💎",
        "gender": "Male",
        "engine": "elevenlabs",
        "tag": "💎 ElevenLabs Pro",
        "desc": "Official ElevenLabs • High emotion, energetic & passionate"
    },
    {
        "id": "eleven_brian",
        "name": "ElevenLabs: Brian (Documentary Master)",
        "voice_id": "nPczCjzI2devNBz1zQrb",
        "lang": "Multilingual (ElevenLabs)",
        "flag": "💎",
        "gender": "Male",
        "engine": "elevenlabs",
        "tag": "💎 ElevenLabs Pro",
        "desc": "Official ElevenLabs • Deep, rich cinema documentary master"
    }
]

VIRAL_TEMPLATES = [
    {
        "id": "bangla_wisdom",
        "category": "🇧🇩 গভীর বিবেক ও শিক্ষা",
        "title": "জীবনে ৩টি মারাত্মক ভুল",
        "emotion": "thoughtful",
        "text": "জীবনে এই তিনটি ভুল কখনো করবেন না। এক, কারো দুর্বলতা নিয়ে কখনো উপহাস করবেন না। দুই, অতিরিক্ত রাগের মাথায় কোনো চূড়ান্ত সিদ্ধান্ত নেবেন না। আর তিন, যার কঠিন বিপদে আপনি নিঃস্বার্থভাবে পাশে ছিলেন, তার কাছ থেকে কখনো কৃতজ্ঞতা আশা করবেন না। ভালো থাকুন নিজের যোগ্যতায়।"
    },
    {
        "id": "bangla_story",
        "category": "🇧🇩 আবেগঘন উপলব্ধি",
        "title": "নীরব মানুষের শক্তির রহস্য",
        "emotion": "storyteller",
        "text": "যে মানুষটা সবচেয়ে বেশি নীরব থাকে, মনে রাখবেন তার মনের ভেতর সবচেয়ে বড় ঝড় বয়ে গেছে। মানুষ যখন বারবার আঘাত পেয়ে ক্লান্ত হয়ে যায়, তখন সে আর কারো কাছে অভিযোগ করে না। সে চুপচাপ নিজের জীবনকে বদলে ফেলে। আপনার জীবনের লড়াইয়ে আপনি কখনো একা নন।"
    },
    {
        "id": "bangla_motivation",
        "category": "🇧🇩 বজ্রকণ্ঠ মোটিভেশন",
        "title": "কেউ তোমাকে বাঁচাতে আসবে না",
        "emotion": "motivational",
        "text": "আজকের এই সত্যিটা মেনে নাও। কেউ তোমাকে টেনে বিছানা থেকে তুলবে না, কেউ তোমাকে সফল বানিয়ে দেবে না। তোমার স্বপ্ন, তোমার ভবিষ্যত কেবল তোমার নিজের কাঁধের ওপর। অজুহাত দেওয়া বন্ধ করো। আজ থেকেই কাজ শুরু করো।"
    },
    {
        "id": "psychology",
        "category": "🧠 Psychology & Power",
        "title": "The 2-Second Silence Rule",
        "emotion": "thoughtful",
        "text": "The psychological trick that makes everyone respect you immediately. Powerful people never explain themselves right away. When asked a tough question, pause for two full seconds before you speak. That tiny silence creates instant tension, commands the entire room, and signals absolute confidence. Save this video so you remember to use it."
    },
    {
        "id": "wealth",
        "category": "💰 Wealth & Mindset",
        "title": "Rule #1 of the Silent Rich",
        "emotion": "mystery",
        "text": "Rule number one of the truly wealthy: Never look rich before you actually are rich. Fake luxury keeps the middle class trapped in debt. Real wealth is quiet, humble, and invisible. The wealthy buy assets that produce cashflow, while the broke buy designer clothes to impress people they don't even like. Change your mindset today."
    },
    {
        "id": "motivation_en",
        "category": "🔥 Relentless Discipline",
        "title": "Nobody is Coming to Save You",
        "emotion": "motivational",
        "text": "Nobody is coming to save you. Nobody is going to drag you out of bed, push you into the gym, or force you to build your business. Your entire future rests squarely on your shoulders. Stop waiting for motivation. Motivation is a myth. Discipline is doing what needs to be done even when you hate doing it. Start today."
    }
]

BROLL_OPTIONS = [
    {"id": "cyber_aurora", "name": "🌌 Cosmic Cyber Aurora", "file": "cyber_aurora.mp4"},
    {"id": "neon_matrix", "name": "🟢 Neon Emerald Matrix", "file": "neon_matrix.mp4"},
    {"id": "golden_luxury", "name": "👑 Golden Luxury Amber", "file": "golden_luxury.mp4"}
]

MUSIC_OPTIONS = [
    {"id": "lofi_ambient", "name": "🎧 Chill Lofi Ambient Pad", "file": "lofi_ambient.mp3"},
    {"id": "cinematic_tension", "name": "🎬 Cinematic Tension Drone", "file": "cinematic_tension.mp3"},
    {"id": "none", "name": "🔇 No Background Music", "file": None}
]

# Helper: Clean and normalize text for flawless human pronunciation
def normalize_text_for_human_speech(text):
    # Ensure proper spacing after punctuation (। , ! ? ; :) so syllables never blur
    cleaned = re.sub(r'([,;।!?])([^\s])', r'\1 \2', text)
    # Remove awkward multiple spaces
    cleaned = re.sub(r'[ \t]+', ' ', cleaned)
    # Normalize double linebreaks
    cleaned = re.sub(r'\n{3,}', '\n\n', cleaned)
    return cleaned.strip()

# Helper: Split text into natural human thought units (breathing clauses)
def split_into_thought_units(text):
    cleaned = normalize_text_for_human_speech(text)
    # Split by sentence enders: Bengali dari (।), English period (.), question (?), exclamation (!)
    pattern = r'([।\.\?!]+(?:\s+|\n+|$))'
    parts = re.split(pattern, cleaned)
    chunks = []
    current = ""
    for token in parts:
        if not token:
            continue
        current += token
        if re.search(r'[।\.\?!]', token):
            c = current.strip()
            if c:
                chunks.append(c)
            current = ""
    if current.strip():
        chunks.append(current.strip())
    return chunks if chunks else [cleaned]

# Helper: Build High-End Studio Microphone & Vocal Warmth Mastering Filter
def get_mastering_filter(emotion_id="thoughtful"):
    if emotion_id == "thoughtful":
        # Warm, intimate, contemplative deep chest resonance
        return (
            "highpass=f=75,"
            "equalizer=f=110:t=q:w=1:g=3.8,"
            "equalizer=f=400:t=q:w=1:g=-2.0,"
            "equalizer=f=3200:t=q:w=1:g=2.5,"
            "equalizer=f=8000:t=q:w=1:g=-1.5,"
            "aecho=0.8:0.88:18:0.12,"
            "acompressor=threshold=-19dB:ratio=3:attack=15:release=100,"
            "loudnorm=I=-14:TP=-1.5:LRA=11"
        )
    elif emotion_id == "motivational":
        # Punchy, energetic broadcast clarity
        return (
            "highpass=f=85,"
            "equalizer=f=125:t=q:w=1:g=3.0,"
            "equalizer=f=400:t=q:w=1:g=-1.5,"
            "equalizer=f=3400:t=q:w=1:g=3.5,"
            "equalizer=f=7500:t=q:w=1:g=-1.0,"
            "acompressor=threshold=-17dB:ratio=4:attack=5:release=50,"
            "loudnorm=I=-14:TP=-1.5:LRA=9"
        )
    elif emotion_id == "mystery":
        # Dark, suspenseful sub-bass resonance
        return (
            "highpass=f=60,"
            "equalizer=f=95:t=q:w=1:g=4.5,"
            "equalizer=f=380:t=q:w=1:g=-2.5,"
            "equalizer=f=2800:t=q:w=1:g=2.0,"
            "equalizer=f=9000:t=q:w=1:g=2.0,"
            "aecho=0.8:0.88:24:0.16,"
            "acompressor=threshold=-20dB:ratio=3:attack=20:release=120,"
            "loudnorm=I=-14:TP=-1.5:LRA=12"
        )
    elif emotion_id == "storyteller":
        # Warm, sensitive room presence
        return (
            "highpass=f=70,"
            "equalizer=f=115:t=q:w=1:g=3.4,"
            "equalizer=f=420:t=q:w=1:g=-1.8,"
            "equalizer=f=3100:t=q:w=1:g=2.6,"
            "equalizer=f=7200:t=q:w=1:g=-2.0,"
            "aecho=0.8:0.88:18:0.12,"
            "acompressor=threshold=-18dB:ratio=3:attack=12:release=90,"
            "loudnorm=I=-14:TP=-1.5:LRA=11"
        )
    else:
        # Conversational: Natural and transparent
        return (
            "highpass=f=75,"
            "equalizer=f=120:t=q:w=1:g=3.0,"
            "equalizer=f=400:t=q:w=1:g=-1.5,"
            "equalizer=f=3200:t=q:w=1:g=2.5,"
            "equalizer=f=7000:t=q:w=1:g=-1.8,"
            "aecho=0.8:0.88:15:0.10,"
            "acompressor=threshold=-18dB:ratio=3:attack=10:release=80,"
            "loudnorm=I=-14:TP=-1.5:LRA=11"
        )

# Helper: Direct ElevenLabs API Synthesis
def synthesize_elevenlabs_direct(text, voice_id, api_key, output_path):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": api_key.strip()
    }
    payload = {
        "text": text,
        "model_id": "eleven_multilingual_v2",
        "voice_settings": {
            "stability": 0.50,
            "similarity_boost": 0.85,
            "style": 0.45,
            "use_speaker_boost": True
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode('utf-8'),
        headers=headers,
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        with open(output_path, "wb") as f:
            f.write(resp.read())

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
@app.route("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "app": "Ishan AI Shorts & Voice Studio",
        "version": "1.0.1",
        "engine": "Ultra-Human Neural Studio + ElevenLabs Cloud",
        "voices_count": len(VOICES),
        "emotions_count": len(EMOTION_PRESETS)
    })

@app.route("/api/voices")
def get_voices():
    return jsonify(VOICES)

@app.route("/api/emotions")
def get_emotions():
    return jsonify(EMOTION_PRESETS)

@app.route("/api/templates")
def get_templates():
    return jsonify(VIRAL_TEMPLATES)

@app.route("/api/broll-list")
def get_broll_list():
    return jsonify(BROLL_OPTIONS)

@app.route("/api/music-list")
def get_music_list():
    return jsonify(MUSIC_OPTIONS)

# Core Synthesis: Ultra-Human Thought Units + Breath Pauses
async def synthesize_ultra_human(chunks, voice, rate_str, pitch_str, pause_sec, temp_dir):
    chunk_files = []
    pause_file = temp_dir / "pause.mp3"

    # 1. Generate clean human breath pause
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
        "-t", str(pause_sec),
        "-c:a", "libmp3lame", "-b:a", "48k",
        str(pause_file)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    concat_file = temp_dir / "concat.txt"
    sentences = []
    current_time = 0.0

    with open(concat_file, "w", encoding="utf-8") as cf:
        for idx, chunk_text in enumerate(chunks):
            chunk_path = temp_dir / f"chunk_{idx}.mp3"
            comm = edge_tts.Communicate(chunk_text, voice, rate=rate_str, pitch=pitch_str)
            with open(chunk_path, "wb") as f:
                async for chunk in comm.stream():
                    if chunk["type"] == "audio":
                        f.write(chunk["data"])

            # Measure chunk duration via ffprobe
            res = subprocess.check_output([
                "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(chunk_path)
            ])
            chunk_duration = float(json.loads(res)["format"]["duration"])

            sentences.append({
                "text": chunk_text,
                "start": current_time,
                "duration": chunk_duration,
                "end": current_time + chunk_duration
            })

            cf.write(f"file '{chunk_path.resolve()}'\n")
            current_time += chunk_duration

            if idx < len(chunks) - 1:
                cf.write(f"file '{pause_file.resolve()}'\n")
                current_time += pause_sec

    # 2. Concat all thought units with natural pauses
    stitched_path = temp_dir / "stitched.mp3"
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(concat_file),
        "-c", "copy", str(stitched_path)
    ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return stitched_path, sentences

@app.route("/api/generate-voice", methods=["POST"])
def generate_voice():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    voice_id = data.get("voice", "bn-BD-PradeepNeural")
    emotion_id = data.get("emotion", "thoughtful")
    user_rate = data.get("rate")
    user_pitch = data.get("pitch")
    mastering = data.get("mastering", True)
    enable_pauses = data.get("enable_pauses", True)
    elevenlabs_key = data.get("elevenlabs_key", "").strip()

    if not text:
        return jsonify({"error": "Please enter some text to speak."}), 400

    # Locate Voice Info
    voice_info = next((v for v in VOICES if v["id"] == voice_id), VOICES[0])
    
    # Locate Emotion Info
    emotion_info = next((e for e in EMOTION_PRESETS if e["id"] == emotion_id), EMOTION_PRESETS[0])

    # Determine rate, pitch, pause
    rate_str = user_rate if user_rate else emotion_info["default_rate"]
    pitch_str = user_pitch if user_pitch else emotion_info["default_pitch"]
    pause_sec = emotion_info["pause_sec"] if enable_pauses else 0.15

    job_id = str(uuid.uuid4())[:10]
    temp_dir = OUTPUT_DIR / f"temp_{job_id}"
    temp_dir.mkdir(parents=True, exist_ok=True)
    final_path = OUTPUT_DIR / f"{job_id}.mp3"

    try:
        # Check if ElevenLabs voice requested and key provided
        is_elevenlabs = voice_info.get("engine") == "elevenlabs" and bool(elevenlabs_key)

        if is_elevenlabs:
            raw_path = temp_dir / "eleven_raw.mp3"
            synthesize_elevenlabs_direct(text, voice_info["voice_id"], elevenlabs_key, raw_path)
            stitched_path = raw_path
            # Approximate sentence bounds for elevenlabs
            sentences = [{"text": text, "start": 0.0, "duration": 0.0, "end": 0.0}]
        else:
            # Ultra-Human Neural Studio with Thought Units & Breath Pauses
            target_voice = voice_info["id"] if voice_info.get("engine") != "elevenlabs" else "en-US-ChristopherNeural"
            
            if enable_pauses:
                chunks = split_into_thought_units(text)
            else:
                chunks = [normalize_text_for_human_speech(text)]

            stitched_path, sentences = asyncio.run(
                synthesize_ultra_human(chunks, target_voice, rate_str, pitch_str, pause_sec, temp_dir)
            )

        # Apply High-End Studio Broadcast Mastering
        if mastering:
            af_filter = get_mastering_filter(emotion_id)
            cmd = [
                "ffmpeg", "-y", "-i", str(stitched_path),
                "-af", af_filter,
                "-c:a", "libmp3lame", "-b:a", "320k",
                str(final_path)
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            cmd = [
                "ffmpeg", "-y", "-i", str(stitched_path),
                "-c:a", "libmp3lame", "-b:a", "256k",
                str(final_path)
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        # Cleanup temp directory
        for p in temp_dir.glob("*"):
            try:
                p.unlink()
            except Exception:
                pass
        try:
            temp_dir.rmdir()
        except Exception:
            pass

        # Exact audio duration via ffprobe
        res = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(final_path)
        ])
        total_duration = round(float(json.loads(res)["format"]["duration"]), 2)

        # Fix elevenlabs sentence duration
        if is_elevenlabs and sentences:
            sentences[0]["duration"] = total_duration
            sentences[0]["end"] = total_duration

        return jsonify({
            "success": True,
            "job_id": job_id,
            "audio_url": f"/api/audio/{final_path.name}",
            "filename": final_path.name,
            "duration": total_duration,
            "sentences": sentences,
            "voice": voice_info["name"],
            "emotion": emotion_info["name"],
            "engine": "ElevenLabs Cloud" if is_elevenlabs else "Ultra-Human Neural Studio"
        })

    except urllib.error.HTTPError as e:
        err_msg = e.read().decode('utf-8', errors='ignore')
        return jsonify({"error": f"ElevenLabs API Error: {err_msg}"}), 400
    except Exception as e:
        return jsonify({"error": f"Synthesis Error: {str(e)}"}), 500

@app.route("/api/generate-shorts", methods=["POST"])
def generate_shorts():
    data = request.get_json(silent=True) or {}
    job_id = data.get("job_id", "")
    broll_id = data.get("broll", "cyber_aurora")
    music_id = data.get("music", "lofi_ambient")
    music_vol = float(data.get("music_vol", 0.15))
    caption_color = data.get("caption_color", "gold")

    voice_path = OUTPUT_DIR / f"{job_id}.mp3"
    if not voice_path.exists():
        return jsonify({"error": "Voice audio file not found. Generate voice first."}), 404

    broll_info = next((b for b in BROLL_OPTIONS if b["id"] == broll_id), BROLL_OPTIONS[0])
    broll_path = BROLL_DIR / broll_info["file"]
    if not broll_path.exists():
        return jsonify({"error": "Background video asset missing."}), 404

    music_info = next((m for m in MUSIC_OPTIONS if m["id"] == music_id), MUSIC_OPTIONS[0])
    has_music = music_info["file"] is not None
    music_path = MUSIC_DIR / music_info["file"] if has_music else None

    # Get exact duration
    res = subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(voice_path)
    ])
    duration = float(json.loads(res)["format"]["duration"])

    # Build ASS subtitle file with Hormozi styles
    sentences = data.get("sentences", [])
    ass_path = OUTPUT_DIR / f"{job_id}.ass"

    # Color codes in ASS format (&HAABBGGRR)
    primary_color = "&H0000E5FF" if caption_color == "gold" else ("&H00FFFF00" if caption_color == "cyan" else "&H00FFFFFF")

    ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hormozi,Arial,64,{primary_color},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,0,2,60,60,440,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    def fmt_time(t):
        m, sec = divmod(t, 60)
        h, m = divmod(m, 60)
        cs = int((sec - int(sec)) * 100)
        return f"{int(h):01d}:{int(m):02d}:{int(sec):02d}.{cs:02d}"

    if sentences:
        for s in sentences:
            start_sec = max(0.0, s["start"])
            end_sec = min(duration, s["end"])
            text_clean = s["text"].replace("\n", " ").strip()
            # If English, make bold uppercase; if Bengali keep pristine unicode
            if re.search(r'[\u0980-\u09FF]', text_clean):
                display_text = text_clean
            else:
                display_text = text_clean.upper()
            ass_content += f"Dialogue: 0,{fmt_time(start_sec)},{fmt_time(end_sec)},Hormozi,,0,0,0,,{display_text}\n"
    else:
        ass_content += f"Dialogue: 0,0:00:00.10,{fmt_time(duration)},Hormozi,,0,0,0,,{data.get('title', 'WATCH TILL END')}\n"

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    video_output = OUTPUT_DIR / f"{job_id}_shorts.mp4"

    try:
        # Loop b-roll, mix audio, burn ASS Hormozi subtitle, 1080x1920 60FPS
        if has_music and music_path and music_path.exists():
            cmd = [
                "ffmpeg", "-y",
                "-stream_loop", "-1", "-i", str(broll_path),
                "-i", str(voice_path),
                "-stream_loop", "-1", "-i", str(music_path),
                "-filter_complex",
                f"[0:v]trim=duration={duration},ass={str(ass_path)}[v];"
                f"[2:a]volume={music_vol}[bgm];"
                f"[1:a][bgm]amix=inputs=2:duration=first[a]",
                "-map", "[v]", "-map", "[a]",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "aac", "-b:a", "192k",
                "-t", str(duration),
                str(video_output)
            ]
        else:
            cmd = [
                "ffmpeg", "-y",
                "-stream_loop", "-1", "-i", str(broll_path),
                "-i", str(voice_path),
                "-filter_complex",
                f"[0:v]trim=duration={duration},ass={str(ass_path)}[v]",
                "-map", "[v]", "-map", "1:a",
                "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                "-c:a", "aac", "-b:a", "192k",
                "-t", str(duration),
                str(video_output)
            ]

        subprocess.run(cmd, check=True)

        return jsonify({
            "success": True,
            "video_url": f"/api/video/{video_output.name}",
            "filename": video_output.name,
            "duration": round(duration, 2)
        })

    except Exception as e:
        return jsonify({"error": f"Rendering Error: {str(e)}"}), 500

@app.route("/api/audio/<filename>")
def serve_audio(filename):
    safe_name = os.path.basename(filename)
    path = OUTPUT_DIR / safe_name
    if not path.exists():
        return "Audio not found", 404
    return send_file(str(path), mimetype="audio/mpeg", as_attachment=False)

@app.route("/api/video/<filename>")
def serve_video(filename):
    safe_name = os.path.basename(filename)
    path = OUTPUT_DIR / safe_name
    if not path.exists():
        return "Video not found", 404
    return send_file(str(path), mimetype="video/mp4", as_attachment=False)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5050))
    print(f"\n=======================================================")
    print(f" 🚀 Ishan AI Shorts & Voice Studio v1.0.1 is LIVE!")
    print(f" 🎙️ Ultra-Human Neural Studio + ElevenLabs Engine Active!")
    print(f" 📱 URL: http://localhost:{port}")
    print(f"=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=False)
