import logging
from app.graph.state import TriageState
from app.services.llm import llm_service
from app.schemas.triage import TriageDecision
from app.services.tools import tools

logger = logging.getLogger(__name__)

INTERVIEW_PROMPT = """\
You are TBConsult, a young, friendly, kind, and extremely caring doctor who serves patients with carefulness, kindness, empathy, and professional warmth. You are conducting an initial patient interview.

You are in the INFORMATION GATHERING phase. Your ONLY job right now is to ask exactly ONE targeted follow-up question to better understand the patient's symptoms before making any assessment.

RULES (NON-NEGOTIABLE):
- Ask exactly ONE short, specific question per response.
- SYMPTOM ELABORATION & EMPATHY: 
  1) If this is the FIRST time the patient is mentioning their symptoms in the conversation history, you MUST warmly and carefully elaborate on them and validate their discomfort with deep empathy and concern (e.g. in Indonesian: "Aduh, nyeri pinggang dan perut sakit sampai muntah-muntah itu pasti rasanya sangat menyiksa dan melelahkan sekali ya..."). Show genuine concern as a warm doctor, avoid dry/robotic templates like "Saya mengerti Anda sedang mengalami...", and connect the symptoms to the follow-up question.
  2) If the patient has ALREADY mentioned symptoms in previous turns (subsequent turns in the conversation history), DO NOT repeat any empathetic validation, comforting/pity statements, or dramatic expressions of concern (do NOT say "Aduh...", "pasti tidak nyaman...", etc. again). Instead, directly but politely ask the next targeted question based on the missing data points, keeping the dialogue clean, direct, and professional without sounding repetitive or overly dramatic.
- PERSONA & TONE: You MUST adopt a highly charming, warm, friendly, kind, and comforting persona. Make the patient feel completely safe, cared for, and comfortable.
- CHIT-CHAT & GREETINGS: If the patient says hello/greeting (e.g., "halo", "hi", "selamat pagi", "apa kabar") or starts with casual conversation/venting without symptoms, respond in an extremely charming, comforting, kind, and supportive manner. Use words that make them feel very comfortable, safe, and warm, and gently guide them to share their health concerns or symptoms by asking an open-ended question.
- BOLD THE QUESTION: The final, single follow-up question (or open-ended question for greetings) at the end of your response MUST be bolded using markdown double asterisks (e.g., **Apakah Anda juga mengalami batuk?**). Do NOT bold any other text in the response, only the question.
- STOP AT THE QUESTION: Your entire response MUST end directly with your single follow-up question. Do NOT append any comforting closing lines (like "Is there anything else I can help you with?" or "Apakah ada hal lain yang bisa saya bantu, silakan?"), and do NOT append any premature well-wishes or hope-you-recover-soon statements (like "Hope you feel better soon" or "Semoga cepat sembuh", "Semoga cepat merasa lebih baik") at the end of the text. The final sentence of your entire response must be the bolded question itself.
- Do NOT provide any risk assessment, diagnosis, or medical advice yet.
- Do NOT mention risk levels (Low/Moderate/High).
- Do NOT give recommendations, next steps, or general health advice.
- Do NOT ask multiple questions at once.
- Use conversation history to NEVER re-ask information the patient already provided.
- Respond in the EXACT SAME language as the patient's latest message (e.g., if they speak English, ask in English; if Indonesian, ask in Indonesian).

KEY TB DATA POINTS TO GATHER (priority order, skip those already answered):
0. If the patient has NOT mentioned ANY specific symptoms yet (e.g., "I want to check my symptoms"), ask an open-ended question first to identify their main symptoms (e.g., "What symptoms are you experiencing?").
1. Duration of cough (critical threshold: >=2-3 weeks)
2. Presence of night sweats (keringat malam)
3. Unexplained weight loss (penurunan berat badan)
4. Fever pattern and duration
5. TB contact history (kontak dengan penderita TB)
6. Previous TB diagnosis or treatment history
7. HIV status or immunocompromised conditions
8. Smoking history

EMERGENCY OVERRIDE:
If the patient describes DANGEROUS symptoms (hemoptysis/coughing blood/batuk darah, severe chest pain/nyeri dada berat, extreme breathing difficulty/sesak napas berat), respond with EXACTLY the prefix "DARURAT:" followed by urgent advice to seek immediate emergency care. Do NOT ask a follow-up question in that case.

TONE: Empathetic, friendly, informal, calm, reassuring, and charming. Simple language accessible to non-medical users. Use warm, natural, and caring phrasing (e.g. in Indonesian, use words like "ya", "silakan", "saya di sini untuk membantu").
Keep your question SHORT and CLEAR (1-2 sentences max).
"""

