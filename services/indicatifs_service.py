"""
Détection automatique du pays depuis l'indicatif téléphonique.
Utilisé lors de l'enregistrement d'une réservation.
"""

# Dictionnaire indicatif → (pays, code_iso, drapeau)
# Trié du plus long au plus court pour matcher en priorité les indicatifs longs
INDICATIFS = {
    # 4 chiffres
    "1242": ("Bahamas", "BS", "🇧🇸"),
    "1246": ("Barbade", "BB", "🇧🇧"),
    "1264": ("Anguilla", "AI", "🇦🇮"),
    "1268": ("Antigua-et-Barbuda", "AG", "🇦🇬"),
    "1284": ("Îles Vierges britanniques", "VG", "🇻🇬"),
    "1340": ("Îles Vierges américaines", "VI", "🇻🇮"),
    "1345": ("Îles Caïmans", "KY", "🇰🇾"),
    "1441": ("Bermudes", "BM", "🇧🇲"),
    "1473": ("Grenade", "GD", "🇬🇩"),
    "1649": ("Îles Turques-et-Caïques", "TC", "🇹🇨"),
    "1664": ("Montserrat", "MS", "🇲🇸"),
    "1670": ("Mariannes du Nord", "MP", "🇲🇵"),
    "1671": ("Guam", "GU", "🇬🇺"),
    "1684": ("Samoa américaines", "AS", "🇦🇸"),
    "1721": ("Sint Maarten", "SX", "🇸🇽"),
    "1758": ("Sainte-Lucie", "LC", "🇱🇨"),
    "1767": ("Dominique", "DM", "🇩🇲"),
    "1784": ("Saint-Vincent", "VC", "🇻🇨"),
    "1787": ("Porto Rico", "PR", "🇵🇷"),
    "1809": ("République dominicaine", "DO", "🇩🇴"),
    "1868": ("Trinité-et-Tobago", "TT", "🇹🇹"),
    "1869": ("Saint-Kitts-et-Nevis", "KN", "🇰🇳"),
    "1876": ("Jamaïque", "JM", "🇯🇲"),
    # 3 chiffres
    "213": ("Algérie", "DZ", "🇩🇿"),
    "216": ("Tunisie", "TN", "🇹🇳"),
    "218": ("Libye", "LY", "🇱🇾"),
    "220": ("Gambie", "GM", "🇬🇲"),
    "221": ("Sénégal", "SN", "🇸🇳"),
    "222": ("Mauritanie", "MR", "🇲🇷"),
    "223": ("Mali", "ML", "🇲🇱"),
    "224": ("Guinée", "GN", "🇬🇳"),
    "225": ("Côte d'Ivoire", "CI", "🇨🇮"),
    "226": ("Burkina Faso", "BF", "🇧🇫"),
    "227": ("Niger", "NE", "🇳🇪"),
    "228": ("Togo", "TG", "🇹🇬"),
    "229": ("Bénin", "BJ", "🇧🇯"),
    "230": ("Maurice", "MU", "🇲🇺"),
    "231": ("Libéria", "LR", "🇱🇷"),
    "232": ("Sierra Leone", "SL", "🇸🇱"),
    "233": ("Ghana", "GH", "🇬🇭"),
    "234": ("Nigeria", "NG", "🇳🇬"),
    "235": ("Tchad", "TD", "🇹🇩"),
    "236": ("République centrafricaine", "CF", "🇨🇫"),
    "237": ("Cameroun", "CM", "🇨🇲"),
    "238": ("Cap-Vert", "CV", "🇨🇻"),
    "239": ("Sao Tomé-et-Principe", "ST", "🇸🇹"),
    "240": ("Guinée équatoriale", "GQ", "🇬🇶"),
    "241": ("Gabon", "GA", "🇬🇦"),
    "242": ("Congo", "CG", "🇨🇬"),
    "243": ("RD Congo", "CD", "🇨🇩"),
    "244": ("Angola", "AO", "🇦🇴"),
    "245": ("Guinée-Bissau", "GW", "🇬🇼"),
    "246": ("Diego Garcia", "IO", "🇮🇴"),
    "247": ("Ascension", "SH", "🇸🇭"),
    "248": ("Seychelles", "SC", "🇸🇨"),
    "249": ("Soudan", "SD", "🇸🇩"),
    "250": ("Rwanda", "RW", "🇷🇼"),
    "251": ("Éthiopie", "ET", "🇪🇹"),
    "252": ("Somalie", "SO", "🇸🇴"),
    "253": ("Djibouti", "DJ", "🇩🇯"),
    "254": ("Kenya", "KE", "🇰🇪"),
    "255": ("Tanzanie", "TZ", "🇹🇿"),
    "256": ("Ouganda", "UG", "🇺🇬"),
    "257": ("Burundi", "BI", "🇧🇮"),
    "258": ("Mozambique", "MZ", "🇲🇿"),
    "260": ("Zambie", "ZM", "🇿🇲"),
    "261": ("Madagascar", "MG", "🇲🇬"),
    "262": ("La Réunion", "RE", "🇷🇪"),
    "263": ("Zimbabwe", "ZW", "🇿🇼"),
    "264": ("Namibie", "NA", "🇳🇦"),
    "265": ("Malawi", "MW", "🇲🇼"),
    "266": ("Lesotho", "LS", "🇱🇸"),
    "267": ("Botswana", "BW", "🇧🇼"),
    "268": ("Eswatini", "SZ", "🇸🇿"),
    "269": ("Comores", "KM", "🇰🇲"),
    "27":  ("Afrique du Sud", "ZA", "🇿🇦"),
    "290": ("Sainte-Hélène", "SH", "🇸🇭"),
    "291": ("Érythrée", "ER", "🇪🇷"),
    "297": ("Aruba", "AW", "🇦🇼"),
    "298": ("Îles Féroé", "FO", "🇫🇴"),
    "299": ("Groenland", "GL", "🇬🇱"),
    "30":  ("Grèce", "GR", "🇬🇷"),
    "31":  ("Pays-Bas", "NL", "🇳🇱"),
    "32":  ("Belgique", "BE", "🇧🇪"),
    "33":  ("France", "FR", "🇫🇷"),
    "34":  ("Espagne", "ES", "🇪🇸"),
    "350": ("Gibraltar", "GI", "🇬🇮"),
    "351": ("Portugal", "PT", "🇵🇹"),
    "352": ("Luxembourg", "LU", "🇱🇺"),
    "353": ("Irlande", "IE", "🇮🇪"),
    "354": ("Islande", "IS", "🇮🇸"),
    "355": ("Albanie", "AL", "🇦🇱"),
    "356": ("Malte", "MT", "🇲🇹"),
    "357": ("Chypre", "CY", "🇨🇾"),
    "358": ("Finlande", "FI", "🇫🇮"),
    "359": ("Bulgarie", "BG", "🇧🇬"),
    "36":  ("Hongrie", "HU", "🇭🇺"),
    "370": ("Lituanie", "LT", "🇱🇹"),
    "371": ("Lettonie", "LV", "🇱🇻"),
    "372": ("Estonie", "EE", "🇪🇪"),
    "373": ("Moldavie", "MD", "🇲🇩"),
    "374": ("Arménie", "AM", "🇦🇲"),
    "375": ("Biélorussie", "BY", "🇧🇾"),
    "376": ("Andorre", "AD", "🇦🇩"),
    "377": ("Monaco", "MC", "🇲🇨"),
    "378": ("Saint-Marin", "SM", "🇸🇲"),
    "380": ("Ukraine", "UA", "🇺🇦"),
    "381": ("Serbie", "RS", "🇷🇸"),
    "382": ("Monténégro", "ME", "🇲🇪"),
    "385": ("Croatie", "HR", "🇭🇷"),
    "386": ("Slovénie", "SI", "🇸🇮"),
    "387": ("Bosnie-Herzégovine", "BA", "🇧🇦"),
    "389": ("Macédoine du Nord", "MK", "🇲🇰"),
    "39":  ("Italie", "IT", "🇮🇹"),
    "40":  ("Roumanie", "RO", "🇷🇴"),
    "41":  ("Suisse", "CH", "🇨🇭"),
    "420": ("République tchèque", "CZ", "🇨🇿"),
    "421": ("Slovaquie", "SK", "🇸🇰"),
    "423": ("Liechtenstein", "LI", "🇱🇮"),
    "43":  ("Autriche", "AT", "🇦🇹"),
    "44":  ("Royaume-Uni", "GB", "🇬🇧"),
    "45":  ("Danemark", "DK", "🇩🇰"),
    "46":  ("Suède", "SE", "🇸🇪"),
    "47":  ("Norvège", "NO", "🇳🇴"),
    "48":  ("Pologne", "PL", "🇵🇱"),
    "49":  ("Allemagne", "DE", "🇩🇪"),
    "500": ("Malouines", "FK", "🇫🇰"),
    "501": ("Belize", "BZ", "🇧🇿"),
    "502": ("Guatemala", "GT", "🇬🇹"),
    "503": ("Salvador", "SV", "🇸🇻"),
    "504": ("Honduras", "HN", "🇭🇳"),
    "505": ("Nicaragua", "NI", "🇳🇮"),
    "506": ("Costa Rica", "CR", "🇨🇷"),
    "507": ("Panama", "PA", "🇵🇦"),
    "508": ("Saint-Pierre-et-Miquelon", "PM", "🇵🇲"),
    "509": ("Haïti", "HT", "🇭🇹"),
    "51":  ("Pérou", "PE", "🇵🇪"),
    "52":  ("Mexique", "MX", "🇲🇽"),
    "53":  ("Cuba", "CU", "🇨🇺"),
    "54":  ("Argentine", "AR", "🇦🇷"),
    "55":  ("Brésil", "BR", "🇧🇷"),
    "56":  ("Chili", "CL", "🇨🇱"),
    "57":  ("Colombie", "CO", "🇨🇴"),
    "58":  ("Venezuela", "VE", "🇻🇪"),
    "590": ("Guadeloupe", "GP", "🇬🇵"),
    "591": ("Bolivie", "BO", "🇧🇴"),
    "592": ("Guyana", "GY", "🇬🇾"),
    "593": ("Équateur", "EC", "🇪🇨"),
    "594": ("Guyane française", "GF", "🇬🇫"),
    "595": ("Paraguay", "PY", "🇵🇾"),
    "596": ("Martinique", "MQ", "🇲🇶"),
    "597": ("Suriname", "SR", "🇸🇷"),
    "598": ("Uruguay", "UY", "🇺🇾"),
    "599": ("Antilles néerlandaises", "AN", "🇧🇶"),
    "60":  ("Malaisie", "MY", "🇲🇾"),
    "61":  ("Australie", "AU", "🇦🇺"),
    "62":  ("Indonésie", "ID", "🇮🇩"),
    "63":  ("Philippines", "PH", "🇵🇭"),
    "64":  ("Nouvelle-Zélande", "NZ", "🇳🇿"),
    "65":  ("Singapour", "SG", "🇸🇬"),
    "66":  ("Thaïlande", "TH", "🇹🇭"),
    "670": ("Timor oriental", "TL", "🇹🇱"),
    "672": ("Territoire antarctique", "AQ", "🇦🇶"),
    "673": ("Brunei", "BN", "🇧🇳"),
    "674": ("Nauru", "NR", "🇳🇷"),
    "675": ("Papouasie-Nouvelle-Guinée", "PG", "🇵🇬"),
    "676": ("Tonga", "TO", "🇹🇴"),
    "677": ("Salomon", "SB", "🇸🇧"),
    "678": ("Vanuatu", "VU", "🇻🇺"),
    "679": ("Fidji", "FJ", "🇫🇯"),
    "680": ("Palaos", "PW", "🇵🇼"),
    "681": ("Wallis-et-Futuna", "WF", "🇼🇫"),
    "682": ("Cook", "CK", "🇨🇰"),
    "683": ("Niue", "NU", "🇳🇺"),
    "685": ("Samoa", "WS", "🇼🇸"),
    "686": ("Kiribati", "KI", "🇰🇮"),
    "687": ("Nouvelle-Calédonie", "NC", "🇳🇨"),
    "688": ("Tuvalu", "TV", "🇹🇻"),
    "689": ("Polynésie française", "PF", "🇵🇫"),
    "690": ("Tokelau", "TK", "🇹🇰"),
    "691": ("Micronésie", "FM", "🇫🇲"),
    "692": ("Marshall", "MH", "🇲🇭"),
    "7":   ("Russie", "RU", "🇷🇺"),
    "81":  ("Japon", "JP", "🇯🇵"),
    "82":  ("Corée du Sud", "KR", "🇰🇷"),
    "84":  ("Vietnam", "VN", "🇻🇳"),
    "850": ("Corée du Nord", "KP", "🇰🇵"),
    "852": ("Hong Kong", "HK", "🇭🇰"),
    "853": ("Macao", "MO", "🇲🇴"),
    "855": ("Cambodge", "KH", "🇰🇭"),
    "856": ("Laos", "LA", "🇱🇦"),
    "86":  ("Chine", "CN", "🇨🇳"),
    "880": ("Bangladesh", "BD", "🇧🇩"),
    "886": ("Taïwan", "TW", "🇹🇼"),
    "90":  ("Turquie", "TR", "🇹🇷"),
    "91":  ("Inde", "IN", "🇮🇳"),
    "92":  ("Pakistan", "PK", "🇵🇰"),
    "93":  ("Afghanistan", "AF", "🇦🇫"),
    "94":  ("Sri Lanka", "LK", "🇱🇰"),
    "95":  ("Myanmar", "MM", "🇲🇲"),
    "960": ("Maldives", "MV", "🇲🇻"),
    "961": ("Liban", "LB", "🇱🇧"),
    "962": ("Jordanie", "JO", "🇯🇴"),
    "963": ("Syrie", "SY", "🇸🇾"),
    "964": ("Irak", "IQ", "🇮🇶"),
    "965": ("Koweït", "KW", "🇰🇼"),
    "966": ("Arabie saoudite", "SA", "🇸🇦"),
    "967": ("Yémen", "YE", "🇾🇪"),
    "968": ("Oman", "OM", "🇴🇲"),
    "970": ("Palestine", "PS", "🇵🇸"),
    "971": ("Émirats arabes unis", "AE", "🇦🇪"),
    "972": ("Israël", "IL", "🇮🇱"),
    "973": ("Bahreïn", "BH", "🇧🇭"),
    "974": ("Qatar", "QA", "🇶🇦"),
    "975": ("Bhoutan", "BT", "🇧🇹"),
    "976": ("Mongolie", "MN", "🇲🇳"),
    "977": ("Népal", "NP", "🇳🇵"),
    "98":  ("Iran", "IR", "🇮🇷"),
    "992": ("Tadjikistan", "TJ", "🇹🇯"),
    "993": ("Turkménistan", "TM", "🇹🇲"),
    "994": ("Azerbaïdjan", "AZ", "🇦🇿"),
    "995": ("Géorgie", "GE", "🇬🇪"),
    "996": ("Kirghizistan", "KG", "🇰🇬"),
    "998": ("Ouzbékistan", "UZ", "🇺🇿"),
    # 1 chiffre
    "1":   ("États-Unis / Canada", "US", "🇺🇸"),
}

