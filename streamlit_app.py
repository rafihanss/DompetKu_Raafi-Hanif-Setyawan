"""DompetKu - Sistem Pengelolaan Keuangan Pribadi Mahasiswa (versi Streamlit).
Jalankan: streamlit run streamlit_app.py
"""
from abc import ABC, abstractmethod
from datetime import date, timedelta


# =====================================================================
#  MODEL OOP (sama dengan versi web sebelumnya)
# =====================================================================
class Kategori:
    def __init__(self, nama, jenis):
        self.__nama = nama
        self.__jenis = jenis  # "pemasukan" / "pengeluaran"

    @property
    def nama(self):
        return self.__nama

    @property
    def jenis(self):
        return self.__jenis


class Dompet:
    def __init__(self, id, nama, jenis, saldo=0):
        self.id = id
        self.__nama = nama
        self.__jenis = jenis
        self.__saldo = saldo

    @property
    def nama(self):
        return self.__nama

    @property
    def jenis(self):
        return self.__jenis

    @property
    def saldo(self):
        return self.__saldo

    def tambah_saldo(self, n):
        self.__saldo += n

    def kurangi_saldo(self, n):
        if n > self.__saldo:
            raise ValueError(f"Saldo {self.__nama} tidak cukup")
        self.__saldo -= n


class Transaksi(ABC):
    def __init__(self, id, tanggal, nominal, deskripsi, kategori, dompet):
        if nominal <= 0:
            raise ValueError("Nominal harus lebih dari 0")
        self.id, self.tanggal, self.nominal = id, tanggal, nominal
        self.deskripsi, self.kategori, self.dompet = deskripsi, kategori, dompet

    @abstractmethod
    def terapkan(self):
        """Memperbarui saldo dompet (polimorfisme)."""

    def to_dict(self):
        return {"id": self.id, "tanggal": str(self.tanggal), "nominal": self.nominal,
                "deskripsi": self.deskripsi, "kategori": self.kategori.nama,
                "dompet": self.dompet.nama, "jenis": self.kategori.jenis}


class Pemasukan(Transaksi):
    def terapkan(self):
        self.dompet.tambah_saldo(self.nominal)


class Pengeluaran(Transaksi):
    def terapkan(self):
        self.dompet.kurangi_saldo(self.nominal)


class Setoran(Transaksi):
    """Setoran dari dompet ke target: saldo dompet berkurang, tetapi bukan pengeluaran biasa."""
    def terapkan(self):
        self.dompet.kurangi_saldo(self.nominal)

    def to_dict(self):
        d = super().to_dict()
        d["jenis"] = "setoran"
        return d


class Anggaran:
    def __init__(self, kategori, batas):
        self.kategori, self.batas = kategori, batas

    def hitung_terpakai(self, transaksi):
        return sum(t.nominal for t in transaksi
                   if isinstance(t, Pengeluaran) and t.kategori is self.kategori)

    def persentase(self, terpakai):
        return round(terpakai / self.batas * 100, 1)

    def melebihi(self, terpakai):
        return terpakai > self.batas


class TargetKeuangan(ABC):
    """Kelas dasar semua target (abstraksi)."""
    def __init__(self, nama, kategori, target, tenggat, terkumpul=0):
        self.nama, self.kategori, self.target = nama, kategori, target
        self.tenggat, self.terkumpul = tenggat, terkumpul

    def setor(self, nominal):
        if nominal <= 0:
            raise ValueError("Nominal setoran harus lebih dari 0")
        self.terkumpul += nominal

    def progres(self):
        return round(min(self.terkumpul / self.target * 100, 100), 1)

    def sisa(self):
        return max(self.target - self.terkumpul, 0)

    @abstractmethod
    def jenis(self):
        """Nama jenis target (polimorfisme)."""


class TargetTabungan(TargetKeuangan):
    def jenis(self):
        return "Tabungan"


class TargetInvestasi(TargetKeuangan):
    def __init__(self, nama, kategori, target, tenggat, estimasi_return, terkumpul=0):
        super().__init__(nama, kategori, target, tenggat, terkumpul)
        self.estimasi_return = estimasi_return  # persen per tahun

    def jenis(self):
        return "Investasi"

    def proyeksi_nilai(self):
        """Perkiraan nilai dana saat tenggat dengan imbal hasil majemuk."""
        try:
            tahun = max((date.fromisoformat(str(self.tenggat)) - date.today()).days, 0) / 365
        except ValueError:
            tahun = 0
        return round(self.terkumpul * (1 + self.estimasi_return / 100) ** tahun)


class Pengguna:
    def __init__(self, nama, email, jurusan):
        self.nama, self.email, self.jurusan = nama, email, jurusan
        self.daftar_dompet = []

    def tambah_dompet(self, dompet):
        self.daftar_dompet.append(dompet)

    def total_saldo(self):
        return sum(d.saldo for d in self.daftar_dompet)


