import streamlit as st
from fuzzywuzzy import fuzz

# Qualifikations-Synonyme und verwandte Qualifikationen
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
    "Fachkraft für Schutz und Sicherheit": ["Sicherheitsdienst"],
    "Servicekraft Schutz und Sicherheit": ["Sicherheitsdienst"],
    "Sachkundeprüfung 34a": ["Sicherheitsdienst"],
    "DATEV": ["Buchhaltung"],
    "Bundeswehr": ["Führung", "Belastbarkeit", "Sicherheit"],
    "Personaldienstleistungskaufmann": ["HR / Personal"]
}

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
        "senior": {"min": 65000, "max": 85000}
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
    }
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

# Gehaltsranges pro Berufsgruppe und Erfahrung
gehalts_ranges = {
    "Pflege": {
        0: (28000, 35000),
        1: (30000, 38000),
        2: (32000, 42000),
        5: (35000, 48000),
        10: (40000, 55000)
    },
    "Vertrieb": {
        0: (25000, 35000),
        1: (28000, 40000),
        2: (32000, 45000),
        5: (38000, 55000),
        10: (45000, 70000)
    },
    "Lager / Logistik": {
        0: (22000, 28000),
        1: (24000, 30000),
        2: (26000, 33000),
        5: (28000, 36000),
        10: (30000, 40000)
    },
    "HR / Personal": {
        0: (28000, 38000),
        1: (32000, 42000),
        2: (36000, 48000),
        5: (42000, 58000),
        10: (50000, 70000)
    },
    "Buchhaltung": {
        0: (25000, 32000),
        1: (28000, 36000),
        2: (32000, 40000),
        5: (36000, 45000),
        10: (40000, 55000)
    },
    "Kundenservice": {
        0: (22000, 28000),
        1: (24000, 30000),
        2: (26000, 33000),
        5: (28000, 36000),
        10: (30000, 40000)
    },
    "IT Support": {
        0: (25000, 32000),
        1: (28000, 36000),
        2: (32000, 42000),
        5: (38000, 50000),
        10: (45000, 65000)
    },
    "Maler und Lackierer": {
        0: (22000, 28000),
        1: (24000, 30000),
        2: (26000, 33000),
        5: (28000, 36000),
        10: (30000, 40000)
    },
    "Büroassistenz": {
        0: (22000, 28000),
        1: (24000, 30000),
        2: (26000, 33000),
        5: (28000, 36000),
        10: (30000, 40000)
    }
}

# Softskill-Ähnlichkeiten
softskill_synonyme = {
    "Kundenservice": ["Kommunikation", "Serviceorientierung"],
    "Pflegeberatung": ["Angehörigenberatung"],
    "Dokumentation": ["Pflegedokumentation"],
    "Verkaufsgespräch": ["Kundenberatung"],
    "Teamführung": ["Führungserfahrung"]
}

# Initialisiere Session State
if "reset_counter" not in st.session_state:
    st.session_state.reset_counter = 0
if "show_results" not in st.session_state:
    st.session_state.show_results = False
if "uploaded_logo" not in st.session_state:
    st.session_state.uploaded_logo = None
if "uploaded_lebenslauf" not in st.session_state:
    st.session_state.uploaded_lebenslauf = None
