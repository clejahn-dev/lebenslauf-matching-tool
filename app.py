import streamlit as st
from fuzzywuzzy import fuzz
import re
import hashlib
import requests
from bs4 import BeautifulSoup
from io import BytesIO
from datetime import datetime

st.set_page_config(
    page_title="Lebenslauf Matching Tool",
    page_icon="📄",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# HELPER FUNKTIONEN
# ============================================================================

def normalize_text(value):
    """Normalisiert Werte für stabile Vergleiche, ohne Umlaute zu entfernen."""
    if value is None:
        return ""
    
    text = str(value).lower().strip()
    text = re.sub(
        r"(?<!\w)(?:[a-zäöüß]\s+){2,}[a-zäöüß](?!\w)",
        lambda match: match.group(0).replace(" ", ""),
        text
    )
    compact_aliases = {
        "seniorhrbusinesspartner": "senior hr business partner",
        "hrbusinesspartner": "hr business partner",
        "peopleculture": "people culture",
        "personalculture": "people culture",
        "p c": "p und c",
        "p&c": "p und c",
        "sap-hr": "sap hr",
        "sap/hr": "sap hr",
        "sap h r": "sap hr",
        "msoffice": "ms office",
        "ms-office": "ms office"
    }
    text = text.replace("–", "-").replace("—", "-").replace("‑", "-")
    text = text.replace("&", " und ")
    text = re.sub(r"\s*-\s*", "-", text)
    text = re.sub(r"\bund\b", "und", text)
    text = re.sub(r"\s+", " ", text)
    for source, target in compact_aliases.items():
        text = text.replace(source, target)
    
    # Häufige Varianten vergleichbarer machen.
    text = text.replace("gesundheits-und krankenpfleger", "gesundheits und krankenpfleger")
    text = text.replace("gesundheits- und krankenpfleger", "gesundheits und krankenpfleger")
    text = text.replace("b-lizenz", "b lizenz")
    text = text.replace("sap-hr", "sap hr")
    
    return text.strip()


def normalize_display_text(text):
    """Normalisiert Vorschautext ohne fachliche Lowercase-Normalisierung."""
    if not text:
        return text
    text = re.sub(r" +", " ", str(text))
    text = re.sub(r"\n\n\n+", "\n\n", text)
    return text.strip()


def split_normalized_values(value):
    return {normalize_text(item) for item in str(value or "").split(",") if normalize_text(item)}


def make_cv_signature(cv_text, selected_group, counter):
    """Erstellt einen stabilen Fingerabdruck für den aktuellen CV-Kontext."""
    if not cv_text:
        return f"empty:{normalize_text(selected_group)}:{counter}"
    signature_data = f"{normalize_text(cv_text)}|{normalize_text(selected_group)}|{counter}"
    return hashlib.sha256(signature_data.encode("utf-8")).hexdigest()


def fetch_text_from_url(url):
    """Lädt eine Webseite und extrahiert lesbaren Text mit BeautifulSoup."""
    try:
        response = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (compatible; JobFitCheck/1.0)"
        })
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")
        for tag in soup(["script", "style", "noscript", "header", "footer", "form"]):
            tag.decompose()
        texts = []
        for element in soup.find_all(["p", "li", "h1", "h2", "h3", "h4"]):
            snippet = element.get_text(separator=" ", strip=True)
            if snippet:
                texts.append(snippet)
        return normalize_display_text("\n".join(texts))
    except Exception:
        return None


def extract_salary_range(text):
    if not text:
        return None, None
    normalized = normalize_text(text)
    patterns = [
        r"(\d{2,3}(?:[\.,]\d{3})?)\s*(?:€|eur|euro)\s*(?:bis|\-|–|—)\s*(\d{2,3}(?:[\.,]\d{3})?)",
        r"(\d{2,3}(?:[\.,]\d{3})?)\s*(?:bis|\-|–|—)\s*(\d{2,3}(?:[\.,]\d{3})?)\s*(?:€|eur|euro)",
        r"(?:ab|mindestens|von)\s*(\d{2,3}(?:[\.,]\d{3})?)\s*(?:€|eur|euro)",
        r"(\d{2,3}(?:[\.,]\d{3})?)\s*(?:€|eur|euro)"
    ]
    for pattern in patterns:
        match = re.search(pattern, normalized)
        if match:
            if len(match.groups()) >= 2 and match.group(2):
                min_val = int(match.group(1).replace('.', '').replace(',', '.'))
                max_val = int(match.group(2).replace('.', '').replace(',', '.'))
                return min_val, max_val
            elif len(match.groups()) >= 1:
                value = int(match.group(1).replace('.', '').replace(',', '.'))
                return value, value
    return None, None


def analyze_job_profile_text(job_text, selected_group, berufsgruppen):
    result = {
        "pflichtskills": [],
        "wunschskills": [],
        "qualifikationen": [],
        "berufserfahrung_jahre": None,
        "gehalt_min": None,
        "gehalt_max": None
    }
    if not job_text:
        return result

    normalized = normalize_text(job_text)
    profile = berufsgruppen.get(selected_group, {})
    pflicht_candidates = profile.get("pflichtskills", [])
    wunsch_candidates = profile.get("wunschskills", [])
    qual_candidates = profile.get("qualifikationen", [])

    def text_contains(term):
        term = normalize_text(term)
        return bool(term) and (term in normalized or fuzz.partial_ratio(term, normalized) >= 92)

    pflicht = {skill for skill in pflicht_candidates if text_contains(skill)}
    wunsch = {skill for skill in wunsch_candidates if text_contains(skill)}
    qual = {qual for qual in qual_candidates if text_contains(qual)}

    for domain, mapping in DOMAIN_MAPPINGS.items():
        if any(text_contains(trigger) for trigger in mapping.get("triggers", [])):
            if domain in relevant_domains_for_group(selected_group):
                pflicht.update({skill for skill in mapping.get("skills", []) if text_contains(skill)})
            else:
                wunsch.update({skill for skill in mapping.get("skills", []) if text_contains(skill)})
            qual.update({q for q in mapping.get("qualifikationen", []) if text_contains(q)})

    experience = None
    exp_match = re.search(r"(?:mindestens|ab|mehr als|über|mind\.|ca\.|circa)\s*(\d{1,2})\s*(?:jahre|j)\b", normalized)
    if exp_match:
        experience = int(exp_match.group(1))
    else:
        exp_match = re.search(r"(\d{1,2})\s*(?:jahre|j)\s*(?:berufserfahrung|erfahrung)", normalized)
        if exp_match:
            experience = int(exp_match.group(1))

    gehalt_min, gehalt_max = extract_salary_range(normalized)

    result["pflichtskills"] = sorted(pflicht)
    result["wunschskills"] = sorted(wunsch)
    result["qualifikationen"] = sorted(qual)
    result["berufserfahrung_jahre"] = experience
    result["gehalt_min"] = gehalt_min
    result["gehalt_max"] = gehalt_max
    return result


def filter_cv_noise(skills):
    exclude = {
        "kontakt", "adresse", "mobil", "email", "e mail", "interessen",
        "literatur", "persönlichkeitsentwicklung", "anschrift", "telefon"
    }
    return [skill for skill in skills if normalize_text(skill) not in exclude]


def generate_cv_summary(cv_analyse, selected_group):
    if not cv_analyse:
        return ""
    parts = []
    experience = cv_analyse.get("berufserfahrung_jahre")
    if experience is not None:
        parts.append(f"Berufserfahrung: {experience} Jahre")
    skills = cv_analyse.get("skills", [])
    if skills:
        parts.append(f"Wichtigste Skills: {', '.join(skills[:8])}")
    qualifikationen = cv_analyse.get("qualifikationen", [])
    if qualifikationen:
        parts.append(f"Qualifikationen: {', '.join(qualifikationen)}")
    sprachen = cv_analyse.get("sprachen", [])
    if sprachen:
        parts.append(f"Sprachen: {', '.join(sprachen)}")
    zertifikate = cv_analyse.get("zertifikate", [])
    if zertifikate:
        parts.append(f"Zertifikate: {', '.join(zertifikate)}")
    fuehrerscheine = cv_analyse.get("fuehrerscheine", [])
    if fuehrerscheine:
        parts.append(f"Führerscheine: {', '.join(fuehrerscheine)}")
    if selected_group and selected_group != "Bitte auswählen":
        parts.append(f"Zielrolle: {selected_group}")
    return "\n".join(parts)


def combine_values(*value_groups):
    """Kombiniert kommaseparierte Texte und Listen ohne Duplikate."""
    combined = []
    seen = set()
    for group in value_groups:
        if not group:
            continue
        values = group.split(",") if isinstance(group, str) else group
        for value in values:
            normalized = normalize_text(value)
            if normalized and normalized not in seen:
                combined.append(normalized)
                seen.add(normalized)
    return ", ".join(combined)


def format_detected_values(values):
    return ", ".join(sorted(values)) if values else "Keine"


def combine_values(*value_groups):
    """Kombiniert kommaseparierte Texte und Listen ohne Duplikate."""
    combined = []
    seen = set()
    for group in value_groups:
        if not group:
            continue
        values = group.split(",") if isinstance(group, str) else group
        for value in values:
            normalized = normalize_text(value)
            if normalized and normalized not in seen:
                combined.append(normalized)
                seen.add(normalized)
    return ", ".join(combined)


def dedupe_sorted(values):
    return sorted({normalize_text(value) for value in values if normalize_text(value)})


def safe_extract_number(text, position="first", default=0):
    """
    Extrahiert Zahlen sicher aus Text wie '1 bis 5 Tage' oder '500 bis 1.200 €'
    
    Args:
        text: Text mit Zahlen
        position: 'first' (erste Zahl), 'last' (letzte Zahl), 'both' (beide)
        default: Standardwert bei Fehler
    
    Returns:
        Zahl oder Standardwert bei Fehler
    """
    try:
        if not text or not isinstance(text, str):
            return default
        
        # Entferne alle nicht-numerischen Zeichen außer Punkte und Leerzeichen
        numbers = re.findall(r'\d+[\.,]?\d*', text)
        if not numbers:
            return default
        
        if position == "first":
            return int(float(numbers[0].replace('.', '').replace(',', '.')))
        elif position == "last":
            return int(float(numbers[-1].replace('.', '').replace(',', '.')))
        elif position == "both":
            first = int(float(numbers[0].replace('.', '').replace(',', '.')))
            last = int(float(numbers[-1].replace('.', '').replace(',', '.'))) if len(numbers) > 1 else first
            return (first, last)
    except (ValueError, IndexError, AttributeError):
        return default
    
    return default


def extract_text_from_pdf(pdf_file):
    """Extrahiert Text aus PDF-Datei sicher"""
    try:
        from pypdf import PdfReader
        pdf_file.seek(0)
        pdf_bytes = pdf_file.read()
        pdf_reader = PdfReader(BytesIO(pdf_bytes))
        text = ""
        for page in pdf_reader.pages:
            page_text = page.extract_text() or ""
            if page_text.strip():
                text += page_text + "\n"
        if not text.strip():
            st.warning("Aus der PDF konnten keine lesbaren Textinhalte extrahiert werden. Bitte den Text manuell eintragen.")
            return None
        return text
    except Exception as e:
        st.warning(f"PDF konnte nicht vollständig gelesen werden: {str(e)}")
        return None


def recognize_skills_from_text(text, skill_dict_list, skill_names_list):
    """Erkennt Skills aus Text basierend auf Keyword-Matching"""
    if not text:
        return []
    
    text_lower = normalize_text(text)
    recognized_skills = set()
    
    try:
        # Durchsuche alle übergebenen Skill-Listen
        for skill_names in skill_names_list:
            for skill in skill_names:
                skill_lower = normalize_text(skill)
                # Exakte oder Fuzzy Matches
                if skill_lower in text_lower or fuzz.ratio(skill_lower, text_lower) > 80:
                    recognized_skills.add(skill)
                # Prüfe auch längere Phrasen
                elif any(word in text_lower for word in skill_lower.split()):
                    recognized_skills.add(skill)
    except Exception:
        pass
    
    return sorted(list(recognized_skills))


def apply_taetigkeit_mapping(skill_text):
    """Mappt Tätigkeitsbeschreibungen zu tatsächlichen Skills"""
    if not skill_text:
        return set()
    
    recognized = set()
    skill_text_lower = normalize_text(skill_text)
    
    for activity, mapped_skills in taetigkeits_mapping.items():
        activity_normalized = normalize_text(activity)
        if activity_normalized in skill_text_lower or fuzz.ratio(activity_normalized, skill_text_lower) > 75:
            recognized.update(mapped_skills)
    
    return recognized


def filter_softskills_from_requirements(skills_set):
    """Entfernt Softskills aus einer Skill-Liste (für Qualifizierungsempfehlungen)"""
    return {s for s in skills_set if normalize_text(s) not in softskill_no_training_normalized}


def check_fuehrerschein_erfuellung(bewerber_fuehrerschein, gefordert_fuehrerschein):
    """
    Prüft, ob ein Bewerber-Führerschein die geforderten Anforderungen erfüllt
    
    Returns: True wenn erfüllt, False wenn nicht
    """
    if not gefordert_fuehrerschein or not bewerber_fuehrerschein:
        return False
    
    geforderte_klassen = extract_fuehrerschein_klassen(gefordert_fuehrerschein)
    bewerber_klassen = extract_fuehrerschein_klassen(bewerber_fuehrerschein)
    if not geforderte_klassen or not bewerber_klassen:
        return False

    erfuellte_klassen = set()
    for klasse in bewerber_klassen:
        erfuellte_klassen.update(fuehrerschein_erfuellung.get(klasse, []))

    return geforderte_klassen.issubset(erfuellte_klassen)


def extract_fuehrerschein_klassen(text):
    """Erkennt Führerscheinklassen ohne falsche Einzelbuchstaben-Treffer."""
    normalized_text = normalize_text(text)
    normalized_text = re.sub(r"\b(fitnesstrainer|trainer)?\s*b\s+lizenz\b", " ", normalized_text)
    normalized = normalized_text.upper()
    pattern = r"(?<![A-Z0-9])(C1E|C1|CE|BE|DE|B|C|D)(?![A-Z0-9])"
    classes = set()

    for keyword_match in re.finditer(r"\b(FÜHRERSCHEIN|FAHRERLAUBNIS|FS|KLASSE)\b", normalized):
        window = normalized[keyword_match.start():keyword_match.end() + 80]
        classes.update(re.findall(pattern, window))

    class_list_pattern = r"(?<![A-Z0-9])(C1E|C1|CE|BE|DE|B|C|D)(?:\s*[,/]\s*(C1E|C1|CE|BE|DE|B|C|D))+"
    for list_match in re.finditer(class_list_pattern, normalized):
        classes.update(re.findall(pattern, list_match.group(0)))

    return classes


def fuehrerschein_skills_from_classes(classes):
    """Macht erkannte Klassen als Skill-Tokens für das Matching nutzbar."""
    skills = set()
    for klasse in classes:
        skills.add(f"führerschein klasse {klasse.lower()}")
        skills.add(f"führerschein {klasse.lower()}")
    return skills


