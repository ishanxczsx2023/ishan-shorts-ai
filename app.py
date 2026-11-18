import os
import sys
import uuid
import re
import json
import time
import asyncio
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

# ElevenLabs-Grade Voice Catalog
VOICES = [
    # English (US) ElevenLabs Clones
    {
        "id": "en-US-ChristopherNeural",
        "name": "Christopher (Viral Mystery)",
        "lang": "English (US)",
        "flag": "🇺🇸",
        "gender": "Male",
        "tag": "🔥 ElevenLabs Clone",
        "desc": "Deep, authoritative, viral TikTok mystery & documentary narrator"
    },
    {
        "id": "en-US-AndrewNeural",
        "name": "Andrew (Viral Storyteller)",
        "lang": "English (US)",
        "flag": "🇺🇸",
        "gender": "Male",
        "tag": "🌟 ElevenLabs Warm",
        "desc": "Warm, engaging, fast-paced storytelling and viral reels"
    },
    {
        "id": "en-US-GuyNeural",
        "name": "Guy (Tech & Energetic)",
        "lang": "English (US)",
        "flag": "🇺🇸",
        "gender": "Male",
        "tag": "⚡ High Energy",
        "desc": "Crisp YouTube tech reviews, gaming, and energetic shorts"
    },
    {
        "id": "en-US-EricNeural",
        "name": "Eric (Deep Radio Master)",
        "lang": "English (US)",
        "flag": "🇺🇸",
        "gender": "Male",
        "tag": "🎙️ Radio Broadcaster",
        "desc": "Deep bass broadcast radio and cinema trailer voice"
    },
    {
        "id": "en-US-AvaNeural",
        "name": "Ava (Expressive Emotion)",
        "lang": "English (US)",
        "flag": "🇺🇸",
        "gender": "Female",
        "tag": "✨ Emotional Story",
        "desc": "Expressive, calm, cinematic female storyteller"
    },
    {
        "id": "en-US-JennyNeural",
        "name": "Jenny (Natural Conversational)",
        "lang": "English (US)",
        "flag": "🇺🇸",
        "gender": "Female",
        "tag": "💬 Conversational",
        "desc": "Natural lifestyle, vlog, and friendly explainer"
    },
    # Bengali (Bangladesh) Neural
    {
        "id": "bn-BD-PradeepNeural",
        "name": "প্রদীপ (Pradeep - News & Story)",
        "lang": "Bangla (BD)",
        "flag": "🇧🇩",
        "gender": "Male",
        "tag": "👑 Bengali Master",
        "desc": "গম্ভীর ও আকর্ষণীয় পুরুষ কণ্ঠ • ভাইরাল গল্প ও ডকুমেন্টারি"
    },
    {
        "id": "bn-BD-NabanitaNeural",
        "name": "নবনীতা (Nabanita - Sweet & Clear)",
        "lang": "Bangla (BD)",
        "flag": "🇧🇩",
        "gender": "Female",
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
        "tag": "🎙️ Deep Bangla",
        "desc": "গভীর ও স্পষ্ট আবৃত্তি ও গল্প বলা"
    },
    {
        "id": "bn-IN-TanishaaNeural",
        "name": "তানিশা (Tanishaa - Modern Tone)",
        "lang": "Bangla (IN)",
        "flag": "🇮🇳",
        "gender": "Female",
        "tag": "✨ Modern Bangla",
        "desc": "স্মার্ট ও আধুনিক ভয়েস ওভার"
    },
    # Hindi
    {
        "id": "hi-IN-MadhurNeural",
        "name": "Madhur (Reels & Story)",
        "lang": "Hindi (IN)",
        "flag": "🇮🇳",
        "gender": "Male",
        "tag": "🔥 Hindi Viral",
        "desc": "Viral Hindi facts, stories and motivational shorts"
    },
    {
        "id": "hi-IN-SwaraNeural",
        "name": "Swara (Professional Narrative)",
        "lang": "Hindi (IN)",
        "flag": "🇮🇳",
        "gender": "Female",
        "tag": "🌟 Hindi Pro",
        "desc": "Clear professional Hindi commentary"
    }
]

