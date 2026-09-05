import streamlit as st
import openai
import json

# Pagina configuratie
st.set_page_config(page_title="JackCraig Script Builder", layout="wide")

st.title("🎬 JackCraig Script Builder")
st.markdown("Zet long-form transcripts om in strakke, virale Shorts scripts. Altijd in het Engels, perfect gestructureerd voor ElevenLabs voice-overs.")

# Sidebar voor API keys
with st.sidebar:
    st.header("⚙️ Instellingen")
    openai_api_key = st.text_input("OpenAI API Key", type="password")
    st.markdown("Zorg dat je model toegang heeft tot JSON mode (bijv. `gpt-4o` of `gpt-3.5-turbo`).")

# Hoofdvenster voor input
transcript = st.text_area("📝 Plak hier je onbewerkte video transcript:", height=300)

# De System Prompt gebaseerd op onze regels
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
                # OpenAI API Call met JSON mode
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
                
                # Parse de JSON output
                script_data = json.loads(response.choices[0].message.content)
                
                st.success("✅ Script succesvol gegenereerd!")
                
                # Weergave in de UI
                st.markdown("### Jouw Script:")
                
                # Een visueel aantrekkelijke weergave van de secties
                for section, content in script_data.items():
                    timestamp = content.get('timestamp', '00:00')
                    text = content.get('text', '')
                    formatted_title = section.replace("_", " ").upper()
                    
                    st.markdown(f"**<span style='color:#FF4B4B'>{formatted_title} ({timestamp})</span>:**", unsafe_allow_html=True)
                    st.write(text)
                    st.divider()
                
                # Uitklapbaar blok met de ruwe JSON (handig voor debugging of kopiëren)
                with st.expander("Bekijk ruwe JSON data (voor API/Voice-over integratie)"):
                    st.json(script_data)

            except Exception as e:
                st.error(f"Er is een fout opgetreden: {e}")