def get_softskill_rahmenbedingungen(skills_set):
    """Extrahiert Softskills/Rahmenbedingungen aus einer Skill-Liste"""
    return {s for s in skills_set if normalize_text(s) in softskill_no_training_normalized}


def extract_skills_from_cv(
    cv_text,
    pflichtskills,
    wunschskills,
    qualifikationen,
    qualifikations_synonyme,
    softskill_synonyme,
    taetigkeits_mapping
):
    """Erkennt passende Skills und Qualifikationen aus einem Lebenslauftext."""
    result = {
        "erkannte_pflichtskills": [],
        "erkannte_wunschskills": [],
        "erkannte_qualifikationen": [],
        "erkannte_transfer_skills": [],
        "erkannte_taetigkeiten": [],
        "erkannte_fuehrerscheine": []
    }
    if not cv_text:
        return result

    cv_normalized = normalize_text(cv_text)
    if not cv_normalized:
        return result

    pflicht_normalized = {normalize_text(skill) for skill in pflichtskills if normalize_text(skill)}
    wunsch_normalized = {normalize_text(skill) for skill in wunschskills if normalize_text(skill)}
    qual_normalized = {normalize_text(qualifikation) for qualifikation in qualifikationen if normalize_text(qualifikation)}
    qual_synonyms = {
        normalize_text(key): {normalize_text(value) for value in values}
        for key, values in qualifikations_synonyme.items()
    }
    soft_synonyms = {
        normalize_text(key): {normalize_text(value) for value in values}
        for key, values in softskill_synonyme.items()
    }

    def text_contains(term):
        term = normalize_text(term)
        if not term:
            return False
        return term in cv_normalized or fuzz.partial_ratio(term, cv_normalized) >= 92

    erkannte_pflicht = set()
    erkannte_wunsch = set()
    erkannte_qualifikationen = set()
    erkannte_transfer = set()
    erkannte_taetigkeiten = set()

    for skill in pflicht_normalized:
        if text_contains(skill):
            erkannte_pflicht.add(skill)

    for skill in wunsch_normalized:
        if text_contains(skill):
            erkannte_wunsch.add(skill)

    for qualifikation in qual_normalized:
        if text_contains(qualifikation):
            erkannte_qualifikationen.add(qualifikation)
            continue

        synonyms = set(qual_synonyms.get(qualifikation, set()))
        for key, values in qual_synonyms.items():
            if qualifikation == key or qualifikation in values:
                synonyms.add(key)
                synonyms.update(values)

        if any(text_contains(synonym) for synonym in synonyms):
            erkannte_qualifikationen.add(qualifikation)

    for activity, mapped_skills in taetigkeits_mapping.items():
        activity_normalized = normalize_text(activity)
        if text_contains(activity_normalized):
            erkannte_taetigkeiten.add(activity_normalized)
            for mapped_skill in mapped_skills:
                mapped_normalized = normalize_text(mapped_skill)
                erkannte_transfer.add(mapped_normalized)
                if mapped_normalized in pflicht_normalized:
                    erkannte_pflicht.add(mapped_normalized)
                if mapped_normalized in wunsch_normalized:
                    erkannte_wunsch.add(mapped_normalized)

    for source, targets in soft_synonyms.items():
        if text_contains(source):
            for target in targets:
                erkannte_transfer.add(target)
                if target in pflicht_normalized:
                    erkannte_pflicht.add(target)
                if target in wunsch_normalized:
                    erkannte_wunsch.add(target)

    for skill in pflicht_normalized:
        if any(skill in soft_synonyms.get(source, set()) and text_contains(source) for source in soft_synonyms):
            erkannte_pflicht.add(skill)
            erkannte_transfer.add(skill)

    for skill in wunsch_normalized:
        if any(skill in soft_synonyms.get(source, set()) and text_contains(source) for source in soft_synonyms):
            erkannte_wunsch.add(skill)
            erkannte_transfer.add(skill)

    fuehrerschein_klassen = extract_fuehrerschein_klassen(cv_text)

    result["erkannte_pflichtskills"] = sorted(erkannte_pflicht)
    result["erkannte_wunschskills"] = sorted(erkannte_wunsch)
    result["erkannte_qualifikationen"] = sorted(erkannte_qualifikationen)
    result["erkannte_transfer_skills"] = sorted(erkannte_transfer)
    result["erkannte_taetigkeiten"] = sorted(erkannte_taetigkeiten)
    result["erkannte_fuehrerscheine"] = sorted(fuehrerschein_klassen)
    return result


def estimate_experience_years(cv_text):
    """Einfache Regex-basierte Schätzung der Berufserfahrung."""
    if not cv_text:
        return None

    normalized = normalize_text(cv_text)
    current_year = datetime.now().year
    candidates = []

    for match in re.finditer(r"(?:über|mehr als|mindestens|ca\.?|circa)?\s*(\d{1,2})\s+jahre(?:n)?\s+(?:berufs)?erfahrung", normalized):
        candidates.append(int(match.group(1)))

    for match in re.finditer(r"(?:seit|ab)\s+(19\d{2}|20\d{2})", normalized):
        start_year = int(match.group(1))
        if 1970 <= start_year <= current_year:
            candidates.append(current_year - start_year)

    for start, end in re.findall(r"\b(19\d{2}|20\d{2})\s*(?:-|bis|–|—)\s*(19\d{2}|20\d{2}|heute|aktuell)\b", normalized):
        start_year = int(start)
        end_year = current_year if end in {"heute", "aktuell"} else int(end)
        if 1970 <= start_year <= end_year <= current_year:
            candidates.append(end_year - start_year)

    if not candidates:
        return None

    plausible = [years for years in candidates if 0 <= years <= 50]
    if not plausible:
        return None
    return max(plausible)


def estimate_relevant_experience_years(cv_text, selected_berufsgruppe):
    """Schätzt relevante Erfahrung aus Datumsbereichen mit Rollen-Kontext."""
    if not cv_text:
        return None

    normalized = normalize_text(cv_text)
    selected = normalize_text(selected_berufsgruppe)
    current_year = datetime.now().year
    explicit_years = estimate_experience_years(cv_text)

    if "hr" in selected or "personal" in selected or "recruiter" in selected:
        keywords = [
            "hr", "personalreferent", "personalleitung", "personalleiter",
            "hr business partner", "p und c", "people culture", "personaladministration",
            "recruiting", "arbeitsrecht", "führungskräfteberatung", "prokurist",
            "personalrecht"
        ]
    elif "sicherheitsdienst" in selected:
        keywords = [
            "sicherheitsdienst", "sicherheitsdienste", "personenschutz", "objektschutz",
            "revierdienst", "dienstplanung", "einsatzplanung", "schichtplanung"
        ]
    elif "fitnesstrainer" in selected:
        keywords = [
            "fitnesstrainer", "ernährungsberater", "coaching", "gesundheitsförderung",
            "training", "stressreduktion"
        ]
    else:
        keywords = []

    relevant_years = []
    date_pattern = r"(\d{1,2}\.\d{1,2}\.(?:19|20)\d{2}|(?:19|20)\d{2})\s*(?:-|bis)\s*(\d{1,2}\.\d{1,2}\.(?:19|20)\d{2}|(?:19|20)\d{2}|heute|aktuell)"
    for match in re.finditer(date_pattern, normalized):
        start_raw, end_raw = match.groups()
        start_year = int(re.search(r"(19|20)\d{2}", start_raw).group(0))
        end_year = current_year if end_raw in {"heute", "aktuell"} else int(re.search(r"(19|20)\d{2}", end_raw).group(0))
        if not (1970 <= start_year <= end_year <= current_year):
            continue

        context_start = max(0, match.start() - 250)
        context_end = min(len(normalized), match.end() + 350)
        context = normalized[context_start:context_end]
        if not keywords or any(keyword in context for keyword in keywords):
            relevant_years.append(max(0, end_year - start_year))

    if relevant_years:
        return min(50, max(sum(relevant_years), max(relevant_years)))
    return explicit_years


DOMAIN_MAPPINGS = {
    "hr": {
        "triggers": [
            "senior hr business partner", "hr business partner", "personalreferent",
            "personalleitung", "personalleiter", "personalmanager", "p und c",
            "people culture", "personaladministration", "vertragswesen", "recruiting",
            "arbeitsrecht", "personalrecht", "führungskräfteberatung",
            "employee lifecycle", "hr-prozesse", "hr prozesse", "change management",
            "hr-controlling", "hr controlling", "sap hr", "sap-hr",
            "personalkostenplanung", "personalkostensteuerung", "bem", "bem-gespräche",
            "wiedereingliederung", "betriebsrat", "betriebsratsarbeit",
            "arbeitnehmervertretung", "arbeitnehmervertretungen", "konfliktmoderation",
            "hr-systeme", "stellenplanung", "ms office", "wrike", "factorial",
            "prokurist", "beratungskompetenz", "kommunikationskompetenz"
        ],
        "skills": [
            "personalbetreuung", "recruiting", "arbeitsrecht", "vertragswesen",
            "mitarbeitergespräche", "führungskräfteberatung", "onboarding",
            "hr administration", "personalentwicklung", "change management",
            "betriebsratsarbeit", "personalcontrolling", "sap hr",
            "hr-prozessmanagement", "konfliktmanagement", "bem",
            "wiedereingliederungsmanagement", "stellenplanung",
            "personalkostenplanung", "personalkostensteuerung", "hr-systeme",
            "ms office", "kommunikation", "beratungskompetenz",
            "kommunikationskompetenz", "personalrecht", "führungserfahrung"
        ],
        "qualifikationen": [
            "personalmanager", "personalreferent", "wirtschaftspsychologie",
            "change manager", "ausbilder gemäß aevo", "aevo"
        ]
    },
    "security": {
        "triggers": [
            "schmalstieg gmbh sicherheitsdienste", "sicherheitsdienste",
            "sicherheitsdienst", "personenschutz", "objektschutz", "revierdienst",
            "personalleiter in sicherheitsunternehmen", "einsatzmodelle",
            "arbeitszeitmodelle", "dienstplanung", "mitarbeiterführung im sicherheitsdienst",
            "einsatzplanung", "schichtplanung"
        ],
        "skills": [
            "sicherheitsdienst", "objektschutz", "revierdienst", "dienstplanung",
            "einsatzplanung", "führungserfahrung", "personalführung",
            "berichtswesen", "verantwortungsbewusstsein", "kommunikation",
            "konfliktmanagement", "schichtplanung", "zugangskontrolle",
            "kontrollgänge", "deeskalation"
        ],
        "qualifikationen": []
    },
    "fitness": {
        "triggers": [
            "fitnesstrainer", "ernährungsberater", "coaching", "gesundheitsförderung",
            "stressreduktion", "selbstständige tätigkeit als fitnesstrainer",
            "beratungskompetenz", "motivation", "kommunikation"
        ],
        "skills": [
            "trainingsbetreuung", "kundenberatung", "coaching",
            "gesundheitsförderung", "ernährungsberatung", "motivation",
            "kommunikation", "serviceorientierung", "stressreduktion",
            "beratungskompetenz"
        ],
        "qualifikationen": [
            "fitnesstrainer", "ernährungsberater"
        ]
    },
    "office": {
        "triggers": ["büroorganisation", "assistenz", "terminplanung", "reisenplanung", "office manager", "bürokaufmann"],
        "skills": ["büroorganisation", "terminplanung", "organisation", "kommunikation", "microsoft office", "schriftverkehr", "protokollführung", "recherche"],
        "qualifikationen": ["kaufmann für büromanagement", "office manager", "assistenz der geschäftsführung"]
    },
    "sales": {
        "triggers": ["vertrieb", "kaltakquise", "salesforce", "key account", "kundenakquise", "pipedrive"],
        "skills": ["vertrieb", "kundenberatung", "verhandlung", "abschlusssicherheit", "crm", "angebotserstellung"],
        "qualifikationen": ["kaufmann im einzelhandel", "industriekaufmann", "sales manager"]
    },
    "care": {
        "triggers": ["pflege", "patientenbetreuung", "hygiene", "wundversorgung", "altenpflege", "krankenpflege"],
        "skills": ["grundpflege", "behandlungspflege", "pflegedokumentation", "patientenbetreuung", "hygiene", "medikamentengabe"],
        "qualifikationen": ["pflegefachkraft", "gesundheits und krankenpfleger", "altenpfleger"]
    },
    "it": {
        "triggers": ["it support", "windows", "netzwerk", "hardware", "helpdesk", "active directory"],
        "skills": ["it support", "fehleranalyse", "netzwerke", "benutzersupport", "ticketsystem", "systemdokumentation"],
        "qualifikationen": ["fachinformatiker systemintegration", "it support specialist"]
    },
    "accounting": {
        "triggers": ["buchhaltung", "datev", "finanzbuchhaltung", "kontenabstimmung", "kreditoren", "debitoren"],
        "skills": ["finanzbuchhaltung", "debitorenbuchhaltung", "kreditorenbuchhaltung", "rechnungsprüfung", "zahlenverständnis", "excel"],
        "qualifikationen": ["buchhalter", "finanzbuchhalter", "steuerfachangestellter"]
    },
    "logistics": {
        "triggers": ["lager", "logistik", "kommissionierung", "wareneingang", "flurförderzeug", "staplerschein"],
        "skills": ["kommissionierung", "lagerung", "verpackung", "inventur", "bestandskontrolle", "staplerschein"],
        "qualifikationen": ["fachkraft für lagerlogistik", "lagerhelfer"]
    },
    "project": {
        "triggers": ["projektmanagement", "stakeholder", "risikomanagement", "projektsteuerung", "budgetkontrolle", "terminplanung"],
        "skills": ["projektplanung", "projektsteuerung", "stakeholdermanagement", "risikomanagement", "budgetkontrolle", "reporting"],
        "qualifikationen": ["projektmanager", "scrum master", "projektmanagement zertifizierung"]
    },
    "marketing": {
        "triggers": ["marketing", "kampagne", "social media", "content", "zielgruppenanalyse", "seo", "sea"],
        "skills": ["marketing", "content erstellung", "social media", "zielgruppenanalyse", "kommunikation", "reporting"],
        "qualifikationen": ["kaufmann für marketingkommunikation", "marketing manager"]
    },
    "data": {
        "triggers": ["datenanalyse", "sql", "reporting", "power bi", "tableau", "business intelligence"],
        "skills": ["datenanalyse", "reporting", "sql", "datenvisualisierung", "business intelligence"],
        "qualifikationen": ["data analyst", "wirtschaftsinformatik"]
    },
    "software": {
        "triggers": ["programmierung", "softwareentwicklung", "git", "testing", "api", "docker"],
        "skills": ["programmierung", "softwareentwicklung", "git", "testing", "api verständnis", "dokumentation"],
        "qualifikationen": ["fachinformatiker anwendungsentwicklung", "informatik studium"]
    },
    "quality": {
        "triggers": ["qualitätsmanagement", "audit", "iso 9001", "prozesse", "fehleranalyse", "reklamationsmanagement"],
        "skills": ["qualitätsmanagement", "audit vorbereitung", "prozessmanagement", "fehleranalyse", "dokumentation"],
        "qualifikationen": ["qualitätsmanagementbeauftragter", "iso 9001 schulung"]
    },
    "purchase": {
        "triggers": ["einkauf", "lieferantenmanagement", "preisverhandlung", "bestellwesen", "warengruppenmanagement"],
        "skills": ["einkauf", "lieferantenmanagement", "preisverhandlung", "bestellwesen", "vertragsprüfung"],
        "qualifikationen": ["industriekaufmann", "einkäufer mit berufserfahrung"]
    }
}

