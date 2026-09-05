import streamlit as st
import openai
import json
import requests
import io
from pydub import AudioSegment
from pydub.silence import split_on_silence

# Pagina configuratie
st.set_page_config(page_title="JackCraig Script Builder", layout="wide")

# Initializeer session state variabelen voor MEERDERE scripts
if "scripts_list" not in st.session_state:
    st.session_state.scripts_list = []

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
    st.markdown("Multi-Script & Voice Builder")
    st.divider()
    
    menu_keuze = st.radio(
        "Navigatie", 
        ["📝 Transcript to Scripts", "🎙️ Script to Voice Over"],
        label_visibility="collapsed"
    )
    
    st.divider()
    st.caption("✅ API Keys Actief")

# De System Prompt (Aangepast voor MAXIMALE KWALITEIT & STORYTELLING)
system_prompt = """
You are a highly-paid, master YouTube Shorts copywriter. Your goal is to review a long-form video transcript and extract ONLY the top 2 or 3 absolute best, most dramatic, and visually interesting experiments/stories. IGNORE boring, short, or mundane segments.

You are a STORYTELLER, not a summarizer. You must dramatize the events, use highly descriptive language, and build intense tension. Do not just write instructions; write a gripping narrative.
You MUST output the scripts in ENGLISH.

Structure for EACH of your chosen top-tier scripts:
- HOOK: One powerful, extreme sentence as a question. Create a massive 'curiosity gap'.
- RISING_ACTION_1: 3 to 5 highly descriptive sentences. Dramatize the setup. Explain the impossible goal and the massive scale. Build up the stakes.
- CONFLICT: 2 to 3 sentences. The devastating plot twist. What went horribly wrong? Make the viewer feel like the experiment is ruined.
- COMEBACK: 1 to 2 sentences. The genius pivot. How does the creator desperately try to save it?
- RISING_ACTION_2: 1 to 2 sentences. The intense build-up to the final moment.
- PAYOFF: 1 to 2 sentences. The highly satisfying, mind-blowing result, preferably with a punchline.

Output STRICTLY as a JSON object containing a SINGLE key called "scripts". The value of "scripts" MUST be an array of objects.
Each object must have:
- "title": A catchy, viral title for this specific script.
- "hook", "rising_action_1", "conflict", "comeback", "rising_action_2", "payoff".

Each of the 6 story keys MUST contain a nested object with exactly two strings: "timestamp" (e.g. "01:30") and "text" (the actual script line).
"""
# --- SCHERM 1: TRANSCRIPT TO SCRIPT ---
if menu_keuze == "📝 Transcript to Scripts":
    st.header("📝 Transcript to Scripts")
    st.markdown("Plak een gigantisch transcript en laat de AI er meerdere Shorts uithalen.")
    
    transcript = st.text_area("Plak hier je onbewerkte video transcript:", height=250)
    
    if st.button("🚀 Genereer Scripts", type="primary", use_container_width=True):
        if not transcript:
            st.warning("⚠️ Plak een transcript om te beginnen.")
        else:
            with st.spinner("AI analyseert de tekst en schrijft meerdere scripts..."):
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
                    
                    # Sla de array met scripts op in het geheugen
                    json_response = json.loads(response.choices[0].message.content)
                    st.session_state.scripts_list = json_response.get("scripts", [])
                    
                    st.success(f"✅ {len(st.session_state.scripts_list)} Scripts succesvol gegenereerd! Klik op 'Script to Voice Over' om ze in te spreken.")
                except Exception as e:
                    st.error(f"Er is een fout opgetreden: {e}")

    # Weergave als er scripts zijn
    if st.session_state.scripts_list:
        st.divider()
        st.subheader(f"Jouw Gegenereerde Scripts ({len(st.session_state.scripts_list)})")
        
        for idx, script in enumerate(st.session_state.scripts_list):
            title = script.get("title", f"Script {idx + 1}")
            with st.expander(f"🎬 {title}", expanded=False):
                for section in ["hook", "rising_action_1", "conflict", "comeback", "rising_action_2", "payoff"]:
                    content = script.get(section, {})
                    timestamp = content.get('timestamp', '00:00')
                    text = content.get('text', '')
                    formatted_title = section.replace("_", " ").upper()
                    
                    st.markdown(f"**<span style='color:#FF4B4B'>{formatted_title} ({timestamp})</span>:**", unsafe_allow_html=True)
                    st.write(text)

# --- SCHERM 2: SCRIPT TO VOICE OVER ---
elif menu_keuze == "🎙️ Script to Voice Over":
    st.header("🎙️ Script to Voice Over")
    st.markdown("Kies een script en genereer de audio in rapid-fire tempo.")
    
    if not st.session_state.scripts_list:
        st.info("Je hebt nog geen scripts gegenereerd. Ga naar het eerste tabblad om te beginnen.")
    else:
        # Maak een lijst met titels voor de dropdown
        script_titles = [s.get("title", f"Script {i+1}") for i, s in enumerate(st.session_state.scripts_list)]
        geselecteerde_titel = st.selectbox("Kies het script dat je wilt inspreken:", script_titles)
        
        # Vind het bijbehorende script in het geheugen
        huidig_script = next(s for s in st.session_state.scripts_list if s.get("title") == geselecteerde_titel)
        
        # Voeg alle tekst uit het gekozen script samen
        full_text_to_speak = ""
        for section in ["hook", "rising_action_1", "conflict", "comeback", "rising_action_2", "payoff"]:
            full_text_to_speak += huidig_script.get(section, {}).get("text", "") + " "
        
        te_spreken_tekst = st.text_area(
            "Tekst voor ElevenLabs (pas aan indien nodig):", 
            value=full_text_to_speak.strip(), 
            height=200
        )
        
        if st.button("🎙️ Maak Voice-over & Verwijder Stiltes", type="primary", use_container_width=True):
            if not te_spreken_tekst:
                st.warning("⚠️ Er is geen tekst om in te spreken.")
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
                                file_name=f"jackcraig_{geselecteerde_titel.replace(' ', '_').lower()}.mp3",
                                mime="audio/mpeg",
                                use_container_width=True
                            )
                        else:
                            st.error(f"ElevenLabs Error: {el_response.text}")
                    except Exception as e:
                        st.error(f"Fout bij het verwerken van de audio: {e}")