# Trier par longueur décroissante pour matcher les codes longs en premier
_SORTED_KEYS = sorted(INDICATIFS.keys(), key=len, reverse=True)


def detect_pays(telephone: str) -> tuple[str, str, str] | None:
    """
    Détecte le pays depuis un numéro de téléphone international.
    
    Retourne (pays, code_iso, drapeau) ou None si non trouvé.
    
    Exemples :
        "+33 6 12 34 56 78" → ("France", "FR", "🇫🇷")
        "+44 20 7946 0958"  → ("Royaume-Uni", "GB", "🇬🇧")
        "+1 212 555 0100"   → ("États-Unis / Canada", "US", "🇺🇸")
    """
    if not telephone:
        return None
    
    # Nettoyer le numéro — garder uniquement les chiffres
    clean = telephone.strip()
    if clean.startswith("+"):
        clean = clean[1:]
    elif clean.startswith("00"):
        clean = clean[2:]
    else:
        return None  # Numéro local sans indicatif
    
    clean = "".join(c for c in clean if c.isdigit())
    
    # Chercher l'indicatif du plus long au plus court
    for key in _SORTED_KEYS:
        if clean.startswith(key):
            return INDICATIFS[key]
    
    return None


def get_pays_from_tel(telephone: str) -> str:
    """Retourne juste le nom du pays, ou chaîne vide si non trouvé."""
    result = detect_pays(telephone)
    return result[0] if result else ""


def get_drapeau_from_tel(telephone: str) -> str:
    """Retourne le drapeau emoji, ou chaîne vide si non trouvé."""
    result = detect_pays(telephone)
    return result[2] if result else ""
