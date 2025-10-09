#!/usr/bin/env python3
import os, time, threading, json
from urllib.parse import quote_plus
from http.server import SimpleHTTPRequestHandler
from socketserver import TCPServer
import requests, re

XT_HOST = os.getenv("XTREAM_HOST","").strip()
XT_USER = os.getenv("XTREAM_USER","").strip()
XT_PASS = os.getenv("XTREAM_PASS","").strip()
FILTER  = os.getenv("FILTER_KEYWORDS","").strip()
REFRESH = int(os.getenv("REFRESH_SECS","21600"))
HTTP_PROXY = os.getenv("HTTP_PROXY","").strip() or None
PORT = int(os.getenv("PORT","35000"))

OUT_PLAYLIST_DIR = "/data/playlist"
OUT_XMLTV_DIR    = "/data/xmltv"
PLAYFILE = os.path.join(OUT_PLAYLIST_DIR,"playlist.m3u")
XMLFILE  = os.path.join(OUT_XMLTV_DIR,"guide.xml")

HEADERS = {
    "Accept": "*/*",
    "User-Agent": "ipTV/193 CFNetwork/1410.4 Darwin/22.6.0",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Host": XT_HOST,
}
PROXIES = {"http": HTTP_PROXY, "https": HTTP_PROXY} if HTTP_PROXY else None

def log(*a): print(time.strftime("[%Y-%m-%d %H:%M:%S]"), *a, flush=True)
def ensure_dirs(): os.makedirs(OUT_PLAYLIST_DIR, exist_ok=True); os.makedirs(OUT_XMLTV_DIR, exist_ok=True)

def fetch_json():
    url = f"http://{XT_HOST}/player_api.php"
    params = {"username": XT_USER, "password": XT_PASS, "action":"get_live_streams"}
    r = requests.get(url, headers=HEADERS, params=params, proxies=PROXIES, timeout=45)
    r.raise_for_status()
    try: return r.json()
    except: return json.loads(r.text)
    