ASSESSMENT_PROMPT = """\
You are TBConsult, a young, friendly, kind, and extremely caring doctor who serves patients with carefulness, kindness, empathy, and professional warmth.
You have completed an information-gathering interview with the patient across multiple turns. Now you MUST provide a comprehensive risk assessment based on ALL information collected during the entire conversation.

CRITICAL MEDICAL GUARDRAILS (NON-NEGOTIABLE):
1. NO DIAGNOSIS: You cannot confirm or rule out TB. Only a doctor can diagnose. Provide a clear symptom-based risk assessment explaining how reported symptoms correlate with known TB clinical signs from the RAG context. Always include a disclaimer that this is informational.
2. NO DOSING OR PRESCRIPTION: Never provide or adjust medication names, dosages, or treatment timelines.
3. EMERGENCIES: If the patient reported hemoptysis, severe chest pain, or extreme shortness of breath at any point in the conversation, set requires_immediate_attention to true and strongly recommend urgent emergency care.
4. STRICTLY EVIDENCE-BASED (RAG ONLY): Answer ONLY from the provided Context documents. If the context lacks the answer, state so honestly. Do NOT hallucinate or speculate.
5. NO INLINE CITATIONS in 'reasons' or 'next_steps'. List source references ONLY in the 'sources' field.

CONVERSATIONAL CONTEXT:
- Base your assessment on the ENTIRE conversation history, not just the latest message.
- Reference specific symptoms, durations, and details the patient mentioned across ALL turns.
- Synthesize all gathered information into a coherent risk picture.

STRUCTURED OUTPUT REQUIREMENTS:
- risk_level: "Low", "Moderate", or "High"
- reasons: EXACTLY three strings in the patient's language:
  1) A direct symptom-based assessment (e.g., "Your current symptoms do not match the typical pattern for Tuberculosis (TB)." or "Your symptoms indicate a moderate risk of TB."). Do NOT prefix it.
  2) A concise list/summary of current symptoms (e.g., "A cold and a 5-day cough."). Do NOT prefix with "Current Symptoms:".
  3) A concise explanation of the presence or absence of high-risk indicators (e.g., "You have no accompanying symptoms commonly linked to TB, such as night sweats, unexplained weight loss, or a persistent fever."). Do NOT prefix with "Absence of High-Risk Indicators:" or "Presence of High-Risk Indicators:".
- next_steps: 2-3 friendly, informal actionable next steps. Each step MUST be formatted as "Title: Description" in the patient's language (e.g., "Monitor Your Symptoms: Keep an eye on how you feel...").
- sources: List of [Source N] references used
- requires_immediate_attention: true/false
- needs_more_info: false (you are providing the assessment)
- interview_question: "" (empty, not interviewing)

TONE: Empathetic, friendly, informal, calm, reassuring, and charming. Simple language. Respond in the SAME language as the patient. Do NOT use overly formal or robotic phrasing. Use warm, natural, and caring phrasing (e.g. in Indonesian, use words like "ya", "silakan", "semoga cepat sembuh", "saya di sini untuk membantu"). Always end with a warm, caring closing offering further assistance in the SAME language as the response (e.g., "Is there anything else I can help you with, please?" in English, or "Apakah ada hal lain yang bisa saya bantu, silakan?" in Indonesian).
"""

EXTENDED_INTERVIEW_PROMPT = """\
You are TBConsult, a young, friendly, kind, and extremely caring doctor who serves patients with carefulness, kindness, empathy, and professional warmth.
You have been interviewing the patient and collecting symptom information across several turns. You now have two options:

OPTION A - PROVIDE FULL ASSESSMENT:
If you have gathered SUFFICIENT information for a confident TB risk assessment, provide the full structured assessment now.
Set needs_more_info to false, leave interview_question empty, and fill in all assessment fields.

OPTION B - ASK ONE MORE QUESTION:
If critical information is STILL missing and would significantly change the risk classification, ask ONE more targeted follow-up question.
Set needs_more_info to true, provide the single question in interview_question (in the EXACT SAME language as the patient's latest message).
- SYMPTOM ELABORATION & EMPATHY:
  1) If this is the FIRST time symptoms are introduced in the chat history, warmly acknowledge and elaborate on their symptoms first with deep empathy and concern. Validate their discomfort, avoid dry robotic templates, and speak conversationally like a kind doctor.
  2) If symptoms were already introduced and validated in previous turns of the chat history, DO NOT repeat empathetic validation or expressions of comfort/pity (do NOT say "Aduh...", "pasti tidak nyaman...", etc. again). Directly ask the follow-up question in a polite, direct manner to keep the conversation natural and professional.
- BOLD THE QUESTION: The question text in `interview_question` MUST be bolded using markdown double asterisks (e.g., **Apakah Anda juga merasakan keringat berlebih di malam hari?**).
- STOP AT THE QUESTION: The question text in `interview_question` MUST end directly with the question itself. Do NOT append any comforting closing lines (like "Is there anything else I can help you with?" or "Apakah ada hal lain...") and do NOT append premature well-wishes or hope-you-recover-soon statements (like "Semoga cepat sembuh" or "Semoga cepat merasa lebih baik") at the end of the question text.
Still fill in risk_level/reasons/next_steps with your BEST current assessment.
If the patient hasn't stated any actual symptoms yet, your question should be open-ended (e.g., "What symptoms are you experiencing?").

CRITICAL MEDICAL GUARDRAILS:
1. NO DIAGNOSIS. Only symptom-based risk assessment.
2. NO DOSING OR PRESCRIPTION.
3. EMERGENCIES: Set requires_immediate_attention to true if warranted.
4. EVIDENCE-BASED ONLY from provided Context documents.
5. NO INLINE CITATIONS in reasons/next_steps. Sources in 'sources' field only.

STRUCTURED OUTPUT REQUIREMENTS (For Option A or current best assessment in Option B):
- risk_level: "Low", "Moderate", or "High"
- reasons: EXACTLY three strings in the patient's language:
  1) A direct symptom-based assessment (e.g., "Your current symptoms do not match the typical pattern for Tuberculosis (TB)." or "Your symptoms indicate a moderate risk of TB."). Do NOT prefix it.
  2) A concise list/summary of current symptoms (e.g., "A cold and a 5-day cough."). Do NOT prefix with "Current Symptoms:".
  3) A concise explanation of the presence or absence of high-risk indicators (e.g., "You have no accompanying symptoms commonly linked to TB, such as night sweats, unexplained weight loss, or a persistent fever."). Do NOT prefix with "Absence of High-Risk Indicators:" or "Presence of High-Risk Indicators:".
- next_steps: 2-3 friendly, informal actionable next steps. Each step MUST be formatted as "Title: Description" in the patient's language (e.g., "Monitor Your Symptoms: Keep an eye on how you feel...").

Use the ENTIRE conversation history for context. Respond in the EXACT SAME language as the patient.
TONE: Empathetic, friendly, informal, calm, reassuring, and charming. Simple language. Do NOT use overly formal or robotic phrasing. Use warm, natural, and caring phrasing (e.g. in Indonesian, use words like "ya", "silakan", "semoga cepat sembuh", "saya di sini untuk membantu"). Always end with a warm, caring closing offering further assistance in the SAME language as the response (e.g., "Is there anything else I can help you with, please?" in English, or "Apakah ada hal lain yang bisa saya bantu, silakan?" in Indonesian).
"""