class PengelolaKeuangan:
    def __init__(self, pengguna):
        self.pengguna = pengguna
        self.kategori = {}
        self.transaksi = []
        self.anggaran = []
        self.target = []

    def _dompet(self, id):
        return next(d for d in self.pengguna.daftar_dompet if d.id == id)

    def catat_transaksi(self, nama_kategori, dompet_id, nominal, deskripsi, tanggal=None):
        kat = self.kategori[nama_kategori]
        kelas = Pemasukan if kat.jenis == "pemasukan" else Pengeluaran
        t = kelas(len(self.transaksi) + 1, tanggal or date.today(), nominal,
                  deskripsi, kat, self._dompet(dompet_id))
        t.terapkan()  # polimorfisme: tiap subclass punya aturan sendiri
        self.transaksi.append(t)
        return t

    def setor_tabungan(self, idx, dompet_id, nominal):
        t = self.target[int(idx)]
        if nominal <= 0:
            raise ValueError("Nominal setoran harus lebih dari 0")
        trx = Setoran(len(self.transaksi) + 1, date.today(), nominal, f"Setor ke {t.nama}",
                      Kategori(f"{t.jenis()} · {t.kategori}", "setoran"), self._dompet(dompet_id))
        trx.terapkan()  # gagal di sini bila saldo kurang, sebelum target diubah
        t.setor(nominal)
        self.transaksi.append(trx)

    def tambah_target(self, jenis, nama, kategori, nominal, tenggat=None, estimasi_return=0):
        nominal = float(nominal or 0)
        if not str(nama).strip() or nominal <= 0:
            raise ValueError("Nama dan nominal target wajib diisi")
        tenggat = tenggat or "-"
        if jenis == "Investasi":
            t = TargetInvestasi(nama.strip(), kategori, nominal, tenggat, float(estimasi_return or 0))
        else:
            t = TargetTabungan(nama.strip(), kategori, nominal, tenggat)
        self.target.append(t)

    def hapus_target(self, idx):
        del self.target[int(idx)]

    def peringatan(self):
        hasil = []
        for a in self.anggaran:
            p = a.persentase(a.hitung_terpakai(self.transaksi))
            if p > 100:
                hasil.append(f"Anggaran {a.kategori.nama} terlampaui ({p}%)!")
            elif p >= 80:
                hasil.append(f"Anggaran {a.kategori.nama} hampir habis ({p}%)")
        return hasil

    def ke_dict(self):
        """Serialisasi seluruh data (untuk cadangan JSON)."""
        p = self.pengguna
        return {
            "pengguna": {"nama": p.nama, "email": p.email, "jurusan": p.jurusan},
            "dompet": [{"id": d.id, "nama": d.nama, "jenis": d.jenis, "saldo": d.saldo} for d in p.daftar_dompet],
            "kategori": [{"nama": k.nama, "jenis": k.jenis} for k in self.kategori.values()],
            "anggaran": [{"kategori": a.kategori.nama, "batas": a.batas} for a in self.anggaran],
            "target": [{"jenis": t.jenis(), "nama": t.nama, "kategori": t.kategori, "target": t.target,
                        "tenggat": str(t.tenggat), "terkumpul": t.terkumpul,
                        "return": getattr(t, "estimasi_return", 0)} for t in self.target],
            "transaksi": [{"tipe": type(t).__name__, "tanggal": str(t.tanggal), "nominal": t.nominal,
                           "deskripsi": t.deskripsi, "kategori": t.kategori.nama,
                           "jenis_kat": t.kategori.jenis, "dompet": t.dompet.id} for t in self.transaksi]}

    @staticmethod
    def dari_dict(d):
        """Membangun kembali seluruh objek dari data cadangan."""
        p = Pengguna(**d["pengguna"])
        app = PengelolaKeuangan(p)
        for x in d["dompet"]:
            p.tambah_dompet(Dompet(x["id"], x["nama"], x["jenis"], x["saldo"]))
        for k in d["kategori"]:
            app.kategori[k["nama"]] = Kategori(k["nama"], k["jenis"])
        for x in d["anggaran"]:
            app.anggaran.append(Anggaran(app.kategori[x["kategori"]], x["batas"]))
        for t in d["target"]:
            if t["jenis"] == "Investasi":
                app.target.append(TargetInvestasi(t["nama"], t["kategori"], t["target"], t["tenggat"],
                                                  t["return"], t["terkumpul"]))
            else:
                app.target.append(TargetTabungan(t["nama"], t["kategori"], t["target"], t["tenggat"], t["terkumpul"]))
        kelas = {"Pemasukan": Pemasukan, "Pengeluaran": Pengeluaran, "Setoran": Setoran}
        for i, t in enumerate(d["transaksi"], 1):
            kat = app.kategori.get(t["kategori"]) or Kategori(t["kategori"], t["jenis_kat"])
            app.transaksi.append(kelas[t["tipe"]](i, date.fromisoformat(t["tanggal"]), t["nominal"],
                                                  t["deskripsi"], kat, app._dompet(t["dompet"])))
        return app

    def tambah_kategori(self, nama, jenis="pengeluaran", batas=None):
        nama = nama.strip()
        if not nama:
            raise ValueError("Nama kategori wajib diisi")
        if jenis not in ("pemasukan", "pengeluaran"):
            raise ValueError("Jenis kategori tidak valid")
        if nama not in self.kategori:
            self.kategori[nama] = Kategori(nama, jenis)
        kat, batas = self.kategori[nama], float(batas or 0)
        if batas > 0 and kat.jenis == "pengeluaran":
            for a in self.anggaran:
                if a.kategori is kat:
                    a.batas = batas  # kategori sudah punya anggaran: perbarui
                    return
            self.anggaran.append(Anggaran(kat, batas))

    def hapus_anggaran(self, idx):
        del self.anggaran[int(idx)]

    def daftar_objek(self):
        p = self.pengguna
        o = [{"objek": p.nama, "class": "Pengguna",
              "atribut": {"nama": p.nama, "email": p.email, "jurusan": p.jurusan},
              "method": ["tambahDompet()", "totalSaldo()"]}]
        for d in p.daftar_dompet:
            o.append({"objek": d.nama, "class": "Dompet",
                      "atribut": {"nama": d.nama, "jenis": d.jenis, "saldo": d.saldo},
                      "method": ["tambahSaldo()", "kurangiSaldo()"]})
        for a in self.anggaran:
            o.append({"objek": "Anggaran " + a.kategori.nama, "class": "Anggaran",
                      "atribut": {"kategori": a.kategori.nama, "batas": a.batas},
                      "method": ["hitungTerpakai()", "persentase()", "melebihi()"]})
        for t in self.target:
            atr = {"nama": t.nama, "kategori": t.kategori, "target": t.target,
                   "terkumpul": t.terkumpul, "tenggat": t.tenggat}
            mtd = ["setor()", "progres()", "sisa()", "jenis()"]
            if isinstance(t, TargetInvestasi):
                atr["estimasiReturn"] = t.estimasi_return
                mtd.append("proyeksiNilai()")
            o.append({"objek": t.nama, "class": type(t).__name__, "atribut": atr, "method": mtd})
        for t in self.transaksi[-5:]:
            o.append({"objek": f"Transaksi #{t.id}", "class": type(t).__name__,
                      "atribut": {"nominal": t.nominal, "deskripsi": t.deskripsi,
                                  "kategori": t.kategori.nama, "dompet": t.dompet.nama},
                      "method": ["terapkan()"]})
        return o

    def ringkasan(self):
        masuk = sum(t.nominal for t in self.transaksi if isinstance(t, Pemasukan))
        keluar = sum(t.nominal for t in self.transaksi if isinstance(t, Pengeluaran))
        per_kat = {}
        for t in self.transaksi:
            if isinstance(t, Pengeluaran):
                per_kat[t.kategori.nama] = per_kat.get(t.kategori.nama, 0) + t.nominal
        return {
            "terdaftar": True, "objek": self.daftar_objek(),
            "pengguna": self.pengguna.nama,
            "total_saldo": self.pengguna.total_saldo(),
            "pemasukan": masuk, "pengeluaran": keluar,
            "di_target": sum(t.terkumpul for t in self.target),
            "dompet": [{"id": d.id, "nama": d.nama, "jenis": d.jenis, "saldo": d.saldo}
                       for d in self.pengguna.daftar_dompet],
            "per_kategori": per_kat,
            "anggaran": [{"kategori": a.kategori.nama, "batas": a.batas,
                          "terpakai": (u := a.hitung_terpakai(self.transaksi)),
                          "persen": a.persentase(u)} for a in self.anggaran],
            "target": [{"nama": t.nama, "jenis": t.jenis(), "kategori": t.kategori,
                        "target": t.target, "terkumpul": t.terkumpul, "sisa": t.sisa(),
                        "progres": t.progres(), "tenggat": str(t.tenggat),
                        "return": getattr(t, "estimasi_return", None),
                        "proyeksi": t.proyeksi_nilai() if isinstance(t, TargetInvestasi) else None}
                       for t in self.target],
            "peringatan": self.peringatan(),
            "kategori": [{"nama": k.nama, "jenis": k.jenis} for k in self.kategori.values()],
            "transaksi": [t.to_dict() for t in reversed(self.transaksi)][:15],
        }


