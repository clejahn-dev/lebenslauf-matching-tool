import streamlit as st
from fuzzywuzzy import fuzz

# Initialisiere Session State
if "reset_counter" not in st.session_state:
    st.session_state.reset_counter = 0
if "show_results" not in st.session_state:
    st.session_state.show_results = False

# Reset-Funktion
def reset_inputs():
    st.session_state.reset_counter += 1
    st.session_state.show_results = False
    st.rerun()

st.set_page_config(
    page_title="Lebenslauf Matching Tool",
    page_icon="📄",
    layout="centered"
)

st.title("Lebenslauf Matching Tool")
st.write("Vergleiche Bewerber-Skills mit Anforderungen aus einer Stellenanzeige.")

berufsgruppen = {
    "Büroassistenz": {
        "pflicht": ["Office", "Terminplanung", "Kommunikation"],
        "wunsch": ["Excel", "Textverarbeitung", "Teamarbeit"],
        "qualifikationen": []
    },
    "HR / Personal": {
        "pflicht": ["Personalbetreuung", "Arbeitsrecht", "Führungskräfteberatung", "Recruiting", "Vertragswesen", "Mitarbeitergespräche"],
        "wunsch": ["SAP HR", "Betriebsratsarbeit", "Change Management", "Personalentwicklung", "Personalcontrolling", "Employer Branding", "HR Prozesse", "Excel"],
        "qualifikationen": ["Personalfachkaufmann", "Personalreferent", "Betriebswirtschaft mit Schwerpunkt Personal", "Wirtschaftsrecht", "HR Management", "Personaldienstleistungskaufmann", "Kaufmann für Büromanagement mit HR Erfahrung"]
    }
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

if selected_group in berufsgruppen:
    profile = berufsgruppen[selected_group]
    pflicht_skills = profile.get("pflicht") or profile.get("pflichtskills") or []
    wunsch_skills = profile.get("wunsch") or profile.get("wunschskills") or []
    qualifikationen = profile.get("qualifikationen") or []
    suggested_pflicht = ", ".join(pflicht_skills)
    suggested_wunsch = ", ".join(wunsch_skills)
    suggested_qualifikationen = ", ".join(qualifikationen)
else:
    suggested_pflicht = ""
    suggested_wunsch = ""
    suggested_qualifikationen = ""

counter = st.session_state.reset_counter

bewerber_eingabe = st.text_area(
    "Skills des Bewerbers",
    placeholder="z. B. Recruiting, Arbeitsrecht, Excel, Personalbetreuung",
    key=f"bewerber_eingabe_{counter}"
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
        key=f"qualifikation_bewerber_{counter}",
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
        key=f"bewerber_erfahrung_{counter}"
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

# Buttons in einer Reihe
col_btn1, col_btn2 = st.columns(2)
with col_btn1:
    matching_clicked = st.button("Matching starten", use_container_width=True)
with col_btn2:
    reset_clicked = st.button("Neueingabe", use_container_width=True)

if reset_clicked:
    reset_inputs()

if matching_clicked:
    if not bewerber_eingabe or not pflicht_skills_eingabe or not wunsch_skills_eingabe or not qualifikation_bewerber or not qualifikation_stelle:
        st.warning("Bitte alle Felder ausfüllen.")
    else:
        st.session_state.show_results = True

if st.session_state.show_results and bewerber_eingabe and pflicht_skills_eingabe and wunsch_skills_eingabe and qualifikation_bewerber and qualifikation_stelle:
    bewerber_skills = set(skill.strip().lower() for skill in bewerber_eingabe.split(",") if skill.strip())
    pflicht_skills = set(skill.strip().lower() for skill in pflicht_skills_eingabe.split(",") if skill.strip())
    wunsch_skills = set(skill.strip().lower() for skill in wunsch_skills_eingabe.split(",") if skill.strip())
    qual_bewerber_set = set(q.strip().lower() for q in qualifikation_bewerber.split(",") if q.strip())
    qual_stelle_set = set(q.strip().lower() for q in qualifikation_stelle.split(",") if q.strip())

    # Ähnliche Skills: explizite Synonyme + Fuzzy-Matching
    synonym_map = {
        "produktion": {"lagerarbeit"},
        "bundeswehr": {"belastbarkeit", "teamfähigkeit"},
    }

    def find_similar_skills(bewerber_skills, stellen_skills, threshold=80):
        direct = bewerber_skills & stellen_skills
        partial = set()
        for b_skill in bewerber_skills:
            remaining = stellen_skills - direct - partial
            for s_skill in remaining:
                if s_skill in synonym_map.get(b_skill, set()):
                    partial.add(s_skill)
                elif fuzz.ratio(b_skill, s_skill) >= threshold:
                    partial.add(s_skill)
        return direct, partial

    qualifizierungs_empfehlungen = {
        "sap": ("SAP Grundlagenschulung", "2 bis 5 Tage"),
        "excel": ("Excel Grundkurs", "1 bis 3 Tage"),
        "hr business partner": ("HR Business Partner Training", "3 bis 5 Tage"),
        "recruiting": ("Recruiting und Auswahlverfahren", "2 bis 4 Tage"),
        "arbeitsrecht": ("Arbeitsrecht für HR", "2 bis 4 Tage"),
        "personalbetreuung": ("Personalbetreuung und -entwicklung", "2 bis 4 Tage"),
        "lagerverwaltung": ("Lagerverwaltungskurs", "2 bis 5 Tage"),
        "kommissionierung": ("Kommissionierungstraining", "1 bis 3 Tage"),
        "sicherheitsvorschriften": ("Arbeitssicherheit und Vorschriften", "1 bis 2 Tage"),
        "staplerfahren": ("Staplerschein", "2 bis 3 Tage"),
        "logistiksoftware": ("Logistiksoftware-Schulung", "2 bis 4 Tage"),
        "versandabwicklung": ("Versand- und Zollabwicklung", "1 bis 3 Tage"),
        "streichen": ("Maler- und Lackierer-Grundkurs", "3 bis 5 Tage"),
        "vorbereitung": ("Oberflächenvorbereitungstechniken", "1 bis 2 Tage"),
        "oberflächenbehandlung": ("Oberflächenbehandlung und Beschichtung", "2 bis 4 Tage"),
        "tapezieren": ("Tapeziertraining", "1 bis 3 Tage"),
        "spachteln": ("Spachtel- und Flächentechnik", "1 bis 3 Tage"),
        "farbberatung": ("Farb- und Materialberatung", "1 bis 2 Tage"),
        "pflegeplanung": ("Pflegeplanung und Dokumentation", "2 bis 4 Tage"),
        "medikamentengabe": ("Medikamentengabe-Schulung", "2 bis 3 Tage"),
        "hygiene": ("Hygieneschulung", "1 bis 2 Tage"),
        "dokumentation": ("Pflegedokumentation", "1 bis 2 Tage"),
        "empathie": ("Kommunikation und Empathie im Pflegebereich", "1 bis 2 Tage"),
        "kundenakquise": ("Verkaufstraining Kundenakquise", "2 bis 4 Tage"),
        "verkaufsberatung": ("Verkaufsberatung und Gesprächsführung", "2 bis 4 Tage"),
        "abschlussstärke": ("Abschlussstarkes Verkaufen", "1 bis 2 Tage"),
        "crm": ("CRM-Grundlagen", "1 bis 3 Tage"),
        "networking": ("Networking im Vertrieb", "1 bis 2 Tage"),
        "verhandlung": ("Verhandlungstechnik", "2 bis 3 Tage"),
        "hardware-support": ("Hardware-Support-Grundlagen", "2 bis 4 Tage"),
        "troubleshooting": ("Troubleshooting und Fehlersuche", "2 bis 4 Tage"),
        "kundensupport": ("Kundensupport und Service", "1 bis 3 Tage"),
        "netzwerktechnik": ("Netzwerktechnik Basics", "2 bis 4 Tage"),
        "windows": ("Windows-Administration", "2 bis 4 Tage"),
        "itil": ("ITIL Grundkurs", "2 bis 3 Tage"),
        "buchführung": ("Buchführungsgrundlagen", "3 bis 5 Tage"),
        "rechnungswesen": ("Rechnungswesen kompakt", "3 bis 5 Tage"),
        "zahlungsverkehr": ("Zahlungsverkehr und Bankprozesse", "1 bis 2 Tage"),
        "datev": ("DATEV-Schulung", "2 bis 4 Tage"),
        "steuergrundlagen": ("Steuerrecht Basics", "2 bis 4 Tage"),
        "kundenkommunikation": ("Kundenkommunikationstraining", "1 bis 3 Tage"),
        "beschwerdemanagement": ("Beschwerdemanagement", "1 bis 2 Tage"),
        "serviceorientierung": ("Serviceorientierung und Kundenbindung", "1 bis 2 Tage"),
        "multitasking": ("Effektives Multitasking", "1 Tag"),
        "konfliktlösung": ("Konfliktlösung im Kundenservice", "1 bis 2 Tage")
    }

    def format_recommendation(skill_set):
        lines = []
        for skill in sorted(skill_set):
            skill_key = skill.lower()
            if skill_key in qualifizierungs_empfehlungen:
                course, duration = qualifizierungs_empfehlungen[skill_key]
                lines.append(f"• {skill}: {course} ({duration})")
            else:
                lines.append(f"• {skill}")
        return "\n".join(lines)

    treffer_pflicht_direct, treffer_pflicht_partial = find_similar_skills(bewerber_skills, pflicht_skills)
    treffer_wunsch_direct, treffer_wunsch_partial = find_similar_skills(bewerber_skills, wunsch_skills)

    # Fehlende Skills (nur direkte, da 'ähnlich' nicht als fehlend gelten)
    fehlende_pflicht = pflicht_skills - bewerber_skills - treffer_pflicht_partial
    fehlende_wunsch = wunsch_skills - bewerber_skills - treffer_wunsch_partial

    # Berechnung des gewichteten Scores
    gewicht_pflicht = 2
    gewicht_wunsch = 1
    partial_weight = 0.5  # Halbe Punkte für ähnliche Skills

    max_punkte = gewicht_pflicht * len(pflicht_skills) + gewicht_wunsch * len(wunsch_skills)
    erzielte_punkte = (
        gewicht_pflicht * len(treffer_pflicht_direct) +
        gewicht_wunsch * len(treffer_wunsch_direct) +
        partial_weight * gewicht_pflicht * len(treffer_pflicht_partial) +
        partial_weight * gewicht_wunsch * len(treffer_wunsch_partial)
    )

    if max_punkte > 0:
        matchscore = (erzielte_punkte / max_punkte) * 100
    else:
        matchscore = 0.0

    # Penalty für fehlende Skills: stärker für Pflichtskills
    penalty_pflicht = 0.1 * len(fehlende_pflicht)  # 10% Abzug pro fehlendem Pflichtskill
    penalty_wunsch = 0.05 * len(fehlende_wunsch)  # 5% Abzug pro fehlendem Wunschskill
    total_penalty = penalty_pflicht + penalty_wunsch

    matchscore = max(0, matchscore * (1 - total_penalty))  # Verhindert negative Scores

    # Qualifikationsscore berechnen
    qual_direct = qual_bewerber_set & qual_stelle_set
    qual_partial = set()
    for bq in qual_bewerber_set:
        for rq in qual_stelle_set - qual_direct:
            if fuzz.ratio(bq, rq) >= 80 or bq in rq or rq in bq:
                qual_partial.add(rq)

    if qual_stelle_set:
        if qual_direct:
            qualification_score = 100.0
        elif qual_partial:
            qualification_score = 60.0
        else:
            qualification_score = 20.0
    else:
        qualification_score = 100.0

    # Berechnung des Erfahrungsscores
    if stelle_min_erfahrung == 0:
        # Wenn keine Erfahrung gefordert ist, gibt es vollen Score
        experience_score = 100.0
    elif bewerber_erfahrung >= stelle_min_erfahrung:
        # Bewerber hat mindestens die geforderte Erfahrung
        experience_score = 100.0
    else:
        # Anteilige Berechnung: Bewerber-Erfahrung / Geforderte Erfahrung
        experience_score = (bewerber_erfahrung / stelle_min_erfahrung) * 100.0

    # Gesamtscore: 60% Skill-Score + 20% Erfahrungs-Score + 20% Qualifikations-Score
    gesamtscore = (matchscore * 0.6) + (experience_score * 0.2) + (qualification_score * 0.2)
    gesamtscore = max(0, min(100, gesamtscore))  # Begrenzt auf 0-100%

    st.subheader("Ergebnis")
    
    # Hilfsfunktion für farbliche Score-Bewertung
    def show_score_with_rating(title, score):
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
    
    col_gesamt, col_skill, col_exp, col_qual = st.columns(4)
    
    with col_gesamt:
        show_score_with_rating("Gesamtscore", gesamtscore)
    
    with col_skill:
        show_score_with_rating("Skill-Score (60%)", matchscore)
    
    with col_exp:
        show_score_with_rating("Erfahrungs-Score (20%)", experience_score)
    
    with col_qual:
        show_score_with_rating("Qualifikations-Score (20%)", qualification_score)

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Treffer (Pflichtskills):**")
        if treffer_pflicht_direct:
            st.success(f"Direkt: {', '.join(treffer_pflicht_direct)}")
        if treffer_pflicht_partial:
            st.info(f"Ähnlich: {', '.join(treffer_pflicht_partial)}")
        if not treffer_pflicht_direct and not treffer_pflicht_partial:
            st.info("Keine")

        st.write("**Fehlende Pflichtskills:**")
        if fehlende_pflicht:
            st.error(", ".join(fehlende_pflicht))
        else:
            st.success("Alle vorhanden")

    with col2:
        st.write("**Treffer (Wunschskills):**")
        if treffer_wunsch_direct:
            st.success(f"Direkt: {', '.join(treffer_wunsch_direct)}")
        if treffer_wunsch_partial:
            st.info(f"Ähnlich: {', '.join(treffer_wunsch_partial)}")
        if not treffer_wunsch_direct and not treffer_wunsch_partial:
            st.info("Keine")

        st.write("**Fehlende Wunschskills:**")
        if fehlende_wunsch:
            st.warning(", ".join(fehlende_wunsch))
        else:
            st.info("Alle vorhanden")

    st.subheader("Qualifikationsmatching")
    if qual_stelle_set:
        if qual_direct:
            st.success(f"Direkte Übereinstimmung: {', '.join(sorted(qual_direct))}")
        elif qual_partial:
            st.info(f"Teilweise passend: {', '.join(sorted(qual_partial))}")
        else:
            st.error("Keine passende Qualifikation gefunden.")
    else:
        st.info("Keine erforderliche Qualifikation angegeben.")

    # Qualifizierungsempfehlung
    st.subheader("Qualifizierungsempfehlung")
    
    if fehlende_pflicht or fehlende_wunsch:
        if fehlende_pflicht:
            st.error("**Schulungsbedarf (Pflicht):**")
            st.error(
                "Folgende Qualifikationen müssen zwingend nachgeschult werden:\n\n" +
                format_recommendation(fehlende_pflicht)
            )
        
        if fehlende_wunsch:
            st.warning("**Optionale Weiterbildung:**")
            st.warning(
                "Diese Qualifikationen werden empfohlen, sind aber nicht zwingend erforderlich:\n\n" +
                format_recommendation(fehlende_wunsch)
            )
    else:
        st.success("✓ Keine Qualifizierungsempfehlung nötig - alle Anforderungen erfüllt!")

    # Geschätzte Einarbeitungszeit
    st.subheader("Geschätzte Einarbeitungszeit")
    
    if gesamtscore >= 80:
        einarbeitungszeit = "1 bis 4 Wochen"
        st.success(f"**{einarbeitungszeit}**\nDer Kandidat ist sehr gut qualifiziert und kann schnell produktiv werden.")
    elif gesamtscore >= 60:
        einarbeitungszeit = "1 bis 3 Monate"
        st.info(f"**{einarbeitungszeit}**\nDer Kandidat hat gute Grundlagen und benötigt eine moderate Einarbeitungszeit.")
    elif gesamtscore >= 40:
        einarbeitungszeit = "3 bis 6 Monate"
        st.warning(f"**{einarbeitungszeit}**\nDer Kandidat benötigt eine längere Einarbeitungszeit mit intensiver Unterstützung.")
    else:
        st.error("**Aktuell nicht empfehlenswert**\nDer Kandidat benötigt umfangreiche Qualifizierung vor der Besetzung dieser Position.")

        # Einschätzung basierend auf Gesamtscore
        if gesamtscore >= 80:
            st.success("Einschätzung: Sehr gute Passung")
        elif gesamtscore >= 60:
            st.info("Einschätzung: Gute Passung mit kleineren Lücken")
        elif gesamtscore >= 40:
            st.warning("Einschätzung: Teilweise passend, Qualifizierung prüfen")
        else:
            st.error("Einschätzung: Aktuell eher geringe Passung")