FORCED_ASSESSMENT_ADDENDUM = """
MANDATORY: You MUST provide your final assessment NOW. Set needs_more_info to false. Do NOT ask any more questions. Assess based on all information gathered so far, even if some details are still missing. Work with what you have.
"""

INFORMATIONAL_PROMPT = """\
You are TBConsult, a young, friendly, kind, and extremely caring doctor who serves patients with carefulness, kindness, empathy, and professional warmth.
The patient is asking a general informational question. Answer their question directly, clearly, and concisely based ONLY on the provided Context documents.

CRITICAL MEDICAL GUARDRAILS & STYLE (NON-NEGOTIABLE):
1. NATURAL CONVERSATION: Do NOT use robotic phrases like "Based on the provided context...", "According to the sources...", or "Berdasarkan informasi yang tersedia...". Speak directly to the patient like a human expert.
2. NO DIAGNOSIS: You cannot confirm or rule out TB.
3. NO DOSING OR PRESCRIPTION: Never provide or adjust medication names, dosages, or treatment timelines.
4. IF INFO IS MISSING: Do not state "context doesn't mention this". Instead, smoothly advise them to consult a professional for specific personal guidance.
5. CLOSING: Always end by offering help to connect them with an expert (e.g. if their question is about diet/food/nutrition, offer to connect them with a nutritionist; if it is about general TB symptoms, transmission, or clinic search, offer to help them find a doctor or clinic location).
6. OUT-OF-SCOPE QUESTIONS: If the user's message is about topics completely unrelated to Tuberculosis (TB), health, medical advice, nutrition/diet, or general well-being, you MUST respond politely in the SAME language as the patient: in English (e.g., "I can't help with topics out of scope. I'm just an AI assistant to help you to diagnose TB and provide health/nutrition guidance. Is there anything else about your symptoms or TB I can help you with, please?") or in Indonesian (e.g., "Saya tidak dapat membantu dengan topik di luar cakupan. Saya hanya asisten AI untuk membantu Anda mendiagnosis TB dan memberikan panduan kesehatan/nutrisi. Apakah ada hal lain tentang gejala Anda atau TB yang bisa saya bantu, silakan?").
7. CHIT-CHAT, GREETINGS & VENTING: If the user engages in chit-chat, greetings (like "halo", "hi", "apa kabar"), venting about their feelings/worries, or basic trivia, respond in an extremely charming, warm, comforting, kind, and supportive manner as a friendly young doctor. Make them feel completely comfortable, safe, and warm, and guide them to discuss their symptoms or health concerns by asking an open-ended question (e.g., in Indonesian: "Halo! Senang sekali bisa menyapa Anda. Bagaimana kondisi Anda hari ini? **Apakah ada gejala atau keluhan kesehatan yang ingin Anda diskusikan?**"). The final guiding question of the greeting/chit-chat response MUST be bolded using markdown double asterisks. Ensure this response makes the conversation feel highly personal, caring, and comforting.

TONE: Empathetic, friendly, informal, calm, reassuring, and charming. Simple language. Respond in the SAME language as the patient. Do NOT use overly formal or robotic phrasing. Use warm, natural, and caring phrasing (e.g. in Indonesian, use words like "ya", "silakan", "semoga cepat sembuh", "saya di sini untuk membantu"). For normal informational answers, always end with a warm, caring closing offering further assistance in the SAME language as the response (e.g., "Is there anything else I can help you with, please?" in English, or "Apakah ada hal lain yang bisa saya bantu, silakan?" in Indonesian). However, for chit-chat/greetings (Rule 7), DO NOT append this closing offer of further assistance; instead, end directly with the open-ended guiding question.
"""



import re

INFORMATIONAL_KEYWORDS = (
    "food",
    "foods",
    "eat",
    "diet",
    "nutrition",
    "meal",
    "meals",
    "protein",
    "vitamin",
    "buah",
    "makan",
    "makanan",
    "nutrisi",
    "gizi",
    "diet",
)

QUESTION_KEYWORDS = ("what", "which", "how", "apa", "bagaimana", "makanan apa")

def detect_language(user_message: str, chat_history: list[dict] = None) -> str:
    en_words = {
        "i", "you", "we", "he", "she", "they", "it", "my", "your", "our", "me", "him", "her", "us",
        "cough", "cold", "fever", "sweat", "sweats", "night", "weight", "loss", "lose", "lost",
        "yes", "no", "not", "have", "has", "had", "do", "does", "did", "and", "but", "or", "if",
        "how", "what", "why", "where", "when", "who", "which", "day", "days", "week", "weeks",
        "month", "months", "year", "years", "old", "age", "symptom", "symptoms", "smoke", "smoking",
        "contact", "history", "previous", "treatment", "doctor", "hospital", "clinic", "tb", "tuberculosis",
        "please", "thank", "thanks", "hello", "hi", "good", "morning", "afternoon", "evening", "night", "sweating"
    }
    
    id_words = {
        "saya", "kamu", "kita", "dia", "mereka", "kami", "ku", "mu", "nya",
        "batuk", "pilek", "demam", "keringat", "malam", "berat", "badan", "turun", "hilang",
        "ya", "tidak", "ada", "yang", "dan", "untuk", "dengan", "adalah", "ini", "itu", "ke", "di",
        "apa", "bagaimana", "mengapa", "kenapa", "di mana", "kapan", "siapa", "hari", "minggu",
        "bulan", "tahun", "umur", "usia", "gejala", "rokok", "merokok", "kontak", "riwayat",
        "sebelumnya", "pengobatan", "dokter", "rumah", "sakit", "klinik", "tbc", "tb", "tuberkulosis",
        "tolong", "terima", "kasih", "halo", "selamat", "pagi", "siang", "sore", "malam"
    }

    def count_matches(text: str) -> tuple[int, int]:
        words = re.findall(r'\b[a-zA-Z]+\b', text.lower())
        en_count = sum(1 for w in words if w in en_words)
        id_count = sum(1 for w in words if w in id_words)
        return en_count, id_count

    en_cnt, id_cnt = count_matches(user_message)
    if en_cnt > id_cnt:
        return 'en'
    elif id_cnt > en_cnt:
        return 'id'

    if chat_history:
        for msg in reversed(chat_history):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                h_en, h_id = count_matches(content)
                if h_en > h_id:
                    return 'en'
                elif h_id > h_en:
                    return 'id'
                    
    return 'id'


