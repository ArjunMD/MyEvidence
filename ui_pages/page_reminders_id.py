import streamlit as st

# ---------------------------------------------------------------------------
# Country / state → region membership
# ---------------------------------------------------------------------------
# When a user types a country or state, we also check all regions it belongs
# to.  This means an organism tagged with "middle east" will match "Iran"
# even if "iran" isn't explicitly in its keyword set.
_REGION_MEMBERSHIP: dict[str, list[str]] = {
    # --- Middle East ---
    "iran": ["middle east"],
    "iraq": ["middle east"],
    "syria": ["middle east"],
    "jordan": ["middle east"],
    "lebanon": ["middle east"],
    "israel": ["middle east"],
    "palestine": ["middle east"],
    "kuwait": ["middle east"],
    "bahrain": ["middle east"],
    "qatar": ["middle east"],
    "united arab emirates": ["middle east"],
    "uae": ["middle east"],
    "oman": ["middle east"],
    "saudi arabia": ["middle east"],
    "yemen": ["middle east"],
    "turkey": ["middle east"],
    "afghanistan": ["middle east", "central asia"],
    "egypt": ["middle east", "north africa"],
    # --- South Asia ---
    "india": ["south asia"],
    "pakistan": ["south asia", "central asia"],
    "bangladesh": ["south asia"],
    "nepal": ["south asia"],
    "sri lanka": ["south asia"],
    "bhutan": ["south asia"],
    "maldives": ["south asia"],
    # --- Southeast Asia ---
    "thailand": ["southeast asia"],
    "vietnam": ["southeast asia"],
    "cambodia": ["southeast asia"],
    "laos": ["southeast asia"],
    "myanmar": ["southeast asia"],
    "malaysia": ["southeast asia"],
    "indonesia": ["southeast asia"],
    "philippines": ["southeast asia"],
    "singapore": ["southeast asia"],
    "timor-leste": ["southeast asia"],
    "brunei": ["southeast asia"],
    # --- East Asia ---
    "china": ["east asia"],
    "japan": ["east asia"],
    "south korea": ["east asia"],
    "korea": ["east asia"],
    "north korea": ["east asia"],
    "taiwan": ["east asia"],
    "mongolia": ["east asia", "central asia"],
    # --- Central Asia ---
    "kazakhstan": ["central asia"],
    "uzbekistan": ["central asia"],
    "turkmenistan": ["central asia"],
    "kyrgyzstan": ["central asia"],
    "tajikistan": ["central asia"],
    # --- Sub-Saharan Africa (West) ---
    "nigeria": ["sub-saharan africa", "west africa"],
    "ghana": ["sub-saharan africa", "west africa"],
    "senegal": ["sub-saharan africa", "west africa"],
    "mali": ["sub-saharan africa", "west africa"],
    "burkina faso": ["sub-saharan africa", "west africa"],
    "guinea": ["sub-saharan africa", "west africa"],
    "guinea-bissau": ["sub-saharan africa", "west africa"],
    "ivory coast": ["sub-saharan africa", "west africa"],
    "cote d'ivoire": ["sub-saharan africa", "west africa"],
    "liberia": ["sub-saharan africa", "west africa"],
    "sierra leone": ["sub-saharan africa", "west africa"],
    "togo": ["sub-saharan africa", "west africa"],
    "benin": ["sub-saharan africa", "west africa"],
    "niger": ["sub-saharan africa", "west africa"],
    "gambia": ["sub-saharan africa", "west africa"],
    "cape verde": ["sub-saharan africa", "west africa"],
    "mauritania": ["sub-saharan africa", "west africa"],
    # --- Sub-Saharan Africa (East) ---
    "kenya": ["sub-saharan africa", "east africa"],
    "tanzania": ["sub-saharan africa", "east africa"],
    "uganda": ["sub-saharan africa", "east africa"],
    "ethiopia": ["sub-saharan africa", "east africa"],
    "eritrea": ["sub-saharan africa", "east africa"],
    "somalia": ["sub-saharan africa", "east africa"],
    "south sudan": ["sub-saharan africa", "east africa"],
    "sudan": ["sub-saharan africa", "east africa"],
    "rwanda": ["sub-saharan africa", "east africa"],
    "burundi": ["sub-saharan africa", "east africa"],
    "djibouti": ["sub-saharan africa", "east africa"],
    "madagascar": ["sub-saharan africa", "east africa"],
    "mozambique": ["sub-saharan africa", "east africa"],
    "malawi": ["sub-saharan africa", "east africa"],
    "zambia": ["sub-saharan africa", "east africa"],
    "zimbabwe": ["sub-saharan africa", "east africa"],
    # --- Sub-Saharan Africa (Central) ---
    "congo": ["sub-saharan africa", "central africa"],
    "democratic republic of the congo": ["sub-saharan africa", "central africa"],
    "drc": ["sub-saharan africa", "central africa"],
    "cameroon": ["sub-saharan africa", "central africa", "west africa"],
    "gabon": ["sub-saharan africa", "central africa"],
    "equatorial guinea": ["sub-saharan africa", "central africa"],
    "central african republic": ["sub-saharan africa", "central africa"],
    "chad": ["sub-saharan africa", "central africa"],
    "republic of the congo": ["sub-saharan africa", "central africa"],
    "sao tome and principe": ["sub-saharan africa", "central africa"],
    # --- Sub-Saharan Africa (Southern) ---
    "south africa": ["sub-saharan africa"],
    "angola": ["sub-saharan africa", "central africa"],
    "namibia": ["sub-saharan africa"],
    "botswana": ["sub-saharan africa"],
    "eswatini": ["sub-saharan africa"],
    "swaziland": ["sub-saharan africa"],
    "lesotho": ["sub-saharan africa"],
    # --- North Africa ---
    "morocco": ["north africa", "mediterranean"],
    "algeria": ["north africa", "mediterranean"],
    "tunisia": ["north africa", "mediterranean"],
    "libya": ["north africa", "mediterranean"],
    # --- Mediterranean (European) ---
    "greece": ["mediterranean", "europe"],
    "italy": ["mediterranean", "europe"],
    "spain": ["mediterranean", "europe"],
    "portugal": ["mediterranean", "europe"],
    "cyprus": ["mediterranean"],
    "croatia": ["mediterranean", "europe"],
    "albania": ["mediterranean", "europe"],
    "montenegro": ["mediterranean", "europe"],
    # --- Europe ---
    "france": ["europe"],
    "germany": ["europe"],
    "united kingdom": ["europe"],
    "uk": ["europe"],
    "ireland": ["europe"],
    "switzerland": ["europe"],
    "austria": ["europe"],
    "sweden": ["europe"],
    "norway": ["europe"],
    "finland": ["europe"],
    "denmark": ["europe"],
    "netherlands": ["europe"],
    "belgium": ["europe"],
    "poland": ["europe"],
    "czech republic": ["europe"],
    "hungary": ["europe"],
    "romania": ["europe"],
    "bulgaria": ["europe"],
    "serbia": ["europe"],
    "russia": ["europe"],
    # --- Central America ---
    "guatemala": ["central america"],
    "honduras": ["central america"],
    "el salvador": ["central america"],
    "nicaragua": ["central america"],
    "costa rica": ["central america"],
    "panama": ["central america"],
    "belize": ["central america"],
    # --- South America ---
    "brazil": ["south america"],
    "argentina": ["south america"],
    "colombia": ["south america"],
    "venezuela": ["south america"],
    "peru": ["south america"],
    "ecuador": ["south america"],
    "bolivia": ["south america"],
    "chile": ["south america"],
    "paraguay": ["south america"],
    "uruguay": ["south america"],
    "guyana": ["south america"],
    "suriname": ["south america"],
    "french guiana": ["south america"],
    # --- Caribbean ---
    "jamaica": ["caribbean"],
    "haiti": ["caribbean"],
    "dominican republic": ["caribbean"],
    "cuba": ["caribbean"],
    "puerto rico": ["caribbean"],
    "trinidad": ["caribbean"],
    "trinidad and tobago": ["caribbean"],
    "barbados": ["caribbean"],
    "bahamas": ["caribbean"],
    # --- Mexico ---
    "mexico": ["central america"],
    # --- Pacific Islands ---
    "fiji": ["pacific islands"],
    "samoa": ["pacific islands"],
    "tonga": ["pacific islands"],
    "vanuatu": ["pacific islands"],
    "papua new guinea": ["pacific islands"],
    "solomon islands": ["pacific islands"],
}

