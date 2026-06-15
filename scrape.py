#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scrape.py - pengumpul berita Jambi untuk GitHub Actions (jalan harian otomatis).
TANPA IndoBERT/GPU. Hasil disimpan & ditambahkan ke data.csv (akumulatif, dedup URL).
Klasifikasi sentimen dilakukan terpisah di Colab.
"""
import csv, re, os, sys
from datetime import datetime

PORTAL_200 = [
    "https://adanu.co.id/",
    "https://aksara24.id/",
    "https://aksatanews.com/",
    "https://aksesjambi.com/",
    "https://ampar.id/",
    "https://amuranews.id/",
    "https://angsoduo.net/",
    "https://awasi.id/",
    "https://azramantap.id/",
    "https://arcomnews.com/",
    "https://bacahukum.com/",
    "https://bacajambi.id/",
    "https://bekato.id/",
    "https://beritaumum.com/",
    "https://beroyatnews.com/",
    "https://betara.id/",
    "https://bicarajambi.com/",
    "https://bidikindonesianews.co.id/",
    "https://bidikkasusnews.com/",
    "https://bitnews.id/",
    "https://bmcnews.id/",
    "https://brito.id/",
    "https://cahayajambi.com/",
    "https://cekidotnews.id/",
    "https://cerdasi.id/",
    "https://channelberita24.com/",
    "https://cicitvjambi.com/",
    "https://datajambi.com/",
    "https://denyutjambi.com/",
    "https://derapjambi.com/",
    "https://detail.id/",
    "https://detikkasus.com/",
    "https://dialektikajambi.com/",
    "https://dinamikajambi.com/",
    "https://diwapost.com/",
    "https://djambi.id/",
    "https://dobrak.id/",
    "https://duasatu.net/",
    "https://eksisjambi.com/",
    "https://enewstime.id/",
    "https://esamesta.com/",
    "https://existjambinews.com/",
    "https://exposse.com/",
    "https://fajarharapan.id/",
    "https://fakta.co/",
    "https://ganyang.me/",
    "https://geloranusantara.id/",
    "https://gemilangpos.com/",
    "https://gentalajambi.com/",
    "https://gerak12.com/",
    "https://gesturkata.com/",
    "https://gojambi.com/",
    "https://haloindonesianews.com/",
    "https://halojambi.id/",
    "https://harus.id/",
    "https://hitamputih.id/",
    "https://iajnews.com/",
    "https://icwpost.id/",
    "https://imcnews.id/",
    "https://indepthnews.id/",
    "https://indonesiadaily.co.id/",
    "https://indonesiasatu.co.id/",
    "https://infokabarjambi.com/",
    "https://inilahjambi.com/",
    "https://inspirasijambi.com/",
    "https://jabungtoday.com/",
    "https://jamberita.com/",
    "https://jambi.antaranews.com/",
    "https://jambicenter.id/",
    "https://jambiekspose.com/",
    "https://jambiekspres.disway.id/",
    "https://jambiflash.com/",
    "https://jambiin.com/",
    "https://jambi-independent.co.id/",
    "https://jambikito.com/",
    "https://jambiklik.id/",
    "https://jambilife.com/",
    "https://jambiline.com/",
    "https://jambilink.com/",
    "https://jambioke.com/",
    "https://jambione.com/",
    "https://jambipanas.com/",
    "https://jambipers.com/",
    "https://jambipos.com/",
    "https://jambipost-online.com/",
    "https://jambipride.id/",
    "https://jambiraya.id/",
    "https://jambisatu.id/",
    "https://jambiseru.com/",
    "https://jambishare.com/",
    "https://jambi-time.com/",
    "https://jambiupdate.co/",
    "https://jambiwin.com/",
    "https://jaripers.id/",
    "https://jatinews.co/",
    "https://jeka24.com/",
    "https://jendelanews.com/",
    "https://jernih.id/",
    "https://jurnaljambi.com/",
    "https://jurnalone.com/",
    "https://kabargentala.id/",
    "https://kabarjambi.com/",
    "https://kabarjambikito.id/",
    "https://kabarnegeri.net/",
    "https://kaki5.id/",
    "https://katigo.id/",
    "https://katoe.id/",
    "https://kenali.co.id/",
    "https://kerincidaily.com/",
    "https://kharismamedia.id/",
    "https://kilasharian.com/",
    "https://kopasjambi.com/",
    "https://koranjambi.com/",
    "https://koranpelita.co/",
    "https://koranprogresif.id/",
    "https://korantekad.id/",
    "https://kuntala.id/",
    "https://lajuberita.id/",
    "https://lamanjambi.com/",
    "https://lamanesia.com/",
    "https://lampukuning.id/",
    "https://lidikjambi.net/",
    "https://lintas.co.id/",
    "https://makalamnews.id/",
    "https://mediajambi.com/",
    "https://medialintassumatera.net/",
    "https://mediarotasi.com/",
    "https://mediatornews.com/",
    "https://memoritoday.com/",
    "https://metrojambi.com/",
    "https://nasionalxpos.co.id/",
    "https://nccmedia.id/",
    "https://newsdigital.id/",
    "https://newsinfo.id/",
    "https://newspublik.press/",
    "https://niagaindo.id/",
    "https://nuansajambi.com/",
    "https://oerban.com/",
    "https://onlinejambi.com/",
    "https://optimalnews.id/",
    "https://orasi.id/",
    "https://orbid.co.id/",
    "https://otodanews.com/",
    "https://paalmerah.com/",
    "https://pantauindonesia.com/",
    "https://pariwarajambi.com/",
    "https://pemayung.id/",
    "https://perisainews.co/",
    "https://peristiwasekitarjambi.com/",
    "https://pesisirtimur.com/",
    "https://petajambi.com/",
    "https://pilardaerah.com/",
    "https://pilarjambi.com/",
    "https://portalbuananew.com/",
    "https://portalone.net/",
    "https://porwebindo.com/",
    "https://potretjambi.com/",
    "https://prestasireformasi.com/",
    "https://promedia.com/",
    "https://pseko.id/",
    "https://radarjambi.co.id/",
    "https://radarnesia.com/",
    "https://ragamnarasi.id/",
    "https://rakjat.com/",
    "https://ramnews.id/",
    "https://ranahjambi.com/",
    "https://rangkumnews.com/",
    "https://realitajambi.com/",
    "https://respectjambi.com/",
    "https://ruangjambi.com/",
    "https://ruangpedia.id/",
    "https://rubrikjambi.com/",
    "https://sainsjambi.com/",
    "https://salimbai.id/",
    "https://sangkakalanews.com/",
    "https://searah.net/",
    "https://sekato.id/",
    "https://selayangnews.id/",
    "https://senjari.id/",
    "https://serambijambi.id/",
    "https://serasah.co.id/",
    "https://sidakpost.id/",
    "https://siginjai99.com/",
    "https://sinarjambi.com/",
    "https://sinarpagibaru.com/",
    "https://sitimang.id/",
    "https://sr28jambinews.com/",
    "https://suarabernas.com/",
    "https://suarabutesarko.com/",
    "https://suarajambi.com/",
    "https://sudutjambi.com/",
    "https://sumateradaily.com/",
    "https://sungkai.id/",
    "https://swarajambi.net/",
    "https://tanyafakta.id/",
    "https://teranew.id/",
    "https://teropongbarat.com/",
    "https://thehok.id/",
    "https://thejambitimes.com/",
    "https://tingkap.co/",
    "https://titikjambi.com/",
    "https://topikjambi.com/",
    "https://transjambinews.net/",
    "https://tropongjambi.com/",
    "https://tuntasnews.com/",
    "https://tuntasonline.id/",
    "https://jambi.tribunnews.com/",
    "https://unggahnews.com/",
    "https://updateku.com/",
    "https://vojnews.id/",
    "https://wartanews.co/",
    "https://zabak.id/",
    "https://zonabrita.com/",
]

ARTICLE_PATTERN = "auto"
MAX_BARU = 80          # batas artikel baru per hari (sopan + cepat)
DATA_FILE = "data.csv"

RELEVAN = re.compile(r"\b(pemprov|pemerintah|gubernur|dinas|opd|dprd|pelayanan|layanan|publik|"
    r"jalan|jembatan|infrastruktur|drainase|banjir|rsud|rumah sakit|puskesmas|kesehatan|pasien|"
    r"sekolah|pendidikan|guru|sma|smk|izin|perizinan|anggaran|apbd|pungli|korupsi|proyek|"
    r"air bersih|pdam|sampah|lingkungan|keluhan|mengeluh|dikeluhkan|disorot|protes|aspirasi|pengaduan)\b", re.I)
NOISE = re.compile(r"\b(lirik|lagu|chord|zodiak|resep|open bo|video syur|gisel|artis|"
    r"harga (hp|motor|mobil|emas)|vario|nmax|promo|nonton|streaming|drakor|prediksi skor|klasemen|liga)\b", re.I)

def harvest_links(listing_urls, must_contain="/berita/", limit=None):
    """Panen URL artikel dari halaman daftar (pencarian / kategori / homepage).
    must_contain="/berita/" (Antara) untuk pola pasti, ATAU "auto" untuk
    deteksi otomatis lintas-portal (heuristik slug/angka). Ganti per portal."""
    import requests, re as _re
    from urllib.parse import urljoin, urlparse
    H = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                        "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"),
         "Accept-Language": "id-ID,id;q=0.9,en;q=0.8", "Accept-Encoding": "gzip, deflate"}
    _SKIP = ("/tag/", "/tags/", "/kategori", "/category", "/author", "/penulis",
             "/page/", "/search", "/cari", "/wp-", "/feed", "/about", "/kontak",
             "/index", "/privacy", "/redaksi", "/pedoman", "javascript:", "mailto:")
    def is_article(url, host):
        p = urlparse(url)
        if p.netloc and host not in p.netloc: return False         # situs sama
        path = p.path.lower()
        if any(s in path for s in _SKIP): return False
        if path in ("", "/"): return False
        if _re.search(r'\.(jpg|jpeg|png|gif|pdf|mp4|css|js)$', path): return False
        slug = path.rstrip("/").split("/")[-1]
        return slug.count("-") >= 2 or bool(_re.search(r'\d{4,}', path))  # slug/id artikel
    seen, found = set(), []
    for lu in listing_urls:
        try:
            r = requests.get(lu, headers=H, timeout=25)
            if r.status_code != 200:
                print(f"  [daftar {r.status_code}] {lu}"); continue
            html = r.text
        except Exception as e:
            print(f"  [daftar-error] {lu}: {e}"); continue
        host = urlparse(lu).netloc
        base = f"{urlparse(lu).scheme}://{host}"
        n0 = len(found)
        for href in _re.findall(r'href=["\']([^"\']+)["\']', html):
            url = urljoin(base, href).split("#")[0].split("?")[0]
            if url in seen or url.rstrip("/") == lu.rstrip("/"): continue
            ok = is_article(url, host) if must_contain == "auto" else (must_contain in url)
            if ok:
                seen.add(url); found.append(url)
        print(f"  {lu} -> +{len(found)-n0} (total {len(found)})")
    return found[:limit] if limit else found

def scrape(urls):
    import trafilatura, requests
    # Samar sebagai browser -> atasi 403 (anti-bot). Encoding gzip/deflate -> hindari ZSTD error.
    HEADERS = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                       "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "id-ID,id;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate",
    }
    arts = []
    for u in urls:
        html = None
        try:
            r = requests.get(u, headers=HEADERS, timeout=25)
            if r.status_code == 200:
                html = r.text
            else:
                print(f"  [{r.status_code}] {u}")
        except Exception as e:
            print(f"  [req-error] {u}: {e}")
        if not html:                                   # fallback ke fetcher bawaan
            html = trafilatura.fetch_url(u)
        if not html:
            print(f"  [gagal] {u}"); continue
        data = trafilatura.extract(html, output_format="json", with_metadata=True)
        if not data:
            print(f"  [tanpa-isi] {u}"); continue
        d = json.loads(data)
        arts.append({
            "source_url": u,                       # PROVENANCE (wajib, auditability)
            "title": d.get("title", ""),
            "date": d.get("date", ""),
            "text": d.get("text", ""),
        })
    return arts

def pseudonymize(text):
    text = re.sub(r'\b(0|\+62)[\d\-\s]{8,13}\b', '[NOMOR]', text)            # HP
    text = re.sub(r'\b\d{16}\b', '[NIK]', text)                              # NIK
    text = re.sub(r'\b(Bapak|Ibu|Pak|Bu|Sdr|Saudara)\s+[A-Z][a-z]+(\s[A-Z][a-z]+)?',
                  r'\1 [NAMA]', text)
    return text

def extract_units_fallback(article_text, title=""):
    seen, units = set(), []
    tnorm = re.sub(r'\s+', ' ', title.lower()).strip()
    for s in re.split(r'(?<=[.!?])\s+', article_text):
        s = s.strip()
        if len(s.split()) < 6:                       # buang fragmen/judul pendek
            continue
        sn = re.sub(r'\s+', ' ', s.lower()).strip()
        if tnorm and (sn == tnorm or sn in tnorm or tnorm in sn):
            continue                                 # buang baris judul
        if not _WARGA_CUE.search(s):                 # harus ada penanda suara warga
            continue
        if _PEJABAT_CUE.search(s):                   # buang suara pejabat
            continue
        key = sn[:80]
        if key in seen:                              # dedup
            continue
        seen.add(key); units.append(s)
    return units

def gov_level(text):
    p, k = bool(_PROV_CUE.search(text)), bool(_KOTA_CUE.search(text))
    return "provinsi" if (p and not k) else "kota" if (k and not p) else "tak jelas"


def baca_url_lama():
    """URL yang sudah pernah diambil (dedup), dari data.csv."""
    seen = set()
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, encoding="utf-8") as f:
            for row in csv.DictReader(f):
                seen.add(row.get("source_url",""))
    return seen

def main():
    seen = baca_url_lama()
    print(f"URL lama: {len(seen)}")

    links = harvest_links(PORTAL_200, must_contain=ARTICLE_PATTERN)
    baru = [u for u in links if u not in seen][:MAX_BARU]
    print(f"Link ditemukan: {len(links)} | baru: {len(baru)}")
    if not baru:
        print("Tidak ada artikel baru. Selesai."); return

    arts = scrape(baru)
    tanggal = datetime.now().strftime("%Y-%m-%d")
    rows = []
    for art in arts:
        clean = pseudonymize(art["text"])
        for u in extract_units_fallback(clean, art.get("title","")):
            if RELEVAN.search(u) and not NOISE.search(u):
                rows.append({"unit": u, "level": gov_level(u),
                             "source_url": art["source_url"], "tanggal_ambil": tanggal})
    print(f"Unit relevan baru: {len(rows)}")
    if not rows:
        print("Tidak ada unit relevan. Selesai."); return

    baru_file = not os.path.exists(DATA_FILE)
    with open(DATA_FILE, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["unit","level","source_url","tanggal_ambil"])
        if baru_file: w.writeheader()
        w.writerows(rows)
    print(f"Ditambahkan {len(rows)} baris ke {DATA_FILE}")

if __name__ == "__main__":
    main()