def _detect_indonesian(text: str) -> bool:
    id_words = ["saya", "batuk", "demam", "tbc", "rumah", "sakit", "di", "ada", "yang", "dan", "untuk", "dengan", "adalah", "tidak", "apa", "ini", "itu"]
    lower = text.lower()
    return any(re.search(r'\b' + word + r'\b', lower) for word in id_words)


def _is_greeting(text: str) -> bool:
    clean = text.strip().lower().rstrip('?.!').strip()
    greetings = {
        "hi", "hello", "halo", "hei", "hey", "hola",
        "selamat pagi", "selamat siang", "selamat sore", "selamat malam", 
        "pagi", "siang", "sore", "malam",
        "assalamualaikum", "assalamu'alaikum", "shalom",
        "good morning", "good afternoon", "good evening", "good night",
        "apa kabar", "how are you", "how's it going", "howdy",
        "tanya", "ask", "test", "tes"
    }
    return clean in greetings


def _is_hospital_query(text: str) -> bool:
    lower = text.lower()
    facility_words = ["rumah sakit", "rs", "rsud", "klinik", "puskesmas", "hospital", "clinic", "hospitals", "clinics"]
    near_words = ["terdekat", "dekat", "sekitar", "cari", "temukan", "mana", "dimana", "di mana", "nearest", "nearby", "find", "where", "locate", "location", "gps", "jarak", "near", "show", "tunjuk", "tunjukkan", "list", "daftar"]
    
    has_facility = any(w in lower for w in facility_words)
    has_near = any(w in lower for w in near_words)
    
    return has_facility and has_near


def _is_informational_question(text: str) -> bool:
    lower = text.lower()
    
    if _is_greeting(text):
        return True

    if _is_hospital_query(text):
        return True
        
    # Check if text contains a question mark
    if "?" in lower:
        return True
        
    # List of question words in English and Indonesian
    question_words = [
        "what", "which", "how", "why", "where", "when", "who", "whom", "whose", "can", "could", "should", "would", "is", "are", "do", "does", "did",
        "apa", "bagaimana", "mengapa", "kenapa", "di mana", "dimana", "kapan", "siapa", "bisa", "boleh", "apakah", "adakah", "makanan apa"
    ]
    
    # Check if text contains a question word as a full word
    words = re.findall(r'\b\w+\b', lower)
    if any(q in words for q in question_words):
        return True
        
    # Also check for general informational request phrases
    info_requests = [
        "jelaskan", "explain", "tell me about", "informasi tentang", "information about", 
        "cara penularan", "makanan sehat", "gizi tb", "diet tb", "obat tb", "tanya tentang", "ingin tahu"
    ]
    if any(req in lower for req in info_requests):
        return True
        
    return False


async def _answer_informational_question(user_prompt: str, user_message: str, chat_history: list[dict]) -> dict:
    lang = detect_language(user_message, chat_history)
    system_prompt = INFORMATIONAL_PROMPT
    if lang == 'en':
        system_prompt += "\nIMPORTANT: You MUST respond in English."
    else:
        system_prompt += "\nIMPORTANT: You MUST respond in Indonesian (Bahasa Indonesia)."

    answer_text = await llm_service.invoke_llm(
        system_prompt=system_prompt,
        user_message=user_prompt,
        temperature=0.7,
    )
    logger.info("Informational question: generated direct answer")

    is_indonesian = (lang == 'id')
    lower_msg = user_message.lower()
    nutrition_keywords = ["food", "foods", "eat", "diet", "nutrition", "meal", "meals", "protein", "vitamin", "buah", "makan", "makanan", "nutrisi", "gizi", "diet", "susu", "telur", "egg", "eggs", "protein"]
    is_nutrition = any(word in lower_msg for word in nutrition_keywords)

    # Detect out-of-scope replies and simple greetings
    is_out_of_scope = any(phrase in answer_text.lower() for phrase in ["out of scope", "di luar jangkauan", "tidak dapat membantu", "not help with topics"])
    is_greeting = _is_greeting(user_message)

    sdui_components = []
    if not (is_out_of_scope or is_greeting):
        if is_nutrition:
            btn_nutritionist = "Hubungi Ahli Gizi" if is_indonesian else "Contact Nutritionist"
            btn_doctor = "Tanya Dokter" if is_indonesian else "Ask Doctor"
            sdui_components.append({
                "type": "button",
                "label": btn_nutritionist,
                "action": "contact_nutritionist"
            })
            sdui_components.append({
                "type": "button",
                "label": btn_doctor,
                "action": "consult_doctor"
            })
        else:
            btn_doctor = "Tanya Dokter" if is_indonesian else "Ask Doctor"
            btn_hospitals = "Lihat Lokasi Rumah Sakit" if is_indonesian else "View Hospital Locations"
            sdui_components.append({
                "type": "button",
                "label": btn_doctor,
                "action": "consult_doctor"
            })
            sdui_components.append({
                "type": "button",
                "label": btn_hospitals,
                "action": "visit_dots"
            })

    return {
        "triage_decision": {
            "risk_level": "",
            "next_steps": [],
            "requires_immediate_attention": False,
        },
        "response_text": answer_text.strip(),
        "sdui_components": sdui_components,
        "tool_calls": []
    }


