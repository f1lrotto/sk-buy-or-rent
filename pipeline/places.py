"""Region keys, the town list and the source names shared by the pipeline scripts."""
import re
import unicodedata

KRAJE = {
    "BA": ("SK010", "Bratislavský kraj"),
    "TT": ("SK021", "Trnavský kraj"),
    "TN": ("SK022", "Trenčiansky kraj"),
    "NR": ("SK023", "Nitriansky kraj"),
    "ZA": ("SK031", "Žilinský kraj"),
    "BB": ("SK032", "Banskobystrický kraj"),
    "PO": ("SK041", "Prešovský kraj"),
    "KE": ("SK042", "Košický kraj"),
}
KRAJ_BY_NUTS = {nuts: k for k, (nuts, _) in KRAJE.items()}

# Okres towns. Realitymap also has smaller towns; v1 lists okres towns plus the city
# districts of Bratislava and Košice, so every place has a known kraj and enough listings.
OKRES_TOWNS = """Bratislava,Košice,Bytča,Čadca,Dolný Kubín,Kysucké Nové Mesto,Liptovský Mikuláš,Martin,Námestovo,
Ružomberok,Turčianske Teplice,Tvrdošín,Žilina,Bardejov,Humenné,Kežmarok,Levoča,Medzilaborce,Poprad,Prešov,Sabinov,
Snina,Stará Ľubovňa,Stropkov,Svidník,Vranov nad Topľou,Dunajská Streda,Galanta,Hlohovec,Piešťany,Senica,Skalica,
Trnava,Banská Bystrica,Banská Štiavnica,Brezno,Detva,Krupina,Lučenec,Poltár,Revúca,Rimavská Sobota,Veľký Krtíš,
Žarnovica,Žiar nad Hronom,Zvolen,Bánovce nad Bebravou,Ilava,Myjava,Nové Mesto nad Váhom,Partizánske,
Považská Bystrica,Prievidza,Púchov,Trenčín,Komárno,Levice,Nitra,Nové Zámky,Šaľa,Topoľčany,Zlaté Moravce,Malacky,
Pezinok,Senec,Gelnica,Michalovce,Rožňava,Sobrance,Spišská Nová Ves,Trebišov"""
OKRES_TOWNS = [t.strip() for t in OKRES_TOWNS.split(",")]

# Realitná únia names for the eight kraj capitals in its monthly table.
RU_CAPITALS = {"bratislava": "Bratislava", "trnava": "Trnava", "trencin": "Trenčín", "nitra": "Nitra",
               "banska-bystrica": "B. Bystrica", "zilina": "Žilina", "presov": "Prešov", "kosice": "Košice"}
# Deloitte Rent Index city names.
DELOITTE_CITIES = {"bratislava": "Bratislava", "trnava": "Trnava", "trencin": "Trenčín", "nitra": "Nitra",
                   "banska-bystrica": "Banská Bystrica", "zilina": "Žilina", "poprad": "Poprad",
                   "presov": "Prešov", "kosice": "Košice"}


def slug(s):
    s = unicodedata.normalize("NFKD", s.strip().lower()).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")
