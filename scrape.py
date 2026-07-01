#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scrape.py - pengumpul berita Jambi untuk GitHub Actions (jalan harian otomatis).
TANPA IndoBERT/GPU. Hasil disimpan & ditambahkan ke data.csv (akumulatif).

DEDUP BERLAPIS (menggantikan dedup URL-saja yang lama):
  1. Dedup URL          - artikel dari URL yang sama tidak diambil ulang.
  2. Dedup EKSAK unit   - kalimat keluhan yang teksnya sama persis dibuang
                          (menangani sindikasi: 1 rilis disalin banyak portal).
  3. Dedup NEAR-DUP unit- kalimat keluhan yang MIRIP (Jaccard shingle >= AMBANG)
                          dibuang walau tak persis sama (edit kecil/judul beda).
  Cakupan: unit baru dicek terhadap SELURUH unit lama di data.csv DAN antar unit baru.

Klasifikasi sentimen & atribusi tupoksi tetap terpisah di Colab (SEL 3).
"""
import csv, re, os, sys, json, hashlib
from datetime import datetime

# ==== PARAMETER DEDUP (atur di sini) ====
# STRATEGI: dedup EKSAK adalah lapis UTAMA (menangkap sindikasi copy-paste persis,
#   yang paling umum di media lokal). Near-dup dibiarkan KETAT (ambang tinggi) agar
#   hanya menangkap yang nyaris identik total -- MENGHINDARI risiko salah-buang
#   keluhan berbeda yang kebetulan mirip. Jangan turunkan NEARDUP_AMBANG tanpa
#   menguji ulang, karena kalimat keluhan pendek rentan salah-buang.
NEARDUP_AMBANG = 0.85     # Jaccard >= ini dianggap near-duplicate (0..1). Sengaja TINGGI (aman).
SHINGLE_K      = 4        # ukuran shingle (jumlah kata per potongan) untuk Jaccard.
LSH_BANDS      = 8        # jumlah band MinHash-LSH (untuk mempercepat pencarian kandidat).
MINHASH_PERM   = 32       # jumlah permutasi MinHash (lebih banyak = lebih akurat, lebih lambat).

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
    "https://jambi.tribunnews.com/",
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
    r"air bersih|pdam|sampah|lingkungan|keluhan|mengeluh|dikeluhkan|disorot|protes|aspirasi|pengaduan|"
    r"bantuan sosial|bansos|subsidi|harga pangan|pasar|harga barang|inflasi|pupuk|nelayan|petani|"
    r"lampu jalan|penerangan|trotoar|kemacetan|parkir|birokrasi|administrasi|ktp|kk|disdukcapil|"
    r"layanan digital|antrean|pelayanan prima|kinerja|transparansi|akuntabilitas|tindak lanjut)\b", re.I)
NOISE = re.compile(r"\b(lirik|lagu|chord|zodiak|resep|open bo|video syur|gisel|artis|"
    r"harga (hp|motor|mobil|emas)|vario|nmax|promo|nonton|streaming|drakor|prediksi skor|klasemen|liga)\b", re.I)

# --- FILTER LOKASI: pastikan konten relevan Provinsi Jambi ---
_JAMBI = re.compile(r"\b(jambi|muaro ?jambi|batang ?hari|bungo|muara bungo|tebo|muara tebo|"
    r"sarolangun|merangin|bangko|kerinci|sungai penuh|tanjung jabung|tanjab|"
    r"kuala tungkal|muara sabak|sengeti|muara bulian|pemprov jambi|provinsi jambi|"
    r"gubernur jambi|al ?haris|abdullah sani|raden mattaher)\b", re.I)
_NONJAMBI = re.compile(r"\b(bengkulu|muko-?muko|mukomuko|kaur|seluma|rejang lebong|kepahiang|"
    r"lebong|argamakmur|curup|manjun?to|"
    r"palembang|sumatera selatan|sumsel|padang|sumatera barat|sumbar|"
    r"pekanbaru|riau|lampung|medan|sumatera utara|sumut|aceh|"
    r"bangka|belitung|babel)\b", re.I)

def is_jambi_article(text, url="", title=""):
    """True jika artikel relevan Jambi. Buang HANYA jika jelas daerah lain
    (ada penanda non-Jambi) DAN tidak ada penanda Jambi sama sekali."""
    blob = f"{url} {title} {text}".lower()
    ada_jambi = bool(_JAMBI.search(blob))
    ada_lain = bool(_NONJAMBI.search(blob))
    if ada_lain and not ada_jambi:
        return False
    return True

def harvest_links(listing_urls, must_contain="/berita/", limit=None):
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
        if p.netloc and host not in p.netloc: return False
        path = p.path.lower()
        if any(s in path for s in _SKIP): return False
        if path in ("", "/"): return False
        if _re.search(r'\.(jpg|jpeg|png|gif|pdf|mp4|css|js)$', path): return False
        slug = path.rstrip("/").split("/")[-1]
        return slug.count("-") >= 2 or bool(_re.search(r'\d{4,}', path))
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
        if not html:
            try:
                html = trafilatura.fetch_url(u)
            except Exception as e:
                print(f"  [fetch-error] {u}: {e}")
        if not html:
            print(f"  [gagal] {u}"); continue
        try:
            data = trafilatura.extract(html, output_format="json", with_metadata=True)
        except Exception as e:
            print(f"  [extract-error] {u}: {e}"); continue
        if not data:
            print(f"  [tanpa-isi] {u}"); continue
        d = json.loads(data)
        arts.append({
            "source_url": u,
            "title": d.get("title", ""),
            "date": d.get("date", ""),
            "text": d.get("text", ""),
        })
    return arts

def pseudonymize(text):
    text = re.sub(r'\b(0|\+62)[\d\-\s]{8,13}\b', '[NOMOR]', text)
    text = re.sub(r'\b\d{16}\b', '[NIK]', text)
    text = re.sub(r'\b(Bapak|Ibu|Pak|Bu|Sdr|Saudara)\s+[A-Z][a-z]+(\s[A-Z][a-z]+)?',
                  r'\1 [NAMA]', text)
    return text

_WARGA_CUE = re.compile(r'\b(warga|masyarakat|pengguna|pemohon|pasien|wali murid|'
                        r'orang ?tua siswa|netizen|warganet|pengunjung|penumpang|keluarga pasien)\b', re.I)
_PEJABAT_CUE = re.compile(r'\b(kepala dinas|kadis|gubernur|wagub|wakil gubernur|sekda|'
                          r'wali ?kota|bupati|pejabat|pihak dinas|direktur|wakil direktur|wadir|'
                          r'kepala (bidang|seksi|uptd|rsud)|ketua|anggota dewan|dprd|kapolda|kapolres|'
                          r'menyatakan|menjelaskan|menegaskan|menganggarkan|menginstruksikan|'
                          r'saya (minta|instruksikan|perintahkan|tegaskan)|kita (punya|akan)|'
                          r'akan (kami|segera kami)|pihak (kami|rumah sakit)|'
                          r'menurut\s+\w+,?\s+(kepala|kadis|direktur))\b', re.I)
_KOTA_CUE = re.compile(r'\b(tirta mayang|pdam|perumda|wali ?kota|puskesmas|jalan kota|'
                       r'sd negeri|smp negeri|kelurahan|pemkot|pemkab|bupati)\b', re.I)
_PROV_CUE = re.compile(r'\b(jalan provinsi|ruas provinsi|pemprov|gubernur|sma negeri|'
                       r'smk negeri|rsud|raden mattaher|dprd provinsi|jalan milik provinsi)\b', re.I)

def extract_units_fallback(article_text, title=""):
    seen, units = set(), []
    tnorm = re.sub(r'\s+', ' ', title.lower()).strip()
    for s in re.split(r'(?<=[.!?])\s+', article_text):
        s = s.strip()
        if len(s.split()) < 6:
            continue
        sn = re.sub(r'\s+', ' ', s.lower()).strip()
        if tnorm and (sn == tnorm or sn in tnorm or tnorm in sn):
            continue
        if not _WARGA_CUE.search(s):
            continue
        if _PEJABAT_CUE.search(s):
            continue
        key = sn[:80]
        if key in seen:
            continue
        seen.add(key); units.append(s)
    return units

def gov_level(text):
    p, k = bool(_PROV_CUE.search(text)), bool(_KOTA_CUE.search(text))
    return "provinsi" if (p and not k) else "kota" if (k and not p) else "tak jelas"

# ==========================================================================
# ====================  DEDUP KONTEN (BARU)  ===============================
# ==========================================================================

def _norm_teks(s):
    """Normalisasi untuk perbandingan: huruf kecil, buang tanda baca, rapikan spasi.
    Dipakai untuk hash eksak DAN shingle near-dup."""
    s = s.lower()
    s = re.sub(r'[^\w\s]', ' ', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def _hash_eksak(s):
    """Hash teks ternormalisasi -> deteksi duplikat PERSIS (setelah normalisasi)."""
    return hashlib.md5(_norm_teks(s).encode('utf-8')).hexdigest()

def _shingles(s, k=SHINGLE_K):
    """Himpunan shingle (potongan k-kata berturut) dari teks ternormalisasi.
    Basis Jaccard: dua teks mirip jika banyak shingle yang sama."""
    kata = _norm_teks(s).split()
    if len(kata) < k:
        return frozenset([' '.join(kata)]) if kata else frozenset()
    return frozenset(' '.join(kata[i:i+k]) for i in range(len(kata)-k+1))

def _jaccard(a, b):
    """Kemiripan Jaccard dua himpunan shingle: |irisan| / |gabungan|."""
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0

# --- MinHash-LSH sederhana untuk mempercepat cari kandidat near-dup ---
_MERSENNE = (1 << 61) - 1
def _minhash(shingle_set, perm=MINHASH_PERM):
    """Tanda tangan MinHash: untuk tiap permutasi, ambil hash minimum antar shingle."""
    if not shingle_set:
        return tuple([0]*perm)
    sig = []
    hashes = [hash(sh) & 0xffffffffffffffff for sh in shingle_set]
    for i in range(perm):
        a = 2*i + 1
        b = 2*i + 3
        sig.append(min(((a*h + b) % _MERSENNE) for h in hashes))
    return tuple(sig)

def _lsh_keys(sig, bands=LSH_BANDS):
    """Pecah signature jadi 'band'; unit dengan band identik jadi kandidat mirip."""
    rows = max(1, len(sig)//bands)
    keys = []
    for bi in range(bands):
        chunk = sig[bi*rows:(bi+1)*rows]
        keys.append((bi, hash(chunk)))
    return keys

def baca_unit_lama():
    """Kembalikan (set_hash_eksak, list_shingle_lama, lsh_index) dari data.csv.
    Dipakai untuk dedup unit baru terhadap SEMUA unit lama."""
    hash_lama = set()
    shingle_lama = []
    lsh = {}
    if not os.path.exists(DATA_FILE):
        return hash_lama, shingle_lama, lsh
    with open(DATA_FILE, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            u = row.get("unit", "")
            if not u:
                continue
            hash_lama.add(_hash_eksak(u))
            sh = _shingles(u)
            idx = len(shingle_lama)
            shingle_lama.append(sh)
            for key in _lsh_keys(_minhash(sh)):
                lsh.setdefault(key, []).append(idx)
    return hash_lama, shingle_lama, lsh

def _near_dup(sh_baru, shingle_ref, lsh_ref):
    """True jika sh_baru near-duplicate terhadap salah satu shingle di ref.
    Pakai LSH untuk ambil kandidat, lalu cek Jaccard sebenarnya."""
    kandidat = set()
    for key in _lsh_keys(_minhash(sh_baru)):
        kandidat.update(lsh_ref.get(key, []))
    for idx in kandidat:
        if _jaccard(sh_baru, shingle_ref[idx]) >= NEARDUP_AMBANG:
            return True
    return False

def baca_url_lama():
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

    # ==== muat unit lama untuk dedup lintas-semua-data ====
    hash_lama, shingle_lama, lsh_lama = baca_unit_lama()
    print(f"Unit lama dimuat untuk dedup: {len(shingle_lama)}")

    # penampung dedup unit BARU (eksak + near-dup) dalam run ini
    hash_baru = set()
    shingle_baru = []
    lsh_baru = {}

    rows = []
    buang_lokasi = 0
    buang_eksak_lama = buang_eksak_baru = 0
    buang_near_lama = buang_near_baru = 0

    for art in arts:
        if not is_jambi_article(art["text"], art["source_url"], art.get("title","")):
            buang_lokasi += 1
            print(f"  [bukan Jambi] {art['source_url']}"); continue
        clean = pseudonymize(art["text"])
        for u in extract_units_fallback(clean, art.get("title","")):
            # filter topik/noise/lokasi (seperti sebelumnya)
            if not (RELEVAN.search(u) and not NOISE.search(u) and not _NONJAMBI.search(u)):
                continue

            h = _hash_eksak(u)
            # --- (2) dedup EKSAK: vs lama, lalu vs baru ---
            if h in hash_lama:
                buang_eksak_lama += 1; continue
            if h in hash_baru:
                buang_eksak_baru += 1; continue

            sh = _shingles(u)
            # --- (3) dedup NEAR-DUP: vs lama, lalu vs baru ---
            if _near_dup(sh, shingle_lama, lsh_lama):
                buang_near_lama += 1; continue
            if _near_dup(sh, shingle_baru, lsh_baru):
                buang_near_baru += 1; continue

            # --- lolos semua dedup: terima unit ---
            hash_baru.add(h)
            idx = len(shingle_baru)
            shingle_baru.append(sh)
            for key in _lsh_keys(_minhash(sh)):
                lsh_baru.setdefault(key, []).append(idx)

            rows.append({"unit": u, "level": gov_level(u),
                         "source_url": art["source_url"], "tanggal_ambil": tanggal})

    print(f"Artikel dibuang (bukan Jambi): {buang_lokasi}")
    print(f"Dibuang dedup EKSAK  : vs-lama={buang_eksak_lama}  vs-baru={buang_eksak_baru}")
    print(f"Dibuang dedup NEARDUP: vs-lama={buang_near_lama}  vs-baru={buang_near_baru}")
    print(f"Unit relevan baru (setelah dedup): {len(rows)}")
    if not rows:
        print("Tidak ada unit relevan baru. Selesai."); return

    baru_file = not os.path.exists(DATA_FILE)
    with open(DATA_FILE, "a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["unit","level","source_url","tanggal_ambil"])
        if baru_file: w.writeheader()
        w.writerows(rows)
    print(f"Ditambahkan {len(rows)} baris ke {DATA_FILE}")

if __name__ == "__main__":
    main()