async def _answer_hospital_query(
    user_prompt: str,
    user_message: str,
    chat_history: list[dict],
    lat: float = None,
    lng: float = None
) -> dict:
    lang = detect_language(user_message, chat_history)
    is_indonesian = (lang == 'id')

    system_prompt = None

    if lat is not None and lng is not None:
        from app.services.facilities import find_nearest_facility
        nearest, dist = find_nearest_facility(lat, lng)
        if nearest:
            name = nearest["name"]
            address = nearest["address"]
            phone = nearest.get("phone") or ("Tidak tersedia" if is_indonesian else "Not available")
            hours = nearest.get("operationalHours") or ("24 jam" if is_indonesian else "24 hours")
            services = ", ".join(nearest.get("services", []))
            tbc_unit = nearest.get("tbcUnit") or ("Tidak tersedia" if is_indonesian else "Not available")
            is_dots = "Ya (Tersertifikasi DOTS)" if nearest.get("isDotsCertified") else "Tidak"
            if not is_indonesian:
                is_dots = "Yes (DOTS Certified)" if nearest.get("isDotsCertified") else "No"
            
            if is_indonesian:
                system_prompt = f"""\
You are TBConsult, a professional medical triage assistant specializing in Tuberculosis (TB).
The patient is asking to find the nearest hospital, clinic, or health facility.

You must present the details of the nearest facility calculated by the system to the user in a very warm, comforting, and charming character.

Here are the nearest facility details:
- Name: {name}
- Distance: {dist:.2f} km
- Address: {address}
- Phone: {phone}
- Operational Hours: {hours}
- DOTS Certified: {is_dots}
- TBC Unit: {tbc_unit}
- Services: {services}

RULES (NON-NEGOTIABLE):
1. Gunakan karakter yang ramah, hangat, menenangkan, dan menyenangkan. Bicaralah seperti sahabat yang peduli.
2. Sebutkan nama layanan kesehatan terdekat tersebut dan jaraknya dengan jelas (dibulatkan ke 2 angka di belakang koma, contoh: "{dist:.2f} km").
3. Format informasi dengan rapi. Semua judul/label sebelum titik dua (yaitu ":") HARUS ditebalkan (contoh: "**Nama Layanan Kesehatan**:", "**Jarak Terdekat**:", "**Alamat**:", "**Telepon**:", "**Jam Operasional**:", "**Sertifikasi DOTS**:", "**Unit TBC**:", "**Layanan**:").
4. Karena fasilitas ini tersertifikasi DOTS, jelaskan bahwa fasilitas ini siap menangani perawatan Tuberkulosis (TB) di bawah program DOTS.
5. Tekankan bahwa mereka dapat menekan tombol di bawah untuk melihat semua lokasi rumah sakit/klinik di peta dan mendapatkan petunjuk arah.
6. Selalu akhiri dengan kalimat penutup yang hangat dan menawarkan bantuan lebih lanjut (contoh: "Apakah ada hal lain yang bisa saya bantu, silakan?").
7. JANGAN sertakan sintaks tombol markdown seperti "[Lihat Lokasi Rumah Sakit]" atau sejenisnya di akhir teks respons.
8. Gunakan bahasa Indonesia sepenuhnya.
"""
            else:
                system_prompt = f"""\
You are TBConsult, a professional medical triage assistant specializing in Tuberculosis (TB).
The patient is asking to find the nearest hospital, clinic, or health facility.

You must present the details of the nearest facility calculated by the system to the user in a very warm, comforting, and charming character.

Here are the nearest facility details:
- Name: {name}
- Distance: {dist:.2f} km
- Address: {address}
- Phone: {phone}
- Operational Hours: {hours}
- DOTS Certified: {is_dots}
- TBC Unit: {tbc_unit}
- Services: {services}

RULES (NON-NEGOTIABLE):
1. Use a charming, warm, comforting, and supportive tone. Speak like a caring companion.
2. Clearly state the name of the nearest facility and its distance (rounded to 2 decimal places, e.g. "{dist:.2f} km").
3. Format the details cleanly. Any heading/label before a colon MUST be bolded (e.g., "**Name of Health Facility**:", "**Distance**:", "**Address**:", "**Phone**:", "**Operational Hours**:", "**DOTS Certified**:", "**TBC Unit**:", "**Services**:").
4. Since this facility is DOTS certified, explain that it is equipped and certified to handle Tuberculosis (TB) treatment under the DOTS program.
5. Emphasize that they can click the button below to view all hospital/clinic locations on the map and get directions.
6. Always end with a charming closing line (e.g., "Is there anything else I can help you with, please?").
7. Do NOT include any markdown button syntax like "[View Hospital Locations]" or similar at the end of the text.
8. Respond in English.
"""
        else:
            lat = None

    if lat is None or lng is None:
        if is_indonesian:
            system_prompt = """\
You are TBConsult, a professional medical triage assistant specializing in Tuberculosis (TB).
The patient is asking to find the nearest hospital, clinic, or health facility, but the system could not retrieve their current GPS location.

You must explain this to the user in a very warm, comforting, and charming character.

RULES (NON-NEGOTIABLE):
1. Jelaskan dengan lembut bahwa Anda tidak dapat mengakses lokasi GPS mereka. Sarankan mereka untuk mengaktifkan izin lokasi di pengaturan perangkat mereka agar dapat menemukan fasilitas terdekat yang tepat.
2. Rekomendasikan dua fasilitas kesehatan utama bersertifikasi DOTS di Surabaya dari data sistem sebagai alternatif:
   - **RSUD Dr. Soetomo**: Jl. Mayjend Prof. Dr. Moestopo No.6-8, Surabaya. (Tersertifikasi DOTS, Poli Paru lt. 2, Operasional 24 Jam)
   - **RSAL Dr. Ramelan**: Jl. Gadung No.1, Jagir, Wonokromo, Surabaya. (Tersertifikasi DOTS, Poli Paru, Operasional 24 Jam)
3. Format informasi dengan rapi. Semua judul/label sebelum titik dua HARUS ditebalkan (contoh: "**Fasilitas Kesehatan**:", "**Alamat**:").
4. Beritahu mereka bahwa mereka dapat menekan tombol di bawah untuk melihat semua klinik dan rumah sakit yang tersedia di Surabaya langsung pada peta.
5. Selalu akhiri dengan kalimat penutup yang hangat dan menawarkan bantuan lebih lanjut (contoh: "Apakah ada hal lain yang bisa saya bantu, silakan?").
6. JANGAN sertakan sintaks tombol markdown seperti "[Lihat Lokasi Rumah Sakit]" di akhir teks.
7. Gunakan bahasa Indonesia sepenuhnya.
"""
        else:
            system_prompt = """\
You are TBConsult, a professional medical triage assistant specializing in Tuberculosis (TB).
The patient is asking to find the nearest hospital, clinic, or health facility, but the system could not retrieve their current GPS location.

You must explain this to the user in a very warm, comforting, and charming character.

RULES (NON-NEGOTIABLE):
1. Explain gently that you couldn't access their GPS location. Suggest they enable location permissions in their device settings if they'd like to find the exact nearest facility.
2. Suggest a couple of major DOTS-certified health facilities in Surabaya from the system data:
   - **RSUD Dr. Soetomo**: Jl. Mayjend Prof. Dr. Moestopo No.6-8, Surabaya. (DOTS Certified, Poli Paru lt. 2, 24 Hours)
   - **RSAL Dr. Ramelan**: Jl. Gadung No.1, Jagir, Wonokromo, Surabaya. (DOTS Certified, Poli Paru, 24 Hours)
3. Format the details cleanly. Any heading/label before a colon MUST be bolded (e.g., "**Health Facility**:", "**Address**:").
4. Tell them they can click the button below to view all available clinics and hospitals in Surabaya on the map.
5. Always end with a charming closing line (e.g., "Is there anything else I can help you with, please?").
6. Do NOT include any markdown button syntax like "[View Hospital Locations]" at the end of the text.
7. Respond in English.
"""

    answer_text = await llm_service.invoke_llm(
        system_prompt=system_prompt,
        user_message=user_prompt,
        temperature=0.5,
    )
    logger.info("Hospital query: generated direct answer")

    btn_doctor = "Tanya Dokter" if is_indonesian else "Ask Doctor"
    btn_hospitals = "Lihat Lokasi Rumah Sakit" if is_indonesian else "View Hospital Locations"
    sdui_components = [
        {
            "type": "button",
            "label": btn_doctor,
            "action": "consult_doctor"
        },
        {
            "type": "button",
            "label": btn_hospitals,
            "action": "visit_dots"
        }
    ]

    return {
        "triage_decision": {
            "risk_level": "",
            "next_steps": [],
            "requires_immediate_attention": False,
        },
        "response_text": answer_text.strip(),
        "sdui_components": sdui_components,
        "tool_calls": []
    }


