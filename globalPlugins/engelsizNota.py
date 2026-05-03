# Engelsiz Nota NVDA Eklentisi
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
import globalVars

FAVORILER_DOSYASI = os.path.join(globalVars.appArgs.configPath, "engelsiznota_favoriler.json")

def favorileri_yukle():
    if os.path.exists(FAVORILER_DOSYASI):
        try:
            with open(FAVORILER_DOSYASI, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def favorileri_kaydet(liste):
    try:
        with open(FAVORILER_DOSYASI, "w", encoding="utf-8") as f:
            json.dump(liste, f, ensure_ascii=False, indent=4)
    except Exception:
        pass

class DetayPenceresi(wx.Dialog):
    def __init__(self, parent, eser):
        super(DetayPenceresi, self).__init__(parent, title="Eser Detayı - " + eser["isim"])
        self.eser = eser
        self.favoriler = favorileri_yukle()
        self.favoride_mi = any(f["link"] == self.eser["link"] for f in self.favoriler)
        
        link = eser["link"]
        if link.startswith("/"):
            self.eser_linki = "https://www.engelsiznota.org" + link
        elif not link.startswith("http"):
            self.eser_linki = "https://www.engelsiznota.org/" + link
        else:
            self.eser_linki = link
            
        duzen = wx.BoxSizer(wx.VERTICAL)
        
        self.bilgi_metni = "Eser Adı: " + eser["isim"] + "\n"
        self.bilgi_metni += "Bestecisi: " + eser["besteci"] + "\n"
        self.bilgi_metni += "Eser Türü: " + eser["tur"] + "\n"
        self.bilgi_metni += "Çalgı Türü: " + eser["calgi"] + "\n\n"
        self.bilgi_metni += "Bu eserin braille (kabartma) nota dosyalarını bilgisayarınıza indirmek için lütfen aşağıdaki 'Tarayıcıda Aç' butonunu kullanarak Engelsiz Nota web sitesine gidiniz. İndirme işlemi için siteye giriş yapmanız gerekmektedir."
        
        self.metin_kutusu = wx.TextCtrl(self, style=wx.TE_MULTILINE | wx.TE_READONLY, value=self.bilgi_metni)
        duzen.Add(self.metin_kutusu, 1, wx.ALL | wx.EXPAND, 5)
        
        buton_duzeni = wx.BoxSizer(wx.HORIZONTAL)
        
        tarayici_butonu = wx.Button(self, label="Tarayıcıda &Aç")
        tarayici_butonu.Bind(wx.EVT_BUTTON, self.tarayicida_ac)
        buton_duzeni.Add(tarayici_butonu, 0, wx.ALL, 5)
        
        kopyala_butonu = wx.Button(self, label="Bilgileri &Kopyala")
        kopyala_butonu.Bind(wx.EVT_BUTTON, self.bilgileri_kopyala)
        buton_duzeni.Add(kopyala_butonu, 0, wx.ALL, 5)
        
        fav_etiket = "Favorilerden &Çıkar" if self.favoride_mi else "&Favorilere Ekle"
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
        webbrowser.open(self.eser_linki)

    def bilgileri_kopyala(self, event):
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self.bilgi_metni))
            wx.TheClipboard.Close()
            ui.message("Eser bilgileri panoya kopyalandı.")

    def favori_islem(self, event):
        if self.favoride_mi:
            self.favoriler = [f for f in self.favoriler if f["link"] != self.eser["link"]]
            ui.message("Eser favorilerden çıkarıldı.")
            self.fav_butonu.SetLabel("&Favorilere Ekle")
        else:
            self.favoriler.append(self.eser)
            ui.message("Eser favorilere eklendi.")
            self.fav_butonu.SetLabel("Favorilerden &Çıkar")
            
        favorileri_kaydet(self.favoriler)
        self.favoride_mi = not self.favoride_mi