def normalize(items):
    import re
    out = []

    # TVG_MAP COMPLET basé sur ton EPG réel (FR/BE/US)
    TVG_MAP = {
        # ========== FRANCE (principales) ==========
        "tf1": "TF1.fr",
        "france2": "France2.fr",
        "france3": "France3.fr", 
        "france4": "France4.fr",
        "france5": "France5.fr",
        "m6": "M6.fr",
        "arte": "ARTE.fr",
        "tmc": "TMC.fr",
        "w9": "W9.fr",
        "tfx": "TFX.fr",
        "cstar": "CStar.fr",
        "6ter": "6ter.fr",
        
        # News FR
        "lci": "LCI.fr",
        "bfmtv": "BFMTV.fr",
        "bfm": "BFMTV.fr",
        "cnews": "CNews.fr",
        "franceinfo": "Franceinfo.fr",
        "france24": "France24.fr",
        "euronews": "Euronews.fr",
        "i24news": "i24News.fr",
        "bfmbusiness": "BFMBusiness.fr",
        "rmcstory": "RMCStory.fr",
        "lachainemeteo": "LaChaineMeteo.fr",
        
        # Canal+ FR
        "canalplus": "CANALplus.fr",
        "canalpluscinema": "CanalPlusCinema.fr",
        "canalpluseries": "CanalplusSeries.fr",
        "canalplusport": "CanalPlusSport.fr",
        "canalplusdocs": "CanalPlusDocs.fr",
        "canalplusgrandecran": "CanalPlusGrandEcran.fr",
        "canalplusfoot": "CanalPlusFoot.fr",
        "canalpluslive1": "CanalPlusLive1.fr",
        "canalpluslive2": "CanalPlusLive2.fr",
        "canalpluslive3": "CanalPlusLive3.fr",
        
        # Cinéma FR
        "ocs": "OCS.fr",
        "tf1seriesfilms": "TF1SeriesFilms.fr",
        "cineplus": "CinePlusFrisson.fr",
        "cineplusfrisson": "CinePlusFrisson.fr",
        "cineplusfamily": "CinePlusFamily.fr",
        "cineplusclassic": "CinePlusClassic.fr",
        "cineplusemotion": "CinePlusEmotion.fr",
        "cineplusfestival": "CinePlusFestival.fr",
        "comediaplus": "ComediePlus.fr",
        "13rue": "13Rue.fr",
        "syfy": "Syfy.fr",
        "tcm": "TCM.fr",
        "action": "Action.fr",
        "paramountchannel": "ParamountChannel.fr",
        "warnertv": "Warnertv.fr",
        "serieclub": "SerieClub.fr",
        "polarplus": "PolarPlus.fr",
        "crimedistrict": "CrimeDistrict.fr",
        
        # Découverte FR
        "rmcdecouverte": "RMCdecouverte.fr",
        "ushuaiatv": "UshuaiaTV.fr",
        "nationalgeographic": "NationalGeographic.fr",
        "natgeo": "NationalGeographic.fr",
        "natgeowild": "NatGeoWildHD.fr",
        "discoverychannel": "DiscoveryChannel.fr",
        "discoveryinvestigation": "DiscoveryInvestigation.fr",
        "tlc": "TLC.fr",
        "histoire": "Histoire.fr",
        "toutehistoire": "TouteHistoire.fr",
        "science": "ScienceEtVie.fr",
        "scienceetvie": "ScienceEtVie.fr",
        "animaux": "Animaux.fr",
        "planeteplus": "PlanetePlus.fr",
        "planeteplusaventure": "PlanetePlusAventure.fr",
        "planetepluscrime": "PlanetePlusCrime.fr",
        "planetejustice": "PLANETEJustice.fr",
        "seasons": "Seasons.fr",
        "trek": "Trek.fr",
        "chassepeche": "ChassePeche.fr",
        "nauticalchannel": "NauticalChannel.fr",
        
        # Enfants FR
        "gulli": "Gulli.fr",
        "nickelodeon": "Nickelodeon.fr",
        "nickjr": "NickJr.fr",
        "disneychannel": "DisneyChannel.fr",
        "disneyjunior": "DisneyJunior.fr",
        "cartoonnetwork": "CartoonNetwork.fr",
        "boomerang": "Boomerang.fr",
        "tiji": "Tiji.fr",
        "piwi": "PIWI.fr",
        "canalj": "CanalJ.fr",
        "teletoon": "TeleTOON.fr",
        "cartoonito": "Cartoonito.fr",
        "babytv": "BabyTV.fr",
        "pitchoun": "Pitchoun.fr",
        
        # Sport FR
        "eurosport1": "Eurosport1.fr",
        "eurosport2": "Eurosport2.fr",
        "lequipe": "Lequipe.fr",
        "rmcsport1": "RMCSport1.fr",
        "beinsports1": "beinSports1.fr",
        "beinsports2": "beinSports2.fr",
        "beinsports3": "beinSports3.fr",
        "bein4max": "Bein4Max.fr",
        "bein5max": "Bein5Max.fr",
        "golfplus": "GolfPlus.fr",
        "automoto": "Automoto.fr",
        "equidialive": "EquidiaLive.fr",
        "infosportplus": "InfoSportPlus.fr",
        "sportenfrance": "SportEnFrance.fr",
        
        # Musique FR
        "mtv": "MTV.fr",
        "mtvhits": "MTVHits.fr",
        "mtvclassics": "MTVCLASSICS.fr",
        "mcm": "MCM.fr",
        "m6music": "M6Music.fr",
        "nrjhits": "NRJHits.fr",
        "melody": "Melody.fr",
        "mezzo": "Mezzo.fr",
        "mezzolive": "MezzoLive.fr",
        
        # Divers FR
        "gameone": "GameOne.fr",
        "mangas": "Mangas.fr",
        "rtl9": "RTL9.fr",
        "cherie25": "Cherie25.fr",
        "tv5monde": "TV5Monde.fr",
        "kto": "KTO.fr",
        "publicsenat": "PublicSenat.fr",
        "lcp": "LCP100.fr",
        "parisremiere": "ParisPremiere.fr",
        "tvbreizh": "TVBreizh.fr",
        "teva": "Teva.fr",
        "ab1": "AB1.fr",
        "jone": "JOne.fr",
        
        # ========== BELGIQUE ==========
        # RTBF
        "laune": "LaUne.be",
        "rtbf": "LaUne.be",
        "tipik": "Tipik.be",
        "latrois": "LaTrois.be",
        "rtbflaune": "LaUne.be",
        "rtbftipik": "Tipik.be",
        "rtbflaterois": "LaTrois.be",
        
        # RTL Belgique
        "rtltvi": "RTLTVI.be",
        "rtl": "RTLTVI.be",
        "clubrtl": "ClubRTL.be",
        "plugrtl": "PlugRTL.be",
        
        # VRT
        "vrt1": "VRT1.be",
        "een": "VRT1.be",
        "canvas": "Canvas.be",
        "ketnet": "Ketnet.be",
        
        # VTM
        "vtm": "Vtm.be",
        "vtm2": "VTM2.be",
        "vtm3": "VTM3.be",
        "vtm4": "VTM4.be",
        "vtmgold": "VTMGold.be",
        "vtmkids": "vtmKIDS.be",
        
        # Play/DPG Media
        "play4": "Play4.be",
        "play5": "Play5.be",
        "play6": "Play6.be",
        "play7": "Play7.be",
        "playsports1": "PlaySportsHD1.be",
        "playsports2": "PlaySportsHD2.be",
        "playsports3": "PlaySportsHD3.be",
        "playsports4": "PlaySportsHD4.be",
        "playsports5": "PlaySportsHD5.be",
        "playsportsgolf": "PlaySportsGolf.be",
        "playcrime": "PlayCrime.be",
        
        # Eleven Sports BE
        "elevensports1": "ElevenSports1F.be",
        "elevensports2": "ElevenSports2F.be",
        "elevensports3": "ElevenSports3F.be",
        "elevenproleague1": "ElevenProLeague1FR.be",
        "elevenproleague2": "ElevenProLeague2FR.be",
        "elevenproleague3": "ElevenProLeague3FR.be",
        
        # Autres BE
        "ab3": "AB3.be",
        "abxplore": "ABXplore.be",
        "ln24": "LN24.be",
        "bx1": "BX1.be",
        "antennecentre": "AntenneCentre.be",
        "canalc": "CanalC.be",
        "canalzoom": "CanalZoom.be",
        "matele": "MaTele.be",
        "notele": "NoTele.be",
        "rtcliege": "RTCLiege.be",
        "telemonborinage": "TeleMonsBorinage.be",
        "telesambre": "Telesambre.be",
        "televesdre": "Televesdre.be",
        "tvcom": "TVCom.be",
        "tvlux": "TVLux.be",
        "njam": "Njam.be",
        "comedycentral": "ComedyCentral.be",
        
        # ========== USA ==========
        # Sport USA
        "espn": "ESPN.us",
        "espn2": "ESPN2.us",
        "espnnews": "ESPNNews.us",
        "espnu": "ESPNU.us",
        "foxsports1": "FoxSports1.us",
        "fs1": "FoxSports1.us",
        "foxsports2": "FoxSports2.us",
        "fs2": "FoxSports2.us",
        "nflnetwork": "NFLNetwork.us",
        "nflredzone": "NFLRedZone.us",
        "nhlnetwork": "NHLNetwork.us",
        "nbatv": "NBATV.us",
        "mlbnetwork": "MLBNetwork.us",
        "golfchannel": "GolfChannel.us",
        "tennischannel": "TennisChannel.us",
        "cbssportsnetwork": "CBSSportsNetwork.us",
        "nbcsportsnetwork": "NBCSportsNetwork.us",
        "bigtennetwork": "BigTenNetwork.us",
        "secnetwork": "SECNetwork.us",
        "beinsports": "beINSports.us",
        "beinsportslaliga": "beINSportsLaLiga.us",
        "beinsportsenespanol": "beINSportsEnEspanol.us",
        "foxdeportes": "FoxDeportes.us",
        "espndeportes": "ESPNDeportes.us",
        "yesnetwork": "YESNetwork.us",
        "spectrumsportsnet": "SpectrumSportsNet.us",
        "stadium": "Stadium.us",
        
        # Réseaux régionaux USA
        "nbcsportschicago": "NBCSportsChicago.us",
        "nbcsportsbayarea": "NBCSportsBayArea.us",
        "nbcsportsphiladelphia": "NBCSportsPhiladelphia.us",
        "nbcsportswashington": "NBCSNWashington.us",
        "foxsportsdetroit": "FoxSportsDetroit.us",
        "foxsportsmidwest": "FoxSportsMidwest.us",
        "foxsportsnorth": "FoxSportsNorth.us",
        "foxsportssun": "FoxSportsSun.us",
        
        # News/Business USA
        "cnbc": "CNBC.us",
        "cnninternational": "CNNInternational.us",
        "cnn": "CNNInternational.us",
        
        # Autres USA
        "nasa": "NASA.Television.(NASA).us",
        "wwe": "WWE.us",
        "ufc": "UFCTV.us",
        "qvc": "QVC.us",
        "hsn": "HomeShoppingNetwork.us",
        "mtv": "MTVLive.us",
        "mtvlive": "MTVLive.us",
        "univision": "Univision.us",
        "galavision": "Galavision.us",
        "telemundo": "TelemundoWKAQ.us",
        "unimas": "UniMas.us",
        "motortrend": "MotorTrend.us",
        "outdoorchannel": "OutdoorChannel.us",
        "weathernation": "WeatherNation.us",
    }

    def slug(s: str) -> str:
        s = s.lower()
        s = re.sub(r'^\|[a-z]{2}\|\s*', '', s)  # enlever |FR|, |BE|, etc.
        s = re.sub(r'\b(4k|uhd|fhd|hd|sd)\b', '', s)
        s = re.sub(r'[^a-z0-9]+', '', s)
        return s

    for c in (items if isinstance(items, list) else []):
        name_raw = c.get("name") or c.get("stream_name") or c.get("title") or f'ch_{c.get("stream_id")}'
        sid = c.get("stream_id") or c.get("channel_id") or c.get("num")
        url = c.get("url") or (f"http://{XT_HOST}/live/{quote_plus(XT_USER)}/{quote_plus(XT_PASS)}/{sid}.ts" if sid else "")
        group = (c.get("category_name") or c.get("category") or "").strip()
        logo = c.get("stream_icon") or c.get("icon") or ""
        tvgid = (c.get("tvg_id") or "").strip()

        # Nettoyage nom
        name = re.sub(r'^\|[A-Z]{2}\|\s*', '', name_raw)
        name = re.sub(r'\b(4K|UHD|FHD|HD|SD)\b', '', name, flags=re.IGNORECASE)
        name = re.sub(r'\s{2,}', ' ', name).strip()

        # Group par défaut
        if not group:
            if re.search(r'(RTBF|RTL|VTM|Een|Canvas|Play\d|LaUne|Tipik|Ketnet)', name, re.I):
                group = "Belgique"
            elif re.search(r'(TF1|France|M6|Arte|TMC|W9|TFX|BFM|LCI|Canal)', name, re.I):
                group = "France"
            elif re.search(r'(ESPN|CNN|NBC|CBS|ABC|FOX|NFL|NBA|MLB|WWE|CNBC)', name, re.I):
                group = "USA"
            else:
                group = "Divers"

        # tvg-id mapping
        if not tvgid:
            key = slug(name)
            if key in TVG_MAP:
                tvgid = TVG_MAP[key]
            else:
                # Fallback avec suffix pays
                if group.lower() == "france":
                    suffix = ".fr"
                elif group.lower() == "belgique":
                    suffix = ".be"
                elif group.lower() == "usa":
                    suffix = ".us"
                else:
                    suffix = ""
                tvgid = key + suffix

        out.append({
            "name": name,
            "url": url,
            "group": group,
            "logo": logo,
            "tvgid": tvgid
        })
    return out

