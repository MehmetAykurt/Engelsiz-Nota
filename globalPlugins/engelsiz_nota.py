# Engelsiz Nota NVDA eklentisi
# Telif Hakkı (C) 2026 Mehmet Aykurt
# Tarih: 1 Mayıs 2026
# Geliştirici: Mehmet Aykurt <m.aykurt38@gmail.com>
#
# Bu eklenti, görme engelli bireylerin Engelsiz Nota e-katalog sistemine NVDA üzerinden
# hızlı ve erişilebilir bir şekilde ulaşabilmesi amacıyla büyük bir özenle geliştirilmiştir.
# Özgür Yazılım Vakfı tarafından yayımlanan GNU Genel Kamu Lisansı (GPL) koşulları
# altında açık kaynak kodlu olarak dağıtılmaktadır.

import globalPluginHandler
import wx
import gui
import urllib.request
import urllib.parse
import re
import threading
import webbrowser
import ui
import os
import json
import html
import globalVars
from logHandler import log


EKLENTI_ADI = "Engelsiz Nota"
ANA_SITE_ADRESI = "https://www.engelsiznota.org"
ESERLER_ADRESI = ANA_SITE_ADRESI + "/eserler"
KULLANICI_ARACISI = "Mozilla/5.0 (Windows NT 10.0; NVDA; Engelsiz Nota eklentisi)"
FAVORILER_DOSYASI = os.path.join(globalVars.appArgs.configPath, "engelsiznota_favoriler.json")


def html_metnini_temizle(metin):
    """HTML içeriğinden gelen kısa metinleri NVDA ile okunabilir düz metne çevirir."""
    if not metin:
        return ""

    metin = re.sub(r"<br\s*/?>", " ", metin, flags=re.IGNORECASE)
    metin = re.sub(r"<[^>]+>", "", metin)
    metin = html.unescape(metin)
    metin = metin.replace("\xa0", " ")
    return " ".join(metin.split()).strip()


def baglanti_adresini_duzenle(link):
    """Göreli veya mutlak bağlantıyı tam Engelsiz Nota bağlantısına dönüştürür."""
    if not link:
        return ESERLER_ADRESI
    return urllib.parse.urljoin(ANA_SITE_ADRESI, html.unescape(link.strip()))


def internetten_oku(url, timeout=12):
    """Sistem ağ ayarlarına saygı göstererek belirtilen adresin HTML içeriğini okur."""
    istek = urllib.request.Request(url, headers={"User-Agent": KULLANICI_ARACISI})
    with urllib.request.urlopen(istek, timeout=timeout) as yanit:
        kodlama = yanit.headers.get_content_charset() or "utf-8"
        return yanit.read().decode(kodlama, errors="replace")


def favori_kaydini_temizle(eser):
    """Favoriler dosyasındaki eski veya eksik kayıtları güvenli bir yapıya çevirir."""
    if not isinstance(eser, dict):
        return None

    isim = str(eser.get("isim", "")).strip()
    link = str(eser.get("link", "")).strip()
    if not isim or not link:
        return None

    return {
        "isim": isim,
        "besteci": str(eser.get("besteci", "Bilinmiyor")).strip() or "Bilinmiyor",
        "tur": str(eser.get("tur", "Bilinmiyor")).strip() or "Bilinmiyor",
        "calgi": str(eser.get("calgi", "Bilinmiyor")).strip() or "Bilinmiyor",
        "link": baglanti_adresini_duzenle(link),
    }


def favorileri_yukle():
    if not os.path.exists(FAVORILER_DOSYASI):
        return []

    try:
        with open(FAVORILER_DOSYASI, "r", encoding="utf-8") as f:
            veri = json.load(f)
    except Exception:
        log.exception("Engelsiz Nota favoriler dosyası okunamadı.")
        return []

    if not isinstance(veri, list):
        log.warning("Engelsiz Nota favoriler dosyası liste biçiminde değil.")
        return []

    favoriler = []
    gorulen_baglantilar = set()
    for kayit in veri:
        temiz_kayit = favori_kaydini_temizle(kayit)
        if not temiz_kayit:
            continue
        if temiz_kayit["link"] in gorulen_baglantilar:
            continue
        favoriler.append(temiz_kayit)
        gorulen_baglantilar.add(temiz_kayit["link"])

    return favoriler


