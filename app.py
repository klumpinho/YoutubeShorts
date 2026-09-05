import streamlit as st
import openai
import json
import requests
import io
from pydub import AudioSegment
from pydub.silence import split_on_silence

# Pagina configuratie
st.set_page_config(page_title="JackCraig Script Builder", layout="wide")

# Initializeer session state variabelen
if "script_data" not in st.session_state:
    st.session_state.script_data = None
if "full_text_to_speak" not in st.session_state:
    st.session_state.full_text_to_speak = ""

# API Keys ophalen (onzichtbaar)
try:
    openai_api_key = st.secrets["OPENAI_API_KEY"]
    elevenlabs_api_key = st.secrets["ELEVENLABS_API_KEY"]
    voice_id = st.secrets.get("VOICE_ID", "pNInz6obpgDQGcFmaJgB") # Adam
except KeyError:
    st.error("⚠️ De API keys ontbreken in de Streamlit Secrets! Voeg ze toe in je dashboard.")
    st.stop()

# --- ZIJBALK NAVIGATIE ---
with st.sidebar:
    st.title("🎬 JackCraig")
    st.markdown("Script & Voice Builder")
    st.divider()
    
    # Het navigatiemenu
    menu_keuze = st.radio(
        "Navigatie", 
        ["📝 Transcript to Script", "🎙️ Script to Voice Over"],
        label_visibility="collapsed"
    )
    
    st.divider()
    st.caption("✅ API Keys Actief")

# De System Prompt
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

# --- SCHERM 1: TRANSCRIPT TO SCRIPT ---
if menu_keuze == "📝 Transcript to Script":
    st.header("📝 Transcript to Script")
    st.markdown("Zet je long-form video om in een viraal Short script.")
    
    transcript = st.text_area("Plak hier je onbewerkte video transcript:", height=250)
    
    if st.button("🚀 Genereer Script", type="primary", use_container_width=True):
        if not transcript:
            st.warning("⚠️ Plak een transcript om te beginnen.")
        else:
            with st.spinner("AI is het script aan het schrijven..."):
                try:
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
                    
                    # Sla op in geheugen
                    st.session_state.script_data = json.loads(response.choices[0].message.content)
                    
                    # Bouw de voice-over tekst direct op
                    st.session_state.full_text_to_speak = ""
                    for key, content in st.session_state.script_data.items():
                        st.session_state.full_text_to_speak += content.get('text', '') + " "
                    
                    st.success("✅ Script succesvol gegenereerd! Klik op 'Script to Voice Over' in de zijbalk om verder te gaan.")
                except Exception as e:
                    st.error(f"Er is een fout opgetreden: {e}")

    # Weergave als er een script is
    if st.session_state.script_data:
        st.divider()
        st.subheader("Jouw Script")
        for section, content in st.session_state.script_data.items():
            timestamp = content.get('timestamp', '00:00')
            text = content.get('text', '')
            formatted_title = section.replace("_", " ").upper()
            
            st.markdown(f"**<span style='color:#FF4B4B'>{formatted_title} ({timestamp})</span>:**", unsafe_allow_html=True)
            st.write(text)

# --- SCHERM 2: SCRIPT TO VOICE OVER ---
elif menu_keuze == "🎙️ Script to Voice Over":
    st.header("🎙️ Script to Voice Over")
    st.markdown("Genereer de audio in rapid-fire tempo (zonder stiltes).")
    
    # We geven de gebruiker een tekstvak waar de gegenereerde tekst in staat. 
    # Zo kunnen ze eventueel nog handmatig iets aanpassen voor het inspreken!
    te_spreken_tekst = st.text_area(
        "Tekst voor ElevenLabs (pas aan indien nodig):", 
        value=st.session_state.full_text_to_speak.strip(), 
        height=200
    )
    
    if st.button("🎙️ Maak Voice-over & Verwijder Stiltes", type="primary", use_container_width=True):
        if not te_spreken_tekst:
            st.warning("⚠️ Er is geen tekst om in te spreken. Genereer eerst een script of typ hierboven tekst.")
        else:
            with st.spinner("ElevenLabs is aan het inspreken en de AI knipt de stiltes weg..."):
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
                
                headers = {
                    "Accept": "audio/mpeg",
                    "Content-Type": "application/json",
                    "xi-api-key": elevenlabs_api_key
                }
                
                data = {
                    "text": te_spreken_tekst,
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
                        
                        # Audio bewerking met Pydub
                        audio_segment = AudioSegment.from_file(io.BytesIO(ruwe_audio_bytes), format="mp3")
                        chunks = split_on_silence(
                            audio_segment,
                            min_silence_len=150,     
                            silence_thresh=-40,      
                            keep_silence=20          
                        )
                        
                        bewerkte_audio = AudioSegment.empty()
                        for chunk in chunks:
                            bewerkte_audio += chunk
                            
                        buffer = io.BytesIO()
                        bewerkte_audio.export(buffer, format="mp3")
                        finale_audio_bytes = buffer.getvalue()

                        st.success("✅ Audio succesvol gegenereerd en stiltes verwijderd!")
                        st.audio(finale_audio_bytes, format='audio/mp3')
                        
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