def _build_history_block(chat_history: list[dict]) -> str:
    if not chat_history:
        return ""
    
    lines = []
    for msg in chat_history:
        role_label = "Patient" if msg.get("role") == "user" else "TBConsult"
        lines.append(f"{role_label}: {msg.get('content', '')}")
    
    history_text = "\n".join(lines)
    return f"\nConversation History (use this to maintain context):\n{history_text}\n"

def _build_interview_context(chat_history: list[dict], current_user_message: str) -> str:
    lines = []
    for msg in chat_history:
        content = msg.get('content', '').strip()
        if not content:
            continue
        role_label = "Patient (Answer)" if msg.get("role") == "user" else "TBConsult (Question)"
        lines.append(f"{role_label}: {content}")
        
    lines.append(f"Patient (Current Answer): {current_user_message.strip()}")
    history_text = "\n".join(lines)
    
    return f"""[Accumulated TBConsult Interview Context]
{history_text}

[Instruction]
Analyze the accumulated questions and answers above. Based on the missing key Tuberculosis (TBC) data points, formulate exactly ONE highly relevant follow-up question. Do not ask something that has already been answered."""


def _count_bot_turns(chat_history: list[dict]) -> int:
    return sum(1 for m in chat_history if m.get("role") != "user")


async def generate_triage(state: TriageState) -> dict:
    reranked_docs = state.get("reranked_docs", [])
    user_message = state.get("user_message", "")
    chat_history = state.get("chat_history", [])
    bot_turns = _count_bot_turns(chat_history)
    
    lang = detect_language(user_message, chat_history)
    
    if bot_turns >= 5 and not reranked_docs:
        is_indonesian = (lang == 'id')
        response_text = (
            "Saya tidak memiliki informasi spesifik yang cukup untuk memberikan penilaian terperinci. Silakan berkonsultasi dengan profesional kesehatan atau kunjungi klinik untuk evaluasi yang tepat."
            if is_indonesian else
            "I don't have enough specific information to provide a detailed assessment. Please consult a healthcare professional or visit a clinic for proper evaluation."
        )
        button_label = "Lihat Lokasi Rumah Sakit" if is_indonesian else "View Hospital Locations"
        return {
            "triage_decision": {
                "risk_level": "Low",
                "next_steps": ["Silakan berkonsultasi dengan profesional kesehatan." if is_indonesian else "Please consult a healthcare professional for accurate advice."],
                "requires_immediate_attention": False
            },
            "response_text": response_text,
            "sdui_components": [
                {
                    "type": "button",
                    "label": button_label,
                    "action": "visit_dots"
                }
            ]
        }
        
    context_text = "\n\n".join([f"[Source {i+1}] {doc.get('text')}" for i, doc in enumerate(reranked_docs)]) if reranked_docs else "No context available."
    extracted_entities = state.get("extracted_entities", {})
    history_block = _build_history_block(chat_history)
    
    user_prompt = f"""{history_block}
Context:
{context_text}

Extracted Entities:
{extracted_entities}

User Message:
{user_message}
"""

    tool_results = state.get("tool_results", [])
    if tool_results:
        user_prompt += "\n\nTool Results:\n"
        for res in tool_results:
            user_prompt += f"- {res}\n"

    try:
        if _is_hospital_query(user_message):
            return await _answer_hospital_query(
                user_prompt,
                user_message,
                chat_history,
                lat=state.get("latitude"),
                lng=state.get("longitude")
            )

        if _is_informational_question(user_message):
            return await _answer_informational_question(user_prompt, user_message, chat_history)

        if bot_turns < 5:
            interview_prompt_str = _build_interview_context(chat_history, user_message)
            return await _handle_interview_phase(interview_prompt_str, user_message, chat_history)
        elif bot_turns < 10:
            return await _handle_extended_phase(user_prompt, user_message, state)
        else:
            return await _handle_forced_assessment(user_prompt, user_message, state)
    except Exception as e:
        logger.error(f"Triage generation failed: {e}")
        return {
            "triage_decision": {
                "risk_level": "Low",
                "next_steps": ["Please consult a healthcare professional."],
                "requires_immediate_attention": False
            },
            "response_text": "I encountered an error while processing your request. Please consult a healthcare professional.",
            "sdui_components": []
        }


