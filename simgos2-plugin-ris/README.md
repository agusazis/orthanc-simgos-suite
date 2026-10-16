# SIMGOSv2 RIS Integration Package for Orthanc PACS

Folder ini berisi berkas ekstensi driver dan template konfigurasi plugin **RIS** untuk **SIMGOSv2** agar dapat langsung berkomunikasi dengan suite PACS Orthanc (`hl7-listener`, `OHIF Viewer`, dan `Stone Web Viewer`).

---

## 📂 Struktur Direktori

```text
simgos2-plugin-ris/
├── config/
│   └── autoload/
│       └── plugins/
│           └── ris.php.example        <-- Template konfigurasi RIS SIMGOSv2
└── src/
    └── driver/
        ├── viewer/
        │   ├── OHIF.php               <-- Driver OHIF Viewer v3 via Nginx Proxy
        │   └── StoneViewer.php        <-- Driver Stone Web Viewer via Nginx Proxy
        └── worklist/
            └── ORTHANC.php            <-- Driver Worklist HL7 MLLP Orthanc
```

---

## 🚀 Panduan Pemasangan di Server SIMGOSv2

Asumsikan direktori root instalasi SIMGOSv2 Anda berada di `/var/www/html`:

### 1. Salin Berkas Driver
```bash
# Salin driver worklist (ORTHANC.php)
cp src/driver/worklist/ORTHANC.php /var/www/html/webapps/webservice/plugins/ris/src/driver/worklist/

# Salin driver web viewer (OHIF.php & StoneViewer.php)
cp src/driver/viewer/*.php /var/www/html/webapps/webservice/plugins/ris/src/driver/viewer/
```

### 2. Salin dan Sesuaikan Konfigurasi
```bash
# Salin template konfigurasi
cp config/autoload/plugins/ris.php.example /var/www/html/webapps/webservice/config/autoload/plugins/ris.php

# Buka dan sesuaikan parameter server:
nano /var/www/html/webapps/webservice/config/autoload/plugins/ris.php
```

Parameter yang perlu disesuaikan di `ris.php`:
* **`host`**: Ganti `192.168.10.30` dengan alamat IP Server PACS Orthanc Anda.
* **`id` & `name`**: Kode faskes Kemenkes dan nama resmi Rumah Sakit Anda.
* **`root`**: Ganti `1.2.360.9999999` menjadi `1.2.360.[KODE_RS_KEMENKES]`.
* **`url` & `queries`**: Sesuaikan IP server PACS dan kode faskes pada URL viewer.