def buat_sistem(d):
    pengguna = Pengguna(d["nama"].strip(), d.get("email", "").strip(), d.get("jurusan", "").strip())
    app = PengelolaKeuangan(pengguna)
    for i, (nm, jn) in enumerate([("Tunai", "tunai"), ("Rekening Bank", "bank"), ("E-Wallet", "ewallet")], 1):
        pengguna.tambah_dompet(Dompet(i, nm, jn, float(d.get(jn) or 0)))
    for nama, jenis in [("Uang Saku", "pemasukan"), ("Freelance", "pemasukan"),
                        ("Lainnya", "pengeluaran")]:
        app.kategori[nama] = Kategori(nama, jenis)
    for item in d.get("anggaran", []):
        if not str(item.get("kategori", "")).strip():
            continue  # lewati baris kosong
        app.tambah_kategori(item["kategori"], "pengeluaran", item.get("batas"))
    tg = d.get("target")
    if tg and str(tg.get("nama", "")).strip():
        app.tambah_target(tg.get("jenis", "Tabungan"), tg["nama"], tg.get("kategori", "Lainnya"),
                          tg.get("nominal"), tg.get("tenggat"), tg.get("return"))
    return app


# =====================================================================
#  TAMPILAN STREAMLIT
# =====================================================================
import json
import re

import altair as alt
import pandas as pd
import streamlit as st