def filter_channels(chs):
    if not FILTER: return chs
    kws = [k.strip().lower() for k in FILTER.split(",") if k.strip()]
    if not kws: return chs
    out=[]
    for c in chs:
        hay = (c["name"]+" "+c["group"]).lower()
        if any(k in hay for k in kws): out.append(c)
    return out

def write_m3u(chs):
    tmp=PLAYFILE+".tmp"
    with open(tmp,"w",encoding="utf-8") as f:
        f.write("#EXTM3U\n")
        for c in chs:
            f.write(f'#EXTINF:-1 tvg-id="{c["tvgid"]}" tvg-name="{c["name"]}" tvg-logo="{c["logo"]}" group-title="{c["group"]}",{c["name"]}\n')
            f.write(c["url"]+"\n")
    os.replace(tmp, PLAYFILE)
    log(f"M3U written: {PLAYFILE} (channels: {len(chs)})")

def write_xmltv():
    """Récupère l'EPG avec headers browser-like et gestion des redirections"""
    if not XT_HOST or not XT_USER or not XT_PASS:
        log("XMLTV ERROR: Missing host/user/pass")
        return
        
    url = f"http://{XT_HOST}/xmltv.php?username={XT_USER}&password={XT_PASS}"
    
    # Headers browser-like pour éviter les redirections cassées
    browser_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'fr-FR,fr;q=0.9,en;q=0.8',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache'
    }
    
    try:
        log(f"Fetching XMLTV from: {url}")
        
        # Session pour maintenir les cookies et headers
        session = requests.Session()
        session.headers.update(browser_headers)
        session.proxies = PROXIES
        
        # ÉTAPE 1: Tester sans suivre les redirections d'abord
        r = session.get(url, allow_redirects=False, timeout=30)
        
        if r.status_code == 302:
            redirect_url = r.headers.get('Location')
            log(f"Redirect detected: {redirect_url}")
            
            # Si redirection vers logip.firstcloud.me (cassée), forcer l'originale
            if redirect_url and 'logip.firstcloud.me' in redirect_url:
                log("Avoiding broken redirect, fetching original URL with browser headers")
                r = session.get(url, allow_redirects=True, timeout=180)
            else:
                # Suivre la redirection valide
                r = session.get(redirect_url, timeout=180)
        elif r.status_code == 200:
            # Pas de redirection, contenu direct
            pass
        else:
            # Autre code, essayer de suivre les redirections normalement
            r = session.get(url, allow_redirects=True, timeout=180)
        
        log(f"XMLTV Final URL: {r.url}")
        log(f"XMLTV Response: {r.status_code}")
        
        if r.status_code != 200:
            log(f"XMLTV Error: HTTP {r.status_code}")
            return try_fallback_epg()
            
        content = r.content
        log(f"XMLTV Content length: {len(content)} bytes")
        
        # Vérifications de validité
        if b'<html>' in content[:1000] or b'404 Not Found' in content:
            log("XMLTV ERROR: Got HTML error page")
            return try_fallback_epg()
            
        if not content.strip().startswith(b'<?xml'):
            log("XMLTV ERROR: Not valid XML")
            return try_fallback_epg()
        
        if len(content) < 1000:
            log("XMLTV ERROR: File too small")
            return try_fallback_epg()
        
        # Sauvegarder
        tmp = XMLFILE + ".tmp"
        with open(tmp, "wb") as f:
            f.write(content)
        os.replace(tmp, XMLFILE)
        log(f"XMLTV written: {XMLFILE} ({len(content)} bytes)")
        
    except Exception as e:
        log(f"XMLTV error: {e}")
        try_fallback_epg()