cv_skill_catalog = DOMAIN_MAPPINGS


def relevant_domains_for_group(selected_berufsgruppe):
    selected = normalize_text(selected_berufsgruppe)
    domains = []
    if any(term in selected for term in ["hr", "personal", "recruiter"]):
        domains.append("hr")
    if "sicherheitsdienst" in selected or "schutz und sicherheit" in selected:
        domains.append("security")
    if "fitnesstrainer" in selected or "fitness" in selected:
        domains.append("fitness")
    return domains or ["hr", "security", "fitness"]


def analyze_cv_text(cv_text, selected_berufsgruppe, berufsprofile, qualifikations_synonyme, softskill_synonyme, taetigkeits_mapping):
    """Extrahiert Lebenslaufdaten für die automatische Feldvorbelegung."""
    result = {
        "skills": [],
        "qualifikationen": [],
        "berufserfahrung_jahre": None,
        "fuehrerscheine": [],
        "sprachen": [],
        "zertifikate": [],
        "taetigkeiten": [],
        "transfer_skills": []
    }
    if not cv_text:
        return result

    cv_normalized = normalize_text(cv_text)
    if not cv_normalized:
        return result

    profile = berufsprofile.get(selected_berufsgruppe, {}) if isinstance(berufsprofile, dict) else {}
    skill_candidates = set()
    skill_candidates.update(profile.get("pflichtskills", []))
    skill_candidates.update(profile.get("wunschskills", []))
    skill_candidates.update(profile.get("qualifikationen", []))
    for values in taetigkeits_mapping.values():
        skill_candidates.update(values)
    for key, values in softskill_synonyme.items():
        skill_candidates.add(key)
        skill_candidates.update(values)

    qualification_candidates = set(profile.get("qualifikationen", []))
    for key, values in qualifikations_synonyme.items():
        qualification_candidates.add(key)
        qualification_candidates.update(values)

    def text_contains(term):
        term = normalize_text(term)
        return bool(term) and (term in cv_normalized or fuzz.partial_ratio(term, cv_normalized) >= 92)

    skills = {normalize_text(skill) for skill in skill_candidates if text_contains(skill)}
    qualifikationen = {normalize_text(qualifikation) for qualifikation in qualification_candidates if text_contains(qualifikation)}
    taetigkeiten = set()
    transfer_skills = set()

    for domain in relevant_domains_for_group(selected_berufsgruppe):
        mapping = cv_skill_catalog.get(domain, {})
        matched_domain = False
        for trigger in mapping.get("triggers", []):
            if text_contains(trigger):
                matched_domain = True
                taetigkeiten.add(normalize_text(trigger))
        if matched_domain:
            skills.update(dedupe_sorted(mapping.get("skills", [])))
            transfer_skills.update(dedupe_sorted(mapping.get("skills", [])))
            qualifikationen.update(
                normalize_text(qualifikation)
                for qualifikation in mapping.get("qualifikationen", [])
                if text_contains(qualifikation)
            )

    for activity, mapped_skills in taetigkeits_mapping.items():
        if text_contains(activity):
            activity_normalized = normalize_text(activity)
            taetigkeiten.add(activity_normalized)
            for mapped_skill in mapped_skills:
                mapped_normalized = normalize_text(mapped_skill)
                transfer_skills.add(mapped_normalized)
                skills.add(mapped_normalized)

    fuehrerscheine = extract_fuehrerschein_klassen(cv_text)
    selected_normalized = normalize_text(selected_berufsgruppe)
    if "sicherheitsdienst" in selected_normalized:
        skills.update(fuehrerschein_skills_from_classes(fuehrerscheine))

    sprach_patterns = {
        "deutsch": r"\bdeutsch\b",
        "englisch": r"\benglisch\b",
        "französisch": r"\bfranzösisch\b",
        "spanisch": r"\bspanisch\b",
        "italienisch": r"\bitalienisch\b",
        "russisch": r"\brussisch\b",
        "türkisch": r"\btürkisch\b",
        "arabisch": r"\barabisch\b",
        "polnisch": r"\bpolnisch\b"
    }
    sprachen = {sprache for sprache, pattern in sprach_patterns.items() if re.search(pattern, cv_normalized)}
    skills.update(sprachen)

    zertifikat_candidates = [
        "sachkundeprüfung 34a",
        "unterrichtung 34a",
        "ersthelfer",
        "erste hilfe",
        "brandschutzhelfer",
        "staplerschein",
        "fitnesstrainer b lizenz",
        "fitnesstrainer a lizenz",
        "personal trainer lizenz",
        "microsoft zertifizierung",
        "iso 9001",
        "scrum master",
        "datev",
        "sap",
        "sap hr"
    ]
    zertifikate = {normalize_text(zertifikat) for zertifikat in zertifikat_candidates if text_contains(zertifikat)}
    skills.update(zertifikate)
    skills = set(filter_cv_noise(skills))

    result["skills"] = sorted(skills)
    result["qualifikationen"] = sorted(qualifikationen)
    result["berufserfahrung_jahre"] = estimate_relevant_experience_years(cv_text, selected_berufsgruppe)
    result["fuehrerscheine"] = sorted(fuehrerscheine)
    result["sprachen"] = sorted(sprachen)
    result["zertifikate"] = sorted(zertifikate)
    result["taetigkeiten"] = sorted(taetigkeiten)
    result["transfer_skills"] = sorted(transfer_skills)
    return result


def get_experience_level(years):
    if years <= 2:
        return "junior"
    if years <= 5:
        return "mid"
    if years <= 10:
        return "senior"
    return "expert"


# ============================================================================
# SKILL-MAPPINGS UND SYNONYME
# ============================================================================

# Tätigkeits-zu-Skills Mapping für automatische Erkennung
taetigkeits_mapping = {
    "personenschutz": ["sicherheitsdienst", "deeskalation", "verantwortungsbewusstsein", "kommunikation", "objektschutz", "zuverlässigkeit"],
    "objektschutz": ["objektschutz", "kontrollgänge", "zugangskontrolle", "berichtswesen", "sicherheitsdienst", "zuverlässigkeit"],
    "revierdienst": ["kontrollgänge", "berichtswesen", "sicherheitsdienst", "zugangskontrolle", "schichtbereitschaft"],
    "fachkraft für schutz und sicherheit": ["sicherheitsdienst", "objektschutz", "zugangskontrolle", "kontrollgänge", "deeskalation", "berichtswesen", "sachkundeprüfung 34a", "zuverlässigkeit"],
    "servicekraft für schutz und sicherheit": ["sicherheitsdienst", "objektschutz", "zugangskontrolle", "kontrollgänge", "deeskalation", "zuverlässigkeit"],
    "sachkundeprüfung 34a": ["sicherheitsdienst", "zugangskontrolle", "objektschutz", "sachkundeprüfung 34a"],
    "sachkunde 34a": ["sicherheitsdienst", "zugangskontrolle", "objektschutz", "sachkundeprüfung 34a"],
    "unterrichtung 34a": ["sicherheitsdienst", "zugangskontrolle", "objektschutz"],
    "empfangsdienst": ["kundenservice", "kommunikation", "zugangskontrolle"],
    "streifendienst": ["kontrollgänge", "sicherheitsdienst", "berichtswesen"],
    "sicherheitsdienst": ["sicherheitsdienst", "objektschutz", "zugangskontrolle", "kontrollgänge", "berichtswesen", "deeskalation", "zuverlässigkeit"],
    "kontrollgänge": ["kontrollgänge", "berichtswesen", "sicherheitsdienst"],
    "zugangskontrolle": ["zugangskontrolle", "sicherheitsdienst", "objektschutz"],
    "deeskalation": ["deeskalation", "kommunikation", "verantwortungsbewusstsein"],
    "berichtswesen": ["berichtswesen", "kommunikation"],
    "bundeswehr": ["belastbarkeit", "teamfähigkeit", "verantwortungsbewusstsein", "schichtbereitschaft", "disziplin", "zuverlässigkeit", "sicherheitsdienst"],
    "soldat": ["belastbarkeit", "teamfähigkeit", "verantwortungsbewusstsein", "schichtbereitschaft", "zuverlässigkeit", "sicherheitsdienst"],
    "krankenschwester": ["pflegefachkraft", "grundpflege", "behandlungspflege", "pflegedokumentation", "patientenbetreuung"],
    "krankenpfleger": ["pflegefachkraft", "grundpflege", "behandlungspflege", "pflegedokumentation", "patientenbetreuung"],
    "altenpflege": ["grundpflege", "pflegeplanung", "patientenbetreuung", "dokumentation"],
    "einzelhandel": ["kundenberatung", "verkaufsgespräche", "kundenkontakt", "beschwerdemanagement", "serviceorientierung"],
    "kundenberatung": ["vertrieb", "kommunikation", "kundenkontakt"],
    "büromanagement": ["organisation", "terminplanung", "e-mail bearbeitung", "microsoft office", "verwaltung"],
    "kaufmann für büromanagement": ["organisation", "terminplanung", "e-mail bearbeitung", "microsoft office", "verwaltung", "büroassistenz"]
}

# Führerschein-Hierarchie: Was erfüllt was
fuehrerschein_erfuellung = {
    "B": ["B"],
    "BE": ["B", "BE"],
    "C1": ["B", "C1"],
    "C1E": ["B", "C1", "C1E"],
    "C": ["B", "C1", "C"],
    "CE": ["B", "C1", "C", "C1E", "CE"],
    "D": ["B", "D"],
    "DE": ["B", "D", "DE"]
}

# Softskills und Rahmenbedingungen - KEINE Qualifizierungen
softskill_no_training = {
    "zuverlässigkeit",
    "verantwortungsbewusstsein",
    "belastbarkeit",
    "teamfähigkeit",
    "teamarbeit",
    "kommunikation",
    "empathie",
    "schichtbereitschaft",
    "kundenkontakt",
    "freundliches auftreten",
    "organisation",
    "sorgfalt",
    "disziplin",
    "serviceorientierung",
    "kundenorientierung",
    "kreativität",
    "problemlösung",
    "analytisches denken",
    "eigeninitiative",
    "motivation",
    "flexibilität",
    "zielorientierung",
    "abschlussorientierung"
}

# Qualifikationen die durch formale Qualifikation automatisch erfüllt sind
qualifikation_automatisch_erfuellt = {
    "fachkraft für schutz und sicherheit": [
        "sachkundeprüfung 34a",
        "unterrichtung 34a",
        "grundqualifikation sicherheitsdienst",
        "sicherheitsdienst",
        "objektschutz",
        "zugangskontrolle",
        "kontrollgänge"
    ],
    "gesundheits- und krankenpfleger": [
        "krankenschwester",
        "pflegefachfrau",
        "pflegefachmann",
        "grundpflege",
        "behandlungspflege",
        "pflegefachkraft"
    ],
    "pflegefachkraft": [
        "pflegefachfrau",
        "pflegefachmann",
        "grundpflege",
        "behandlungspflege",
        "gesundheits- und krankenpfleger",
        "altenpfleger"
    ],
    "fitnesstrainer b-lizenz": [
        "fitnesstrainer",
        "trainingsbetreuung",
        "trainingsplanung"
    ]
}
qualifikations_synonyme = {
    "Gesundheits und Krankenpfleger": ["Krankenschwester", "Pflegefachfrau", "Pflegefachmann", "Altenpfleger", "Krankenpflegehelfer"],
    "Pflegefachfrau": ["Gesundheits und Krankenpfleger", "Krankenschwester", "Pflegefachmann", "Altenpfleger"],
    "Pflegefachmann": ["Gesundheits und Krankenpfleger", "Krankenschwester", "Pflegefachfrau", "Altenpfleger"],
    "Krankenschwester": ["Gesundheits und Krankenpfleger", "Pflegefachfrau", "Pflegefachmann", "Altenpfleger"],
    "Altenpfleger": ["Gesundheits und Krankenpfleger", "Pflegefachfrau", "Pflegefachmann", "Krankenschwester"],
    "Einzelhandelskaufmann": ["Vertrieb", "Kundenservice"],
    "Kaufmann für Büromanagement": ["HR / Personal", "Buchhaltung", "Kundenservice", "Büroassistenz"],
    "Industriekaufmann": ["Einkauf", "Buchhaltung", "Controlling", "Vertrieb", "Projektmanagement"],
    "Fachinformatiker Systemintegration": ["IT Support"],
    "Fachinformatiker Anwendungsentwicklung": ["Softwareentwicklung"],
    "Fachkraft für Schutz und Sicherheit": ["Sicherheitsdienst", "Sachkundeprüfung 34a", "Unterrichtung 34a"],
    "Servicekraft Schutz und Sicherheit": ["Sicherheitsdienst"],
    "Sachkundeprüfung 34a": ["Sicherheitsdienst", "Fachkraft für Schutz und Sicherheit"],
    "Unterrichtung 34a": ["Sicherheitsdienst", "Fachkraft für Schutz und Sicherheit"],
    "DATEV": ["Buchhaltung"],
    "Bundeswehr": ["Führung", "Belastbarkeit", "Sicherheit"],
    "Personaldienstleistungskaufmann": ["HR / Personal"],
    "Personalfachkaufmann": ["HR Business Partner", "Recruiter", "HR / Personal"],
    "Fitnesstrainer B-Lizenz": ["Fitnesstrainer", "Personaltrainer"],
    "Medizinische Fachangestellte": ["MFA", "Arzthelfer"],
    "Verwaltungsfachangestellter": ["Office Manager", "Büroassistenz"],
    "Sport- und Fitnesskaufmann": ["Fitnesstrainer", "Eventmanagement"]
}

pflege_synonyme = [
    "Krankenschwester",
    "Krankenpfleger",
    "Gesundheits- und Krankenpfleger",
    "Gesundheits und Krankenpfleger",
    "Gesundheits- und Krankenpflegerin",
    "Pflegefachfrau",
    "Pflegefachmann",
    "Pflegefachkraft",
    "Altenpfleger",
    "Altenpflegerin"
]
for pflege_qualifikation in pflege_synonyme:
    qualifikations_synonyme.setdefault(pflege_qualifikation, [])
    qualifikations_synonyme[pflege_qualifikation].extend(
        synonym for synonym in pflege_synonyme if synonym != pflege_qualifikation
    )

qualifikations_synonyme.update({
    "Sachkunde 34a": ["Sachkundeprüfung 34a", "Fachkraft für Schutz und Sicherheit", "Sicherheitsdienst"],
    "B Lizenz": ["Fitnesstrainer B-Lizenz", "Fitnesstrainer", "Trainer B Lizenz"],
    "Trainer B Lizenz": ["Fitnesstrainer B-Lizenz", "Fitnesstrainer", "B Lizenz"],
    "Teamleitung": ["Führungserfahrung"],
    "Personalmanager": ["Personalreferent", "HR Business Partner", "HR / Personal"],
    "Personalreferent": ["Personalmanager", "HR Business Partner", "HR / Personal"],
    "Wirtschaftspsychologie": ["HR / Personal", "Personalentwicklung"],
    "Change Manager": ["Change Management", "HR Business Partner"],
    "Ausbilder gemäß AEVO": ["AEVO", "Personalentwicklung"],
    "AEVO": ["Ausbilder gemäß AEVO", "Personalentwicklung"],
    "Ernährungsberater": ["Fitnesstrainer", "Gesundheitsförderung"],
    "Fitnesstrainer": ["Fitnesstrainer B-Lizenz", "Personaltrainer"]
})

