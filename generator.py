import asyncio
import os
import tempfile
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import (
    AudioFileClip,
    CompositeAudioClip,
    CompositeVideoClip,
    ImageClip,
    concatenate_videoclips,
)
from moviepy.video.fx.all import crop


def _font(size):
    candidates = [
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation2/LiberationSans-Bold.ttf",
        "C:/Windows/Fonts/arialbd.ttf",
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
    ]
    for candidate in candidates:
        if os.path.exists(candidate):
            return ImageFont.truetype(candidate, size=size)
    return ImageFont.load_default()


def _cover_image(path, size):
    image = Image.open(path).convert("RGB")
    target_w, target_h = size
    scale = max(target_w / image.width, target_h / image.height)
    resized = image.resize((int(image.width * scale), int(image.height * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def _text_overlay(text, size, name=None):
    width, height = size
    canvas = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    font = _font(max(28, int(width * 0.045)))
    small_font = _font(max(22, int(width * 0.028)))

    # Bandeau semi-transparent en bas de l'image
    band_h = int(height * 0.24)
    y0 = height - band_h
    draw.rounded_rectangle(
        (int(width * 0.045), y0, int(width * 0.955), height - int(height * 0.035)),
        radius=28,
        fill=(0, 0, 0, 170),
    )
    if name:
        draw.text((int(width * 0.075), y0 + 22), name.upper(), font=small_font, fill=(255, 220, 80, 255))
        text_y = y0 + 62
    else:
        text_y = y0 + 30

    max_width = int(width * 0.82)
    words = text.split()
    lines, line = [], ""
    for word in words:
        trial = (line + " " + word).strip()
        if draw.textbbox((0, 0), trial, font=font)[2] <= max_width:
            line = trial
        else:
            if line:
                lines.append(line)
            line = word
    if line:
        lines.append(line)

    line_height = int(font.size * 1.2)
    max_lines = max(1, int((height * 0.17) / line_height))
    for index, line in enumerate(lines[:max_lines]):
        draw.text((int(width * 0.075), text_y + index * line_height), line, font=font, fill="white")
    return np.array(canvas)


async def _make_tts(text, voice, output_path):
    import edge_tts
    communicate = edge_tts.Communicate(text=text, voice=voice)
    await communicate.save(output_path)


def _create_voice(text, voice, output_path):
    try:
        asyncio.run(_make_tts(text, voice, output_path))
        return output_path if os.path.exists(output_path) and os.path.getsize(output_path) > 0 else None
    except RuntimeError:
        # Cas où un event loop existe déjà
        import threading
        result = {"ok": False, "error": None}

        def worker():
            try:
                asyncio.run(_make_tts(text, voice, output_path))
                result["ok"] = True
            except Exception as exc:
                result["error"] = exc

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join()
        return output_path if result["ok"] else None
    except Exception:
        return None


def build_team_video(
    characters_data,
    villa_paths,
    out_name="team_nasdas.mp4",
    voice_enabled=True,
    voice="fr-FR-HenriNeural",
    music_path=None,
    music_volume=0.15,
    video_size=(1080, 1920),
    fps=30,
    bitrate="6000k",
):
    """Construit un montage vertical MP4 à partir des photos et phrases fournies."""
    if not characters_data:
        raise ValueError("Aucun personnage n'a été fourni.")
    if not villa_paths:
        raise ValueError("Aucune photo de villa n'a été fournie.")

    width, height = video_size
    clips = []
    audio_parts = []
    temp_audio_paths = []
    cursor = 0.0

    try:
        # Intro villa
        intro_text = "BIENVENUE À LA VILLA NASDAS"
        intro_path = _make_frame(villa_paths[0], video_size, intro_text, None)
        intro_clip = ImageClip(intro_path).set_duration(2.8)
        clips.append(intro_clip)
        cursor += intro_clip.duration

        # Présentation de chaque membre, puis plans de villa
        for index, character in enumerate(characters_data):
            image_path = character["path"]
            phrase = character.get("phrase") or f"Bienvenue à la Villa NASDAS, moi c'est {character['name']}."
            frame_path = _make_frame(image_path, video_size, phrase, character.get("name"))
            segment_duration = 4.0
            clip = ImageClip(frame_path).set_duration(segment_duration)
            clips.append(clip)

            if voice_enabled:
                audio_path = os.path.join(tempfile.gettempdir(), f"nasdas_voice_{os.getpid()}_{index}.mp3")
                created = _create_voice(phrase, voice, audio_path)
                if created:
                    temp_audio_paths.append(created)
                    voice_clip = AudioFileClip(created).set_start(cursor)
                    audio_parts.append(voice_clip)

            cursor += segment_duration

            villa_path = villa_paths[index % len(villa_paths)]
            villa_text = "LA VILLA • TEAM NASDAS"
            villa_frame = _make_frame(villa_path, video_size, villa_text, None)
            villa_clip = ImageClip(villa_frame).set_duration(2.6)
            clips.append(villa_clip)
            cursor += villa_clip.duration

        final_clip = concatenate_videoclips(clips, method="compose")

        if music_path and os.path.exists(music_path):
            music = AudioFileClip(music_path)
            if music.duration > final_clip.duration:
                music = music.subclip(0, final_clip.duration)
            music = music.volumex(max(0.0, min(1.0, music_volume)))
            audio_parts.append(music)

        if audio_parts:
            final_clip = final_clip.set_audio(CompositeAudioClip(audio_parts).set_duration(final_clip.duration))

        final_clip.write_videofile(
            out_name,
            fps=fps,
            codec="libx264",
            audio_codec="aac",
            bitrate=bitrate,
            preset="medium",
            threads=2,
            logger=None,
        )
        final_clip.close()
        for clip in clips:
            clip.close()
        return out_name
    finally:
        for path in temp_audio_paths:
            try:
                os.unlink(path)
            except OSError:
                pass


def _make_frame(image_path, size, text, name):
    image = _cover_image(image_path, size).convert("RGBA")
    overlay = Image.fromarray(_text_overlay(text, size, name), mode="RGBA")
    image.alpha_composite(overlay)
    # Stockage temporaire PNG afin que MoviePy puisse charger une image stable
    fd, path = tempfile.mkstemp(suffix=".png", prefix="nasdas_frame_")
    os.close(fd)
    image.save(path, "PNG")
    return path