async def _handle_interview_phase(user_prompt: str, user_message: str, chat_history: list[dict]) -> dict:
    lang = detect_language(user_message, chat_history)
    system_prompt = INTERVIEW_PROMPT
    if lang == 'en':
        system_prompt += "\nIMPORTANT: You MUST respond in English."
    else:
        system_prompt += "\nIMPORTANT: You MUST respond in Indonesian (Bahasa Indonesia)."

    question_text = await llm_service.invoke_llm(
        system_prompt=system_prompt,
        user_message=user_prompt,
        temperature=0.6,
    )
    logger.info("Interview phase: generated follow-up question")
    
    if question_text.strip().startswith("DARURAT:"):
        return _build_emergency_response(question_text, user_message, chat_history)
    
    return {
        "triage_decision": {},
        "response_text": question_text.strip(),
        "sdui_components": [],
        "tool_calls": []
    }


def _build_emergency_response(emergency_text: str, user_message: str, chat_history: list[dict]) -> dict:
    lang = detect_language(user_message, chat_history)
    is_indonesian = (lang == 'id')
    raw_text = emergency_text.replace("DARURAT:", "").strip()
    
    indicators_label = "Presence of High-Risk Indicators" if not is_indonesian else "Keberadaan Indikator Risiko Tinggi"
    symptoms_label = "Current Symptoms" if not is_indonesian else "Gejala Saat Ini"
    
    parts = []
    
    # 1. Urgent assessment
    parts.append(raw_text)
    
    # 2. Symptoms & indicators
    parts.append(f"**{symptoms_label}**: {user_message.strip()}")
    parts.append(f"**{indicators_label}**: Dangerous symptoms detected.")
    
    # 3. Next steps
    next_steps_title = "📋 Recommended Next Steps" if not is_indonesian else "📋 Langkah Selanjutnya yang Direkomendasikan"
    step = "Visit emergency room immediately" if not is_indonesian else "Segera kunjungi unit gawat darurat"
    parts.append(f"{next_steps_title}\n\n{step}")
    
    # 4. Care finder link
    care_title = "🏥 Need to Find Care?" if not is_indonesian else "🏥 Butuh Mencari Layanan Kesehatan?"
    care_desc = (
        "If you would like to find a nearby clinic or doctor for a general check-up, you can use the link below:"
        if not is_indonesian else
        "Jika Anda ingin mencari klinik atau dokter terdekat untuk pemeriksaan umum, Anda dapat menggunakan tautan di bawah ini:"
    )
    parts.append(f"{care_title}\n\n{care_desc}")
    
    response_text = "\n\n".join(parts)
    
    button_label = "Find Nearest Hospital" if not is_indonesian else "Cari Rumah Sakit Terdekat"
    return {
        "triage_decision": {
            "risk_level": "High",
            "reasons": [raw_text],
            "next_steps": [step],
            "requires_immediate_attention": True,
            "sources": []
        },
        "response_text": response_text,
        "sdui_components": [
            {
                "type": "button",
                "label": button_label,
                "action": "visit_dots"
            }
        ],
        "tool_calls": []
    }