for pflege_qualifikation in pflege_synonyme:
    qualifikation_automatisch_erfuellt.setdefault(pflege_qualifikation, [])
    qualifikation_automatisch_erfuellt[pflege_qualifikation].extend([
        "grundpflege",
        "behandlungspflege",
        "pflegedokumentation",
        "patientenbetreuung",
        "hygiene",
        "pflegefachkraft"
    ])

qualifikation_automatisch_erfuellt.update({
    "Servicekraft für Schutz und Sicherheit": [
        "sicherheitsdienst",
        "objektschutz",
        "zugangskontrolle",
        "kontrollgänge",
        "deeskalation"
    ],
    "Sachkunde 34a": [
        "sachkundeprüfung 34a",
        "sicherheitsdienst",
        "zugangskontrolle",
        "objektschutz"
    ],
    "B Lizenz": [
        "fitnesstrainer",
        "trainingsbetreuung",
        "trainingsplanung"
    ],
    "Trainer B Lizenz": [
        "fitnesstrainer",
        "trainingsbetreuung",
        "trainingsplanung"
    ]
})

# Gehaltsrahmen pro Berufsgruppe und Erfahrungslevel
gehaltsrahmen_nach_beruf = {
    "Büroassistenz": {
        "junior": {"min": 30000, "max": 38000},
        "mid": {"min": 36000, "max": 46000},
        "senior": {"min": 43000, "max": 55000}
    },
    "HR / Personal": {
        "junior": {"min": 38000, "max": 48000},
        "mid": {"min": 48000, "max": 65000},
        "senior": {"min": 65000, "max": 85000},
        "expert": {"min": 80000, "max": 110000}
    },
    "Lager / Logistik": {
        "junior": {"min": 28000, "max": 36000},
        "mid": {"min": 34000, "max": 45000},
        "senior": {"min": 42000, "max": 55000}
    },
    "Maler und Lackierer": {
        "junior": {"min": 30000, "max": 38000},
        "mid": {"min": 36000, "max": 48000},
        "senior": {"min": 45000, "max": 58000}
    },
    "Pflege": {
        "junior": {"min": 35000, "max": 43000},
        "mid": {"min": 42000, "max": 52000},
        "senior": {"min": 50000, "max": 65000}
    },
    "Vertrieb": {
        "junior": {"min": 35000, "max": 45000},
        "mid": {"min": 45000, "max": 65000},
        "senior": {"min": 60000, "max": 90000}
    },
    "IT Support": {
        "junior": {"min": 38000, "max": 50000},
        "mid": {"min": 50000, "max": 65000},
        "senior": {"min": 65000, "max": 85000}
    },
    "Buchhaltung": {
        "junior": {"min": 38000, "max": 48000},
        "mid": {"min": 48000, "max": 65000},
        "senior": {"min": 60000, "max": 80000}
    },
    "Kundenservice": {
        "junior": {"min": 28000, "max": 36000},
        "mid": {"min": 34000, "max": 45000},
        "senior": {"min": 42000, "max": 55000}
    },
    "Sicherheitsdienst": {
        "junior": {"min": 28000, "max": 36000},
        "mid": {"min": 34000, "max": 46000},
        "senior": {"min": 42000, "max": 60000}
    },
    "Projektmanagement": {
        "junior": {"min": 45000, "max": 58000},
        "mid": {"min": 58000, "max": 78000},
        "senior": {"min": 75000, "max": 100000}
    },
    "Controlling": {
        "junior": {"min": 45000, "max": 58000},
        "mid": {"min": 58000, "max": 78000},
        "senior": {"min": 75000, "max": 100000}
    },
    "Marketing": {
        "junior": {"min": 38000, "max": 50000},
        "mid": {"min": 50000, "max": 70000},
        "senior": {"min": 65000, "max": 90000}
    },
    "E-Commerce": {
        "junior": {"min": 38000, "max": 50000},
        "mid": {"min": 50000, "max": 70000},
        "senior": {"min": 65000, "max": 90000}
    },
    "Data Analyst": {
        "junior": {"min": 45000, "max": 58000},
        "mid": {"min": 58000, "max": 78000},
        "senior": {"min": 75000, "max": 100000}
    },
    "Softwareentwicklung": {
        "junior": {"min": 50000, "max": 65000},
        "mid": {"min": 65000, "max": 85000},
        "senior": {"min": 85000, "max": 115000}
    },
    "Einkauf": {
        "junior": {"min": 38000, "max": 48000},
        "mid": {"min": 48000, "max": 65000},
        "senior": {"min": 60000, "max": 85000}
    },
    "Assistenz der Geschäftsführung": {
        "junior": {"min": 32000, "max": 42000},
        "mid": {"min": 40000, "max": 55000},
        "senior": {"min": 50000, "max": 70000}
    },
    "Qualitätsmanagement": {
        "junior": {"min": 38000, "max": 48000},
        "mid": {"min": 48000, "max": 65000},
        "senior": {"min": 60000, "max": 80000}
    },
    "Fitnesstrainer": {
        "junior": {"min": 28000, "max": 35000},
        "mid": {"min": 34000, "max": 45000},
        "senior": {"min": 42000, "max": 58000}
    },
    "HR Business Partner": {
        "junior": {"min": 45000, "max": 58000},
        "mid": {"min": 60000, "max": 80000},
        "senior": {"min": 75000, "max": 100000},
        "expert": {"min": 95000, "max": 130000}
    },
    "Recruiter": {
        "junior": {"min": 35000, "max": 48000},
        "mid": {"min": 50000, "max": 70000},
        "senior": {"min": 65000, "max": 90000}
    },
    "Pflegefachkraft": {
        "junior": {"min": 35000, "max": 43000},
        "mid": {"min": 42000, "max": 52000},
        "senior": {"min": 50000, "max": 65000}
    },
    "Medizinische Fachangestellte": {
        "junior": {"min": 28000, "max": 36000},
        "mid": {"min": 34000, "max": 45000},
        "senior": {"min": 42000, "max": 55000}
    },
    "Verwaltungsfachangestellter": {
        "junior": {"min": 28000, "max": 36000},
        "mid": {"min": 34000, "max": 45000},
        "senior": {"min": 42000, "max": 55000}
    },
    "Office Manager": {
        "junior": {"min": 35000, "max": 46000},
        "mid": {"min": 45000, "max": 60000},
        "senior": {"min": 55000, "max": 75000}
    }
}

for gehalt_profile in gehaltsrahmen_nach_beruf.values():
    if "expert" not in gehalt_profile and "senior" in gehalt_profile:
        senior_min = gehalt_profile["senior"]["min"]
        senior_max = gehalt_profile["senior"]["max"]
        gehalt_profile["expert"] = {
            "min": max(senior_min, int(senior_max * 0.85)),
            "max": int(senior_max * 1.15)
        }


# Qualifizierungskatalog
qualifizierungs_katalog = {
    "SAP": {
        "schulung": "SAP Grundlagenschulung",
        "dauer": "2 bis 5 Tage",
        "kosten": "700 bis 2.500 €",
        "prioritaet": "mittel"
    },
    "SAP HR": {
        "schulung": "SAP HR / HCM Grundlagenschulung",
        "dauer": "3 bis 5 Tage",
        "kosten": "1.000 bis 3.000 €",
        "prioritaet": "mittel"
    },
    "Excel": {
        "schulung": "Excel Grundlagen oder Aufbaukurs",
        "dauer": "1 bis 2 Tage",
        "kosten": "300 bis 900 €",
        "prioritaet": "mittel"
    },
    "DATEV": {
        "schulung": "DATEV Grundlagenschulung Buchhaltung",
        "dauer": "2 bis 3 Tage",
        "kosten": "500 bis 1.200 €",
        "prioritaet": "hoch"
    },
    "Staplerschein": {
        "schulung": "Staplerschein / Flurförderzeugschulung",
        "dauer": "1 bis 3 Tage",
        "kosten": "150 bis 400 €",
        "prioritaet": "hoch"
    },
    "Führungskräfteberatung": {
        "schulung": "HR Business Partner Training / Führungskräfteberatung",
        "dauer": "2 bis 5 Tage",
        "kosten": "800 bis 2.500 €",
        "prioritaet": "hoch"
    },
    "Arbeitsrecht": {
        "schulung": "Grundlagen Arbeitsrecht",
        "dauer": "2 bis 3 Tage",
        "kosten": "600 bis 1.800 €",
        "prioritaet": "hoch"
    },
    "Betriebsratsarbeit": {
        "schulung": "Zusammenarbeit mit dem Betriebsrat",
        "dauer": "1 bis 3 Tage",
        "kosten": "500 bis 1.500 €",
        "prioritaet": "mittel"
    },
    "Change Management": {
        "schulung": "Grundlagen Change Management",
        "dauer": "2 bis 4 Tage",
        "kosten": "800 bis 2.500 €",
        "prioritaet": "mittel"
    },
    "CRM": {
        "schulung": "CRM Grundlagenschulung",
        "dauer": "1 bis 2 Tage",
        "kosten": "300 bis 1.000 €",
        "prioritaet": "mittel"
    },
    "Salesforce": {
        "schulung": "Salesforce Grundlagen",
        "dauer": "2 bis 5 Tage",
        "kosten": "900 bis 3.000 €",
        "prioritaet": "mittel"
    },
    "Microsoft 365": {
        "schulung": "Microsoft 365 Grundlagen",
        "dauer": "1 bis 3 Tage",
        "kosten": "400 bis 1.200 €",
        "prioritaet": "mittel"
    },
    "Active Directory": {
        "schulung": "Active Directory Grundlagen",
        "dauer": "2 bis 4 Tage",
        "kosten": "800 bis 2.500 €",
        "prioritaet": "hoch"
    },
    "IT Sicherheit": {
        "schulung": "IT Security Grundlagen",
        "dauer": "2 bis 5 Tage",
        "kosten": "900 bis 3.000 €",
        "prioritaet": "hoch"
    },
    "Pflegedokumentation": {
        "schulung": "Pflegedokumentation und Pflegeplanung",
        "dauer": "1 bis 2 Tage",
        "kosten": "250 bis 800 €",
        "prioritaet": "hoch"
    },
    "Hygiene": {
        "schulung": "Hygieneschulung Pflege",
        "dauer": "1 Tag",
        "kosten": "100 bis 400 €",
        "prioritaet": "hoch"
    },
    "Medikamentengabe": {
        "schulung": "Medikamentengabe Schulung",
        "dauer": "1 bis 2 Tage",
        "kosten": "200 bis 700 €",
        "prioritaet": "hoch"
    },
    "Ladungssicherung": {
        "schulung": "Ladungssicherung Schulung",
        "dauer": "1 bis 2 Tage",
        "kosten": "200 bis 600 €",
        "prioritaet": "mittel"
    },
    "Warenwirtschaftssystem": {
        "schulung": "Warenwirtschaftssystem Grundlagen",
        "dauer": "1 bis 3 Tage",
        "kosten": "300 bis 1.200 €",
        "prioritaet": "mittel"
    }
}

# Softskill-Ähnlichkeiten
softskill_synonyme = {
    "Kundenservice": ["Kommunikation", "Serviceorientierung"],
    "Pflegeberatung": ["Angehörigenberatung"],
    "Dokumentation": ["Pflegedokumentation"],
    "Verkaufsgespräch": ["Kundenberatung"],
    "Teamführung": ["Führungserfahrung"],
    "Teamleitung": ["Führungserfahrung"],
    "Revierdienst": ["Kontrollgänge", "Berichtswesen"],
    "Objektschutz": ["Zugangskontrolle", "Kontrollgänge"],
    "Personenschutz": ["Sicherheitsdienst", "Deeskalation", "Verantwortungsbewusstsein"]
}

softskill_no_training_normalized = {normalize_text(skill) for skill in softskill_no_training}
qualifizierungs_lookup = {
    normalize_text(key): value
    for key, value in qualifizierungs_katalog.items()
}
qualifikations_synonyme_normalized = {
    normalize_text(key): {normalize_text(value) for value in values}
    for key, values in qualifikations_synonyme.items()
}
softskill_synonyme_normalized = {
    normalize_text(key): {normalize_text(value) for value in values}
    for key, values in softskill_synonyme.items()
}
qualifikation_automatisch_erfuellt_normalized = {
    normalize_text(key): {normalize_text(value) for value in values}
    for key, values in qualifikation_automatisch_erfuellt.items()
}

# Initialize additional session state for document analysis
if "lebenslauf_text" not in st.session_state:
    st.session_state.lebenslauf_text = ""
if "stellenprofil_text" not in st.session_state:
    st.session_state.stellenprofil_text = ""
if "recognized_skills" not in st.session_state:
    st.session_state.recognized_skills = []
if "recognized_pflicht" not in st.session_state:
    st.session_state.recognized_pflicht = []

if "reset_counter" not in st.session_state:
    st.session_state.reset_counter = 0

if "show_results" not in st.session_state:
    st.session_state.show_results = False 
if "calculation_complete" not in st.session_state:
    st.session_state.calculation_complete = False
if "results" not in st.session_state:
    st.session_state.results = {}
if "cv_autofill_signature" not in st.session_state:
    st.session_state.cv_autofill_signature = ""
    
# Reset-Funktion
def reset_inputs():
    st.session_state.reset_counter += 1
    st.session_state.show_results = False
    st.session_state.calculation_complete = False
    st.session_state.results = {}
    st.session_state.cv_autofill_signature = ""
    st.rerun()

# CSS für besseres Design
st.markdown("""
    <style>
    .main {
        padding-top: 1rem;
    }
    .stMetric {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
    }
    </style>
""", unsafe_allow_html=True)

st.title("📄 Lebenslauf & Stellenprofil Matching")
st.write("""
**Schlankes Matching für Lebenslauf & Stellenprofil**

Lade einen Lebenslauf hoch oder füge den Text ein. Füge anschließend ein Stellenprofil als Text, PDF oder Link hinzu.
Das Tool extrahiert Skills, Qualifikationen, Berufserfahrung und optional den Gehaltsrahmen.
**Die Ergebnisse sind unterstützende Hinweise, keine finale Entscheidung.**
""")

berufsgruppen = {
    "Büroassistenz": {
        "pflichtskills": ["Office", "Terminplanung", "Kommunikation"],
        "wunschskills": ["Excel", "Textverarbeitung", "Teamarbeit"],
        "qualifikationen": ["Kaufmann für Büromanagement", "Assistenz der Geschäftsführung", "Sekretärin", "Bürofachkraft"]
    },
    "HR / Personal": {
        "pflichtskills": [
            "Personalbetreuung",
            "Recruiting",
            "Arbeitsrecht",
            "Vertragswesen",
            "Mitarbeitergespräche",
            "Führungskräfteberatung",
            "Onboarding",
            "HR Administration"
        ],
        "wunschskills": [
            "SAP HR",
            "Personio",
            "Betriebsratsarbeit",
            "Change Management",
            "Personalentwicklung",
            "Personalcontrolling",
            "Employer Branding",
            "Excel"
        ],
        "qualifikationen": [
            "Personalfachkaufmann",
            "Personalreferent",
            "Personaldienstleistungskaufmann",
            "Betriebswirtschaft mit Schwerpunkt Personal",
            "HR Management",
            "Wirtschaftsrecht",
            "Kaufmann für Büromanagement mit HR Erfahrung"
        ]
    },
}

