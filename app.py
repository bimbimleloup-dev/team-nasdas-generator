import os
import tempfile
import streamlit as st
from PIL import Image
from generator import build_team_video

st.set_page_config(page_title="Team NASDAS Generator", page_icon="🔥", layout="centered")

st.title("🔥 Team NASDAS — Générateur de Vlog")
st.caption("Crée une vidéo verticale de présentation de la villa, prête pour TikTok et Instagram Reels.")

TEAM_MEMBERS = ["NASDAS", "SAMOS", "ASSYA", "ABDV", "TOUNSI"]

with st.sidebar:
    st.header("⚙️ Réglages vidéo")
    voice_enabled = st.checkbox("Voix off automatique (français)", value=True)
    voice = st.selectbox(
        "Voix française",
        ["fr-FR-HenriNeural", "fr-FR-DeniseNeural", "fr-FR-EloiseNeural"],
        index=0,
        disabled=not voice_enabled,
    )
    width = st.selectbox("Format", ["Vertical 9:16 (TikTok / Reels)", "Carré 1:1"], index=0)
    quality = st.select_slider("Qualité", options=["Rapide", "Standard", "Haute"], value="Standard")
    music_volume = st.slider("Volume musique (%)", 0, 100, 15)
    st.caption("La génération vocale nécessite une connexion Internet.")

st.subheader("1️⃣ Les membres de la Team")
st.write("Ajoute une photo pour chaque personne. Les membres sans photo seront simplement ignorés.")

characters_data = []
uploaded_character_files = []
for name in TEAM_MEMBERS:
    with st.expander(f"📸 {name}", expanded=(name == "NASDAS")):
        file = st.file_uploader(f"Photo de {name}", type=["jpg", "jpeg", "png", "webp"], key=f"file_{name}")
        default_phrase = f"Salut, moi c'est {name}, bienvenue à la Villa NASDAS !"
        if name == "NASDAS":
            default_phrase = "Wesh la Team, moi c'est Nasdas, on va vous faire visiter la villa de fou !"
        elif name == "ASSYA":
            default_phrase = "Coucou la team, c'est Assya, installez-vous, on vous fait visiter !"
        phrase = st.text_input(f"Phrase de {name}", value=default_phrase, key=f"phrase_{name}")
        if file:
            st.image(file, width=180)
            characters_data.append({"file": file, "name": name, "phrase": phrase.strip()})
            uploaded_character_files.append(file)

st.subheader("2️⃣ Les photos de la villa")
villa_files = st.file_uploader(
    "Ajoute 1 à 12 photos de la villa",
    type=["jpg", "jpeg", "png", "webp"],
    accept_multiple_files=True,
    key="villa",
)
if villa_files:
    cols = st.columns(min(len(villa_files), 3))
    for i, f in enumerate(villa_files):
        cols[i % 3].image(f, use_container_width=True)

st.subheader("3️⃣ Musique (facultatif)")
music_file = st.file_uploader("Ajoute une musique MP3, WAV ou M4A", type=["mp3", "wav", "m4a"], key="music")
st.caption("Utilise uniquement une musique que tu as le droit d'utiliser sur tes réseaux.")

st.divider()
if st.button("🚀 GÉNÉRER LA VIDÉO", type="primary", use_container_width=True):
    if not characters_data:
        st.error("Ajoute au moins une photo de personnage.")
    elif not villa_files:
        st.error("Ajoute au moins une photo de la villa.")
    else:
        temp_paths = []
        try:
            with st.spinner("Préparation des images et montage vidéo… Cela peut prendre quelques minutes."):
                prepared_characters = []
                for item in characters_data:
                    suffix = os.path.splitext(item["file"].name)[1] or ".jpg"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(item["file"].getvalue())
                        temp_paths.append(tmp.name)
                        prepared_characters.append({
                            "path": tmp.name,
                            "name": item["name"],
                            "phrase": item["phrase"] or f"Bienvenue à la Villa NASDAS !",
                        })

                villa_paths = []
                for file in villa_files:
                    suffix = os.path.splitext(file.name)[1] or ".jpg"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(file.getvalue())
                        temp_paths.append(tmp.name)
                        villa_paths.append(tmp.name)

                music_path = None
                if music_file:
                    suffix = os.path.splitext(music_file.name)[1] or ".mp3"
                    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
                        tmp.write(music_file.getvalue())
                        temp_paths.append(tmp.name)
                        music_path = tmp.name

                video_size = (1080, 1920) if width.startswith("Vertical") else (1080, 1080)
                fps = 24 if quality == "Rapide" else 30
                bitrate = "3500k" if quality == "Rapide" else ("6000k" if quality == "Standard" else "9000k")
                output_path = os.path.join(tempfile.gettempdir(), "team_nasdas_villa.mp4")

                build_team_video(
                    prepared_characters,
                    villa_paths,
                    out_name=output_path,
                    voice_enabled=voice_enabled,
                    voice=voice,
                    music_path=music_path,
                    music_volume=music_volume / 100,
                    video_size=video_size,
                    fps=fps,
                    bitrate=bitrate,
                )

            st.success("✅ Vidéo prête !")
            with open(output_path, "rb") as video:
                video_bytes = video.read()
            st.video(video_bytes)
            st.download_button(
                "⬇️ Télécharger la vidéo MP4",
                data=video_bytes,
                file_name="team_nasdas_villa.mp4",
                mime="video/mp4",
                use_container_width=True,
            )
        except Exception as exc:
            st.error(f"La génération a échoué : {exc}")
            st.info("Vérifie les dépendances et réessaie. Consulte le README si le problème persiste.")
        finally:
            for path in temp_paths:
                try:
                    os.unlink(path)
                except OSError:
                    pass

st.divider()
st.caption("Team NASDAS Generator • Génération locale dans ton environnement Streamlit.")