# ---------------------------------------------------------------------------
# Location → endemic‐infection lookup data
# ---------------------------------------------------------------------------
# Each entry: (organism_display, incubation_period, set_of_matching_location_keywords)
# Keywords are lowercase.  The lookup expands the user query to include
# parent regions via _REGION_MEMBERSHIP, so organisms tagged with
# "middle east" will match a search for "Iran".
_ENDEMIC_MAP: list[tuple[str, str, set[str]]] = [
    # -- Mycoses --
    (
        "Histoplasma capsulatum",
        "3–17 days (median ~10 days)",
        {
            "ohio", "mississippi", "indiana", "illinois", "kentucky",
            "tennessee", "arkansas", "missouri", "iowa", "wisconsin",
            "minnesota", "west virginia",
            "central america", "guatemala", "honduras", "el salvador",
            "nicaragua", "costa rica", "panama", "belize",
            "caribbean", "jamaica", "puerto rico", "dominican republic",
            "haiti", "cuba", "trinidad",
            "sub-saharan africa", "nigeria", "congo", "kenya", "tanzania",
            "uganda", "ethiopia", "ghana", "cameroon", "senegal",
            "south africa", "mozambique", "zambia", "zimbabwe", "malawi",
            "mali", "burkina faso", "guinea", "ivory coast", "cote d'ivoire",
            "niger", "chad", "sudan", "south sudan", "rwanda", "burundi",
            "angola", "namibia", "botswana", "madagascar", "somalia",
            "eritrea", "gabon", "liberia", "sierra leone", "togo", "benin",
        },
    ),
    (
        "Blastomyces dermatitidis",
        "21–100 days (median ~45 days)",
        {
            "wisconsin", "michigan", "minnesota", "illinois", "indiana",
            "ohio", "kentucky", "tennessee", "arkansas", "mississippi",
            "iowa", "missouri", "west virginia",
            "ontario", "manitoba", "quebec",
        },
    ),
    (
        "Coccidioides immitis / posadasii",
        "7–21 days (range 1–4 weeks)",
        {
            "arizona", "california", "nevada", "new mexico", "utah", "texas",
            "mexico", "central america", "guatemala", "honduras",
            "el salvador", "nicaragua", "costa rica", "panama", "belize",
            "south america", "brazil", "argentina", "colombia", "venezuela",
            "peru", "ecuador", "bolivia", "paraguay", "chile",
        },
    ),
    (
        "Paracoccidioides brasiliensis",
        "1 month – many years (long latency; reactivation decades after exposure)",
        {
            "brazil", "colombia", "venezuela", "argentina", "ecuador",
            "peru", "paraguay", "uruguay",
            "central america", "south america",
        },
    ),
    (
        "Talaromyces (Penicillium) marneffei",
        "~2–3 weeks (can be longer in subclinical infection)",
        {
            "thailand", "vietnam", "china", "india", "myanmar", "laos",
            "cambodia", "malaysia", "indonesia", "taiwan",
            "southeast asia",
        },
    ),
    (
        "Emergomyces pasteurianus",
        "Unknown (typically presents in advanced HIV/AIDS)",
        {"south africa"},
    ),
    # -- Parasites --
    (
        "Plasmodium spp. — malaria",
        "P. falciparum 7–14 days; P. vivax/ovale 12–18 days (relapse months–years); P. malariae 18–40 days",
        {
            "sub-saharan africa", "nigeria", "congo", "kenya", "tanzania",
            "uganda", "ethiopia", "ghana", "cameroon", "senegal",
            "south africa", "mozambique", "zambia", "zimbabwe", "malawi",
            "mali", "burkina faso", "guinea", "ivory coast", "cote d'ivoire",
            "niger", "chad", "sudan", "south sudan", "rwanda", "burundi",
            "angola", "namibia", "botswana", "madagascar", "somalia",
            "eritrea", "gabon", "liberia", "sierra leone", "togo", "benin",
            "india", "bangladesh", "pakistan", "sri lanka", "nepal",
            "myanmar", "thailand", "vietnam", "cambodia", "laos",
            "indonesia", "philippines", "malaysia", "papua new guinea",
            "southeast asia", "south asia",
            "central america", "south america",
            "guatemala", "honduras", "nicaragua", "panama", "belize",
            "colombia", "venezuela", "peru", "ecuador", "brazil",
            "bolivia", "guyana", "suriname",
        },
    ),
    (
        "Strongyloides stercoralis",
        "~2–4 weeks to initial symptoms; autoinfection can cause indefinite latency/reactivation years later",
        {
            "tropical", "subtropical",
            "southeast asia", "south asia",
            "sub-saharan africa", "central america", "south america",
            "brazil", "colombia", "peru", "india", "bangladesh", "thailand",
            "vietnam", "cambodia", "nigeria", "congo", "kenya", "tanzania",
            "appalachia", "west virginia", "kentucky", "tennessee",
            "virginia", "north carolina", "south carolina",
            "georgia", "alabama", "mississippi", "louisiana", "florida",
            "texas", "arkansas",
        },
    ),
    (
        "Trypanosoma cruzi — Chagas disease",
        "Acute phase 1–2 weeks after bite; chronic manifestations 10–30 years later",
        {
            "mexico", "central america", "south america",
            "guatemala", "honduras", "el salvador", "nicaragua",
            "costa rica", "panama", "belize",
            "brazil", "argentina", "bolivia", "colombia", "venezuela",
            "peru", "ecuador", "paraguay", "uruguay", "chile",
            "texas", "arizona", "new mexico", "california", "louisiana",
        },
    ),
    (
        "Trypanosoma brucei — African sleeping sickness",
        "T. b. rhodesiense days–weeks; T. b. gambiense weeks–months",
        {
            "sub-saharan africa",
            "congo", "central african republic", "south sudan", "chad",
            "uganda", "tanzania", "malawi", "zambia", "zimbabwe",
            "angola", "cameroon", "guinea", "nigeria", "gabon",
        },
    ),
    (
        "Leishmania spp.",
        "Cutaneous 2–8 weeks; visceral 2–6 months (range weeks–years)",
        {
            "middle east", "iraq", "iran", "syria", "afghanistan",
            "saudi arabia", "yemen", "turkey", "jordan", "lebanon",
            "pakistan", "india", "bangladesh", "nepal", "sri lanka",
            "central asia",
            "east africa", "ethiopia", "kenya", "sudan", "south sudan",
            "somalia", "eritrea", "uganda",
            "central america", "south america",
            "brazil", "colombia", "peru", "bolivia", "venezuela",
            "ecuador", "paraguay",
        },
    ),
    (
        "Schistosoma spp.",
        "Cercarial dermatitis within hours; Katayama fever 4–8 weeks; chronic disease months–years",
        {
            "sub-saharan africa", "nigeria", "congo", "kenya", "tanzania",
            "uganda", "ethiopia", "ghana", "cameroon", "senegal",
            "south africa", "mozambique", "zambia", "zimbabwe", "malawi",
            "mali", "burkina faso", "guinea", "ivory coast", "niger",
            "chad", "sudan", "south sudan", "rwanda", "burundi",
            "angola", "madagascar", "sierra leone", "togo", "benin",
            "egypt",
            "southeast asia", "philippines", "indonesia", "cambodia",
            "laos", "china",
            "middle east", "iraq", "yemen", "saudi arabia",
            "brazil", "south america",
        },
    ),
    (
        "Wuchereria bancrofti / Brugia spp. — lymphatic filariasis",
        "Months–years for clinical manifestations; microfilaremia ~6–12 months post-exposure",
        {
            "sub-saharan africa", "nigeria", "congo", "kenya", "tanzania",
            "uganda", "ethiopia", "ghana", "cameroon", "madagascar",
            "mozambique", "india", "bangladesh", "myanmar", "sri lanka",
            "indonesia", "philippines", "malaysia",
            "southeast asia", "south asia",
            "pacific islands", "papua new guinea", "fiji", "samoa",
        },
    ),
    (
        "Onchocerca volvulus — river blindness",
        "Months–years; microfilariae appear ~10–20 months after infection",
        {
            "sub-saharan africa", "nigeria", "congo", "cameroon",
            "ethiopia", "tanzania", "uganda", "mali", "burkina faso",
            "guinea", "ghana", "senegal", "sierra leone", "liberia",
            "ivory coast", "cote d'ivoire", "chad", "sudan",
            "yemen",
            "central america", "south america",
            "guatemala", "mexico", "venezuela", "brazil", "colombia",
            "ecuador",
        },
    ),
    (
        "Entamoeba histolytica",
        "2–4 weeks (range 1 week – months); liver abscess can present weeks–months after intestinal infection",
        {
            "central america", "south america",
            "mexico", "guatemala", "honduras", "nicaragua",
            "brazil", "colombia", "peru", "ecuador", "bolivia",
            "india", "bangladesh", "pakistan", "nepal",
            "south asia",
            "sub-saharan africa", "nigeria", "congo", "kenya", "ethiopia",
            "ghana", "cameroon", "tanzania", "uganda",
        },
    ),
    (
        "Echinococcus granulosus — hydatid cyst disease",
        "Months–years; cysts grow slowly (often asymptomatic for 5–20 years)",
        {
            "mediterranean", "greece", "italy", "spain", "portugal",
            "turkey", "cyprus",
            "middle east", "iraq", "iran", "syria", "jordan", "lebanon",
            "central asia", "kazakhstan", "uzbekistan", "turkmenistan",
            "kyrgyzstan", "tajikistan", "mongolia",
            "east africa", "kenya", "ethiopia", "tanzania", "uganda",
            "sudan",
            "south america", "argentina", "uruguay", "chile", "peru",
            "brazil",
            "china",
        },
    ),
    (
        "Clonorchis / Opisthorchis spp. — liver flukes",
        "~4 weeks to egg production; clinical symptoms may take months–years of chronic infection",
        {
            "china", "korea", "south korea", "north korea",
            "thailand", "vietnam", "laos", "cambodia", "myanmar",
            "east asia", "southeast asia",
            "russia",
        },
    ),
    (
        "Paragonimus westermani — lung fluke",
        "2–15 days for abdominal symptoms; pulmonary disease ~6–8 weeks after ingestion",
        {
            "china", "korea", "south korea", "north korea",
            "japan", "taiwan", "philippines",
            "thailand", "vietnam", "laos", "cambodia", "myanmar",
            "east asia", "southeast asia",
            "west africa", "nigeria", "cameroon",
            "central america", "south america",
            "peru", "ecuador", "colombia", "mexico",
        },
    ),
    (
        "Taenia solium — cysticercosis / neurocysticercosis",
        "Intestinal tapeworm 8–14 weeks; neurocysticercosis months–years (often 2–5 years)",
        {
            "central america", "south america",
            "mexico", "guatemala", "honduras", "el salvador", "nicaragua",
            "brazil", "peru", "colombia", "ecuador", "bolivia",
            "sub-saharan africa", "nigeria", "congo", "kenya", "tanzania",
            "uganda", "ethiopia", "cameroon", "mozambique", "zambia",
            "india", "nepal", "indonesia", "vietnam", "china",
            "south asia", "southeast asia",
        },
    ),
    (
        "Loa loa — eye worm",
        "Months–years; Calabar swellings typically appear ≥5 months after exposure",
        {
            "west africa", "central africa",
            "cameroon", "congo", "gabon", "equatorial guinea",
            "central african republic", "nigeria", "chad",
        },
    ),
    (
        "Babesia spp.",
        "1–4 weeks after tick bite (range 1–9 weeks); longer if transfusion-transmitted (1–9 weeks)",
        {
            "connecticut", "massachusetts", "rhode island", "new york",
            "new jersey", "pennsylvania", "maine", "new hampshire",
            "vermont", "delaware", "maryland", "virginia",
            "wisconsin", "minnesota", "michigan",
            "europe", "france", "united kingdom", "ireland", "spain",
            "portugal", "germany", "switzerland", "austria", "croatia",
            "sweden",
        },
    ),
    # -- Bacteria --
    (
        "Burkholderia pseudomallei — melioidosis",
        "1–21 days (median ~9 days); latent reactivation years–decades later",
        {
            "southeast asia", "thailand", "vietnam", "cambodia", "laos",
            "myanmar", "malaysia", "indonesia", "singapore",
            "india", "bangladesh", "sri lanka", "south asia",
            "australia", "papua new guinea",
            "brazil",
            "sub-saharan africa", "nigeria", "madagascar",
        },
    ),
    (
        "Brucella spp. — brucellosis",
        "1–4 weeks (range 5 days – months)",
        {
            "mediterranean", "greece", "italy", "spain", "portugal",
            "turkey",
            "middle east", "iraq", "iran", "syria", "jordan", "lebanon",
            "saudi arabia",
            "central asia", "kazakhstan", "uzbekistan",
            "mexico", "central america", "south america",
            "sub-saharan africa", "east africa",
            "india", "pakistan",
        },
    ),
    (
        "Coxiella burnetii — Q fever",
        "2–3 weeks (range 1–6 weeks)",
        {
            "australia",
            "mediterranean", "france", "spain", "italy", "greece",
            "middle east",
            "sub-saharan africa",
            "south asia", "india",
        },
    ),
    (
        "Rickettsia rickettsii — Rocky Mountain spotted fever",
        "2–14 days (median ~7 days)",
        {
            "north carolina", "tennessee", "oklahoma", "arkansas",
            "missouri", "virginia", "georgia", "south carolina",
            "texas", "arizona", "mississippi", "alabama",
            "mexico", "central america", "south america",
            "brazil", "colombia", "panama", "costa rica", "argentina",
        },
    ),
    (
        "Orientia tsutsugamushi — scrub typhus",
        "6–21 days (median ~10 days)",
        {
            "southeast asia", "thailand", "vietnam", "cambodia", "laos",
            "myanmar", "malaysia", "indonesia",
            "east asia", "china", "japan", "south korea", "korea", "taiwan",
            "south asia", "india", "nepal", "sri lanka", "bangladesh",
            "australia", "papua new guinea",
            "pacific islands",
        },
    ),
    (
        "Rickettsia typhi — endemic (murine) typhus",
        "7–14 days",
        {
            "texas", "california", "hawaii", "florida",
            "southeast asia", "south asia",
            "sub-saharan africa",
            "mediterranean", "middle east",
            "central america", "south america",
        },
    ),
    (
        "Bartonella bacilliformis — Carrion's disease / Oroya fever",
        "~3 weeks (range 2–14 weeks)",
        {"peru", "ecuador", "colombia"},
    ),
    (
        "Leptospira spp. — leptospirosis",
        "2–30 days (median ~10 days)",
        {
            "southeast asia", "thailand", "vietnam", "philippines",
            "malaysia", "indonesia", "cambodia", "laos", "myanmar",
            "south asia", "india", "bangladesh", "sri lanka", "nepal",
            "central america", "south america",
            "brazil", "peru", "colombia", "nicaragua",
            "caribbean", "puerto rico", "jamaica", "haiti",
            "sub-saharan africa",
            "pacific islands",
            "hawaii",
        },
    ),
    (
        "Borrelia burgdorferi — Lyme disease",
        "3–30 days (median ~7–14 days for erythema migrans)",
        {
            "connecticut", "massachusetts", "rhode island", "new york",
            "new jersey", "pennsylvania", "maine", "new hampshire",
            "vermont", "delaware", "maryland", "virginia",
            "wisconsin", "minnesota", "michigan",
            "europe", "germany", "austria", "switzerland", "france",
            "sweden", "norway", "finland", "united kingdom",
            "czech republic", "poland", "slovenia",
        },
    ),
    (
        "Francisella tularensis — tularemia",
        "3–5 days (range 1–14 days)",
        {
            "arkansas", "missouri", "oklahoma", "kansas",
            "massachusetts", "connecticut",
            "europe", "sweden", "finland", "norway",
            "turkey", "central asia",
        },
    ),
    (
        "Yersinia pestis — plague",
        "Bubonic 2–8 days; pneumonic 1–3 days",
        {
            "new mexico", "arizona", "colorado", "california", "oregon",
            "utah", "nevada",
            "madagascar", "congo", "uganda", "tanzania",
            "sub-saharan africa",
            "peru", "bolivia",
            "central asia",
            "china", "mongolia", "india",
        },
    ),
    (
        "Mycobacterium ulcerans — Buruli ulcer",
        "~4–5 months (range weeks–months)",
        {
            "west africa", "ghana", "cameroon", "nigeria",
            "ivory coast", "cote d'ivoire", "benin", "togo",
            "congo",
            "sub-saharan africa",
            "australia",
        },
    ),
    # -- Viruses --
    (
        "Dengue virus",
        "4–10 days (median ~5–7 days)",
        {
            "southeast asia", "thailand", "vietnam", "philippines",
            "malaysia", "indonesia", "cambodia", "laos", "myanmar",
            "singapore",
            "south asia", "india", "bangladesh", "sri lanka", "nepal",
            "pakistan",
            "sub-saharan africa", "east africa", "west africa",
            "central america", "south america",
            "brazil", "colombia", "mexico", "peru", "ecuador",
            "venezuela", "honduras", "nicaragua", "guatemala",
            "el salvador", "costa rica", "panama",
            "caribbean", "puerto rico", "cuba", "jamaica",
            "haiti", "dominican republic",
            "hawaii", "florida", "texas",
        },
    ),
    (
        "Chikungunya virus",
        "3–7 days (range 1–12 days)",
        {
            "southeast asia", "south asia",
            "india", "bangladesh", "sri lanka", "thailand",
            "philippines", "indonesia", "malaysia",
            "sub-saharan africa", "east africa", "west africa",
            "central america", "south america",
            "caribbean",
            "brazil", "colombia",
        },
    ),
    (
        "Zika virus",
        "3–14 days (median ~6 days)",
        {
            "southeast asia", "south asia",
            "central america", "south america",
            "brazil", "colombia", "mexico",
            "caribbean", "puerto rico",
            "sub-saharan africa",
            "pacific islands",
            "texas", "florida",
        },
    ),
    (
        "Yellow fever virus",
        "3–6 days",
        {
            "sub-saharan africa", "nigeria", "congo", "cameroon",
            "ethiopia", "ghana", "guinea", "mali", "senegal",
            "sierra leone", "angola", "uganda", "kenya",
            "south america", "brazil", "peru", "colombia",
            "ecuador", "bolivia", "venezuela",
            "trinidad",
        },
    ),
    (
        "Japanese encephalitis virus",
        "5–15 days",
        {
            "east asia", "china", "japan", "south korea", "korea", "taiwan",
            "southeast asia", "thailand", "vietnam", "cambodia", "laos",
            "myanmar", "philippines", "malaysia", "indonesia",
            "south asia", "india", "nepal", "bangladesh", "sri lanka",
            "pakistan",
            "australia", "papua new guinea",
        },
    ),
    (
        "Ebola virus",
        "2–21 days (median ~8–10 days)",
        {
            "congo", "democratic republic of the congo",
            "guinea", "sierra leone", "liberia",
            "uganda", "sudan", "south sudan", "gabon",
            "west africa", "central africa",
            "sub-saharan africa",
        },
    ),
    (
        "Marburg virus",
        "2–21 days (median ~5–9 days)",
        {
            "uganda", "congo", "angola", "kenya",
            "south africa", "rwanda",
            "east africa", "central africa",
            "sub-saharan africa",
        },
    ),
    (
        "Lassa virus — Lassa fever",
        "1–3 weeks",
        {
            "west africa",
            "nigeria", "sierra leone", "liberia", "guinea",
            "mali", "ghana", "benin", "togo",
        },
    ),
    (
        "Crimean-Congo hemorrhagic fever virus",
        "1–3 days (tick bite) or 5–6 days (blood/tissue contact)",
        {
            "turkey", "middle east", "iran", "iraq",
            "central asia", "kazakhstan", "uzbekistan", "tajikistan",
            "afghanistan", "pakistan",
            "sub-saharan africa", "south africa", "congo", "uganda",
            "senegal", "mauritania", "nigeria",
            "mediterranean", "greece", "albania", "bulgaria",
            "russia",
        },
    ),
    (
        "Rift Valley fever virus",
        "2–6 days",
        {
            "sub-saharan africa", "east africa",
            "kenya", "tanzania", "somalia", "sudan", "south sudan",
            "ethiopia", "madagascar", "mozambique",
            "egypt",
            "middle east", "saudi arabia", "yemen",
        },
    ),
    (
        "West Nile virus",
        "2–14 days (median ~2–6 days)",
        {
            "sub-saharan africa",
            "middle east", "egypt", "israel",
            "mediterranean", "greece", "italy", "romania",
            "europe", "russia",
            "texas", "california", "colorado", "arizona",
            "illinois", "new york", "florida", "louisiana",
            "nebraska", "ohio", "michigan", "south dakota",
            "north dakota",
        },
    ),
    (
        "Hantavirus — hantavirus pulmonary syndrome / HFRS",
        "HPS 1–5 weeks; HFRS 1–2 weeks (range 5–42 days)",
        {
            "new mexico", "arizona", "colorado", "utah",
            "california", "washington", "montana", "oregon",
            "texas", "idaho",
            "argentina", "chile", "brazil", "panama",
            "south america",
            "europe", "finland", "sweden", "russia", "germany",
            "china", "south korea", "korea",
        },
    ),
    (
        "Tick-borne encephalitis virus",
        "7–14 days (range 4–28 days)",
        {
            "europe", "austria", "czech republic", "germany",
            "switzerland", "sweden", "finland", "norway",
            "poland", "hungary", "romania", "bulgaria",
            "croatia", "slovenia", "serbia",
            "russia", "china", "mongolia",
            "south korea", "japan",
        },
    ),
    (
        "Nipah virus",
        "4–14 days (range up to 45 days)",
        {
            "bangladesh", "india",
            "malaysia", "singapore",
            "south asia", "southeast asia",
        },
    ),
    (
        "Rabies virus",
        "1–3 months (range days – >1 year)",
        {
            "india", "south asia", "bangladesh", "nepal", "pakistan",
            "southeast asia", "indonesia", "philippines", "vietnam",
            "myanmar", "thailand", "cambodia", "laos",
            "sub-saharan africa", "east africa", "west africa",
            "central africa",
            "china",
            "central america", "south america",
            "middle east", "afghanistan",
        },
    ),
]