st.set_page_config(page_title="DompetKu", page_icon="💰", layout="wide")
st.markdown("""<style>
:root{--bg:#0f1218;--card:#161b24;--c2:#1d2330;--bd:#262d3b;--tx:#e6e9ef;--mut:#8b94a5;--g:#2bb673;--r:#e5586a;--y:#e0a43a}
.stApp{background:var(--bg)}
.block-container{max-width:1100px;padding-top:4.5rem}
footer{visibility:hidden}
.stApp label,.stApp .stMarkdown p,.stApp h1,.stApp h2,.stApp h3,.stApp h4{color:var(--tx)}
.stApp [data-testid="stCaptionContainer"]{color:var(--mut)}
div[data-baseweb="input"],div[data-baseweb="base-input"],div[data-baseweb="select"]>div{background:var(--c2)!important;border-color:var(--bd)!important}
.stApp input{color:var(--tx)!important}
button[data-baseweb="tab"]{font-weight:700}
[data-testid="stVerticalBlockBorderWrapper"]{background:var(--card);border-color:var(--bd);border-radius:14px}
.stButton>button[kind="primary"]{background:var(--g);border:0;font-weight:700}
.stButton>button[kind="primary"] p{color:#04130c!important}
.top{display:flex;align-items:center;justify-content:space-between;padding:4px 0 14px}
.brand{font-weight:700;font-size:19px;display:flex;align-items:center;gap:8px;color:var(--tx)}
.brand i{width:12px;height:12px;border-radius:50%;background:var(--g);display:inline-block}
.me{display:flex;align-items:center;gap:10px;font-weight:600;color:var(--tx)}
.av{width:32px;height:32px;border-radius:50%;background:var(--g);color:#04130c;display:grid;place-items:center;font-weight:800}
.card{background:var(--card);border:1px solid var(--bd);border-radius:14px;padding:22px;margin-bottom:20px;color:var(--tx)}
.card h3{margin:0 0 12px;font-size:15px;color:var(--tx)}
.mut{color:var(--mut);font-size:12px}
.big{font-size:30px;font-weight:700;letter-spacing:-.5px}
.chip{display:inline-block;padding:3px 10px;border-radius:6px;font-weight:700;font-size:12px;margin-left:10px;vertical-align:middle}
.up{color:var(--g)}.dn{color:var(--r)}.ys{color:var(--y)}
.chip.up{background:rgba(43,182,115,.12)}.chip.dn{background:rgba(229,88,106,.12)}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-top:16px}
.stats>div{background:var(--c2);border-radius:10px;padding:12px}
.li{display:flex;align-items:center;gap:12px;padding:11px 0;border-bottom:1px solid var(--bd)}
.li:last-child{border:0}
.ic{width:36px;height:36px;border-radius:50%;background:var(--c2);display:grid;place-items:center;font-weight:800;color:var(--g)}
.li .m{flex:1;min-width:0}.li .r{text-align:right;font-weight:600}.li b{font-weight:600}
.bar{height:5px;background:var(--c2);border-radius:4px;margin-top:6px;overflow:hidden}.bar i{display:block;height:100%}
.al{padding:10px 14px;border-radius:10px;margin-bottom:10px;background:rgba(224,164,58,.12);color:var(--y);font-weight:600}
.al.bad{background:rgba(229,88,106,.12);color:var(--r)}
.card table{width:100%;border-collapse:collapse;font-size:13px}
.card th,.card td{padding:9px 8px;border-bottom:1px solid var(--bd);text-align:left}
.card th{color:var(--mut);font-weight:600}
</style>""", unsafe_allow_html=True)

S = st.session_state
STAT = r'''classDiagram
  class Pengguna {
    -nama: str
    -email: str
    -jurusan: str
    +tambahDompet(dompet)
    +totalSaldo() float
  }
  class Dompet {
    -nama: str
    -jenis: str
    -saldo: float
    +tambahSaldo(n)
    +kurangiSaldo(n)
  }
  class Transaksi {
    <<abstract>>
    -id: int
    -tanggal: date
    -nominal: float
    -deskripsi: str
    +terapkan()*
  }
  class Pemasukan {
    +terapkan()
  }
  class Pengeluaran {
    +terapkan()
  }
  class Setoran {
    +terapkan()
  }
  class Kategori {
    -nama: str
    -jenis: str
  }
  class Anggaran {
    -batas: float
    +hitungTerpakai()
    +persentase()
    +melebihi()
  }
  class TargetKeuangan {
    <<abstract>>
    -nama: str
    -kategori: str
    -target: float
    -terkumpul: float
    -tenggat: date
    +setor(nominal)
    +progres()
    +sisa()
    +jenis()*
  }
  class TargetTabungan {
    +jenis()
  }
  class TargetInvestasi {
    -estimasiReturn: float
    +jenis()
    +proyeksiNilai()
  }
  class PengelolaKeuangan {
    +catatTransaksi()
    +setorTabungan()
    +tambahTarget()
    +tambahKategori()
    +ringkasan()
    +peringatan()
    +daftarObjek()
  }
  Transaksi <|-- Pemasukan
  Transaksi <|-- Pengeluaran
  Transaksi <|-- Setoran
  Pengguna "1" --> "*" Dompet
  Dompet "1" --> "*" Transaksi
  Kategori "1" --> "*" Transaksi
  Kategori "1" --> "0..1" Anggaran
  Pengguna "1" --> "*" TargetKeuangan
  TargetKeuangan <|-- TargetTabungan
  TargetKeuangan <|-- TargetInvestasi
  PengelolaKeuangan o-- Dompet
  PengelolaKeuangan o-- Transaksi
  PengelolaKeuangan o-- Anggaran
  PengelolaKeuangan o-- TargetKeuangan'''