VIRAL_TEMPLATES = [
    {
        "id": "psychology",
        "category": "🧠 Psychology",
        "title": "The 2-Second Silence Rule",
        "text": "The psychological trick that makes everyone respect you immediately. Powerful people never explain themselves right away. When asked a tough question, pause for two full seconds before you speak. That tiny silence creates instant tension, commands the entire room, and signals absolute confidence. Save this video so you remember to use it."
    },
    {
        "id": "wealth",
        "category": "💰 Wealth & Money",
        "title": "Rule #1 of the Silent Rich",
        "text": "Rule number one of the truly wealthy: Never look rich before you actually are rich. Fake luxury keeps the middle class trapped in debt. Real wealth is quiet, humble, and invisible. The wealthy buy assets that produce cashflow, while the broke buy designer clothes to impress people they don't even like. Change your mindset today."
    },
    {
        "id": "motivation",
        "category": "🔥 Discipline",
        "title": "Nobody is Coming to Save You",
        "text": "Nobody is coming to save you. Nobody is going to drag you out of bed, push you into the gym, or force you to build your business. Your entire future rests squarely on your shoulders. Stop waiting for motivation. Motivation is a myth. Discipline is doing what needs to be done even when you hate doing it. Start today."
    },
    {
        "id": "bangla_life",
        "category": "🇧🇩 বাংলা মোটিভেশন",
        "title": "জীবনে ৩টি মারাত্মক ভুল",
        "text": "জীবনে এই তিনটি ভুল কখনো করবেন না। এক, কারো দুর্বলতা নিয়ে কখনো উপহাস করবেন না। দুই, অতিরিক্ত রাগের মাথায় কোনো চূড়ান্ত সিদ্ধান্ত নেবেন না। আর তিন, যার কঠিন বিপদে আপনি নিঃস্বার্থভাবে পাশে ছিলেন, তার কাছ থেকে কখনো কৃতজ্ঞতা আশা করবেন না। ভালো থাকুন নিজের যোগ্যতায়।"
    },
    {
        "id": "bangla_facts",
        "category": "🇧🇩 বাংলা ফ্যাক্টস",
        "title": "মানুষের মস্তিষ্কের গোপন শক্তি",
        "text": "আপনি কি জানেন? মানুষের মস্তিষ্ক প্রতিদিন প্রায় ৬০ থেকে ৭০ হাজার আলাদা চিন্তা তৈরি করে! যার প্রায় আশি শতাংশই থাকে অতীত নিয়ে দুশ্চিন্তা। কিন্তু আপনি যদি প্রতিদিন সকালে ৫ মিনিট গভীর ধ্যান করেন, তবে আপনার ব্রেন পাওয়ার দ্বিগুণ হয়ে যাবে। ভিডিওটি বন্ধুদের সাথে শেয়ার করুন।"
    }
]

BROLL_OPTIONS = [
    {"id": "cyber_aurora", "name": "🌌 Cosmic Cyber Aurora", "file": "cyber_aurora.mp4"},
    {"id": "neon_matrix", "name": "🟢 Neon Emerald Matrix", "file": "neon_matrix.mp4"},
    {"id": "golden_luxury", "name": "👑 Golden Luxury Amber", "file": "golden_luxury.mp4"}
]

MUSIC_OPTIONS = [
    {"id": "lofi_ambient", "name": "🎧 Chill Lofi Ambient", "file": "lofi_ambient.mp3"},
    {"id": "cinematic_tension", "name": "🎬 Cinematic Tension Drone", "file": "cinematic_tension.mp3"},
    {"id": "none", "name": "🔇 No Background Music", "file": None}
]

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/health")
@app.route("/api/health")
def health():
    return jsonify({
        "status": "healthy",
        "app": "Ishan AI Shorts & Voice Studio",
        "version": "1.0.0",
        "voices_count": len(VOICES)
    })

@app.route("/api/voices")
def get_voices():
    return jsonify(VOICES)

@app.route("/api/templates")
def get_templates():
    return jsonify(VIRAL_TEMPLATES)

@app.route("/api/broll-list")
def get_broll_list():
    return jsonify(BROLL_OPTIONS)

@app.route("/api/music-list")
def get_music_list():
    return jsonify(MUSIC_OPTIONS)

async def synthesize_edge_tts(text, voice, rate_str, pitch_str, output_path):
    communicate = edge_tts.Communicate(text, voice, rate=rate_str, pitch=pitch_str)
    sentences = []
    
    with open(output_path, "wb") as f:
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                f.write(chunk["data"])
            elif chunk["type"] == "SentenceBoundary":
                sentences.append({
                    "text": chunk.get("text", "").strip(),
                    "start": chunk.get("offset", 0) / 10000000.0,
                    "duration": chunk.get("duration", 0) / 10000000.0,
                    "end": (chunk.get("offset", 0) + chunk.get("duration", 0)) / 10000000.0
                })
    return sentences