def favorileri_kaydet(liste):
    try:
        os.makedirs(os.path.dirname(FAVORILER_DOSYASI), exist_ok=True)
        temiz_liste = []
        gorulen_baglantilar = set()

        for eser in liste:
            temiz_eser = favori_kaydini_temizle(eser)
            if not temiz_eser:
                continue
            if temiz_eser["link"] in gorulen_baglantilar:
                continue
            temiz_liste.append(temiz_eser)
            gorulen_baglantilar.add(temiz_eser["link"])

        gecici_dosya = FAVORILER_DOSYASI + ".tmp"
        with open(gecici_dosya, "w", encoding="utf-8") as f:
            json.dump(temiz_liste, f, ensure_ascii=False, indent=4)
        os.replace(gecici_dosya, FAVORILER_DOSYASI)
        return True
    except Exception:
        log.exception("Engelsiz Nota favoriler dosyası kaydedilemedi.")
        return False


class DetayPenceresi(wx.Dialog):
    def __init__(self, parent, eser):
        self.eser = favori_kaydini_temizle(eser) or {
            "isim": "Bilinmeyen eser",
            "besteci": "Bilinmiyor",
            "tur": "Bilinmiyor",
            "calgi": "Bilinmiyor",
            "link": ESERLER_ADRESI,
        }
        super(DetayPenceresi, self).__init__(parent, title="Eser detayı - " + self.eser["isim"])

        self.favoriler = favorileri_yukle()
        self.favoride_mi = any(f["link"] == self.eser["link"] for f in self.favoriler)
        self.eser_linki = baglanti_adresini_duzenle(self.eser["link"])

        duzen = wx.BoxSizer(wx.VERTICAL)

        self.bilgi_metni = "Eser adı: " + self.eser["isim"] + "\n"
        self.bilgi_metni += "Besteci: " + self.eser["besteci"] + "\n"
        self.bilgi_metni += "Eser türü: " + self.eser["tur"] + "\n"
        self.bilgi_metni += "Çalgı türü: " + self.eser["calgi"] + "\n\n"
        self.bilgi_metni += "Bu eserin Braille (kabartma) nota dosyalarını bilgisayarınıza indirmek için lütfen aşağıdaki 'Tarayıcıda aç' düğmesini kullanarak Engelsiz Nota sitesine gidiniz. İndirme işlemi için siteye giriş yapmanız gerekir."

        self.metin_kutusu = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY, value=self.bilgi_metni)
        duzen.Add(self.metin_kutusu, 1, wx.ALL | wx.EXPAND, 5)

        buton_duzeni = wx.BoxSizer(wx.HORIZONTAL)

        tarayici_butonu = wx.Button(self, label="Tarayıcıda &aç")
        tarayici_butonu.Bind(wx.EVT_BUTTON, self.tarayicida_ac)
        buton_duzeni.Add(tarayici_butonu, 0, wx.ALL, 5)

        kopyala_butonu = wx.Button(self, label="Bilgileri &kopyala")
        kopyala_butonu.Bind(wx.EVT_BUTTON, self.bilgileri_kopyala)
        buton_duzeni.Add(kopyala_butonu, 0, wx.ALL, 5)

        fav_etiket = "Favorilerden &çıkar" if self.favoride_mi else "&Favorilere ekle"
        self.fav_butonu = wx.Button(self, label=fav_etiket)
        self.fav_butonu.Bind(wx.EVT_BUTTON, self.favori_islem)
        buton_duzeni.Add(self.fav_butonu, 0, wx.ALL, 5)

        kapat_butonu = wx.Button(self, wx.ID_CANCEL, label="Kapa&t")
        buton_duzeni.Add(kapat_butonu, 0, wx.ALL, 5)

        duzen.Add(buton_duzeni, 0, wx.CENTER)

        self.SetSizer(duzen)
        self.SetSize((700, 400))
        self.CenterOnParent()
        self.metin_kutusu.SetFocus()

    def tarayicida_ac(self, event):
        try:
            if not webbrowser.open(self.eser_linki):
                ui.message("Tarayıcı açılamadı.")
        except Exception:
            log.exception("Engelsiz Nota eser bağlantısı tarayıcıda açılamadı.")
            ui.message("Tarayıcı açılamadı.")

    def bilgileri_kopyala(self, event):
        if not wx.TheClipboard.Open():
            ui.message("Pano açılamadı.")
            return

        try:
            wx.TheClipboard.SetData(wx.TextDataObject(self.bilgi_metni))
            ui.message("Eser bilgileri panoya kopyalandı.")
        except Exception:
            log.exception("Engelsiz Nota eser bilgileri panoya kopyalanamadı.")
            ui.message("Eser bilgileri panoya kopyalanamadı.")
        finally:
            wx.TheClipboard.Close()

    def favori_islem(self, event):
        if self.favoride_mi:
            yeni_favoriler = [f for f in self.favoriler if f["link"] != self.eser["link"]]
            if favorileri_kaydet(yeni_favoriler):
                self.favoriler = yeni_favoriler
                self.favoride_mi = False
                self.fav_butonu.SetLabel("&Favorilere ekle")
                ui.message("Eser favorilerden çıkarıldı.")
            else:
                ui.message("Favoriler dosyası güncellenemedi.")
            return

        yeni_favoriler = [f for f in self.favoriler if f["link"] != self.eser["link"]]
        yeni_favoriler.append(self.eser)
        if favorileri_kaydet(yeni_favoriler):
            self.favoriler = yeni_favoriler
            self.favoride_mi = True
            self.fav_butonu.SetLabel("Favorilerden &çıkar")
            ui.message("Eser favorilere eklendi.")
        else:
            ui.message("Favoriler dosyası güncellenemedi.")