PALET = ["#2bb673", "#e5586a", "#e0a43a", "#5b8def", "#9b7bea", "#3fb8c4"]
HALAMAN = ["Dashboard", "Transaksi", "Anggaran", "Target", "Diagram Class"]
KAT = {"Tabungan": ["Dana Darurat", "Liburan", "Pendidikan", "Gadget / Laptop", "Kendaraan",
                    "Rumah / Properti", "Pernikahan", "Lainnya"],
       "Investasi": ["Reksa Dana", "Saham", "Emas", "Obligasi / SBN", "Deposito", "Crypto"]}


# ---------- helper angka (titik ribuan) ----------
def fmt(n):
    return f"{int(round(n)):,}".replace(",", ".")


def rp(n):
    return "Rp" + fmt(n)


def angka(s):
    digit = "".join(c for c in str(s) if c.isdigit())
    return int(digit) if digit else 0


def _titik(key):
    n = angka(S[key])
    S[key] = fmt(n) if n else ""


def uang(label, key, awal=0):
    """Input nominal: titik ribuan muncul otomatis setelah Enter / pindah kolom."""
    if key not in S:
        S[key] = fmt(awal) if awal else ""
    st.text_input(label, key=key, on_change=_titik, args=(key,), placeholder="0")


def jalankan(fn, sukses, *args):
    try:
        fn(*args)
        S.pesan = ("ok", sukses)
    except (ValueError, KeyError, IndexError, StopIteration, TypeError) as e:
        S.pesan = ("error", str(e) or "Data tidak valid")


def tampil_pesan():
    if "pesan" in S:
        jenis, teks = S.pop("pesan")
        (st.error if jenis == "error" else st.success)(teks)


# ---------- helper HTML (kartu gaya Stockbit) ----------
import html as _html


def esc(x):
    return _html.escape(str(x))


def kartu(judul, isi):
    return f'<div class="card"><h3>{judul}</h3>{isi}</div>'


def html_hero(d):
    net = d["pemasukan"] - d["pengeluaran"]
    naik = net >= 0
    return ('<div class="card"><div class="mut">Total Saldo</div><div>'
            f'<span class="big">{rp(d["total_saldo"])}</span>'
            f'<span class="chip {"up" if naik else "dn"}">{"▲ +" if naik else "▼ -"}{rp(abs(net))}</span></div>'
            '<div class="stats">'
            f'<div><div class="mut">Pemasukan</div><b class="up">{rp(d["pemasukan"])}</b></div>'
            f'<div><div class="mut">Pengeluaran</div><b class="dn">{rp(d["pengeluaran"])}</b></div>'
            f'<div><div class="mut">Di Target</div><b>{rp(d["di_target"])}</b></div>'
            '</div></div>')


def html_dompet(d):
    return "".join(f'<div class="li"><div class="ic">{esc(x["nama"][:1])}</div><div class="m"><b>{esc(x["nama"])}</b>'
                   f'<div class="mut">{esc(x["jenis"])}</div></div><div class="r">{rp(x["saldo"])}</div></div>'
                   for x in d["dompet"])


def html_anggaran(d):
    if not d["anggaran"]:
        return '<div class="mut">Belum ada anggaran.</div>'
    baris = ""
    for x in d["anggaran"]:
        warna = "var(--r)" if x["persen"] > 100 else "var(--y)" if x["persen"] >= 80 else "var(--g)"
        baris += (f'<div class="li"><div class="m"><b>{esc(x["kategori"])}</b>'
                  f'<div class="mut">{rp(x["terpakai"])} dari {rp(x["batas"])}</div>'
                  f'<div class="bar"><i style="width:{min(x["persen"], 100)}%;background:{warna}"></i></div></div>'
                  f'<div class="r" style="color:{warna}">{x["persen"]}%</div></div>')
    return baris


def html_target(d):
    if not d["target"]:
        return '<div class="mut">Belum ada target. Tambahkan di halaman Target.</div>'
    baris = ""
    for t in d["target"]:
        proyeksi = (f'<div class="mut">Estimasi {t["return"]}%/tahun, proyeksi nilai saat tenggat {rp(t["proyeksi"])}</div>'
                    if t["proyeksi"] is not None else "")
        baris += ('<div style="margin-bottom:14px"><div style="display:flex;justify-content:space-between;align-items:center">'
                  f'<div><b>{esc(t["nama"])}</b><span class="chip" style="background:var(--c2);color:var(--mut)">'
                  f'{esc(t["jenis"])} · {esc(t["kategori"])}</span></div><b class="up">{t["progres"]}%</b></div>'
                  f'<div class="bar"><i style="width:{t["progres"]}%;background:var(--g)"></i></div>'
                  f'<div class="mut" style="margin-top:6px">{rp(t["terkumpul"])} dari {rp(t["target"])} | tenggat {esc(t["tenggat"])}</div>'
                  f'{proyeksi}</div>')
    return baris