class FavorilerPenceresi(wx.Dialog):
    def __init__(self, parent):
        super(FavorilerPenceresi, self).__init__(parent, title="Engelsiz Nota - Favorilerim")
        self.favoriler = favorileri_yukle()
        
        duzen = wx.BoxSizer(wx.VERTICAL)
        
        etiket = wx.StaticText(self, label="Favori Eserleriniz:")
        duzen.Add(etiket, 0, wx.ALL, 5)
        
        self.liste = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.liste.InsertColumn(0, "Eser Adı", width=300)
        self.liste.InsertColumn(1, "Bestecisi", width=150)
        self.liste.InsertColumn(2, "Eser Türü", width=120)
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
        else:
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
        super(EngelsizNotaPenceresi, self).__init__(parent, title="Engelsiz Nota - Veriler Yükleniyor...")
        
        self.arama_sonuclari = []
        
        self.ana_duzen = wx.BoxSizer(wx.VERTICAL)
        
        etiket_eser_adi = wx.StaticText(self, label="&Eser Adı:")
        self.ana_duzen.Add(etiket_eser_adi, 0, wx.ALL, 5)
        self.eser_adi_kutusu = wx.TextCtrl(self)
        self.ana_duzen.Add(self.eser_adi_kutusu, 0, wx.ALL | wx.EXPAND, 5)
        
        etiket_kurum = wx.StaticText(self, label="Alındığı Kuru&m:")
        self.ana_duzen.Add(etiket_kurum, 0, wx.ALL, 5)
        self.kurum_kutusu = wx.Choice(self, choices=["Yükleniyor..."])
        self.ana_duzen.Add(self.kurum_kutusu, 0, wx.ALL | wx.EXPAND, 5)
        
        etiket_besteci = wx.StaticText(self, label="&Bestecisi:")
        self.ana_duzen.Add(etiket_besteci, 0, wx.ALL, 5)
        self.besteci_kutusu = wx.Choice(self, choices=["Yükleniyor..."])
        self.ana_duzen.Add(self.besteci_kutusu, 0, wx.ALL | wx.EXPAND, 5)
        
        etiket_eser_turu = wx.StaticText(self, label="Eser &Türü:")
        self.ana_duzen.Add(etiket_eser_turu, 0, wx.ALL, 5)
        self.eser_turu_kutusu = wx.Choice(self, choices=["Yükleniyor..."])
        self.ana_duzen.Add(self.eser_turu_kutusu, 0, wx.ALL | wx.EXPAND, 5)
        
        etiket_calgi = wx.StaticText(self, label="&Çalgı Türü:")
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
        
        etiket_liste = wx.StaticText(self, label="Arama Sonuçları:")
        self.ana_duzen.Add(etiket_liste, 0, wx.ALL, 5)
        
        self.sonuclar_listesi = wx.ListCtrl(self, style=wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.sonuclar_listesi.InsertColumn(0, "Eser Adı", width=300)
        self.sonuclar_listesi.InsertColumn(1, "Bestecisi", width=150)
        self.sonuclar_listesi.InsertColumn(2, "Eser Türü", width=120)
        self.sonuclar_listesi.InsertColumn(3, "Çalgı", width=120)
        self.sonuclar_listesi.InsertItem(0, "Arama yapmak için Ara butonuna basınız.")
        self.sonuclar_listesi.SetItemState(0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
        self.ana_duzen.Add(self.sonuclar_listesi, 1, wx.ALL | wx.EXPAND, 5)
        
        self.sonuclar_listesi.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.eser_secildi)
        
        etiket_sayfa = wx.StaticText(self, label="Sayfa (&P):")
        self.ana_duzen.Add(etiket_sayfa, 0, wx.ALL, 5)
        
        self.sayfa_kutusu = wx.SpinCtrl(self, value="1", min=1, max=1000)
        self.ana_duzen.Add(self.sayfa_kutusu, 0, wx.ALL | wx.EXPAND, 5)
        self.sayfa_kutusu.Bind(wx.EVT_SPINCTRL, self.sayfa_degistirildi)
        
        self.kapat_butonu = wx.Button(self, wx.ID_CANCEL, label="&Kapat")
        self.ana_duzen.Add(self.kapat_butonu, 0, wx.ALL | wx.CENTER, 5)
        
        self.SetSizerAndFit(self.ana_duzen)
        self.eser_adi_kutusu.SetFocus()

        threading.Thread(target=self.verileri_cek).start()

    def formu_temizle(self, event):
        self.eser_adi_kutusu.Clear()
        
        if self.kurum_kutusu.GetCount() > 0:
            self.kurum_kutusu.SetSelection(0)
        if self.besteci_kutusu.GetCount() > 0:
            self.besteci_kutusu.SetSelection(0)
        if self.eser_turu_kutusu.GetCount() > 0:
            self.eser_turu_kutusu.SetSelection(0)
        if self.calgi_kutusu.GetCount() > 0:
            self.calgi_kutusu.SetSelection(0)
            
        self.sayfa_kutusu.SetValue(1)
        
        self.sonuclar_listesi.DeleteAllItems()
        self.arama_sonuclari.clear()
        self.sonuclar_listesi.InsertItem(0, "Arama yapmak için Ara butonuna basınız.")
        self.sonuclar_listesi.SetItemState(0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
        
        self.eser_adi_kutusu.SetFocus()

    def secenekleri_ayikla(self, html, select_id):
        secenekler_listesi = []
        hedef_id = 'id="' + select_id + '"'
        baslangic = html.find(hedef_id)
        
        if baslangic != -1:
            bitis = html.find('</select>', baslangic)
            if bitis != -1:
                options_blogu = html[baslangic:bitis]
                option_deseni = r'<option value="([^"]*)"[^>]*>(.*?)</option>'
                secenekler = re.findall(option_deseni, options_blogu, re.DOTALL | re.IGNORECASE)
                
                for deger, gorunen_isim in secenekler:
                    gorunen_isim = gorunen_isim.replace("&#039;", "'").replace("&amp;", "&").strip()
                    gorunen_isim = re.sub(r'<[^>]+>', '', gorunen_isim).strip()
                    if gorunen_isim and deger:
                        secenekler_listesi.append((gorunen_isim, deger))
                    
        if not secenekler_listesi:
            secenekler_listesi = [("- Tümü -", "All")]
            
        return secenekler_listesi

    def verileri_cek(self):
        url = "https://www.engelsiznota.org/eserler"
        try:
            istek = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            
            with opener.open(istek, timeout=10) as yanit:
                html_icerik = yanit.read().decode('utf-8')
            
            kurumlar = self.secenekleri_ayikla(html_icerik, "edit-kurum")
            besteciler = self.secenekleri_ayikla(html_icerik, "edit-bestecisi")
            eser_turleri = self.secenekleri_ayikla(html_icerik, "edit-field-eser-t-r-target-id")
            calgilar = self.secenekleri_ayikla(html_icerik, "edit-calgi")
            
            wx.CallAfter(self.arayuzu_guncelle, kurumlar, besteciler, eser_turleri, calgilar)
            
        except Exception:
            hata_listesi = [("Bağlantı hatası!", "All")]
            wx.CallAfter(self.arayuzu_guncelle, hata_listesi, hata_listesi, hata_listesi, hata_listesi)

    def kutuyu_doldur(self, kutu, veri_listesi):
        kutu.Freeze() 
        kutu.Clear()
        for gorunen_isim, deger in veri_listesi:
            kutu.Append(gorunen_isim, deger)
        kutu.SetSelection(0)
        kutu.Thaw() 

    def arayuzu_guncelle(self, kurumlar, besteciler, eser_turleri, calgilar):
        self.SetTitle("Engelsiz Nota E-Kütüphane")
        
        self.kutuyu_doldur(self.kurum_kutusu, kurumlar)
        self.kutuyu_doldur(self.besteci_kutusu, besteciler)
        self.kutuyu_doldur(self.eser_turu_kutusu, eser_turleri)
        self.kutuyu_doldur(self.calgi_kutusu, calgilar)
        
        self.eser_adi_kutusu.SetFocus()

    def sayfa_degistirildi(self, event):
        self.arama_tetikle(sifirla=False)

    def arama_yap(self, event):
        self.arama_tetikle(sifirla=True)

    def arama_tetikle(self, sifirla=True):
        if sifirla:
            self.sayfa_kutusu.SetValue(1)
        
        sayfa_no = self.sayfa_kutusu.GetValue() - 1
        
        self.sonuclar_listesi.DeleteAllItems()
        self.sonuclar_listesi.InsertItem(0, "Arama yapılıyor, lütfen bekleyin...")
        self.sonuclar_listesi.SetItemState(0, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED, wx.LIST_STATE_SELECTED | wx.LIST_STATE_FOCUSED)
        self.sonuclar_listesi.SetFocus()
        
        secilen_eser_adi = self.eser_adi_kutusu.GetValue()
        secilen_kurum = self.kurum_kutusu.GetClientData(self.kurum_kutusu.GetSelection())
        secilen_besteci = self.besteci_kutusu.GetClientData(self.besteci_kutusu.GetSelection())
        secilen_eser_turu = self.eser_turu_kutusu.GetClientData(self.eser_turu_kutusu.GetSelection())
        secilen_calgi = self.calgi_kutusu.GetClientData(self.calgi_kutusu.GetSelection())
        
        threading.Thread(target=self.sonuclari_cek, args=(
            secilen_eser_adi, secilen_kurum, secilen_besteci, secilen_eser_turu, secilen_calgi, sayfa_no
        )).start()

    def sonuclari_cek(self, sec_eser_adi, sec_kurum, sec_besteci, sec_eser_turu, sec_calgi, sayfa_no):
        temel_url = "https://www.engelsiznota.org/eserler"
        
        parametreler = {
            'title': sec_eser_adi,
            'kurum': sec_kurum,
            'bestecisi': sec_besteci,
            'field_eser_t_r__target_id': sec_eser_turu,
            'calgi': sec_calgi,
            'page': str(sayfa_no)
        }
        
        sorgu = urllib.parse.urlencode(parametreler)
        tam_url = temel_url + "?" + sorgu
        
        try:
            istek = urllib.request.Request(tam_url, headers={'User-Agent': 'Mozilla/5.0'})
            proxy_handler = urllib.request.ProxyHandler({})
            opener = urllib.request.build_opener(proxy_handler)
            
            with opener.open(istek, timeout=12) as yanit:
                html_icerik = yanit.read().decode('utf-8')
            
            tbody_match = re.search(r'<tbody>(.*?)</tbody>', html_icerik, re.DOTALL | re.IGNORECASE)
            eserler = []
            
            if tbody_match:
                tbody = tbody_match.group(1)
                satirlar = tbody.split('<tr')
                
                for satir in satirlar[1:]:
                    title_match = re.search(r'<td headers="view-title-table-column"[^>]*>.*?<a href="([^"]+)"[^>]*>(.*?)</a>', satir, re.DOTALL | re.IGNORECASE)
                    if not title_match:
                        continue
                    
                    link = title_match.group(1).strip()
                    isim = title_match.group(2).strip()
                    isim = re.sub(r'<[^>]+>', '', isim).replace("&#039;", "'").replace("&amp;", "&").strip()
                    
                    besteci_match = re.search(r'<td headers="view-field-bestecisi-table-column"[^>]*>(.*?)</td>', satir, re.DOTALL | re.IGNORECASE)
                    besteci = re.sub(r'<[^>]+>', '', besteci_match.group(1)).strip() if besteci_match else "Bilinmiyor"
                    
                    tur_match = re.search(r'<td headers="view-field-eser-t-r-table-column"[^>]*>(.*?)</td>', satir, re.DOTALL | re.IGNORECASE)
                    tur = re.sub(r'<[^>]+>', '', tur_match.group(1)).strip() if tur_match else "Bilinmiyor"
                    
                    calgi_match = re.search(r'<td headers="view-field-alg-t-r-table-column"[^>]*>(.*?)</td>', satir, re.DOTALL | re.IGNORECASE)
                    calgi = re.sub(r'<[^>]+>', '', calgi_match.group(1)).strip() if calgi_match else "Bilinmiyor"
                    
                    eserler.append({
                        "isim": isim,
                        "besteci": besteci,
                        "tur": tur,
                        "calgi": calgi,
                        "link": link
                    })
            
            wx.CallAfter(self.sonuclari_goster, eserler)
            
        except Exception:
            wx.CallAfter(self.sonuclari_goster, [])

    def sonuclari_goster(self, eser_listesi):
        self.sonuclar_listesi.DeleteAllItems()
        self.arama_sonuclari.clear()
        
        if not eser_listesi:
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
            gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, id=self.item_engelsiznota.GetId())
            gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, id=self.item_favoriler.GetId())
            gui.mainFrame.sysTrayIcon.Unbind(wx.EVT_MENU, id=self.item_yardim.GetId())
            self.tools_menu.Remove(self.engelsiznota_menu_item)
        except Exception:
            pass
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
        # Yardım dosyası yolu doc klasörüne göre güncellendi!
        yardim_yolu = os.path.join(kok_klasor, "doc", "readme.html")
        
        if os.path.exists(yardim_yolu):
            try:
                os.startfile(yardim_yolu)
            except Exception:
                ui.message("Yardım dosyası tarayıcıda açılamadı.")
        else:
            ui.message("Yardım dosyası doc klasöründe bulunamadı.")

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