berufsprofile = {
    "Lager / Logistik": {
        "pflichtskills": [
            "Wareneingang",
            "Warenausgang",
            "Kommissionierung",
            "Verpackung",
            "Lagerung",
            "Bestandskontrolle",
            "Inventur",
            "Scanner",
            "körperliche Belastbarkeit",
            "Zuverlässigkeit"
        ],
        "wunschskills": [
            "Staplerschein",
            "SAP",
            "Warenwirtschaftssystem",
            "Warehouse Management System",
            "Retourenbearbeitung",
            "Schichtbereitschaft",
            "Ladungssicherung",
            "Führerschein Klasse B"
        ],
        "qualifikationen": [
            "Fachlagerist",
            "Fachkraft für Lagerlogistik",
            "Lagerhelfer mit Berufserfahrung",
            "Handelsfachpacker",
            "Staplerschein",
            "Berufserfahrung Lagerlogistik"
        ]
    },
    "Maler und Lackierer": {
        "pflichtskills": [
            "Malerarbeiten",
            "Lackieren",
            "Tapezieren",
            "Spachteln",
            "Schleifen",
            "Untergrundvorbereitung",
            "Streichen",
            "Beschichten",
            "Kundenkontakt",
            "sauberes Arbeiten"
        ],
        "wunschskills": [
            "Fassadenarbeiten",
            "Trockenbau",
            "Wärmedämmung",
            "Bodenverlegung",
            "Schimmelbeseitigung",
            "Aufmaß",
            "Führerschein Klasse B",
            "Baustellenerfahrung"
        ],
        "qualifikationen": [
            "Maler und Lackierer",
            "Bauten und Korrosionsschutz",
            "Gestaltung und Instandhaltung",
            "Ausbautechnik und Oberflächengestaltung",
            "Malerhelfer mit Berufserfahrung",
            "Malermeister"
        ]
    },
    "Pflege": {
        "pflichtskills": [
            "Grundpflege",
            "Behandlungspflege",
            "Pflegedokumentation",
            "Vitalzeichenkontrolle",
            "Medikamentengabe",
            "Wundversorgung",
            "Patientenbetreuung",
            "Hygiene",
            "Empathie",
            "Belastbarkeit"
        ],
        "wunschskills": [
            "Schichtbereitschaft",
            "Demenzbetreuung",
            "Angehörigenberatung",
            "Notfallmanagement",
            "Qualitätsmanagement",
            "Pflegeplanung",
            "EDV Dokumentation",
            "Führerschein Klasse B"
        ],
        "qualifikationen": [
            "Pflegefachmann",
            "Pflegefachfrau",
            "Gesundheits und Krankenpfleger",
            "Altenpfleger",
            "Krankenpflegehelfer",
            "Pflegehelfer mit Berufserfahrung",
            "Heilerziehungspfleger"
        ]
    },
    "Vertrieb": {
        "pflichtskills": [
            "Kundenberatung",
            "Verkaufsgespräche",
            "Angebotserstellung",
            "Kundenakquise",
            "Verhandlungsgeschick",
            "CRM",
            "Kommunikation",
            "Abschlussorientierung",
            "Produktkenntnisse",
            "Zielorientierung"
        ],
        "wunschskills": [
            "B2B Vertrieb",
            "Key Account Management",
            "Kaltakquise",
            "Salesforce",
            "HubSpot",
            "Marktbeobachtung",
            "Umsatzplanung",
            "Präsentationstechniken",
            "Englisch"
        ],
        "qualifikationen": [
            "Kaufmann im Groß und Außenhandelsmanagement",
            "Industriekaufmann",
            "Kaufmann im Einzelhandel",
            "Vertriebsmitarbeiter mit Berufserfahrung",
            "Sales Manager",
            "Betriebswirtschaftliches Studium"
        ]
    },
    "IT Support": {
        "pflichtskills": [
            "IT Support",
            "Fehleranalyse",
            "Windows",
            "Hardware",
            "Software",
            "Netzwerke",
            "Ticketsystem",
            "Benutzersupport",
            "Systemdokumentation",
            "Kundenorientierung"
        ],
        "wunschskills": [
            "Active Directory",
            "Microsoft 365",
            "Azure",
            "Linux",
            "IT Sicherheit",
            "Remote Support",
            "Helpdesk",
            "Serveradministration",
            "Englisch",
            "Cloud Computing"
        ],
        "qualifikationen": [
            "Fachinformatiker Systemintegration",
            "IT Systemelektroniker",
            "Informatikkaufmann",
            "IT Support Specialist",
            "Quereinsteiger IT mit Berufserfahrung",
            "Microsoft Zertifizierung"
        ]
    },
    "Buchhaltung": {
        "pflichtskills": [
            "Finanzbuchhaltung",
            "Debitorenbuchhaltung",
            "Kreditorenbuchhaltung",
            "Kontenabstimmung",
            "Rechnungsprüfung",
            "Zahlungsverkehr",
            "DATEV",
            "Excel",
            "Sorgfalt",
            "Zahlenverständnis"
        ],
        "wunschskills": [
            "Lohnbuchhaltung",
            "Jahresabschluss",
            "Umsatzsteuer",
            "SAP FI",
            "Kostenrechnung",
            "Mahnwesen",
            "HGB",
            "Controlling",
            "Reisekostenabrechnung"
        ],
        "qualifikationen": [
            "Buchhalter",
            "Finanzbuchhalter",
            "Steuerfachangestellter",
            "Kaufmann für Büromanagement mit Buchhaltungserfahrung",
            "Industriekaufmann",
            "Bilanzbuchhalter",
            "Betriebswirtschaftliches Studium"
        ]
    },
    "Kundenservice": {
        "pflichtskills": [
            "Kundenbetreuung",
            "Telefonservice",
            "E-Mail Bearbeitung",
            "Beschwerdemanagement",
            "Kommunikation",
            "Serviceorientierung",
            "Problemlösung",
            "CRM",
            "Dokumentation",
            "Freundliches Auftreten"
        ],
        "wunschskills": [
            "Chat Support",
            "Reklamationsbearbeitung",
            "Sales Support",
            "Kundenbindung",
            "Zendesk",
            "Freshdesk",
            "Englisch",
            "Schichtbereitschaft",
            "Social Media Support"
        ],
        "qualifikationen": [
            "Kaufmann für Dialogmarketing",
            "Kaufmann für Büromanagement",
            "Kaufmann im Einzelhandel",
            "Servicefachkraft Dialogmarketing",
            "Kundenberater mit Berufserfahrung",
            "Call Center Agent mit Berufserfahrung"
        ]
    },
    "Sicherheitsdienst": {
        "pflichtskills": [
            "Sicherheitsdienst", "Objektschutz", "Kontrollgänge", "Zugangskontrolle", "Deeskalation", "Berichtswesen"
        ],
        "wunschskills": [
            "Sachkundeprüfung 34a", "Ersthelfer", "Brandschutzhelfer", "Personenschutz",
            "Empfangsdienst", "Führerschein Klasse B", "Englisch", "Konfliktmanagement", "Streifendienst"
        ],
        "qualifikationen": [
            "Fachkraft für Schutz und Sicherheit", "Servicekraft für Schutz und Sicherheit",
            "Sachkundeprüfung 34a", "Unterrichtung 34a", "Sicherheitsmitarbeiter mit Berufserfahrung",
            "ehemaliger Soldat mit Sicherheitserfahrung"
        ]
    },
    "Projektmanagement": {
        "pflichtskills": [
            "Projektplanung", "Projektsteuerung", "Stakeholdermanagement", "Kommunikation",
            "Terminplanung", "Risikomanagement", "Budgetkontrolle", "Reporting", "Organisation", "Problemlösung"
        ],
        "wunschskills": [
            "Jira", "MS Project", "Scrum", "Agile Methoden", "Change Management",
            "Prozessmanagement", "Englisch", "Präsentationstechniken"
        ],
        "qualifikationen": [
            "Projektmanager", "Scrum Master", "Betriebswirtschaftliches Studium",
            "Wirtschaftsingenieurwesen", "Projektmanagement Zertifizierung", "Berufserfahrung Projektmanagement"
        ]
    },
    "Controlling": {
        "pflichtskills": [
            "Controlling", "Reporting", "Budgetplanung", "Forecasting", "Excel",
            "Kostenrechnung", "Abweichungsanalyse", "Zahlenverständnis", "Finanzanalyse", "Sorgfalt"
        ],
        "wunschskills": [
            "SAP CO", "Power BI", "SQL", "Jahresplanung", "Monatsabschluss",
            "KPI Analyse", "Business Intelligence", "Englisch"
        ],
        "qualifikationen": [
            "Controller", "Betriebswirtschaftliches Studium", "Industriekaufmann mit Controlling Erfahrung",
            "Bilanzbuchhalter", "Finanzbuchhalter mit Controlling Erfahrung"
        ]
    },
    "Marketing": {
        "pflichtskills": [
            "Marketing", "Kampagnenplanung", "Content Erstellung", "Zielgruppenanalyse", "Kommunikation",
            "Social Media", "Markenverständnis", "Projektkoordination", "Kreativität", "Reporting"
        ],
        "wunschskills": [
            "SEO", "SEA", "Google Analytics", "Meta Ads", "Canva",
            "Adobe Creative Cloud", "E-Mail Marketing", "Performance Marketing"
        ],
        "qualifikationen": [
            "Kaufmann für Marketingkommunikation", "Marketing Manager", "Mediengestalter mit Marketingerfahrung",
            "Betriebswirtschaftliches Studium mit Marketing Schwerpunkt", "Kommunikationswissenschaften"
        ]
    },
    "E-Commerce": {
        "pflichtskills": [
            "Online Shop Betreuung", "Produktdatenpflege", "Marketplace Management", "Kundenorientierung",
            "Warenwirtschaft", "Analyse", "Content Pflege", "Prozessverständnis", "Kommunikation", "Excel"
        ],
        "wunschskills": [
            "Shopify", "Amazon Seller Central", "Ebay", "SEO", "Google Analytics",
            "Performance Marketing", "ERP Systeme", "Retourenmanagement"
        ],
        "qualifikationen": [
            "Kaufmann im E-Commerce", "Kaufmann für Büromanagement mit E-Commerce Erfahrung",
            "Marketing Ausbildung", "Betriebswirtschaftliches Studium", "E-Commerce Manager"
        ]
    },
    "Data Analyst": {
        "pflichtskills": [
            "Datenanalyse", "Excel", "SQL", "Reporting", "Datenvisualisierung",
            "Zahlenverständnis", "Datenqualität", "analytisches Denken", "Statistik Grundlagen", "Kommunikation"
        ],
        "wunschskills": [
            "Python", "Power BI", "Tableau", "Pandas", "Machine Learning Grundlagen",
            "ETL", "Datenbanken", "Business Intelligence"
        ],
        "qualifikationen": [
            "Data Analyst", "Wirtschaftsinformatik", "Informatik", "Statistik",
            "Betriebswirtschaft mit Analytics Schwerpunkt", "Quereinsteiger mit Datenanalyse Erfahrung"
        ]
    },
    "Softwareentwicklung": {
        "pflichtskills": [
            "Programmierung", "Softwareentwicklung", "Problemlösung", "Git", "Testing",
            "Datenbanken", "API Verständnis", "saubere Code Struktur", "Dokumentation", "Teamarbeit"
        ],
        "wunschskills": [
            "Python", "JavaScript", "TypeScript", "React", "Backend Entwicklung",
            "Cloud", "Docker", "CI CD", "Agile Methoden"
        ],
        "qualifikationen": [
            "Fachinformatiker Anwendungsentwicklung", "Informatik Studium", "Softwareentwickler mit Berufserfahrung",
            "Quereinsteiger mit Projektportfolio", "Wirtschaftsinformatik"
        ]
    },
    "Assistenz der Geschäftsführung": {
        "pflichtskills": [
            "Terminmanagement", "Organisation", "Kommunikation", "Vertraulichkeit", "E-Mail Bearbeitung",
            "Reiseplanung", "Protokollführung", "Priorisierung", "Microsoft Office", "Zuverlässigkeit"
        ],
        "wunschskills": [
            "Englisch", "Projektkoordination", "Eventplanung", "Budgetübersicht",
            "Präsentationserstellung", "Stakeholdermanagement", "CRM"
        ],
        "qualifikationen": [
            "Kaufmann für Büromanagement", "Fremdsprachenkorrespondent", "Office Manager",
            "Assistenz der Geschäftsführung mit Berufserfahrung", "Betriebswirtschaftliche Ausbildung"
        ]
    },
    "Einkauf": {
        "pflichtskills": [
            "Einkauf", "Lieferantenmanagement", "Preisverhandlung", "Angebotseinholung", "Bestellwesen",
            "Vertragsprüfung", "Kommunikation", "Zahlenverständnis", "Organisation", "ERP Systeme"
        ],
        "wunschskills": [
            "SAP MM", "Englisch", "strategischer Einkauf", "Warengruppenmanagement",
            "Vertragsmanagement", "Kostenanalyse", "Lieferantenbewertung"
        ],
        "qualifikationen": [
            "Industriekaufmann", "Kaufmann im Groß und Außenhandelsmanagement", "Einkäufer mit Berufserfahrung",
            "Betriebswirtschaftliches Studium", "Supply Chain Management"
        ]
    },
    "Qualitätsmanagement": {
        "pflichtskills": [
            "Qualitätsmanagement", "Prozessmanagement", "Dokumentation", "Fehleranalyse", "Audit Vorbereitung",
            "Kommunikation", "Sorgfalt", "Normenverständnis", "Maßnahmenverfolgung", "Reporting"
        ],
        "wunschskills": [
            "ISO 9001", "Lean Management", "Six Sigma", "Reklamationsmanagement",
            "Risikomanagement", "Schulungserfahrung", "Prozessoptimierung"
        ],
        "qualifikationen": [
            "Qualitätsmanagementbeauftragter", "Qualitätsmanager", "Techniker mit QM Erfahrung",
            "Betriebswirtschaftliches Studium mit QM Erfahrung", "ISO 9001 Schulung"
        ]
    },
    "Fitnesstrainer": {
        "pflichtskills": [
            "Trainingsplanung", "Trainingsbetreuung", "Kundenberatung", "Anatomie Grundlagen",
            "Übungsanleitung", "Gesundheitsorientiertes Training", "Kommunikation", "Motivation",
            "Belastungssteuerung", "Serviceorientierung"
        ],
        "wunschskills": [
            "Medizinisches Fitnesstraining", "Ernährungsberatung", "Reha Training", "Prävention",
            "Personal Training", "Gruppentraining", "EMS Training", "Verkauf", "Erste Hilfe", "Social Media"
        ],
        "qualifikationen": [
            "Fitnesstrainer B-Lizenz", "Fitnesstrainer A-Lizenz", "Medizinischer Fitnesstrainer",
            "Sport- und Fitnesskaufmann", "Ernährungsberater", "Personal Trainer Lizenz",
            "Sportwissenschaft Studium", "Physiotherapeut mit Trainingserfahrung"
        ]
    },
    "HR Business Partner": {
        "pflichtskills": [
            "Personalbetreuung", "Arbeitsrecht", "HR Strategie", "Recruiting", "Führungskräfteentwicklung",
            "Change Management", "Kommunikation", "Mitarbeitergespräche", "Konfliktlösung", "Reporting"
        ],
        "wunschskills": [
            "SAP HR", "Talent Management", "Organisationsentwicklung", "Coaching", "Employer Branding",
            "Diversity Management", "Englisch", "Projektmanagement", "Performance Management"
        ],
        "qualifikationen": [
            "Personalfachkaufmann", "Diplom-Kaufmann mit HR Schwerpunkt", "HR Manager Zertifikat",
            "Wirtschaftspsychologie Studium", "HR Business Partner Zertifizierung", "MBA mit HR Fokus"
        ]
    },
    "Recruiter": {
        "pflichtskills": [
            "Recruiting", "Kandidatensuche", "Bewerberverwaltung", "ATS-Systeme", "Kommunikation",
            "Verhandlung", "Netzwerken", "Social Media Recruiting", "Anforderungsmanagement", "Reporting"
        ],
        "wunschskills": [
            "LinkedIn Recruiting", "Boolean Search", "Video Interviews", "Talent Pool Management",
            "Onboarding", "Active Sourcing", "Employer Branding", "Analytics", "Multi-Channel Recruiting"
        ],
        "qualifikationen": [
            "Recruiter Zertifikat", "Personalfachkaufmann", "HR Manager", "Business Degree",
            "Recruiting Spezialist mit Erfahrung", "Talent Acquisition Manager"
        ]
    },
    "Pflegefachkraft": {
        "pflichtskills": [
            "Grundpflege", "Behandlungspflege", "Pflegedokumentation", "Vitalzeichenkontrolle",
            "Medikamentengabe", "Wundversorgung", "Patientenbetreuung", "Hygiene", "Empathie", "Belastbarkeit"
        ],
        "wunschskills": [
            "Schichtbereitschaft", "Demenzbetreuung", "Angehörigenberatung", "Notfallmanagement",
            "Qualitätsmanagement", "Pflegeplanung", "EDV Dokumentation", "Spezialtraining", "Kommunikation"
        ],
        "qualifikationen": [
            "Pflegefachfrau", "Pflegefachmann", "Gesundheits- und Krankenpflegerin",
            "Altenpflegerin", "Krankenpflegehelfer", "Heilerziehungspfleger", "Berufserfahrung Pflege"
        ]
    },
    "Medizinische Fachangestellte": {
        "pflichtskills": [
            "Patientenbetreuung", "Praxisorganisation", "Terminplanung", "Abrechnungskenntnisse",
            "Blutentnahmen", "Injektionen", "EKG-Bedienung", "Hygiene", "Kommunikation", "Sorgfalt"
        ],
        "wunschskills": [
            "Laborarbeiten", "Röntgenassistenz", "Zahnmedizin", "Orthopädie", "Ultraschall",
            "Praxissoftware", "Englisch", "Qualitätsmanagement", "Weiterbildung"
        ],
        "qualifikationen": [
            "Medizinische Fachangestellte", "MFA Ausbildung", "Ärztliche Assistentin",
            "Zahnarzthelfer", "Berufserfahrung Praxis", "Spezialisierung im Gesundheitswesen"
        ]
    },
    "Verwaltungsfachangestellter": {
        "pflichtskills": [
            "Verwaltungsverfahren", "Büroorganisation", "Arbeitsrecht", "Datenschutz", "Terminplanung",
            "Schriftverkehr", "Aktenverwaltung", "Kommunikation", "Microsoft Office", "Sorgfalt"
        ],
        "wunschskills": [
            "Haushaltsplanung", "Kostenregelung", "Qualitätskontrolle", "Prozessoptimierung",
            "Rechnungswesen", "Personalverwaltung", "Englisch", "E-Government", "Digitalisierung"
        ],
        "qualifikationen": [
            "Verwaltungsfachangestellter", "Bürokaufmann", "Kaufmann für Büromanagement",
            "Verwaltungsausbildung", "Sachbearbeiter mit Ausbildung", "Betriebswirtschaftliche Grundkenntnisse"
        ]
    },
    "Office Manager": {
        "pflichtskills": [
            "Büroorganisation", "Terminplanung", "Reiseplanung", "Visitenkartenverwaltung",
            "Protokollführung", "Schriftverkehr", "Einkauf Office", "Kommunikation", "Multitasking", "Zuverlässigkeit"
        ],
        "wunschskills": [
            "Englisch", "Eventplanung", "Budgetmanagement", "Führungserfahrung", "Projektkoordination",
            "CRM Systeme", "Rechnungswesen", "HR-Support", "Facility Management"
        ],
        "qualifikationen": [
            "Kaufmann für Büromanagement", "Bürokaufmann", "Office Manager Zertifikat",
            "Assistenz der Geschäftsführung", "Sekretärin", "Administrative Ausbildung"
        ]
    }
}