def html_tabel(sis, n=None, jenis=None, dompet=None):
    baris = [t.to_dict() for t in reversed(sis.transaksi)]
    baris = [t for t in baris if (jenis is None or t["jenis"] == jenis)
             and (dompet is None or t["dompet"] == dompet)][:n]
    if not baris:
        return '<div class="mut">Belum ada transaksi.</div>'
    isi = ""
    for t in baris:
        kelas = {"pemasukan": "up", "setoran": "ys"}.get(t["jenis"], "dn")
        tanda = "+" if t["jenis"] == "pemasukan" else "-"
        isi += (f'<tr><td>{t["tanggal"]}</td><td>{esc(t["deskripsi"])}</td><td>{esc(t["kategori"])}</td>'
                f'<td>{esc(t["dompet"])}</td><td class="{kelas}" style="text-align:right;font-weight:600">'
                f'{tanda}{rp(t["nominal"])}</td></tr>')
    return ('<table><thead><tr><th>Tanggal</th><th>Deskripsi</th><th>Kategori</th><th>Dompet</th>'
            '<th style="text-align:right">Nominal</th></tr></thead><tbody>' + isi + '</tbody></table>')


# ---------- form target (dipakai di pendaftaran & dashboard) ----------
def form_target(p):
    jenis = st.selectbox("Jenis target", list(KAT), key=f"{p}_tg_jenis")
    st.selectbox("Kategori", KAT[jenis], key=f"{p}_tg_kat_{jenis}")
    st.text_input("Nama target", key=f"{p}_tg_nama", placeholder="cth: Laptop baru, Beli emas")
    uang("Nominal target (Rp)", f"{p}_tg_nominal")
    st.date_input("Tenggat", value=date.today() + timedelta(days=365), key=f"{p}_tg_tenggat")
    if jenis == "Investasi":
        st.number_input("Estimasi imbal hasil (% per tahun)", 0.0, 100.0, 8.0, 0.5, key=f"{p}_tg_ret")


def baca_target(p):
    jenis = S[f"{p}_tg_jenis"]
    return {"jenis": jenis, "kategori": S[f"{p}_tg_kat_{jenis}"], "nama": S[f"{p}_tg_nama"],
            "nominal": angka(S[f"{p}_tg_nominal"]), "tenggat": str(S[f"{p}_tg_tenggat"]),
            "return": S.get(f"{p}_tg_ret", 0) if jenis == "Investasi" else 0}


# ---------- diagram ----------
def diagram_dinamis(objek):
    bersih = lambda s: re.sub(r"[^\w .@-]", "", str(s))[:28]
    kel = {}
    for o in objek:
        kel.setdefault(o["class"], o)
    m = "classDiagram\n"
    for c, o in kel.items():
        m += f"class {c} {{\n"
        m += "".join(f"-{k}\n" for k in o["atribut"]) + "".join(f"+{f}\n" for f in o["method"]) + "}\n"
    for i, o in enumerate(objek):
        m += f'class o{i}["{bersih(o["objek"])} : {o["class"]}"] {{\n<<objek>>\n'
        for k, v in o["atribut"].items():
            m += f"{k} = {bersih(v) or '-'}\n"
        m += f"}}\no{i} ..> {o['class']} : instance\n"
    return m


def gambar(teks, tinggi):
    html = f"""<style>body{{margin:0}}#w{{background:#161b24;padding:12px;border-radius:10px;overflow:auto;
color:#e6e9ef;font-family:sans-serif}}#g svg{{max-width:100%;height:auto}}</style>
<div id="w"><div id="g">Memuat diagram...</div></div>
<script src="https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"></script>
<script>
mermaid.initialize({{startOnLoad:false, theme:'dark', suppressErrorRendering:true}});
let selesai = false, coba = 0;
async function gambar() {{
  if (selesai || document.documentElement.clientWidth < 100) return;
  selesai = true;
  try {{
    const r = await mermaid.render('svgdiagram', {json.dumps(teks)});
    document.getElementById('g').innerHTML = r.svg;
  }} catch (e) {{
    const sisa = document.getElementById('dsvgdiagram'); if (sisa) sisa.remove();
    if (++coba < 4) {{ selesai = false; setTimeout(gambar, 800); }}
    else document.getElementById('g').textContent = 'Diagram gagal dibuat: ' + e.message;
  }}
}}
window.addEventListener('load', gambar);
window.addEventListener('resize', gambar);
setTimeout(gambar, 300);
</script>"""
    if hasattr(st, "iframe"):  # Streamlit terbaru
        st.iframe(html, height=tinggi)
    else:  # Streamlit lama
        import streamlit.components.v1 as components
        components.html(html, height=tinggi, scrolling=True)


# ---------- aksi (callback tombol) ----------
def aksi_daftar():
    def kerja():
        if not S.r_nama.strip():
            raise ValueError("Nama wajib diisi")
        ang = []
        for _, r in S["_ang"].iterrows():
            nama = r["Kategori"]
            if pd.notna(nama) and str(nama).strip():
                batas = r["Batas per bulan (Rp)"]
                ang.append({"kategori": str(nama), "batas": float(batas) if pd.notna(batas) else 0})
        S.sistem = buat_sistem({
            "nama": S.r_nama, "email": S.r_email, "jurusan": S.r_jurusan,
            "tunai": angka(S.r_tunai), "bank": angka(S.r_bank), "ewallet": angka(S.r_ewallet),
            "anggaran": ang, "target": baca_target("r")})
    jalankan(kerja, "Berhasil masuk")


def keluar():
    for k in list(S.keys()):
        del S[k]


def aksi_catat():
    def kerja():
        S.sistem.catat_transaksi(S.t_kat, S.t_dompet, angka(S.t_nominal), S.t_desk.strip() or "-")
        S.t_nominal, S.t_desk = "", ""
    jalankan(kerja, "Transaksi tersimpan")