def _lookup_infections(query: str) -> list[tuple[str, str]]:
    """Return list of (organism, incubation_period) matching *query*.

    The query is expanded:
      1. Direct substring match of the raw query against organism keyword sets
         (lenient — handles partial input like "Congo" matching "congo").
      2. If the query matches a country/state in _REGION_MEMBERSHIP, all of
         that location's parent regions are checked with **exact** matching
         (e.g. "iran" → exact-check "middle east", avoiding "east asia"
         falsely matching "southeast asia").
    """
    q = query.strip().lower()
    if not q:
        return []

    # Collect parent regions via exact membership lookup
    extra_regions: set[str] = set()
    for loc, regions in _REGION_MEMBERSHIP.items():
        if q in loc or loc in q:
            extra_regions.update(regions)

    hits: list[tuple[str, str]] = []
    for organism, incubation, keywords in _ENDEMIC_MAP:
        matched = False
        # 1) Check expanded regions with EXACT match (no substring)
        if extra_regions & keywords:
            matched = True
        # 2) Check the raw user query with substring match
        if not matched:
            for kw in keywords:
                if q in kw or kw in q:
                    matched = True
                    break
        if matched:
            hits.append((organism, incubation))
    return hits


def render() -> None:
    st.title("📝 Infectious Disease")

    with st.expander("Endemic Infections", expanded=False):
        # --- location lookup inside expander ---
        location = st.text_input(
            "Enter a country or US state",
            placeholder="e.g. Brazil, Ohio, Thailand …",
            key="endemic_lookup",
        )
        if location and location.strip():
            results = _lookup_infections(location)
            if results:
                st.success(f"**{len(results)}** endemic infection(s) associated with **{location.strip()}**:")
                for organism, incubation in results:
                    st.markdown(f"- **{organism}**  \n  *Incubation:* {incubation}")
            else:
                st.warning(f"No endemic infections found for **{location.strip()}**. Try a different spelling or a broader region (e.g. 'Sub-Saharan Africa', 'Southeast Asia').")

        st.markdown("---")

        # --- reference tables ---
        st.markdown(
            "### Endemic Mycoses\n\n"
            "| Organism | Geographic Area |\n"
            "| --- | --- |\n"
            "| **Histoplasma capsulatum** | Ohio & Mississippi River valleys, Central America, Caribbean, Sub-Saharan Africa |\n"
            "| **Blastomyces dermatitidis** | Great Lakes, Ohio & Mississippi River valleys, St. Lawrence River |\n"
            "| **Coccidioides immitis / posadasii** | Southwestern US (Arizona, California Central Valley), Northern Mexico, Central & South America |\n"
            "| **Paracoccidioides brasiliensis** | Latin America (Brazil, Colombia, Venezuela, Argentina) |\n"
            "| **Talaromyces (Penicillium) marneffei** | Southeast Asia (Thailand, Vietnam, Southern China, India) |\n"
            "| **Emergomyces pasteurianus** | South Africa, primarily in HIV/AIDS |\n"
            "\n---\n\n"
            "### Endemic Parasites\n\n"
            "| Organism | Geographic Area |\n"
            "| --- | --- |\n"
            "| **Plasmodium spp.** (malaria) | Sub-Saharan Africa, South/Southeast Asia, Central & South America |\n"
            "| **Strongyloides stercoralis** | Tropical/subtropical worldwide, Southeastern US, Appalachia |\n"
            "| **Trypanosoma cruzi** (Chagas) | Central & South America, Mexico, Southern US |\n"
            "| **Trypanosoma brucei** (African sleeping sickness) | Sub-Saharan Africa (tsetse fly belt) |\n"
            "| **Leishmania spp.** | Middle East, Central/South Asia, East Africa, Central & South America |\n"
            "| **Schistosoma spp.** | Sub-Saharan Africa, Southeast Asia, Middle East, South America (Brazil) |\n"
            "| **Wuchereria bancrofti / Brugia** (lymphatic filariasis) | Sub-Saharan Africa, South/Southeast Asia, Pacific Islands |\n"
            "| **Onchocerca volvulus** (river blindness) | Sub-Saharan Africa, Yemen, focal areas in Central & South America |\n"
            "| **Entamoeba histolytica** | Central & South America, South Asia, Sub-Saharan Africa |\n"
            "| **Echinococcus granulosus** (hydatid cyst) | Mediterranean, Middle East, Central Asia, East Africa, South America |\n"
            "| **Clonorchis / Opisthorchis** (liver flukes) | East & Southeast Asia (China, Korea, Thailand, Vietnam) |\n"
            "| **Paragonimus westermani** (lung fluke) | East & Southeast Asia, West Africa, Central & South America |\n"
            "| **Taenia solium** (cysticercosis) | Central & South America, Sub-Saharan Africa, South/Southeast Asia |\n"
            "| **Loa loa** (eye worm) | West & Central Africa (rain forest belt) |\n"
            "| **Babesia spp.** | Northeastern & upper Midwestern US, parts of Europe |\n"
            "\n---\n\n"
            "### Endemic Bacteria\n\n"
            "| Organism | Geographic Area |\n"
            "| --- | --- |\n"
            "| **Burkholderia pseudomallei** (melioidosis) | Southeast Asia, Northern Australia, South Asia |\n"
            "| **Brucella spp.** (brucellosis) | Mediterranean, Middle East, Central Asia, Mexico, Sub-Saharan Africa |\n"
            "| **Coxiella burnetii** (Q fever) | Australia, Mediterranean, Middle East, Sub-Saharan Africa |\n"
            "| **Rickettsia rickettsii** (RMSF) | Southeastern & South-central US, Mexico, Central & South America |\n"
            "| **Orientia tsutsugamushi** (scrub typhus) | East & Southeast Asia, South Asia, Australia, Pacific Islands |\n"
            "| **Rickettsia typhi** (endemic typhus) | Texas, California, Hawaii, Florida, tropical worldwide |\n"
            "| **Bartonella bacilliformis** (Carrion's disease) | Andes (Peru, Ecuador, Colombia) |\n"
            "| **Leptospira spp.** (leptospirosis) | Tropical worldwide, Southeast Asia, South Asia, Caribbean, Central & South America |\n"
            "| **Borrelia burgdorferi** (Lyme disease) | Northeastern & upper Midwestern US, Northern Europe |\n"
            "| **Francisella tularensis** (tularemia) | South-central US, Scandinavia, Turkey |\n"
            "| **Yersinia pestis** (plague) | Southwestern US, Madagascar, Congo, Peru, Central Asia |\n"
            "| **Mycobacterium ulcerans** (Buruli ulcer) | West Africa, Australia |\n"
            "\n---\n\n"
            "### Endemic Viruses\n\n"
            "| Organism | Geographic Area |\n"
            "| --- | --- |\n"
            "| **Dengue virus** | Tropical worldwide, Southeast Asia, South Asia, Central & South America, Caribbean |\n"
            "| **Chikungunya virus** | Southeast Asia, South Asia, Sub-Saharan Africa, Central & South America, Caribbean |\n"
            "| **Zika virus** | Central & South America, Southeast Asia, Pacific Islands, Sub-Saharan Africa |\n"
            "| **Yellow fever virus** | Sub-Saharan Africa, tropical South America |\n"
            "| **Japanese encephalitis virus** | East & Southeast Asia, South Asia, Northern Australia |\n"
            "| **Ebola virus** | Central & West Africa (Congo, Guinea, Sierra Leone, Liberia, Uganda) |\n"
            "| **Marburg virus** | Central & East Africa (Uganda, Congo, Angola) |\n"
            "| **Lassa virus** (Lassa fever) | West Africa (Nigeria, Sierra Leone, Liberia, Guinea) |\n"
            "| **Crimean-Congo hemorrhagic fever virus** | Turkey, Middle East, Central Asia, Sub-Saharan Africa, Southeastern Europe |\n"
            "| **Rift Valley fever virus** | East Africa, Egypt, Middle East |\n"
            "| **West Nile virus** | Sub-Saharan Africa, Middle East, Mediterranean, US |\n"
            "| **Hantavirus** (HPS / HFRS) | Southwestern US, South America, Europe, East Asia |\n"
            "| **Tick-borne encephalitis virus** | Central & Northern Europe, Russia, East Asia |\n"
            "| **Nipah virus** | Bangladesh, India, Malaysia |\n"
            "| **Rabies virus** | South Asia, Southeast Asia, Sub-Saharan Africa, Central & South America |"
        )