@app.route("/api/generate-voice", methods=["POST"])
def generate_voice():
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    voice = data.get("voice", "en-US-ChristopherNeural")
    rate = data.get("rate", "+0%")
    pitch = data.get("pitch", "+0Hz")
    mastering = data.get("mastering", True)

    if not text:
        return jsonify({"error": "Please enter some text to speak."}), 400

    job_id = str(uuid.uuid4())[:10]
    raw_path = OUTPUT_DIR / f"{job_id}_raw.mp3"
    final_path = OUTPUT_DIR / f"{job_id}.mp3"

    try:
        # Run async edge-tts
        sentences = asyncio.run(synthesize_edge_tts(text, voice, rate, pitch, raw_path))

        # Check audio validity
        if not raw_path.exists() or raw_path.stat().st_size == 0:
            raise Exception("Voice generation failed. Please try a different voice or text.")

        if mastering:
            # ElevenLabs Studio Broadcast Master Filter:
            # 1. Warm EQ (120Hz bass body boost)
            # 2. Presence EQ (3.5kHz vocal clarity)
            # 3. Air EQ (10kHz crispness)
            # 4. Studio multiband-style compressor
            # 5. Volume balancing
            af_filter = (
                "equalizer=f=120:t=q:w=1:g=3.5,"
                "equalizer=f=3500:t=q:w=1:g=2.0,"
                "equalizer=f=10000:t=q:w=1:g=2.5,"
                "acompressor=threshold=-18dB:ratio=3:attack=5:release=50,"
                "volume=1.25"
            )
            cmd = [
                "ffmpeg", "-y", "-i", str(raw_path),
                "-af", af_filter,
                "-c:a", "libmp3lame", "-b:a", "320k",
                str(final_path)
            ]
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            raw_path.unlink(missing_ok=True)
        else:
            raw_path.rename(final_path)

        # Get exact audio duration via ffprobe
        res = subprocess.check_output([
            "ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", str(final_path)
        ])
        duration = round(float(json.loads(res)["format"]["duration"]), 2)

        return jsonify({
            "success": True,
            "job_id": job_id,
            "audio_url": f"/api/audio/{final_path.name}",
            "filename": final_path.name,
            "duration": duration,
            "sentences": sentences,
            "voice": voice
        })

    except Exception as e:
        return jsonify({"error": f"Synthesis Error: {str(e)}"}), 500

@app.route("/api/generate-shorts", methods=["POST"])
def generate_shorts():
    data = request.get_json(silent=True) or {}
    job_id = data.get("job_id", "")
    broll_id = data.get("broll", "cyber_aurora")
    music_id = data.get("music", "lofi_ambient")
    music_vol = float(data.get("music_vol", 0.15))
    caption_color = data.get("caption_color", "gold")  # gold, cyan, white

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
    # Gold/Yellow: &H0000E5FF
    # Cyan: &H00FFFF00
    # White: &H00FFFFFF
    primary_color = "&H0000E5FF" if caption_color == "gold" else ("&H00FFFF00" if caption_color == "cyan" else "&H00FFFFFF")

    ass_content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Hormozi,Arial,62,{primary_color},&H000000FF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,0,2,60,60,420,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    if sentences:
        for s in sentences:
            start_sec = max(0.0, s["start"])
            end_sec = min(duration, s["end"])
            # Format time as H:MM:SS.cs
            def fmt_time(t):
                m, sec = divmod(t, 60)
                h, m = divmod(m, 60)
                cs = int((sec - int(sec)) * 100)
                return f"{int(h):01d}:{int(m):02d}:{int(sec):02d}.{cs:02d}"

            text_clean = s["text"].replace("\n", " ").strip().upper()
            ass_content += f"Dialogue: 0,{fmt_time(start_sec)},{fmt_time(end_sec)},Hormozi,,0,0,0,,{text_clean}\n"
    else:
        # Fallback single block
        ass_content += f"Dialogue: 0,0:00:00.10,0:00:{int(duration):02d}.00,Hormozi,,0,0,0,,{data.get('title', 'WATCH TILL END').upper()}\n"

    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    video_output = OUTPUT_DIR / f"{job_id}_shorts.mp4"

    try:
        # FFmpeg pipeline:
        # 1. Loop b-roll (9:16)
        # 2. Voiceover (input 1)
        # 3. Optional BGM (input 2) ducked
        # 4. Burn ASS Hormozi subtitle
        # 5. Output 1080x1920 60FPS video
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
    print(f" 🚀 Ishan AI Shorts & Voice Studio is LIVE!")
    print(f" 🎙️ ElevenLabs-Grade Neural Engine Active!")
    print(f" 📱 URL: http://localhost:{port}")
    print(f"=======================================================\n")
    app.run(host="0.0.0.0", port=port, debug=False)