def aksi_kategori():
    def kerja():
        S.sistem.tambah_kategori(S.k_nama, S.k_jenis, angka(S.k_batas))
        S.k_nama, S.k_batas = "", ""
    jalankan(kerja, "Kategori disimpan")


def aksi_target():
    t = baca_target("g")

    def kerja():
        S.sistem.tambah_target(t["jenis"], t["nama"], t["kategori"], t["nominal"], t["tenggat"], t["return"])
        S.g_tg_nama, S.g_tg_nominal = "", ""
    jalankan(kerja, "Target ditambahkan")


def aksi_hapus_ang():
    jalankan(S.sistem.hapus_anggaran, "Anggaran dihapus", S.h_ang)
    S.h_ang = 0


def aksi_hapus_tgt():
    jalankan(S.sistem.hapus_target, "Target dihapus", S.h_tgt)
    S.h_tgt, S.s_target = 0, 0


def aksi_pulihkan():
    def kerja():
        berkas = S.get("r_file")
        if berkas is None:
            raise ValueError("Pilih file cadangan (.json) terlebih dahulu")
        S.sistem = PengelolaKeuangan.dari_dict(json.loads(berkas.getvalue().decode("utf-8")))
    jalankan(kerja, "Data berhasil dipulihkan")


def aksi_setor():
    def kerja():
        S.sistem.setor_tabungan(S.s_target, S.s_dompet, angka(S.s_nominal))
        S.s_nominal = ""
    jalankan(kerja, "Setoran berhasil")


# ---------- halaman pendaftaran ----------
def halaman_daftar():
    st.markdown('<div class="top"><div class="brand"><i></i>DompetKu</div></div>', unsafe_allow_html=True)
    st.markdown("## Selamat datang!")
    st.caption("Isi data berikut untuk membuat dashboard keuanganmu. Data ini menjadi objek di dalam sistem.")
    tampil_pesan()
    with st.expander("Punya file cadangan? Pulihkan data"):
        st.file_uploader("File cadangan (.json)", type="json", key="r_file")
        st.button("Pulihkan data", on_click=aksi_pulihkan)
    st.subheader("Data diri")
    c = st.columns(3)
    c[0].text_input("Nama lengkap", key="r_nama")
    c[1].text_input("Email", key="r_email")
    c[2].text_input("Jurusan", key="r_jurusan")
    st.subheader("Saldo awal dompet")
    c = st.columns(3)
    with c[0]:
        uang("Tunai (Rp)", "r_tunai")
    with c[1]:
        uang("Rekening Bank (Rp)", "r_bank")
    with c[2]:
        uang("E-Wallet (Rp)", "r_ewallet")
    st.subheader("Anggaran bulanan (bebas pilih kategori)")
    st.caption("Klik baris kosong paling bawah untuk menambah kategori, pilih baris lalu tekan Delete untuk menghapus.")
    awal = pd.DataFrame({"Kategori": ["Makan", "Transport", "Hiburan", "Kuliah"],
                         "Batas per bulan (Rp)": [600000, 200000, 150000, 300000]})
    S["_ang"] = st.data_editor(awal, num_rows="dynamic", hide_index=True, key="r_ang", column_config={
        "Batas per bulan (Rp)": st.column_config.NumberColumn(min_value=0, step=10000, format="localized")})
    st.subheader("Target keuangan (opsional)")
    form_target("r")
    st.button("Masuk ke Dashboard", type="primary", on_click=aksi_daftar)


# ---------- halaman dashboard ----------
def daftar_target(d):
    st.markdown(html_target(d), unsafe_allow_html=True)