berufsgruppen.update(berufsprofile)

berufsgruppe = st.selectbox(
    "Berufsgruppe / Zielposition",
    options=["Bitte auswählen"] + list(berufsgruppen.keys()),
    key="berufsgruppe"
)

selected_group = berufsgruppe if berufsgruppe in berufsgruppen else "Bitte auswählen"
selected_key = selected_group.lower().replace(" ", "_").replace("/", "_") if selected_group != "Bitte auswählen" else "none"

profile = berufsgruppen.get(selected_group, {})
suggested_pflicht = ", ".join(profile.get("pflichtskills", []))
suggested_wunsch = ", ".join(profile.get("wunschskills", []))
suggested_qualifikationen = ", ".join(profile.get("qualifikationen", []))

counter = st.session_state.reset_counter

bewerber_eingabe_key = f"bewerber_eingabe_{counter}"
qualifikation_bewerber_key = f"qualifikation_bewerber_{counter}"
bewerber_erfahrung_key = f"bewerber_erfahrung_{counter}"

st.divider()

# Datenschutz-Hinweis
st.warning("""
**Hinweis zum Datenschutz:** Hochgeladene Dateien werden in dieser MVP-Version nur während der aktuellen Sitzung verarbeitet und nicht dauerhaft gespeichert. Bitte laden Sie keine sensiblen personenbezogenen Daten hoch, wenn keine Rechtsgrundlage oder Einwilligung vorliegt. Für einen produktiven Einsatz sind Datenschutzkonzept, Löschkonzept, Rollen-/Rechtekonzept und DSGVO-konforme Verarbeitung erforderlich.
""")

# Lebenslauf Upload (optional)
st.subheader("Lebenslauf hochladen (optional)")
uploaded_lebenslauf = st.file_uploader(
    "Lebenslauf (PDF)",
    type=["pdf"],
    key=f"lebenslauf_upload_{counter}"
)

lebenslauf_text = ""
cv_analyse = {
    "skills": [],
    "qualifikationen": [],
    "berufserfahrung_jahre": None,
    "fuehrerscheine": [],
    "sprachen": [],
    "zertifikate": [],
    "taetigkeiten": [],
    "transfer_skills": []
}
cv_erkennung = extract_skills_from_cv(
    lebenslauf_text,
    split_normalized_values(suggested_pflicht),
    split_normalized_values(suggested_wunsch),
    split_normalized_values(suggested_qualifikationen),
    qualifikations_synonyme,
    softskill_synonyme,
    taetigkeits_mapping
)

if uploaded_lebenslauf:
    lebenslauf_text = extract_text_from_pdf(uploaded_lebenslauf)
    if lebenslauf_text:
        st.session_state.lebenslauf_text = lebenslauf_text
        st.success("✓ PDF erfolgreich verarbeitet")

        lebenslauf_display = normalize_display_text(lebenslauf_text)
        with st.expander("Lebenslauf Vorschau (erste 1500 Zeichen)"):
            preview_text = lebenslauf_display[:1500] + "..." if len(lebenslauf_display) > 1500 else lebenslauf_display
            st.text_area("Lebenslauf-Text", preview_text, height=180, disabled=True)

        cv_analyse = analyze_cv_text(
            lebenslauf_text,
            selected_group,
            berufsgruppen,
            qualifikations_synonyme,
            softskill_synonyme,
            taetigkeits_mapping
        )
        cv_erkennung = extract_skills_from_cv(
            lebenslauf_text,
            split_normalized_values(suggested_pflicht),
            split_normalized_values(suggested_wunsch),
            split_normalized_values(suggested_qualifikationen),
            qualifikations_synonyme,
            softskill_synonyme,
            taetigkeits_mapping
        )

        selected_normalized = normalize_text(selected_group)
        fuehrerschein_autofill_skills = (
            fuehrerschein_skills_from_classes(cv_analyse["fuehrerscheine"])
            if "sicherheitsdienst" in selected_normalized
            else []
        )
        auto_skills = combine_values(
            cv_analyse["transfer_skills"],
            cv_analyse["skills"],
            cv_analyse["sprachen"],
            cv_analyse["zertifikate"],
            fuehrerschein_autofill_skills
        )
        auto_qualifikationen = combine_values(cv_analyse["qualifikationen"])
        autofill_signature = (
            f"{getattr(uploaded_lebenslauf, 'name', 'lebenslauf')}:"
            f"{getattr(uploaded_lebenslauf, 'size', 0)}:"
            f"{selected_group}:"
            f"{counter}"
        )
        should_apply_autofill = st.session_state.get("cv_autofill_signature") != autofill_signature

        if should_apply_autofill and auto_skills:
            st.session_state[bewerber_eingabe_key] = combine_values(
                st.session_state.get(bewerber_eingabe_key, ""),
                auto_skills
            )
        if should_apply_autofill and auto_qualifikationen:
            st.session_state[qualifikation_bewerber_key] = combine_values(
                st.session_state.get(qualifikation_bewerber_key, ""),
                auto_qualifikationen
            )
        if should_apply_autofill and cv_analyse["berufserfahrung_jahre"] is not None:
            current_experience = st.session_state.get(bewerber_erfahrung_key, 0)
            if not current_experience:
                st.session_state[bewerber_erfahrung_key] = min(cv_analyse["berufserfahrung_jahre"], 50)
        if should_apply_autofill:
            st.session_state.cv_autofill_signature = autofill_signature

        if cv_analyse["skills"] or cv_analyse["qualifikationen"] or cv_analyse["fuehrerscheine"]:
            with st.expander("Automatisch erkannte Skills aus dem Lebenslauf"):
                st.write(f"**Skills:** {format_detected_values(cv_analyse['skills'])}")
                st.write(f"**Qualifikationen:** {format_detected_values(cv_analyse['qualifikationen'])}")
                st.write(f"**Führerscheine:** {format_detected_values(cv_analyse['fuehrerscheine'])}")
                st.write(f"**Sprachen:** {format_detected_values(cv_analyse['sprachen'])}")
                st.write(f"**Zertifikate:** {format_detected_values(cv_analyse['zertifikate'])}")
                if cv_analyse["berufserfahrung_jahre"] is not None:
                    st.write(f"**Berufserfahrung:** {cv_analyse['berufserfahrung_jahre']} Jahre")

        cv_summary = generate_cv_summary(cv_analyse, selected_group)
        if cv_summary:
            with st.expander("Lebenslauf Zusammenfassung"):
                st.write(cv_summary)
    else:
        st.session_state.lebenslauf_text = ""
        st.warning("Der Lebenslauf konnte nicht vollständig ausgelesen werden. Bitte Bewerber-Skills manuell ergänzen.")

st.divider()

bewerber_eingabe = st.text_area(
    "Skills des Bewerbers",
    placeholder="z. B. Recruiting, Arbeitsrecht, Excel, Personalbetreuung",
    key=bewerber_eingabe_key
)

pflicht_skills_eingabe = st.text_area(
    "Pflichtskills der Stelle (höhere Gewichtung)",
    placeholder="z. B. Recruiting, Arbeitsrecht",
    value=suggested_pflicht,
    key=f"pflicht_skills_eingabe_{counter}_{selected_key}"
)

wunsch_skills_eingabe = st.text_area(
    "Wunschskills der Stelle (niedrigere Gewichtung)",
    placeholder="z. B. SAP, HR Business Partner, Excel",
    value=suggested_wunsch,
    key=f"wunsch_skills_eingabe_{counter}_{selected_key}"
)

col_qual_bewerber, col_qual_stelle = st.columns(2)

with col_qual_bewerber:
    qualifikation_bewerber = st.text_area(
        "Qualifikation des Bewerbers",
        placeholder="z. B. Personalfachkaufmann",
        key=qualifikation_bewerber_key,
        height=80
    )

with col_qual_stelle:
    qualifikation_stelle = st.text_area(
        "Erforderliche Qualifikation",
        placeholder="z. B. Personalfachkaufmann",
        value=suggested_qualifikationen,
        key=f"qualifikation_stelle_{counter}_{selected_key}",
        height=80
    )

col_bewerber, col_stelle = st.columns(2)

with col_bewerber:
    bewerber_erfahrung = st.number_input(
        "Berufserfahrung des Bewerbers in Jahren",
        min_value=0,
        max_value=50,
        value=0,
        step=1,
        key=bewerber_erfahrung_key
    )

with col_stelle:
    stelle_min_erfahrung = st.number_input(
        "Geforderte Berufserfahrung in Jahren",
        min_value=0,
        max_value=50,
        value=0,
        step=1,
        key=f"stelle_min_erfahrung_{counter}"
    )

col_gehalt_bewerber, col_gehalt_stelle = st.columns(2)

with col_gehalt_bewerber:
    bewerber_gehalt = st.number_input(
        "Gehaltswunsch des Bewerbers (€ brutto/Jahr)",
        min_value=0,
        max_value=200000,
        value=0,
        step=1000,
        key=f"bewerber_gehalt_{counter}"
    )

