import streamlit as st
import openai
import json
import requests

# Pagina configuratie
st.set_page_config(page_title="JackCraig Script Builder", layout="wide")

st.title("🎬 JackCraig Script Builder")
st.markdown("Zet long-form transcripts om in strakke, virale Shorts scripts inclusief ElevenLabs voice-overs.")

# Haal de API keys onzichtbaar op uit Streamlit Secrets
try:
    openai_api_key = st.secrets["OPENAI_API_KEY"]
    elevenlabs_api_key = st.secrets["ELEVENLABS_API_KEY"]
    voice_id = st.secrets.get("VOICE_ID", "pNInz6obpgDQGcFmaJgB") # Standaard Adam
except KeyError:
    st.error("⚠️ De API keys ontbreken in de Streamlit Secrets! Voeg ze toe in je dashboard.")
    st.stop()

# We houden de sidebar alleen nog voor een beetje info
with st.sidebar:
    st.success("✅ API Keys succesvol en veilig geladen!")
    st.markdown("Je bent direct klaar om scripts en audio te genereren.")

# Initializeer session state zodat het script niet verdwijnt bij een nieuwe klik
if "script_data" not in st.session_state:
    st.session_state.script_data = None

# Hoofdvenster voor input
transcript = st.text_area("📝 Plak hier je onbewerkte video transcript:", height=300)

system_prompt = """
You are a master YouTube Shorts copywriter. Your goal is to convert a long-form video transcript into a super-engaging Short script. 
You MUST output the script in ENGLISH, regardless of the input language.
You MUST follow the exact structure below and estimate or extract timestamps (MM:SS) from the original video to show where the clips can be found.

Structure:
- HOOK: One powerful sentence as a question. Create a 'curiosity gap' by sketching a hypothetical or extreme scenario. No intros.
- RISING_ACTION_1: 3 to 5 sentences. Explain the process and scale. Build tension on how they try to answer the hook.
- CONFLICT: 2 to 3 sentences. The plot twist. What went wrong unexpectedly? This must disrupt the plan.
- COMEBACK: 1 sentence. The quick fix or pivot. How does the creator overcome the conflict?
- RISING_ACTION_2: 1 to 2 sentences. Build up to the climax and the extreme consequence of the comeback.
- PAYOFF: 1 sentence. The satisfying result and answer to the hook, preferably with a punchline.

Output STRICTLY as a JSON object with the keys:
"hook", "rising_action_1", "conflict", "comeback", "rising_action_2", "payoff".
Each key MUST contain a nested object with exactly two strings: "timestamp" (e.g. "01:30") and "text" (the actual script line).
"""

if st.button("🚀 Genereer Script", use_container_width=True):
    if not openai_api_key:
        st.warning("⚠️ Vul eerst je OpenAI API key in aan de linkerkant.")
    elif not transcript:
        st.warning("⚠️ Plak een transcript om te beginnen.")
    else:
        with st.spinner("AI is het script aan het schrijven en structureren..."):
            try:
                # OpenAI API Call
                client = openai.OpenAI(api_key=openai_api_key)
                response = client.chat.completions.create(
                    model="gpt-4o",
                    response_format={ "type": "json_object" },
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": transcript}
                    ],
                    temperature=0.7
                )
                
                # Sla het script op in het geheugen van de app
                st.session_state.script_data = json.loads(response.choices[0].message.content)
                st.success("✅ Script succesvol gegenereerd!")
                
            except Exception as e:
                st.error(f"Er is een fout opgetreden: {e}")

# Laat het script zien als het is gegenereerd
if st.session_state.script_data:
    st.markdown("### Jouw Script:")
    
    # We maken direct een lege string aan om alle tekst samen te voegen voor ElevenLabs
    full_text_to_speak = ""
    
    for section, content in st.session_state.script_data.items():
        timestamp = content.get('timestamp', '00:00')
        text = content.get('text', '')
        
        # Voeg de tekst toe aan de volledige string (met een spatie ertussen)
        full_text_to_speak += text + " "
        
        formatted_title = section.replace("_", " ").upper()
        st.markdown(f"**<span style='color:#FF4B4B'>{formatted_title} ({timestamp})</span>:**", unsafe_allow_html=True)
        st.write(text)
        st.divider()
    
    with st.expander("Bekijk ruwe JSON data (voor debugging)"):
        st.json(st.session_state.script_data)

    st.markdown("### 🔊 Audio Genereren")
    
    if elevenlabs_api_key and voice_id:
        if st.button("🎙️ Maak Voice-over & Verwijder Stiltes", type="primary", use_container_width=True):
            with st.spinner("ElevenLabs is aan het inspreken en de AI knipt de stiltes weg..."):
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
                
                headers = {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": elevenlabs_api_key
                }
                
                data = {
                    "text": full_text_to_speak.strip(),
                    "model_id": "eleven_multilingual_v2",
                    "voice_settings": {
                        "stability": 0.5,
                        "similarity_boost": 0.75
                    }
                }
                
                try:
                    el_response = requests.post(url, json=data, headers=headers)
                    
                    if el_response.status_code == 200:
                        ruwe_audio_bytes = el_response.content
                        
                        # --- START AUDIO BEWERKING ---
                        from pydub import AudioSegment
                        from pydub.silence import split_on_silence
                        import io
                        
                        # Laad de audio in Pydub
                        audio_segment = AudioSegment.from_file(io.BytesIO(ruwe_audio_bytes), format="mp3")
                        
                        # Detecteer stiltes en knip de audio op
                        chunks = split_on_silence(
                            audio_segment,
                            min_silence_len=150,     # Knip stiltes langer dan 150ms eruit
                            silence_thresh=-40,      # Het volume (in dB) dat we als 'stilte' beschouwen
                            keep_silence=20          # Laat 20ms over voor een heeeel klein beetje overgang
                        )
                        
                        # Plak alles strak aan elkaar vast
                        bewerkte_audio = AudioSegment.empty()
                        for chunk in chunks:
                            bewerkte_audio += chunk
                            
                        # Zet terug naar MP3 bytes voor de download
                        buffer = io.BytesIO()
                        bewerkte_audio.export(buffer, format="mp3")
                        finale_audio_bytes = buffer.getvalue()
                        # --- EINDE AUDIO BEWERKING ---

                        st.success("Audio succesvol gegenereerd én supersnel achter elkaar gezet!")
                        
                        # Speel de bewerkte audio af in de app
                        st.audio(finale_audio_bytes, format='audio/mp3')
                        
                        # Downloadknop voor de supersnelle MP3
                        st.download_button(
                            label="⬇️ Download Rapid-Fire .mp3",
                            data=finale_audio_bytes,
                            file_name="jackcraig_rapidfire_voiceover.mp3",
                            mime="audio/mpeg",
                            use_container_width=True
                        )
                    else:
                        st.error(f"ElevenLabs Error: {el_response.text}")
                except Exception as e:
                    st.error(f"Fout bij het verwerken van de audio: {e}")
    else:
        st.info("Vul je ElevenLabs API key en Voice ID in (in de linkerbalk) om de audio-knop te ontgrendelen.")