class FavorilerPenceresi(wx.Dialog):
    def __init__(self, parent):
        super(FavorilerPenceresi, self).__init__(parent, title="Engelsiz Nota - Favorilerim")
        self.favoriler = favorileri_yukle()

        duzen = wx.BoxSizer(wx.VERTICAL)

        etiket = wx.StaticText(self, label="Favori eserleriniz:")
        duzen.Add(etiket, 0, wx.ALL, 5)

        self.liste = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.liste.InsertColumn(0, "Eser adı", width=300)
        self.liste.InsertColumn(1, "Besteci", width=150)
        self.liste.InsertColumn(2, "Eser türü", width=120)
        self.liste.InsertColumn(3, "Çalgı", width=120)

        self.listeyi_doldur()

        duzen.Add(self.liste, 1, wx.ALL | wx.EXPAND, 5)
        self.liste.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.eser_secildi)

        kapat_butonu = wx.Button(self, wx.ID_CANCEL, label="&Kapat")
        duzen.Add(kapat_butonu, 0, wx.ALL | wx.CENTER, 5)

        self.SetSizer(duzen)
        self.SetSize((800, 500))
        self.CenterOnParent()
        self.liste.SetFocus()

    def listeyi_doldur(self):
        self.liste.DeleteAllItems()
        if not self.favoriler:
            self.liste.InsertItem(0, "Henüz favorilere eklenmiş bir eser bulunmuyor.")
            self.liste.SetItemState(0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
            return

        for index, eser in enumerate(self.favoriler):
            self.liste.InsertItem(index, eser["isim"])
            self.liste.SetItem(index, 1, eser["besteci"])
            self.liste.SetItem(index, 2, eser["tur"])
            self.liste.SetItem(index, 3, eser["calgi"])
        self.liste.SetItemState(0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)

    def eser_secildi(self, event):
        index = event.GetIndex()
        if self.favoriler and index < len(self.favoriler):
            eser = self.favoriler[index]
            detay = DetayPenceresi(self, eser)
            detay.ShowModal()
            detay.Destroy()

            self.favoriler = favorileri_yukle()
            self.listeyi_doldur()


class EngelsizNotaPenceresi(wx.Dialog):
    def __init__(self, parent):
        super(EngelsizNotaPenceresi, self).__init__(parent, title="Engelsiz Nota - Veriler yükleniyor...")

        self.arama_sonuclari = []
        self._kapaniyor = False
        self._son_arama_kimligi = 0

        self.ana_duzen = wx.BoxSizer(wx.VERTICAL)

        etiket_eser_adi = wx.StaticText(self, label="&Eser adı:")
        self.ana_duzen.Add(etiket_eser_adi, 0, wx.ALL, 5)
        self.eser_adi_kutusu = wx.TextCtrl(self)
        self.ana_duzen.Add(self.eser_adi_kutusu, 0, wx.ALL | wx.EXPAND, 5)

        etiket_kurum = wx.StaticText(self, label="Alındığı kuru&m:")
        self.ana_duzen.Add(etiket_kurum, 0, wx.ALL, 5)
        self.kurum_kutusu = wx.Choice(self, choices=["Yükleniyor..."])
        self.ana_duzen.Add(self.kurum_kutusu, 0, wx.ALL | wx.EXPAND, 5)

        etiket_besteci = wx.StaticText(self, label="&Besteci:")
        self.ana_duzen.Add(etiket_besteci, 0, wx.ALL, 5)
        self.besteci_kutusu = wx.Choice(self, choices=["Yükleniyor..."])
        self.ana_duzen.Add(self.besteci_kutusu, 0, wx.ALL | wx.EXPAND, 5)

        etiket_eser_turu = wx.StaticText(self, label="Eser &türü:")
        self.ana_duzen.Add(etiket_eser_turu, 0, wx.ALL, 5)
        self.eser_turu_kutusu = wx.Choice(self, choices=["Yükleniyor..."])
        self.ana_duzen.Add(self.eser_turu_kutusu, 0, wx.ALL | wx.EXPAND, 5)

        etiket_calgi = wx.StaticText(self, label="&Çalgı türü:")
        self.ana_duzen.Add(etiket_calgi, 0, wx.ALL, 5)
        self.calgi_kutusu = wx.Choice(self, choices=["Yükleniyor..."])
        self.ana_duzen.Add(self.calgi_kutusu, 0, wx.ALL | wx.EXPAND, 5)

        butonlar_duzeni = wx.BoxSizer(wx.HORIZONTAL)

        self.ara_butonu = wx.Button(self, label="&Ara")
        self.ara_butonu.Bind(wx.EVT_BUTTON, self.arama_yap)
        butonlar_duzeni.Add(self.ara_butonu, 1, wx.ALL | wx.EXPAND, 5)

        self.temizle_butonu = wx.Button(self, label="Temi&zle")
        self.temizle_butonu.Bind(wx.EVT_BUTTON, self.formu_temizle)
        butonlar_duzeni.Add(self.temizle_butonu, 1, wx.ALL | wx.EXPAND, 5)

        self.ana_duzen.Add(butonlar_duzeni, 0, wx.ALL | wx.EXPAND, 0)

        etiket_liste = wx.StaticText(self, label="Arama sonuçları:")
        self.ana_duzen.Add(etiket_liste, 0, wx.ALL, 5)

        self.sonuclar_listesi = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.sonuclar_listesi.InsertColumn(0, "Eser adı", width=300)
        self.sonuclar_listesi.InsertColumn(1, "Besteci", width=150)
        self.sonuclar_listesi.InsertColumn(2, "Eser türü", width=120)
        self.sonuclar_listesi.InsertColumn(3, "Çalgı", width=120)
        self.sonuclar_listesi.InsertItem(0, "Arama yapmak için Ara düğmesine basınız.")
        self.sonuclar_listesi.SetItemState(0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
        self.ana_duzen.Add(self.sonuclar_listesi, 1, wx.ALL | wx.EXPAND, 5)

        self.sonuclar_listesi.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.eser_secildi)

        etiket_sayfa = wx.StaticText(self, label="Sayfa (&P):")
        self.ana_duzen.Add(etiket_sayfa, 0, wx.ALL, 5)

        self.sayfa_kutusu = wx.SpinCtrl(self, value="1", min=1, max=1000)
        self.ana_duzen.Add(self.sayfa_kutusu, 0, wx.ALL | wx.EXPAND, 5)
        self.sayfa_kutusu.Bind(wx.EVT_SPINCTRL, self.sayfa_degistirildi)

        self.kapat_butonu = wx.Button(self, wx.ID_CANCEL, label="&Kapat")
        self.kapat_butonu.Bind(wx.EVT_BUTTON, self.kapat)
        self.ana_duzen.Add(self.kapat_butonu, 0, wx.ALL | wx.CENTER, 5)
        self.Bind(wx.EVT_CLOSE, self.kapat)
        self.Bind(wx.EVT_WINDOW_DESTROY, self.pencere_yok_ediliyor)

        self.SetSizerAndFit(self.ana_duzen)
        self.eser_adi_kutusu.SetFocus()

        self.is_parcacigi_baslat(self.verileri_cek)

    def is_parcacigi_baslat(self, hedef, args=()):
        is_parcacigi = threading.Thread(target=hedef, args=args, daemon=True)
        is_parcacigi.start()
        return is_parcacigi

    def pencere_yok_ediliyor(self, event):
        self._kapaniyor = True
        event.Skip()

    def pencere_kullanilabilir_mi(self):
        try:
            return not self._kapaniyor and not self.IsBeingDeleted()
        except RuntimeError:
            return False

    def kapat(self, event):
        self._kapaniyor = True
        try:
            if self.IsModal():
                self.EndModal(wx.ID_CANCEL)
            else:
                self.Destroy()
        except Exception:
            log.exception("Engelsiz Nota penceresi kapatılırken hata oluştu.")
            try:
                self.Destroy()
            except Exception:
                pass

    def formu_temizle(self, event):
        if not self.pencere_kullanilabilir_mi():
            return

        self._son_arama_kimligi += 1
        self.ara_butonu.Enable(True)
        self.sayfa_kutusu.Enable(True)

        self.eser_adi_kutusu.Clear()

        for kutu in (self.kurum_kutusu, self.besteci_kutusu, self.eser_turu_kutusu, self.calgi_kutusu):
            if kutu.GetCount() > 0:
                kutu.SetSelection(0)

        self.sayfa_kutusu.SetValue(1)

        self.sonuclar_listesi.DeleteAllItems()
        self.arama_sonuclari.clear()
        self.sonuclar_listesi.InsertItem(0, "Arama yapmak için Ara düğmesine basınız.")
        self.sonuclar_listesi.SetItemState(0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)

        self.eser_adi_kutusu.SetFocus()

    def secenekleri_ayikla(self, html_icerik, select_id):
        secenekler_listesi = []
        select_deseni = r'<select\b[^>]*\bid=["\']' + re.escape(select_id) + r'["\'][^>]*>(.*?)</select>'
        select_match = re.search(select_deseni, html_icerik, re.DOTALL | re.IGNORECASE)

        if select_match:
            options_blogu = select_match.group(1)
            option_deseni = r'<option\b[^>]*\bvalue=["\']([^"\']*)["\'][^>]*>(.*?)</option>'
            secenekler = re.findall(option_deseni, options_blogu, re.DOTALL | re.IGNORECASE)

            for deger, gorunen_isim in secenekler:
                gorunen_isim = html_metnini_temizle(gorunen_isim)
                deger = html.unescape(deger.strip()) or "All"
                if gorunen_isim:
                    secenekler_listesi.append((gorunen_isim, deger))

        if not secenekler_listesi:
            secenekler_listesi = [("- Tümü -", "All")]

        return secenekler_listesi

    def verileri_cek(self):
        try:
            html_icerik = internetten_oku(ESERLER_ADRESI, timeout=12)

            kurumlar = self.secenekleri_ayikla(html_icerik, "edit-kurum")
            besteciler = self.secenekleri_ayikla(html_icerik, "edit-bestecisi")
            eser_turleri = self.secenekleri_ayikla(html_icerik, "edit-field-eser-t-r-target-id")
            calgilar = self.secenekleri_ayikla(html_icerik, "edit-calgi")

            wx.CallAfter(self.arayuzu_guncelle_guvenli, kurumlar, besteciler, eser_turleri, calgilar)

        except Exception:
            log.exception("Engelsiz Nota katalog seçenekleri alınamadı.")
            hata_listesi = [("Bağlantı hatası!", "All")]
            wx.CallAfter(self.arayuzu_guncelle_guvenli, hata_listesi, hata_listesi, hata_listesi, hata_listesi)

    def kutuyu_doldur(self, kutu, veri_listesi):
        kutu.Freeze()
        try:
            kutu.Clear()
            for gorunen_isim, deger in veri_listesi:
                kutu.Append(gorunen_isim, deger)
            if kutu.GetCount() > 0:
                kutu.SetSelection(0)
        finally:
            kutu.Thaw()

    def arayuzu_guncelle_guvenli(self, kurumlar, besteciler, eser_turleri, calgilar):
        if not self.pencere_kullanilabilir_mi():
            return
        self.arayuzu_guncelle(kurumlar, besteciler, eser_turleri, calgilar)

    def arayuzu_guncelle(self, kurumlar, besteciler, eser_turleri, calgilar):
        self.SetTitle("Engelsiz Nota e-kütüphane")

        self.kutuyu_doldur(self.kurum_kutusu, kurumlar)
        self.kutuyu_doldur(self.besteci_kutusu, besteciler)
        self.kutuyu_doldur(self.eser_turu_kutusu, eser_turleri)
        self.kutuyu_doldur(self.calgi_kutusu, calgilar)

        self.eser_adi_kutusu.SetFocus()

    def sayfa_degistirildi(self, event):
        self.arama_tetikle(sifirla=False)

    def arama_yap(self, event):
        self.arama_tetikle(sifirla=True)

    def secili_degeri_al(self, kutu):
        secim = kutu.GetSelection()
        if secim == wx.NOT_FOUND or kutu.GetCount() == 0:
            return "All"
        deger = kutu.GetClientData(secim)
        return deger if deger is not None else "All"

    def arama_tetikle(self, sifirla=True):
        if not self.pencere_kullanilabilir_mi():
            return

        if sifirla:
            self.sayfa_kutusu.SetValue(1)

        self._son_arama_kimligi += 1
        arama_kimligi = self._son_arama_kimligi
        sayfa_no = self.sayfa_kutusu.GetValue() - 1

        self.ara_butonu.Enable(False)
        self.sayfa_kutusu.Enable(False)

        self.sonuclar_listesi.DeleteAllItems()
        self.sonuclar_listesi.InsertItem(0, "Arama yapılıyor, lütfen bekleyin...")
        self.sonuclar_listesi.SetItemState(0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
        self.sonuclar_listesi.SetFocus()

        secilen_eser_adi = self.eser_adi_kutusu.GetValue().strip()
        secilen_kurum = self.secili_degeri_al(self.kurum_kutusu)
        secilen_besteci = self.secili_degeri_al(self.besteci_kutusu)
        secilen_eser_turu = self.secili_degeri_al(self.eser_turu_kutusu)
        secilen_calgi = self.secili_degeri_al(self.calgi_kutusu)

        self.is_parcacigi_baslat(
            self.sonuclari_cek,
            (arama_kimligi, secilen_eser_adi, secilen_kurum, secilen_besteci, secilen_eser_turu, secilen_calgi, sayfa_no),
        )

    def tablo_hucresini_ayikla(self, satir, header_id):
        hucre_deseni = r'<td\b[^>]*headers=["\'][^"\']*' + re.escape(header_id) + r'[^"\']*["\'][^>]*>(.*?)</td>'
        hucre_match = re.search(hucre_deseni, satir, re.DOTALL | re.IGNORECASE)
        if not hucre_match:
            return ""
        return html_metnini_temizle(hucre_match.group(1))

    def eserleri_ayikla(self, html_icerik):
        tbody_match = re.search(r"<tbody\b[^>]*>(.*?)</tbody>", html_icerik, re.DOTALL | re.IGNORECASE)
        eserler = []

        if not tbody_match:
            return eserler

        tbody = tbody_match.group(1)
        satirlar = re.split(r"<tr\b", tbody, flags=re.IGNORECASE)

        for satir in satirlar[1:]:
            title_match = re.search(
                r'<td\b[^>]*headers=["\'][^"\']*view-title-table-column[^"\']*["\'][^>]*>.*?'
                r'<a\b[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>',
                satir,
                re.DOTALL | re.IGNORECASE,
            )
            if not title_match:
                continue

            link = html.unescape(title_match.group(1).strip())
            isim = html_metnini_temizle(title_match.group(2))
            if not isim:
                continue

            besteci = self.tablo_hucresini_ayikla(satir, "view-field-bestecisi-table-column") or "Bilinmiyor"
            tur = self.tablo_hucresini_ayikla(satir, "view-field-eser-t-r-table-column") or "Bilinmiyor"
            calgi = (
                self.tablo_hucresini_ayikla(satir, "view-field-alg-t-r-table-column")
                or self.tablo_hucresini_ayikla(satir, "view-field-calgi-table-column")
                or "Bilinmiyor"
            )

            eserler.append({
                "isim": isim,
                "besteci": besteci,
                "tur": tur,
                "calgi": calgi,
                "link": link,
            })

        return eserler

    def sonuclari_cek(self, arama_kimligi, sec_eser_adi, sec_kurum, sec_besteci, sec_eser_turu, sec_calgi, sayfa_no):
        parametreler = {
            "title": sec_eser_adi,
            "kurum": sec_kurum,
            "bestecisi": sec_besteci,
            "field_eser_t_r__target_id": sec_eser_turu,
            "calgi": sec_calgi,
            "page": str(sayfa_no),
        }

        sorgu = urllib.parse.urlencode(parametreler)
        tam_url = ESERLER_ADRESI + "?" + sorgu

        try:
            html_icerik = internetten_oku(tam_url, timeout=15)
            eserler = self.eserleri_ayikla(html_icerik)
            wx.CallAfter(self.sonuclari_goster_guvenli, arama_kimligi, eserler, None)
        except Exception:
            log.exception("Engelsiz Nota arama sonuçları alınamadı.")
            wx.CallAfter(
                self.sonuclari_goster_guvenli,
                arama_kimligi,
                [],
                "Bağlantı hatası nedeniyle arama sonuçları alınamadı.",
            )

    def sonuclari_goster_guvenli(self, arama_kimligi, eser_listesi, hata_mesaji):
        if not self.pencere_kullanilabilir_mi():
            return
        if arama_kimligi != self._son_arama_kimligi:
            return
        self.sonuclari_goster(eser_listesi, hata_mesaji)

    def sonuclari_goster(self, eser_listesi, hata_mesaji=None):
        self.ara_butonu.Enable(True)
        self.sayfa_kutusu.Enable(True)
        self.sonuclar_listesi.DeleteAllItems()
        self.arama_sonuclari.clear()

        if hata_mesaji:
            self.sonuclar_listesi.InsertItem(0, hata_mesaji)
        elif not eser_listesi:
            self.sonuclar_listesi.InsertItem(0, "Aradığınız kriterlere veya sayfaya uygun eser bulunamadı.")
        else:
            self.arama_sonuclari = eser_listesi
            for index, eser in enumerate(eser_listesi):
                self.sonuclar_listesi.InsertItem(index, eser["isim"])
                self.sonuclar_listesi.SetItem(index, 1, eser["besteci"])
                self.sonuclar_listesi.SetItem(index, 2, eser["tur"])
                self.sonuclar_listesi.SetItem(index, 3, eser["calgi"])

        self.sonuclar_listesi.SetItemState(0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
        self.sonuclar_listesi.SetFocus()

    def eser_secildi(self, event):
        index = event.GetIndex()
        if self.arama_sonuclari and index < len(self.arama_sonuclari):
            eser = self.arama_sonuclari[index]
            detay_penceresi = DetayPenceresi(self, eser)
            detay_penceresi.ShowModal()
            detay_penceresi.Destroy()


class GlobalPlugin(globalPluginHandler.GlobalPlugin):

    def __init__(self):
        super(GlobalPlugin, self).__init__()
        self.tools_menu = None
        self.engelsiznota_menu = None
        self.engelsiznota_menu_item = None
        self.menu_olustur()

    def menu_olustur(self):
        self.tools_menu = gui.mainFrame.sysTrayIcon.toolsMenu
        self.engelsiznota_menu = wx.Menu()

        self.item_engelsiznota = self.engelsiznota_menu.Append(wx.ID_ANY, "Engelsiz Nota'da &Ara...\tCtrl+Shift+E", "Engelsiz Nota arama penceresini açar")
        gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.menu_engelsiznota_ac, self.item_engelsiznota)

        self.item_favoriler = self.engelsiznota_menu.Append(wx.ID_ANY, "&Favorilerim", "Favori eserlerinizi listeler")
        gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.menu_favoriler_ac, self.item_favoriler)

        self.item_yardim = self.engelsiznota_menu.Append(wx.ID_ANY, "&Yardım", "Eklenti kullanım kılavuzunu açar")
        gui.mainFrame.sysTrayIcon.Bind(wx.EVT_MENU, self.menu_yardim_ac, self.item_yardim)

        self.engelsiznota_menu_item = self.tools_menu.AppendSubMenu(self.engelsiznota_menu, "En&gelsiz Nota")

    def terminate(self):
        try:
            if getattr(self, "item_engelsiznota", None):
                gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, id=self.item_engelsiznota.GetId())
            if getattr(self, "item_favoriler", None):
                gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, id=self.item_favoriler.GetId())
            if getattr(self, "item_yardim", None):
                gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, id=self.item_yardim.GetId())
            if self.tools_menu and self.engelsiznota_menu_item:
                self.tools_menu.Remove(self.engelsiznota_menu_item)
        except Exception:
            log.exception("Engelsiz Nota araçlar menüsünden kaldırılırken hata oluştu.")
        super(GlobalPlugin, self).terminate()

    def menu_engelsiznota_ac(self, event):
        self.engelsiznota_pencereyi_baslat()

    def menu_favoriler_ac(self, event):
        def calistir():
            pencere = FavorilerPenceresi(gui.mainFrame)
            pencere.ShowModal()
            pencere.Destroy()
        wx.CallAfter(calistir)

    def menu_yardim_ac(self, event):
        kok_klasor = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        yardim_yollari = [
            os.path.join(kok_klasor, "doc", "tr", "readme.html"),
            os.path.join(kok_klasor, "doc", "readme.html"),
        ]

        for yardim_yolu in yardim_yollari:
            if os.path.exists(yardim_yolu):
                try:
                    os.startfile(yardim_yolu)
                    return
                except Exception:
                    log.exception("Engelsiz Nota yardım dosyası açılamadı.")
                    ui.message("Yardım dosyası tarayıcıda açılamadı.")
                    return

        ui.message("Yardım dosyası doc/tr klasöründe bulunamadı.")

    def script_engelsiznotaAc(self, gesture):
        self.engelsiznota_pencereyi_baslat()

    script_engelsiznotaAc.__doc__ = "Engelsiz Nota arama penceresini açar."
    script_engelsiznotaAc.category = "Engelsiz Nota"

    def engelsiznota_pencereyi_baslat(self):
        def calistir():
            pencere = EngelsizNotaPenceresi(gui.mainFrame)
            pencere.ShowModal()
            pencere.Destroy()
        wx.CallAfter(calistir)

    __gestures = {
        "kb:control+shift+e": "engelsiznotaAc"
    }