with col_gehalt_stelle:
    # Automatische Vorbelegung basierend auf Berufsgruppe und geforderter Erfahrung
    if selected_group in gehaltsrahmen_nach_beruf:
        auto_min = gehaltsrahmen_nach_beruf[selected_group][get_experience_level(stelle_min_erfahrung)]["min"]
        auto_max = gehaltsrahmen_nach_beruf[selected_group][get_experience_level(stelle_min_erfahrung)]["max"]
        gehaltsrahmen_verfuegbar = True
    else:
        auto_min = 0
        auto_max = 0
        gehaltsrahmen_verfuegbar = False
    
    st.write("**Gehaltsrahmen der Stelle** (automatisch vorbefüllt)")
    st.caption("Automatisch vorgeschlagener Gehaltsrahmen auf Basis von Berufsgruppe und geforderter Berufserfahrung.")
    if not gehaltsrahmen_verfuegbar:
        st.warning("Für diese Berufsgruppe ist noch kein spezifischer Gehaltsrahmen hinterlegt. Bitte geben Sie bei Bedarf einen realistischen Wert ein.")
    st.caption("Die Werte sollten mit internen / marktüblichen Daten überprüft werden.")
    col_gmin, col_gmax = st.columns(2)
    with col_gmin:
        stelle_gehalt_min_key = f"stelle_gehalt_min_{counter}_{selected_key}"
        stelle_gehalt_max_key = f"stelle_gehalt_max_{counter}_{selected_key}"
        stelle_gehalt_min = st.number_input(
            "Min € brutto/Jahr",
            min_value=0,
            max_value=200000,
            value=st.session_state.get(stelle_gehalt_min_key, auto_min),
            step=1000,
            key=stelle_gehalt_min_key
        )
    with col_gmax:
        stelle_gehalt_max = st.number_input(
            "Max € brutto/Jahr",
            min_value=0,
            max_value=200000,
            value=st.session_state.get(stelle_gehalt_max_key, auto_max),
            step=1000,
            key=stelle_gehalt_max_key
        )

st.divider()

st.subheader("Stellenprofil-Quelle eingeben (optional)")
stellenprofil_text_key = f"stellenprofil_text_{counter}"
stellenprofil_link_key = f"stellenprofil_link_{counter}"

stellenprofil_text_input = st.text_area(
    "Stellenprofil-Text (optional)",
    value=st.session_state.get(stellenprofil_text_key, ""),
    key=stellenprofil_text_key,
    height=200
)
stellenprofil_link = st.text_input(
    "Link zur Stellenanzeige (optional)",
    value=st.session_state.get(stellenprofil_link_key, ""),
    key=stellenprofil_link_key,
    placeholder="https://..."
)

if stellenprofil_link and not stellenprofil_text_input:
    fetched_profile_text = fetch_text_from_url(stellenprofil_link)
    if fetched_profile_text:
        st.session_state[stellenprofil_text_key] = fetched_profile_text
        stellenprofil_text_input = fetched_profile_text
        st.success("✓ Stellenprofil aus dem Link erfolgreich geladen.")
    else:
        st.warning("Der Link konnte nicht automatisch ausgelesen werden. Bitte Stellenprofil-Text einfügen oder PDF hochladen.")

stellenprofil_text = stellenprofil_text_input or ""
job_profile_analysis = analyze_job_profile_text(stellenprofil_text, selected_group, berufsgruppen) if stellenprofil_text else None

if job_profile_analysis:
    job_profile_signature = make_cv_signature(stellenprofil_text, selected_group, counter)
    job_profile_autofill_key = "job_profile_autofill_signature"
    should_apply_job_autofill = st.session_state.get(job_profile_autofill_key) != job_profile_signature
    if should_apply_job_autofill:
        st.session_state[f"pflicht_skills_eingabe_{counter}_{selected_key}"] = combine_values(
            st.session_state.get(f"pflicht_skills_eingabe_{counter}_{selected_key}", ""),
            ", ".join(job_profile_analysis["pflichtskills"])
        )
        st.session_state[f"wunsch_skills_eingabe_{counter}_{selected_key}"] = combine_values(
            st.session_state.get(f"wunsch_skills_eingabe_{counter}_{selected_key}", ""),
            ", ".join(job_profile_analysis["wunschskills"])
        )
        st.session_state[f"qualifikation_stelle_{counter}_{selected_key}"] = combine_values(
            st.session_state.get(f"qualifikation_stelle_{counter}_{selected_key}", ""),
            ", ".join(job_profile_analysis["qualifikationen"])
        )
        stelle_min_key = f"stelle_min_erfahrung_{counter}"
        if job_profile_analysis["berufserfahrung_jahre"] is not None and not st.session_state.get(stelle_min_key):
            st.session_state[stelle_min_key] = min(job_profile_analysis["berufserfahrung_jahre"], 50)
        if job_profile_analysis["gehalt_min"]:
            current_min = st.session_state.get(stelle_gehalt_min_key, 0)
            if not current_min:
                st.session_state[stelle_gehalt_min_key] = job_profile_analysis["gehalt_min"]
        if job_profile_analysis["gehalt_max"]:
            current_max = st.session_state.get(stelle_gehalt_max_key, 0)
            if not current_max:
                st.session_state[stelle_gehalt_max_key] = job_profile_analysis["gehalt_max"]
        st.session_state[job_profile_autofill_key] = job_profile_signature

st.divider()

# Stellenprofil Upload (optional)
st.subheader("Stellenprofil hochladen (optional)")
uploaded_stellenprofil = st.file_uploader(
    "Stellenprofil / Ausschreibung (PDF)",
    type=["pdf"],
    key=f"stellenprofil_upload_{counter}"
)

stellenprofil_text = ""
if uploaded_stellenprofil and not stellenprofil_text:
    stellenprofil_text = extract_text_from_pdf(uploaded_stellenprofil)
    if stellenprofil_text:
        st.success("✓ Stellenprofil PDF erfolgreich verarbeitet")
        job_profile_analysis = analyze_job_profile_text(stellenprofil_text, selected_group, berufsgruppen)
        # Normalisiere und kürze Text für Anzeige
        stellenprofil_display = normalize_display_text(stellenprofil_text)
        with st.expander("Stellenprofil Vorschau (erste 1500 Zeichen)"):
            st.text_area("Stellenprofil-Text", stellenprofil_display[:1500] + "..." if len(stellenprofil_display) > 1500 else stellenprofil_display, height=200, disabled=True)

st.divider()

# Hilfsfunktion für farbliche Score-Bewertung (vor Matching-Logik definiert)
def show_score_with_rating(title, score):
    """Zeigt Score mit farblicher Bewertung an"""
    if score >= 90:
        st.success(f"**{title}**: {round(score, 2)} % ✓ Sehr gut geeignet")
    elif score >= 75:
        st.success(f"**{title}**: {round(score, 2)} % ✓ Gut geeignet")
    elif score >= 60:
        st.info(f"**{title}**: {round(score, 2)} % ℹ Grundsätzlich geeignet mit Einarbeitung")
    elif score >= 40:
        st.warning(f"**{title}**: {round(score, 2)} % ⚠ Bedingt geeignet mit deutlichem Qualifizierungsbedarf")
    else:
        st.error(f"**{title}**: {round(score, 2)} % ✗ Aktuell nicht passend")

# Buttons in einer Reihe
col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    matching_clicked = st.button("Matching starten", use_container_width=True)
with col_btn2:
    reset_clicked = st.button("Neueingabe", use_container_width=True)

if reset_clicked:
    reset_inputs()

if matching_clicked:
    has_cv_input = bool(lebenslauf_text)
    has_candidate_input = bool(bewerber_eingabe or qualifikation_bewerber or has_cv_input)
    if not has_candidate_input or not pflicht_skills_eingabe or not wunsch_skills_eingabe or not qualifikation_stelle:
        st.warning("Bitte alle Felder ausfüllen.")
        st.session_state.show_results = False
        st.session_state.calculation_complete = False
        st.session_state.results = {}
    else:
        st.session_state.show_results = True

if st.session_state.show_results and (bewerber_eingabe or qualifikation_bewerber or lebenslauf_text) and pflicht_skills_eingabe and wunsch_skills_eingabe and qualifikation_stelle:
    try:
        manuelle_bewerber_skills = split_normalized_values(bewerber_eingabe)
        bewerber_skills = set(manuelle_bewerber_skills)
        pflicht_skills_stelle = split_normalized_values(pflicht_skills_eingabe)
        wunsch_skills_stelle = split_normalized_values(wunsch_skills_eingabe)
        manuelle_qualifikationen = split_normalized_values(qualifikation_bewerber)
        qual_bewerber_set = set(manuelle_qualifikationen)
        qual_stelle_set = split_normalized_values(qualifikation_stelle)
        if lebenslauf_text:
            cv_analyse = analyze_cv_text(
                lebenslauf_text,
                selected_group,
                berufsgruppen,
                qualifikations_synonyme,
                softskill_synonyme,
                taetigkeits_mapping
            )
            cv_erkennung = extract_skills_from_cv(
                lebenslauf_text,
                pflicht_skills_stelle,
                wunsch_skills_stelle,
                qual_stelle_set,
                qualifikations_synonyme,
                softskill_synonyme,
                taetigkeits_mapping
            )
        cv_skills = set(cv_erkennung.get("erkannte_pflichtskills", []))
        cv_skills.update(cv_erkennung.get("erkannte_wunschskills", []))
        cv_skills.update(cv_erkennung.get("erkannte_transfer_skills", []))
        cv_skills.update(cv_erkennung.get("erkannte_taetigkeiten", []))
        cv_skills.update(cv_analyse.get("skills", []))
        cv_skills.update(cv_analyse.get("transfer_skills", []))
        cv_skills.update(cv_analyse.get("taetigkeiten", []))
        cv_skills.update(cv_analyse.get("sprachen", []))
        cv_skills.update(cv_analyse.get("zertifikate", []))
        cv_fuehrerschein_skills = fuehrerschein_skills_from_classes(cv_erkennung.get("erkannte_fuehrerscheine", []))
        cv_fuehrerschein_skills.update(fuehrerschein_skills_from_classes(cv_analyse.get("fuehrerscheine", [])))
        cv_qualifikationen = set(cv_erkennung.get("erkannte_qualifikationen", []))
        cv_qualifikationen.update(cv_analyse.get("qualifikationen", []))

        # Automatisch erkannte Lebenslaufdaten ergänzen die manuellen Eingaben.
        bewerber_skills.update(cv_skills)
        bewerber_skills.update(cv_fuehrerschein_skills)
        qual_bewerber_set.update(cv_qualifikationen)
        bewerber_skills.update(cv_qualifikationen)
        
        # **WICHTIG: Automatisch erfüllte Skills aus Qualifikationen hinzufügen**
        for qual in qual_bewerber_set:
            if qual in qualifikation_automatisch_erfuellt_normalized:
                # Füge alle automatisch erfüllten Skills zu bewerber_skills hinzu
                bewerber_skills.update(qualifikation_automatisch_erfuellt_normalized[qual])
        
        # Funktion für Qualifikationsmatching
        def calculate_qualification_score(bewerber_quals, stelle_quals):
            if not stelle_quals:
                return 100.0
            direct_match = False
            related_match = False
            partial_match = False
            for bq in bewerber_quals:
                for sq in stelle_quals:
                    if bq == sq or fuzz.ratio(bq, sq) >= 90:
                        direct_match = True
                    elif sq in qualifikations_synonyme_normalized.get(bq, set()):
                        related_match = True
                    elif bq in qualifikations_synonyme_normalized.get(sq, set()):
                        related_match = True
                    elif any(fuzz.ratio(sq, related) >= 90 for related in qualifikations_synonyme_normalized.get(bq, set())):
                        related_match = True
                    elif fuzz.ratio(bq, sq) >= 60:
                        partial_match = True
            if direct_match:
                return 100.0
            elif related_match:
                return 70.0
            elif partial_match:
                return 50.0
            else:
                return 10.0

        # Funktion für Skill-Matching mit Softskills
        def find_similar_skills(bewerber_skills, stellen_skills):
            direct = bewerber_skills & stellen_skills
            similar = set()
            for b_skill in bewerber_skills - direct:
                for s_skill in stellen_skills - direct:
                    # Spezielle Behandlung für Führerscheine
                    if "führerschein" in s_skill and ("führerschein" in b_skill or extract_fuehrerschein_klassen(b_skill)):
                        if check_fuehrerschein_erfuellung(b_skill, s_skill):
                            similar.add(s_skill)
                    # Standard Fuzzy Matching
                    elif fuzz.ratio(b_skill, s_skill) >= 80:
                        similar.add(s_skill)
                    # Synonyme Check
                    elif s_skill in softskill_synonyme_normalized.get(b_skill, set()):
                        similar.add(s_skill)
                    elif b_skill in softskill_synonyme_normalized.get(s_skill, set()):
                        similar.add(s_skill)
            return direct, similar

        # Skill-Matching
        pflicht_direct, pflicht_similar = find_similar_skills(bewerber_skills, pflicht_skills_stelle)
        wunsch_direct, wunsch_similar = find_similar_skills(bewerber_skills, wunsch_skills_stelle)

        # Scores berechnen
        pflicht_score = (len(pflicht_direct) + 0.5 * len(pflicht_similar)) / len(pflicht_skills_stelle) * 100 if pflicht_skills_stelle else 100
        wunsch_score = (len(wunsch_direct) + 0.5 * len(wunsch_similar)) / len(wunsch_skills_stelle) * 100 if wunsch_skills_stelle else 100

        # Softskill-Score (ähnliche Skills)
        softskill_score = min(100, len(pflicht_similar) * 10 + len(wunsch_similar) * 5)

        # Erfahrungs-Score
        if stelle_min_erfahrung == 0:
            experience_score = 100.0
        elif bewerber_erfahrung >= stelle_min_erfahrung:
            experience_score = 100.0
        else:
            experience_score = (bewerber_erfahrung / stelle_min_erfahrung) * 100.0

        # Qualifikations-Score
        qualification_score = calculate_qualification_score(qual_bewerber_set, qual_stelle_set)

        # Gesamtscore: Pflicht 40%, Wunsch 15%, Erfahrung 25%, Qualifikation 15%, Softskill 5%
        skill_score = (pflicht_score * 0.4) + (wunsch_score * 0.15) + (softskill_score * 0.05)
        gesamtscore = (skill_score * 0.6) + (experience_score * 0.25) + (qualification_score * 0.15)
        gesamtscore = max(0, min(100, gesamtscore))

        # Gehaltsmatching
        if selected_group in gehaltsrahmen_nach_beruf:
            # Bestimme Erfahrungslevel anhand der geforderten Berufserfahrung
            level = get_experience_level(stelle_min_erfahrung)
            
            markt_min = gehaltsrahmen_nach_beruf[selected_group][level]["min"]
            markt_max = gehaltsrahmen_nach_beruf[selected_group][level]["max"]
            
            # Bewertung des Gehalts
            if bewerber_gehalt == 0:
                gehalt_match = "Nicht angegeben"
                gehalt_status = "ℹ️"
            elif bewerber_gehalt < stelle_gehalt_min:
                gehalt_match = "Unter Marktwert – Risiko später er Unzufriedenheit"
                gehalt_status = "⚠️"
            elif bewerber_gehalt <= stelle_gehalt_max:
                gehalt_match = "✓ Im Budget – Passend"
                gehalt_status = "✓"
            elif bewerber_gehalt <= markt_max * 1.1:  # bis 10% über Budget
                gehalt_match = "Leicht über Budget – aber im Marktrahmen"
                gehalt_status = "⚠️"
            elif bewerber_gehalt <= markt_max:
                gehalt_match = "Deutlich über Budget"
                gehalt_status = "❌"
            else:
                gehalt_match = "Weit über Marktrahmen"
                gehalt_status = "❌"
        else:
            gehalt_match = "Keine Daten verfügbar"
            gehalt_status = "ℹ️"
            markt_min = 30000
            markt_max = 60000
            level = "mid"
        
        # Flag setzen dass Ergebnisse erfolgreich berechnet wurden
        st.session_state.calculation_complete = True
        fehlende_pflicht = pflicht_skills_stelle - bewerber_skills - pflicht_similar
        fehlende_wunsch = wunsch_skills_stelle - bewerber_skills - wunsch_similar
        fehlende_pflicht = filter_softskills_from_requirements(fehlende_pflicht)
        fehlende_wunsch = filter_softskills_from_requirements(fehlende_wunsch)

        st.session_state.results = {
            "gesamtscore": gesamtscore,
            "skill_score": skill_score,
            "experience_score": experience_score,
            "qualification_score": qualification_score,
            "gehalt_match": gehalt_match,
            "gehalt_status": gehalt_status,
            "markt_min": markt_min,
            "markt_max": markt_max,
            "level": level,
            "pflicht_direct": pflicht_direct,
            "pflicht_similar": pflicht_similar,
            "wunsch_direct": wunsch_direct,
            "wunsch_similar": wunsch_similar,
            "bewerber_skills": bewerber_skills,
            "pflicht_skills_stelle": pflicht_skills_stelle,
            "wunsch_skills_stelle": wunsch_skills_stelle,
            "qual_bewerber_set": qual_bewerber_set,
            "qual_stelle_set": qual_stelle_set,
            "fehlende_pflicht": fehlende_pflicht,
            "fehlende_wunsch": fehlende_wunsch,
            "cv_erkennung": cv_erkennung,
            "cv_analyse": cv_analyse,
            "manuelle_bewerber_skills": manuelle_bewerber_skills,
            "manuelle_qualifikationen": manuelle_qualifikationen,
            "bewerber_gehalt": bewerber_gehalt,
            "stelle_gehalt_min": stelle_gehalt_min,
            "stelle_gehalt_max": stelle_gehalt_max,
            "bewerber_erfahrung": bewerber_erfahrung
        }

    except Exception as e:
        st.session_state.calculation_complete = False
        st.session_state.results = {}
        st.error(f"❌ Fehler bei der Verarbeitung: {str(e)}")
        st.info("Bitte überprüfe die Eingaben und versuche es erneut. Falls das Problem persistiert, kontaktiere den Administrator.")