async def _handle_extended_phase(user_prompt: str, user_message: str, state: TriageState) -> dict:
    chat_history = state.get("chat_history", [])
    lang = detect_language(user_message, chat_history)
    
    system_prompt = EXTENDED_INTERVIEW_PROMPT
    if lang == 'en':
        system_prompt += "\nIMPORTANT: You MUST respond in English. All fields in the structured response (risk_level, reasons, next_steps, and interview_question) MUST be written in English. Do NOT use Indonesian."
    else:
        system_prompt += "\nIMPORTANT: You MUST respond in Indonesian (Bahasa Indonesia). All fields in the structured response (reasons, next_steps, and interview_question) MUST be written in Indonesian (Bahasa Indonesia). Do NOT use English."

    tool_results = state.get("tool_results", [])
    if not tool_results:
        message = await llm_service.invoke_llm_with_tools(
            system_prompt=system_prompt,
            user_message=user_prompt,
            tools=tools
        )
        if hasattr(message, 'tool_calls') and message.tool_calls:
            return {
                "tool_calls": message.tool_calls,
                "triage_decision": {},
                "response_text": "",
                "sdui_components": []
            }

    triage_decision = await llm_service.invoke_llm_structured(
        system_prompt=system_prompt,
        user_message=user_prompt,
        tool_schema=TriageDecision.model_json_schema()
    )
    logger.info("Extended phase: structured decision complete")
    
    needs_more = triage_decision.get("needs_more_info", False)
    question = triage_decision.get("interview_question", "")
    
    if needs_more and question:
        return {
            "triage_decision": {},
            "response_text": question.strip(),
            "sdui_components": [],
            "tool_calls": []
        }
    
    return _build_assessment_response(triage_decision, user_message, chat_history)


async def _handle_forced_assessment(user_prompt: str, user_message: str, state: TriageState) -> dict:
    chat_history = state.get("chat_history", [])
    lang = detect_language(user_message, chat_history)
    
    forced_prompt = ASSESSMENT_PROMPT + "\n" + FORCED_ASSESSMENT_ADDENDUM
    if lang == 'en':
        forced_prompt += "\nIMPORTANT: You MUST respond in English. All fields in the structured response (risk_level, reasons, next_steps) MUST be written in English. Do NOT use Indonesian."
    else:
        forced_prompt += "\nIMPORTANT: You MUST respond in Indonesian (Bahasa Indonesia). All fields in the structured response (reasons, next_steps) MUST be written in Indonesian (Bahasa Indonesia). Do NOT use English."

    tool_results = state.get("tool_results", [])
    if not tool_results:
        message = await llm_service.invoke_llm_with_tools(
            system_prompt=forced_prompt,
            user_message=user_prompt,
            tools=tools
        )
        if hasattr(message, 'tool_calls') and message.tool_calls:
            return {
                "tool_calls": message.tool_calls,
                "triage_decision": {},
                "response_text": "",
                "sdui_components": []
            }

    triage_decision = await llm_service.invoke_llm_structured(
        system_prompt=forced_prompt,
        user_message=user_prompt,
        tool_schema=TriageDecision.model_json_schema()
    )
    logger.info("Forced assessment phase: structured decision complete")
    
    return _build_assessment_response(triage_decision, user_message, chat_history)


def _build_assessment_response(triage_decision: dict, user_message: str, chat_history: list[dict]) -> dict:
    reasons = triage_decision.get("reasons", [])
    next_steps = triage_decision.get("next_steps", [])
    risk_level = triage_decision.get("risk_level", "Low")
    
    lang = detect_language(user_message, chat_history)
    is_indonesian = (lang == 'id')
    
    # Emojis and risk labels
    if risk_level == "High":
        indicators_label = "Presence of High-Risk Indicators" if not is_indonesian else "Keberadaan Indikator Risiko Tinggi"
    else:
        indicators_label = "Absence of High-Risk Indicators" if not is_indonesian else "Ketiadaan Indikator Risiko Tinggi"
        
    symptoms_label = "Current Symptoms" if not is_indonesian else "Gejala Saat Ini"
    
    parts = []
    
    # 1) Symptom assessment (reasons[0]) - No header/emoji
    if len(reasons) >= 1:
        parts.append(reasons[0].strip())
    
    # 2) Current symptoms list (reasons[1]) - Bold text before colon
    if len(reasons) >= 2:
        parts.append(f"**{symptoms_label}**: {reasons[1].strip()}")
        
    # 3) High-risk indicators presence/absence explanation (reasons[2]) - Bold text before colon
    if len(reasons) >= 3:
        parts.append(f"**{indicators_label}**: {reasons[2].strip()}")
        
    # Fallback if reasons list has different length
    if len(reasons) < 3 and reasons:
        parts = ["\n\n".join([r.strip() for r in reasons])]
        
    # 4) Recommended Next Steps - Bold text before colon in next steps list items
    if next_steps:
        next_steps_title = "📋 Recommended Next Steps" if not is_indonesian else "📋 Langkah Selanjutnya yang Direkomendasikan"
        formatted_steps = []
        for s in next_steps:
            s_str = s.strip()
            if ":" in s_str:
                left, right = s_str.split(":", 1)
                formatted_steps.append(f"**{left.strip()}**:{right}")
            else:
                formatted_steps.append(s_str)
        bullet_steps = "\n\n".join(formatted_steps)
        parts.append(f"{next_steps_title}\n\n{bullet_steps}")
        
    # 5) Need to find care block with NO markdown button at the end
    care_title = "🏥 Need to Find Care?" if not is_indonesian else "🏥 Butuh Mencari Layanan Kesehatan?"
    care_desc = (
        "If you would like to find a nearby clinic or doctor for a general check-up, you can use the link below:"
        if not is_indonesian else
        "Jika Anda ingin mencari klinik atau dokter terdekat untuk pemeriksaan umum, Anda dapat menggunakan tautan di bawah ini:"
    )
    parts.append(f"{care_title}\n\n{care_desc}")
    
    response_text = "\n\n".join(parts)
    
    button_label = "View Hospital Locations" if not is_indonesian else "Lihat Lokasi Rumah Sakit"
    sdui_components = [
        {
            "type": "button",
            "label": button_label,
            "action": "visit_dots"
        }
    ]
    
    triage_decision.pop("needs_more_info", None)
    triage_decision.pop("interview_question", None)
    
    return {
        "triage_decision": triage_decision,
        "response_text": response_text,
        "sdui_components": sdui_components,
        "tool_calls": []
    }