if "bewerber_skills_text" not in st.session_state:
    st.session_state.bewerber_skills_text = ""

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
        "pflichtskills": ["Office", "Terminplanung", "Kommunikation"],
        "wunschskills": ["Excel", "Textverarbeitung", "Teamarbeit"],
        "qualifikationen": []
    },
    "HR / Personal": {
        "pflichtskills": ["Personalbetreuung", "Arbeitsrecht", "Führungskräfteberatung", "Recruiting", "Vertragswesen", "Mitarbeitergespräche"],
        "wunschskills": ["SAP HR", "Betriebsratsarbeit", "Change Management", "Personalentwicklung", "Personalcontrolling", "Employer Branding", "HR Prozesse", "Excel"],
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
    },
    "Sicherheitsdienst": {
        "pflichtskills": [
            "Sicherheitsdienst", "Objektschutz", "Kontrollgänge", "Zugangskontrolle", "Deeskalation",
            "Berichtswesen", "Zuverlässigkeit", "Verantwortungsbewusstsein", "Kommunikation", "Schichtbereitschaft"
        ],
        "wunschskills": [
            "Sachkundeprüfung 34a", "Ersthelfer", "Brandschutzhelfer", "Personenschutz",
            "Empfangsdienst", "Führerschein Klasse B", "Englisch", "Konfliktmanagement"
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
    # Automatische Vorbelegung basierend auf Berufsgruppe und Erfahrung
    if selected_group in gehaltsrahmen_nach_beruf:
        if bewerber_erfahrung <= 2:
            level = "junior"
        elif bewerber_erfahrung <= 5:
            level = "mid"
        else:
            level = "senior"
        
        auto_min = gehaltsrahmen_nach_beruf[selected_group][level]["min"]
        auto_max = gehaltsrahmen_nach_beruf[selected_group][level]["max"]
    else:
        auto_min = 30000
        auto_max = 60000
    
    st.write("**Gehaltsrahmen der Stelle** (automatisch vorbefüllt)")
    col_gmin, col_gmax = st.columns(2)
    with col_gmin:
        stelle_gehalt_min = st.number_input(
            "Min € brutto/Jahr",
            min_value=0,
            max_value=200000,
            value=auto_min,
            step=1000,
            key=f"stelle_gehalt_min_{counter}"
        )
    with col_gmax:
        stelle_gehalt_max = st.number_input(
            "Max € brutto/Jahr",
            min_value=0,
            max_value=200000,
            value=auto_max,
            step=1000,
            key=f"stelle_gehalt_max_{counter}"
        )

st.divider()

# Unternehmenskontext (optional)
st.subheader("Unternehmenskontext (optional)")

col_logo, col_ent = st.columns([1, 2])
with col_logo:
    st.write("**Unternehmenslogo**")
    uploaded_logo = st.file_uploader(
        "Logo hochladen",
        type=["png", "jpg", "jpeg"],
        key=f"logo_upload_{counter}",
        label_visibility="collapsed"
    )

with col_ent:
    col_name, col_branch = st.columns(2)
    with col_name:
        unternehmensname = st.text_input(
            "Unternehmensname",
            key=f"unternehmensname_{counter}",
            placeholder="z. B. Musterunternehmen GmbH"
        )
    with col_branch:
        branche = st.text_input(
            "Branche",
            key=f"branche_{counter}",
            placeholder="z. B. Einzelhandel, IT-Services"
        )

col_standort, col_modell = st.columns(2)
with col_standort:
    standort = st.text_input(
        "Standort",
        key=f"standort_{counter}",
        placeholder="z. B. Berlin, Remote"
    )
with col_modell:
    arbeitsmodell = st.selectbox(
        "Arbeitsmodell",
        ["Vor Ort", "Hybrid", "Remote"],
        key=f"arbeitsmodell_{counter}"
    )

col_team, col_schicht = st.columns(2)
with col_team:
    teamgroesse = st.number_input(
        "Teamgröße",
        min_value=0,
        max_value=1000,
        value=0,
        step=1,
        key=f"teamgroesse_{counter}"
    )
with col_schicht:
    schichtarbeit = st.selectbox(
        "Schichtarbeit erforderlich",
        ["Nein", "Ja"],
        key=f"schichtarbeit_{counter}"
    )

kundenkontakt = st.checkbox(
    "Kundenkontakt erforderlich",
    key=f"kundenkontakt_{counter}"
)

st.divider()

# Lebenslauf Upload (optional)
st.subheader("Lebenslauf Upload (optional)")
uploaded_lebenslauf = st.file_uploader(
    "Lebenslauf hochladen (PDF oder TXT)",
    type=["pdf", "txt"],
    key=f"lebenslauf_upload_{counter}"
)

if uploaded_lebenslauf:
    if uploaded_lebenslauf.type == "text/plain":
        lebenslauf_text = uploaded_lebenslauf.read().decode("utf-8")
        st.success("TXT-Datei gelesen")
        with st.expander("Lebenslauf Inhalt anzeigen"):
            st.text(lebenslauf_text)
    elif uploaded_lebenslauf.type == "application/pdf":
        st.info("PDF-Analyse wird in einer späteren Version ergänzt")

st.divider()

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
    pflicht_skills_stelle = set(skill.strip().lower() for skill in pflicht_skills_eingabe.split(",") if skill.strip())
    wunsch_skills_stelle = set(skill.strip().lower() for skill in wunsch_skills_eingabe.split(",") if skill.strip())
    qual_bewerber_set = set(q.strip().lower() for q in qualifikation_bewerber.split(",") if q.strip())
    qual_stelle_set = set(q.strip().lower() for q in qualifikation_stelle.split(",") if q.strip())

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
                elif bq in qualifikations_synonyme and sq in qualifikations_synonyme[bq]:
                    related_match = True
                elif any(sq in related for related in qualifikations_synonyme.get(bq, [])):
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
                if fuzz.ratio(b_skill, s_skill) >= 80:
                    similar.add(s_skill)
                elif s_skill in softskill_synonyme.get(b_skill, []):
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

    # Gesamtscore: Pflicht 45%, Wunsch 10%, Erfahrung 20%, Qualifikation 20%, Softskill 5%
    skill_score = (pflicht_score * 0.45) + (wunsch_score * 0.1) + (softskill_score * 0.05)
    gesamtscore = (skill_score * 0.7) + (experience_score * 0.2) + (qualification_score * 0.2)
    gesamtscore = max(0, min(100, gesamtscore))

    # Gehaltsmatching
    if selected_group in gehalts_ranges:
        erfahrung_key = min([k for k in gehalts_ranges[selected_group].keys() if bewerber_erfahrung >= k], default=0)
        markt_min, markt_max = gehalts_ranges[selected_group][erfahrung_key]
        if bewerber_gehalt == 0:
            gehalt_match = "Nicht angegeben"
        elif bewerber_gehalt < stelle_gehalt_min:
            gehalt_match = "Unter Marktwert"
        elif bewerber_gehalt <= stelle_gehalt_max:
            gehalt_match = "Passend"
        elif bewerber_gehalt <= markt_max:
            gehalt_match = "Leicht über Budget"
        else:
            gehalt_match = "Deutlich über Budget"
    else:
        gehalt_match = "Keine Daten verfügbar"

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
        show_score_with_rating("Skill-Score (70%)", skill_score)
    
    with col_exp:
        show_score_with_rating("Erfahrungs-Score (20%)", experience_score)
    
    with col_qual:
        show_score_with_rating("Qualifikations-Score (20%)", qualification_score)

    # Gehaltsmatching anzeigen
    st.subheader("Gehaltsmatching")
    st.write(f"**Bewertung**: {gehalt_match}")
    if selected_group in gehalts_ranges:
        erfahrung_key = min([k for k in gehalts_ranges[selected_group].keys() if bewerber_erfahrung >= k], default=0)
        markt_min, markt_max = gehalts_ranges[selected_group][erfahrung_key]
        st.write(f"**Marktüblicher Rahmen** (bei {bewerber_erfahrung} Jahren Erfahrung): {markt_min:,} - {markt_max:,} €")

    col1, col2 = st.columns(2)

    with col1:
        st.write("**Treffer (Pflichtskills):**")
        if pflicht_direct:
            st.success(f"Direkt: {', '.join(sorted(pflicht_direct))}")
        if pflicht_similar:
            st.info(f"Ähnlich: {', '.join(sorted(pflicht_similar))}")
        if not pflicht_direct and not pflicht_similar:
            st.info("Keine")

    with col2:
        st.write("**Treffer (Wunschskills):**")
        if wunsch_direct:
            st.success(f"Direkt: {', '.join(sorted(wunsch_direct))}")
        if wunsch_similar:
            st.info(f"Ähnlich: {', '.join(sorted(wunsch_similar))}")
        if not wunsch_direct and not wunsch_similar:
            st.info("Keine")

    st.subheader("Qualifikationsmatching")
    if qual_stelle_set:
        if qualification_score == 100:
            st.success("Direkte Übereinstimmung gefunden")
        elif qualification_score == 70:
            st.info("Verwandte Qualifikation vorhanden")
        elif qualification_score == 50:
            st.warning("Teilweise passende Qualifikation")
        else:
            st.error("Keine passende Qualifikation")
    else:
        st.info("Keine erforderliche Qualifikation angegeben")

    # Fehlende Skills berechnen
    fehlende_pflicht = pflicht_skills_stelle - bewerber_skills - pflicht_similar
    fehlende_wunsch = wunsch_skills_stelle - bewerber_skills - wunsch_similar

    # Qualifizierungsempfehlungen
    st.subheader("Qualifizierungsempfehlungen")
    
    def get_recommendation(skill, is_pflicht=True):
        skill_lower = skill.lower()
        if skill_lower in qualifizierungs_katalog:
            info = qualifizierungs_katalog[skill_lower]
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
        
        for emp in empfehlungen:
            if emp["prioritaet"] == "hoch":
                st.error(f"**{emp['skill']}** (Priorität: {emp['prioritaet']})")
            else:
                st.warning(f"**{emp['skill']}** (Priorität: {emp['prioritaet']})")
            st.write(f"- Schulung: {emp['schulung']}")
            st.write(f"- Dauer: {emp['dauer']}")
            st.write(f"- Kosten: {emp['kosten']}")
            st.write("---")
        
        # Gesamtschätzung
        total_dauer_min = sum(int(d.split()[0]) for emp in empfehlungen for d in emp["dauer"].split(" bis ") if d.split()[0].isdigit())
        total_dauer_max = sum(int(d.split()[0]) for emp in empfehlungen for d in emp["dauer"].split(" bis ")[-1] if d.split()[0].isdigit())
        total_kosten_min = sum(int(k.split()[0].replace(".", "")) for emp in empfehlungen for k in emp["kosten"].split(" bis ") if k.split()[0].replace(".", "").isdigit())
        total_kosten_max = sum(int(k.split()[0].replace(".", "")) for emp in empfehlungen for k in emp["kosten"].split(" bis ")[-1] if k.split()[0].replace(".", "").isdigit())
        
        st.subheader("Geschätzter Qualifizierungsaufwand")
        st.write(f"**Dauer**: ca. {total_dauer_min} bis {total_dauer_max} Tage")
        st.write(f"**Kosten**: ca. {total_kosten_min:,} bis {total_kosten_max:,} €")
        st.caption("*Unverbindliche Richtwerte als Orientierung*")
    else:
        st.success("✓ Keine Qualifizierungsempfehlungen nötig - alle Anforderungen erfüllt!")

    # Professionelle Einschätzung
    st.subheader("Einschätzung")
    if gesamtscore >= 90:
        st.success("**Sehr gut geeignet** - Der Kandidat passt hervorragend zur Position und kann sofort starten.")
    elif gesamtscore >= 75:
        st.success("**Gut geeignet** - Starke Übereinstimmung mit geringem Qualifizierungsbedarf.")
    elif gesamtscore >= 60:
        st.info("**Grundsätzlich geeignet mit Einarbeitung** - Gute Grundlagen vorhanden, moderate Unterstützung erforderlich.")
    elif gesamtscore >= 40:
        st.warning("**Bedingt geeignet mit deutlichem Qualifizierungsbedarf** - Potenzial vorhanden, aber intensive Schulung nötig.")
    else:
        st.error("**Aktuell nicht passend** - Umfangreiche Qualifizierung erforderlich oder Quereinstieg prüfen.")