# Ergebnis-Anzeige (nur wenn Berechnung erfolgreich war)
if st.session_state.show_results and (bewerber_eingabe or qualifikation_bewerber or lebenslauf_text) and pflicht_skills_eingabe and wunsch_skills_eingabe and qualifikation_stelle and st.session_state.calculation_complete:
    results = st.session_state.results
    
    st.subheader("Ergebnis")
    
    col_gesamt, col_skill, col_exp, col_qual = st.columns(4)
    
    with col_gesamt:
        show_score_with_rating("Gesamtscore", st.session_state.results["gesamtscore"])
    
    with col_skill:
        show_score_with_rating("Skill-Score (60%)", st.session_state.results["skill_score"])
    
    with col_exp:
        show_score_with_rating("Erfahrungs-Score (25%)", st.session_state.results["experience_score"])
    
    with col_qual:
        show_score_with_rating("Qualifikations-Score (15%)", results["qualification_score"])

    # Gehaltsmatching anzeigen
    st.subheader("💰 Gehaltsmatching")
    
    col_g1, col_g2, col_g3 = st.columns(3)
    
    with col_g1:
        st.write("**Empfohlener Rahmen**")
        st.write(f"{results['markt_min']:,} – {results['markt_max']:,} €")
        st.caption(f"*{results['level'].capitalize()}-Level ({results['bewerber_erfahrung']} Jahre)*")
    
    with col_g2:
        st.write("**Stellenbudget**")
        st.write(f"{results['stelle_gehalt_min']:,} – {results['stelle_gehalt_max']:,} €")
    
    with col_g3:
        st.write("**Bewerberwunsch**")
        if results["bewerber_gehalt"] > 0:
            st.write(f"{results['bewerber_gehalt']:,} €")
        else:
            st.write("Nicht angegeben")
    
    # Ausführliche Bewertung
    st.write(f"**Bewertung**: {results['gehalt_status']} {results['gehalt_match']}")
    
    if results.get("fehlende_pflicht") is not None:
        st.subheader("Direkter Abgleich Lebenslauf ↔ Stellenprofil")
        st.write(f"**Direkte Pflichttreffer:** {format_detected_values(results['pflicht_direct']) or 'Keine'}")
        st.write(f"**Direkte Wunschtreffer:** {format_detected_values(results['wunsch_direct']) or 'Keine'}")
        st.write(f"**Fehlende Pflichtskills:** {format_detected_values(results['fehlende_pflicht']) or 'Keine'}")
        st.write(f"**Fehlende Wunschskills:** {format_detected_values(results['fehlende_wunsch']) or 'Keine'}")
    
    st.info("ℹ️ **Hinweis:** Die hier angezeigten Gehaltswerte sind interne Richtwerte und ersetzen keine verbindliche Marktanalyse. Für belastbare Gehaltsdaten sollte der [Entgeltatlas der Bundesagentur für Arbeit](https://web.arbeitsagentur.de/entgeltatlas/) ergänzend geprüft werden.")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Treffer (Pflichtskills):**")
        if results["pflicht_direct"]:
            st.success(f"Direkt: {', '.join(sorted(results['pflicht_direct']))}")
        if results["pflicht_similar"]:
            st.info(f"Ähnlich: {', '.join(sorted(results['pflicht_similar']))}")
        if not results["pflicht_direct"] and not results["pflicht_similar"]:
            st.info("Keine")

    with col2:
        st.write("**Treffer (Wunschskills):**")
        if results["wunsch_direct"]:
            st.success(f"Direkt: {', '.join(sorted(results['wunsch_direct']))}")
        if results["wunsch_similar"]:
            st.info(f"Ähnlich: {', '.join(sorted(results['wunsch_similar']))}")
        if not results["wunsch_direct"] and not results["wunsch_similar"]:
            st.info("Keine")

    cv_result = results.get("cv_erkennung", {})
    recognized_anything = any(cv_result.get(key) for key in [
        "erkannte_pflichtskills",
        "erkannte_wunschskills",
        "erkannte_qualifikationen",
        "erkannte_transfer_skills",
        "erkannte_taetigkeiten",
        "erkannte_fuehrerscheine"
    ])
    with st.expander("Automatisch erkannte Inhalte aus dem Lebenslauf"):
        if recognized_anything:
            st.write(f"**Erkannte Pflichtskills:** {format_detected_values(cv_result.get('erkannte_pflichtskills', []))}")
            st.write(f"**Erkannte Wunschskills:** {format_detected_values(cv_result.get('erkannte_wunschskills', []))}")
            st.write(f"**Erkannte Qualifikationen:** {format_detected_values(cv_result.get('erkannte_qualifikationen', []))}")
            st.write(f"**Abgeleitete Skills aus Tätigkeiten:** {format_detected_values(cv_result.get('erkannte_transfer_skills', []))}")
            st.write(f"**Erkannte Tätigkeiten:** {format_detected_values(cv_result.get('erkannte_taetigkeiten', []))}")
            st.write(f"**Erkannte Führerscheinklassen:** {format_detected_values(cv_result.get('erkannte_fuehrerscheine', []))}")
        else:
            st.info("Keine eindeutigen Skills automatisch erkannt. Bitte manuell ergänzen.")

    cv_analysis_result = results.get("cv_analyse", {})
    imported_anything = any(cv_analysis_result.get(key) for key in [
        "skills",
        "qualifikationen",
        "fuehrerscheine",
        "sprachen",
        "zertifikate",
        "taetigkeiten",
        "transfer_skills"
    ]) or cv_analysis_result.get("berufserfahrung_jahre") is not None
    with st.expander("Aus dem Lebenslauf automatisch übernommen"):
        if imported_anything:
            st.write(f"**Übernommene Skills:** {format_detected_values(cv_analysis_result.get('skills', []))}")
            st.write(f"**Übernommene Qualifikationen:** {format_detected_values(cv_analysis_result.get('qualifikationen', []))}")
            if cv_analysis_result.get("berufserfahrung_jahre") is not None:
                st.write(f"**Erkannte Berufserfahrung:** {cv_analysis_result['berufserfahrung_jahre']} Jahre")
            else:
                st.write("**Erkannte Berufserfahrung:** Keine")
            st.write(f"**Erkannte Führerscheine:** {format_detected_values(cv_analysis_result.get('fuehrerscheine', []))}")
            st.write(f"**Erkannte Sprachkenntnisse:** {format_detected_values(cv_analysis_result.get('sprachen', []))}")
            st.write(f"**Erkannte Zertifikate:** {format_detected_values(cv_analysis_result.get('zertifikate', []))}")
        else:
            st.info("Es konnten keine eindeutigen Daten automatisch übernommen werden. Bitte Angaben manuell ergänzen.")

    st.subheader("🎓 Qualifikationsmatching")
    if results["qual_stelle_set"]:
        if results["qualification_score"] == 100:
            st.success("✓ Formale Qualifikation perfekt vorhanden – Direkte Übereinstimmung")
        elif results["qualification_score"] == 70:
            st.info("ℹ️ Verwandte formale Qualifikation erkannt – Gute Basis für diese Rolle vorhanden")
        elif results["qualification_score"] == 50:
            st.warning("⚠️ Teilweise formale Qualifikation vorhanden – Komplementäre Erfahrung sollte geprüft werden")
        else:
            st.error("❌ Keine direkte formale Qualifikation erkannt. Verwandte Qualifikationen oder relevante Praxiserfahrung sollten zusätzlich geprüft werden.")
    else:
        st.info("ℹ️ Keine erforderliche Qualifikation angegeben")

    fehlende_pflicht = results["fehlende_pflicht"]
    fehlende_wunsch = results["fehlende_wunsch"]

    # Qualifizierungsempfehlungen
    st.subheader("Qualifizierungsempfehlungen")
    
    def get_recommendation(skill, is_pflicht=True):
        skill_key = normalize_text(skill)
        if skill_key in qualifizierungs_lookup:
            info = qualifizierungs_lookup[skill_key]
            prioritaet = "hoch" if is_pflicht else info["prioritaet"]
            return {
                "skill": skill,
                "schulung": info["schulung"],
                "dauer": info["dauer"],
                "kosten": info["kosten"],
                "prioritaet": prioritaet
            }
        else:
            return {
                "skill": skill,
                "schulung": "Fachliche Einarbeitung / interne Schulung",
                "dauer": "1 bis 5 Tage",
                "kosten": "0 bis 1.000 €",
                "prioritaet": "hoch" if is_pflicht else "mittel"
            }

    empfehlungen = []
    for skill in fehlende_pflicht:
        empfehlungen.append(get_recommendation(skill, True))
    for skill in fehlende_wunsch:
        empfehlungen.append(get_recommendation(skill, False))

    if empfehlungen:
        # Sortieren nach Priorität
        prioritaet_order = {"hoch": 0, "mittel": 1, "niedrig": 2}
        empfehlungen.sort(key=lambda x: prioritaet_order.get(x["prioritaet"], 3))
        
        # Zeige maximal die Top 5 Empfehlungen in einer Tabelle
        st.subheader("Qualifizierungsempfehlungen")
        st.write("Die folgenden Qualifizierungen könnten den Kandidaten für die Rolle vorbereiten:")
        
        # Vorbereitung der Tabellendaten
        table_data = []
        for idx, emp in enumerate(empfehlungen[:5]):  # Nur Top 5
            prioritaet_icon = "🔴" if emp["prioritaet"] == "hoch" else "🟡" if emp["prioritaet"] == "mittel" else "🟢"
            table_data.append({
                "Skill": emp['skill'],
                "Priorität": f"{prioritaet_icon} {emp['prioritaet'].capitalize()}",
                "Schulung": emp['schulung'],
                "Dauer": emp['dauer'],
                "Kosten": emp['kosten']
            })
        
        # Zeige Tabelle
        st.dataframe(table_data, use_container_width=True, hide_index=True)
        
        # Weitere Empfehlungen Hinweis
        if len(empfehlungen) > 5:
            further_skills = [emp['skill'] for emp in empfehlungen[5:]]
            st.info(f"**Weitere Qualifizierungsfelder:** {', '.join(further_skills)}")
        
        # Gesamtschätzung mit sicherer Zahlenextraktion
        st.subheader("Geschätzter Gesamtaufwand")
        
        total_dauer_min = 0
        total_dauer_max = 0
        total_kosten_min = 0
        total_kosten_max = 0
        
        # Nur nicht-softskills in Berechnung einbeziehen
        for emp in empfehlungen:
            if normalize_text(emp['skill']) not in softskill_no_training_normalized:
                # Dauer sicher extrahieren
                dauer_vals = safe_extract_number(emp["dauer"], "both", (0, 0))
                if isinstance(dauer_vals, tuple):
                    total_dauer_min += dauer_vals[0]
                    total_dauer_max += dauer_vals[1]
                
                # Kosten sicher extrahieren  
                kosten_vals = safe_extract_number(emp["kosten"], "both", (0, 0))
                if isinstance(kosten_vals, tuple):
                    total_kosten_min += kosten_vals[0]
                    total_kosten_max += kosten_vals[1]
        
        # Einschätzung der Realisierbarkeit
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Geschätzte Dauer:** {total_dauer_min} bis {total_dauer_max} Tage")
        with col2:
            st.write(f"**Geschätzter Kostenrahmen:** {total_kosten_min:,} bis {total_kosten_max:,} €")
        
        # Realisierungseinschätzung
        if total_dauer_max <= 5:
            st.success("**Realisierbarkeit:** Schnell umsetzbar in 1-2 Wochen")
        elif total_dauer_max <= 15:
            st.info("**Realisierbarkeit:** Mittelfristig umsetzbar in 1-3 Monaten")
        else:
            st.warning("**Realisierbarkeit:** Längerfristige Qualifizierung erforderlich")
        
        st.caption("*Unverbindliche Richtwerte. Externe Weiterbildungsangebote können unter https://www.mein-now.de der Bundesagentur für Arbeit recherchiert werden.*")
        
        # Link zur mein-now.de
        st.info("💡 **Externe Recherche empfohlen:** [Weiterbildungsportal mein-now.de der Bundesagentur für Arbeit](https://www.mein-now.de)")
        
    else:
        st.success("✓ Keine Qualifizierungsempfehlungen nötig - alle Anforderungen erfüllt!")

    # Professionelle Einschätzung
    st.subheader("📋 Professionelle Einschätzung")
    if results["gesamtscore"] >= 90:
        st.success("**Sehr hohe Passung** – Der Kandidat erfüllt die Anforderungen sehr gut und kann zeitnah starten.")
    elif results["gesamtscore"] >= 75:
        st.success("**Gute Passung** – Starke fachliche Übereinstimmung mit minimalem Einarbeitungsbedarf.")
    elif results["gesamtscore"] >= 60:
        st.info("**Grundsätzlich geeignet** – Gute Grundlagen vorhanden. Gezielte Einarbeitung in spezifische Anforderungen sinnvoll.")
    elif results["gesamtscore"] >= 40:
        st.warning("**Mittlere Passung mit Entwicklungsbedarf** – Potenzial erkannt, aber strukturierte Qualifizierung erforderlich.")
    else:
        st.error("**Geringe Passung** – Eine Besetzung wäre nur mit deutlicher Einarbeitung oder Qualifizierung sinnvoll.")