def try_fallback_epg():
    """EPG de secours si le principal échoue"""
    log("Trying fallback EPG sources...")
    
    fallback_urls = [
        # Essayer d'autres URLs du même fournisseur
        f"http://{XT_HOST}/epg.php?username={XT_USER}&password={XT_PASS}",
        f"http://{XT_HOST}/guide.php?username={XT_USER}&password={XT_PASS}",
        # EPG générique minimal
        "https://raw.githubusercontent.com/matthuisman/i.mjh.nz/master/PlutoTV/all.xml",
    ]
    
    for fallback_url in fallback_urls:
        try:
            log(f"Trying fallback: {fallback_url}")
            r = requests.get(fallback_url, timeout=60)
            if r.status_code == 200 and len(r.content) > 1000:
                tmp = XMLFILE + ".tmp"
                with open(tmp, "wb") as f:
                    f.write(r.content)
                os.replace(tmp, XMLFILE)
                log(f"Fallback EPG written: {XMLFILE}")
                return
        except Exception as e:
            log(f"Fallback failed {fallback_url}: {e}")
            continue
    
    # Dernier recours : EPG minimal
    create_minimal_epg()

def create_minimal_epg():
    """Crée un EPG minimal pour éviter les erreurs"""
    log("Creating minimal EPG...")
    minimal_xml = '''<?xml version="1.0" encoding="UTF-8"?>
<tv generator-info-name="xtream-minimal">
  <channel id="TF1.fr">
    <display-name>TF1</display-name>
  </channel>
  <channel id="France2.fr">
    <display-name>France 2</display-name>
  </channel>
  <channel id="M6.fr">
    <display-name>M6</display-name>
  </channel>
  <programme channel="TF1.fr" start="20251008000000 +0200" stop="20251009000000 +0200">
    <title>Programme TF1</title>
  </programme>
  <programme channel="France2.fr" start="20251008000000 +0200" stop="20251009000000 +0200">
    <title>Programme France 2</title>
  </programme>
  <programme channel="M6.fr" start="20251008000000 +0200" stop="20251009000000 +0200">
    <title>Programme M6</title>
  </programme>
</tv>'''
    
    try:
        with open(XMLFILE, "w", encoding="utf-8") as f:
            f.write(minimal_xml)
        log(f"Minimal EPG created: {XMLFILE}")
    except Exception as e:
        log(f"Failed to create minimal EPG: {e}")
        