def halaman_dashboard():
    sis = S.sistem
    d = sis.ringkasan()
    nama_dompet = {x["id"]: x["nama"] for x in d["dompet"]}
    h1, h2, h3 = st.columns([7, 2, 1])
    h1.markdown(f'<div class="top"><div class="brand"><i></i>DompetKu</div><div class="me">Halo, {esc(d["pengguna"])}'
                f'<div class="av">{esc(d["pengguna"][:1].upper())}</div></div></div>', unsafe_allow_html=True)
    h2.download_button("Unduh cadangan", json.dumps(sis.ke_dict(), indent=2, ensure_ascii=False),
                       "dompetku_cadangan.json", "application/json")
    h3.button("Ganti", on_click=keluar)
    if S.get("menu") not in HALAMAN:
        S["menu"] = HALAMAN[0]
    pilih = st.segmented_control("Menu", HALAMAN, key="menu", label_visibility="collapsed") or HALAMAN[0]
    tampil_pesan()

    if pilih == HALAMAN[0]:
        for p in d["peringatan"]:
            st.markdown(f'<div class="al {"bad" if "terlampaui" in p else ""}">{esc(p)}</div>', unsafe_allow_html=True)
        kiri, kanan = st.columns([3, 2])
        with kiri:
            st.markdown(html_hero(d), unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown("**Pengeluaran per Kategori**")
                if d["per_kategori"]:
                    df = pd.DataFrame({"Kategori": list(d["per_kategori"]), "Jumlah": list(d["per_kategori"].values())})
                    st.altair_chart(alt.Chart(df).mark_arc(innerRadius=70).encode(
                        theta="Jumlah:Q",
                        color=alt.Color("Kategori:N", scale=alt.Scale(range=PALET)),
                        tooltip=["Kategori", "Jumlah"]).configure_legend(labelColor="#e6e9ef", titleColor="#8b94a5"))
                else:
                    st.caption("Belum ada pengeluaran.")
            st.markdown(kartu("Transaksi Terbaru", html_tabel(sis, 10)), unsafe_allow_html=True)
        with kanan:
            st.markdown(kartu("Dompet", html_dompet(d)), unsafe_allow_html=True)
            st.markdown(kartu("Anggaran Bulanan", html_anggaran(d)), unsafe_allow_html=True)
            st.markdown(kartu("Target Keuangan", html_target(d)), unsafe_allow_html=True)

    elif pilih == HALAMAN[1]:
        st.subheader("Catat Transaksi")
        c = st.columns(2)
        c[0].selectbox("Kategori", [k["nama"] for k in d["kategori"]], key="t_kat",
                       format_func=lambda n: f"{n} ({sis.kategori[n].jenis})")
        c[1].selectbox("Dompet", list(nama_dompet), key="t_dompet", format_func=nama_dompet.get)
        c = st.columns(2)
        with c[0]:
            uang("Nominal (Rp)", "t_nominal")
        c[1].text_input("Deskripsi", key="t_desk")
        st.button("Simpan Transaksi", type="primary", on_click=aksi_catat)
        f1, f2 = st.columns(2)
        f1.selectbox("Tampilkan", ["Semua", "Pemasukan", "Pengeluaran", "Setoran"], key="f_jenis")
        f2.selectbox("Dompet", ["Semua"] + list(nama_dompet.values()), key="f_dompet")
        jenis = None if S.f_jenis == "Semua" else S.f_jenis.lower()
        dompet = None if S.f_dompet == "Semua" else S.f_dompet
        st.markdown(kartu("Riwayat Transaksi", html_tabel(sis, None, jenis, dompet)), unsafe_allow_html=True)
        csv = pd.DataFrame([t.to_dict() for t in sis.transaksi]).to_csv(index=False).encode("utf-8")
        st.download_button("Unduh CSV", csv, "transaksi_dompetku.csv", "text/csv")

    elif pilih == HALAMAN[2]:
        st.markdown("### Anggaran")
        kiri, kanan = st.columns([2, 3])
        with kiri:
            with st.container(border=True):
                st.markdown("**Tambah kategori / anggaran**")
                st.text_input("Nama kategori", key="k_nama", placeholder="cth: Kos, Ngopi, Gaji")
                st.selectbox("Jenis", ["pengeluaran", "pemasukan"], key="k_jenis")
                uang("Batas bulanan (Rp, opsional, hanya pengeluaran)", "k_batas")
                st.button("Simpan Kategori", type="primary", on_click=aksi_kategori)
        with kanan:
            st.markdown(kartu("Anggaran Bulanan", html_anggaran(d)), unsafe_allow_html=True)
            if d["anggaran"]:
                with st.expander("Hapus anggaran"):
                    st.selectbox("Pilih anggaran", list(range(len(d["anggaran"]))), key="h_ang",
                                 format_func=lambda i: d["anggaran"][i]["kategori"])
                    st.button("Hapus", on_click=aksi_hapus_ang)
    elif pilih == HALAMAN[3]:
        st.markdown("### Target Keuangan")
        kiri, kanan = st.columns([3, 2])
        with kiri:
            st.markdown(kartu("Target Saya", html_target(d)), unsafe_allow_html=True)
            if d["target"]:
                with st.container(border=True):
                    st.markdown("**Setor ke target**")
                    st.selectbox("Target", list(range(len(d["target"]))), key="s_target",
                                 format_func=lambda i: d["target"][i]["nama"])
                    st.selectbox("Dari dompet", list(nama_dompet), key="s_dompet", format_func=nama_dompet.get)
                    uang("Nominal setoran (Rp)", "s_nominal")
                    st.button("Setor", type="primary", on_click=aksi_setor)
                with st.expander("Hapus target"):
                    st.selectbox("Pilih target", list(range(len(d["target"]))), key="h_tgt",
                                 format_func=lambda i: d["target"][i]["nama"])
                    st.button("Hapus target", on_click=aksi_hapus_tgt)
        with kanan:
            with st.container(border=True):
                st.markdown("**Tambah target baru**")
                form_target("g")
                st.button("Simpan Target", type="primary", on_click=aksi_target)
    else:
        st.subheader("Class Diagram (rancangan umum)")
        gambar(STAT, 760)
        st.subheader("Diagram Class + Objek (sesuai data yang kamu input)")
        st.caption("Kotak class berisi atribut (-) dan method (+). Kotak objek berisi nilai atribut dari inputmu, "
                   "dan panah putus-putus menunjukkan objek dibuat dari class mana.")
        gambar(diagram_dinamis(d["objek"]), 900)
        st.subheader("Tabel Objek, Class, Atribut, dan Method")
        st.dataframe(pd.DataFrame([{"Objek": o["objek"], "Class": o["class"],
                                    "Atribut = Nilai": "; ".join(f"{k} = {v}" for k, v in o["atribut"].items()),
                                    "Method": ", ".join(o["method"])} for o in d["objek"]]), hide_index=True)


if "sistem" in S:
    halaman_dashboard()
else:
    halaman_daftar()