def update_loop():
    ensure_dirs()
    while True:
        try:
            items = fetch_json()
            chs = normalize(items)
            chs = filter_channels(chs)
            if len(chs) > 480:  # garde une marge sous la limite Plex
                chs = chs[:480]
            write_m3u(chs)
        except Exception as e:
            log("M3U error:", e)
        try:
            write_xmltv()
        except Exception as e:
            log("XMLTV error:", e)
        log(f"Sleeping {REFRESH}s")
        time.sleep(REFRESH)

class DualDir(SimpleHTTPRequestHandler):
    def translate_path(self, path):
        """Gère les chemins /xmltv/ et / pour servir les bons répertoires"""
        import os
        import urllib.parse
        
        # Décoder l'URL
        path = urllib.parse.unquote(path)
        
        if path.startswith("/xmltv/"):
            # Enlever /xmltv/ du chemin
            rel_path = path[7:]  # enlever "/xmltv/"
            if not rel_path:
                rel_path = "guide.xml"  # fichier par défaut
            target = os.path.join(OUT_XMLTV_DIR, rel_path)
            return target
        else:
            # Servir depuis playlist dir
            rel_path = path.lstrip("/")
            if not rel_path:
                rel_path = "playlist.m3u"  # fichier par défaut
            target = os.path.join(OUT_PLAYLIST_DIR, rel_path)
            return target
    
    def guess_type(self, path):
        """Force le bon Content-Type pour XML"""
        if path.endswith('.xml'):
            return 'application/xml'
        elif path.endswith('.m3u'):
            return 'audio/x-mpegurl'
        return super().guess_type(path)
    
    def end_headers(self):
        """Ajouter des headers CORS si nécessaire"""
        self.send_header('Access-Control-Allow-Origin', '*')
        super().end_headers()

def serve():
    with TCPServer(("", PORT), DualDir) as httpd:
        log(f"HTTP listening on 0.0.0.0:{PORT} (playlist & xmltv)")
        httpd.serve_forever()

if __name__=="__main__":
    threading.Thread(target=serve, daemon=True).start()
    update_loop()
