# Orthanc PACS & SIMGOSv2 Integration Suite

Repositori ini menyediakan solusi *turnkey* (siap pakai) untuk integrasi **PACS Orthanc**, **[SIMGOSv2](https://docs.simgos2.simpel.web.id)** (Sistem Informasi Manajemen Rumah Sakit Generasi 2 dari Kementerian Kesehatan RI), dan **Kemenkes SatuSehat** berbasis Docker Compose.

Arsitektur ini dirancang khusus untuk mengatasi kendala integrasi HL7 MLLP dan viewer radiologi pada SIMGOSv2, serta menyediakan pipeline pengiriman citra DICOM yang stabil, aman, dan berkinerja tinggi.

---

## 📌 Alur Kerja Sistem (Data Flow)

```text
[ Dokter SIMRS SIMGOSv2 ]
       │
       ▼ (1. Order Pemeriksaan Radiologi)
[ HL7 MLLP Port 2575 ] ───▶ (2. Microservice hl7-listener)
                                   │
                                   ▼ (3. Generate DICOM MWL *.wl)
                       [ Storage /worklists ]
                                   │
                                   ▼ (4. C-FIND Modality Worklist Query)
                        [ Mesin Modalitas (CR/DR/CT/USG) ]
                                   │
                                   ▼ (5. C-STORE Kirim Citra DICOM)
                         [ Orthanc Core (Port 4242) ]
                                ┌──┴──────────────────────────┐
                                ▼                             ▼
                    [ Metadata di PostgreSQL ]     [ Citra di NAS Storage ]
                                │                             │
                                └──────────────┬──────────────┘
                                               │
               ┌───────────────────────────────┴───────────────────────────────┐
               ▼                                                               ▼
   [ Nginx Reverse Proxy Port 80 ]                                [ dicom-mover Service ]
   (Auto-Auth Basic Header)                                       (Karya SIMpel Development)
               │                                                               │
               ▼                                                               ▼
   [ Dokter Buka Viewer SIMGOSv2 ]                                 [ Router SatuSehat ]
   (/ohif/ atau /stone-webviewer/)                                             │
                                                                               ▼
                                                                 [ Cloud SatuSehat Kemenkes ]
```

---

## 🏗️ Komponen Arsitektur (5 Services)

1. **`postgres-db` (PostgreSQL 15 Alpine)**:
   Menyimpan seluruh metadata dan indeks pencarian studi DICOM di drive lokal (SSD) agar query sangat cepat (< 1 ms).
2. **`orthanc` (Orthanc PACS Core)**:
   Server inti DICOM (AET: `ORTHANC`, Port `4242` dan REST API Port `8042`) dilengkapi web viewer modern (**OHIF Viewer v3** dan **Stone Web Viewer**).
3. **`hl7-listener` (Python MLLP Microservice)**:
   Penerima pesan HL7 order dari SIMGOSv2. Menangani parsing MSH SIMGOSv2, memformat nama dokter sesuai standar DICOM PN (`Family^Given^^Prefix^Suffix`), dan menulis file Modality Worklist (MWL) secara *atomic*.
4. **`nginx-proxy` (Reverse Proxy Auto-Auth)**:
   Meneruskan request web viewer dari antarmuka SIMGOSv2 di port 80 dengan menyuntikkan *Basic Authentication* secara transparan ke Orthanc, sekaligus mengisolasi dan memblokir antarmuka admin Orthanc Explorer dari akses luar.
5. **`dicom-mover` (Kemenkes SatuSehat Bridge by SIMpel Development)**:
   Engine sinkronisasi otomatis yang dikembangkan oleh **SIMpel Development** (pengembang asli SIMGOSv2). Repositori resmi: [https://git.simpel.web.id/pub/dicom-mover](https://git.simpel.web.id/pub/dicom-mover). Layanan ini membaca order selesai di database SIMGOSv2, memerintahkan Orthanc via C-MOVE untuk menarik citra, dan meneruskannya ke Router SatuSehat Kemenkes.

---

## 🚀 Panduan Deployment (100% Menggunakan `.env`)

Seluruh konfigurasi (identitas RS, kredensial database, port, dan IP modalitas) **hanya diatur melalui satu file `.env`**. File `docker-compose.yml` sudah terstandarisasi penuh dan tidak perlu diubah secara manual.

### 1. Prasyarat Server
* **Sistem Operasi**: Linux (Ubuntu Server 22.04 / 24.04 LTS direkomendasikan).
* **Hardware**: Minimal 4 GB RAM, 2-4 vCPU.
* **Storage Rekomendasi**:
  * Drive SSD lokal (misal: `/var/lib/pacs-local`) untuk PostgreSQL dan worklist aktif.
  * Drive NFS NAS / ZFS Storage (misal: `/mnt/pacs-data`) untuk menampung file citra DICOM berkapasitas besar.
* **Docker dan Docker Compose**:
  ```bash
  curl -fsSL https://get.docker.com -o get-docker.sh
  sudo sh get-docker.sh
  sudo usermod -aG docker $USER
  ```

### 2. Kloning dan Persiapan Direktori
```bash
git clone https://github.com/agusazis/orthanc-simgos-suite.git /opt/orthanc
cd /opt/orthanc

# Buat direktori host yang diperlukan
sudo mkdir -p /var/lib/pacs-local/pg-data
sudo mkdir -p /var/lib/pacs-local/worklists
sudo mkdir -p /mnt/pacs-data/orthanc-storage
sudo chmod -R 777 /var/lib/pacs-local/worklists

# Persiapan direktori log dan tracking file dicom-mover
mkdir -p dicom-mover/logs
[ ! -f dicom-mover/acn_last.txt ] && echo "0" > dicom-mover/acn_last.txt
```

### 3. Konfigurasi Lingkungan (`.env`)
Salin file template `.env.example` ke `.env`:
```bash
cp .env.example .env
chmod 600 .env
nano .env
```

Sesuaikan parameter berikut di `.env`:
* **`INSTITUTION_NAME`**: Nama resmi Rumah Sakit Anda.
* **`DICOM_UID_ROOT`**: Format `1.2.360.[KODE_RS_KEMENKES]`.
* **`POSTGRES_PASSWORD`**: Tentukan password database PostgreSQL lokal PACS.
* **`ORTHANC_SIMRS_PASSWORD`**: Tentukan password akses web Orthanc.
* **`ORTHANC_BASIC_AUTH`**: String Basic Auth untuk Nginx. Hitung dengan:
  ```bash
  echo -n 'orthanc_simrs:PASSWORD_ORTHANC_ANDA' | base64
  ```
  Masukkan hasilnya: `ORTHANC_BASIC_AUTH="Basic [HASIL_BASE64]"`.
* **`ORTHANC_DICOM_MODALITIES`**: Daftarkan AETitle, IP, dan Port modalitas mesin rontgen/CT/USG Anda.
* **`DB_HOST`, `DB_USER`, `DB_PASS`**: Kredensial koneksi ke database MySQL SIMGOSv2 (`kemkes-ihs`).

### 4. Jalankan Sistem
```bash
docker compose up -d --build
```

Periksa kesehatan seluruh kontainer:
```bash
docker compose ps
```

---

## 🔧 Integrasi dengan SIMGOSv2

### 1. Pengaturan HL7 Listener di SIMGOSv2
Pada menu konfigurasi Radiologi/LIS SIMGOSv2:
* **HL7 Host / IP**: IP Server PACS Anda (contoh: `192.168.10.30`)
* **HL7 Port**: `2575`
* **Format Pesan**: HL7 2.x (ORM / OBR)

### 2. Pengaturan URL Viewer di SIMGOSv2
Untuk tombol "Buka Citra / Hasil" pada Elektronik Rekam Medis (ERM):
* **OHIF Viewer v3**:
  ```text
  http://[IP_SERVER_PACS]/ohif/viewer?StudyInstanceUIDs=1.2.360.[KODE_RS].[ACCESSION_NUMBER]
  ```
* **Stone Web Viewer**:
  ```text
  http://[IP_SERVER_PACS]/stone-webviewer/index.html?study=1.2.360.[KODE_RS].[ACCESSION_NUMBER]
  ```

---

## 🏥 Pengaturan Mesin Modalitas (CR / DR / CT / USG)

Masukkan parameter berikut pada konsol mesin radiologi:
* **DICOM Server Host / IP**: IP Server PACS Anda (contoh: `192.168.10.30`)
* **Storage Port**: `4242`
* **Worklist Port (MWL)**: `4242`
* **Called AE Title**: `ORTHANC`
* **Calling AE Title**: Daftarkan nama AET modalitas Anda di `.env` (contoh: `CR_ROOM1`, `CT_SCAN`).

Uji koneksi worklist dari terminal:
```bash
findscu -v -W \
  -k "ScheduledProcedureStepSequence[0].ScheduledStationAETitle=ORTHANC" \
  -k "ScheduledProcedureStepSequence[0].Modality" \
  -k PatientName \
  -k PatientID \
  -k AccessionNumber \
  [IP_SERVER_PACS] 4242
```

---

## 🧹 Pemeliharaan Rutin (Cronjob)

### 1. Auto-Cleanup File Worklist Usang
Bersihkan file MWL (`.wl`) yang berusia lebih dari 2 hari:
```bash
# crontab -e
0 1 * * * find /var/lib/pacs-local/worklists -type f -name "*.wl" -mtime +2 -delete
```

### 2. Auto-Sweep Dicom Mover (SatuSehat Catch-up)
Mundur 15 hari setiap dini hari pukul 01:15 untuk menyinkronkan ulang data yang sempat tertinggal jika internet putus:
```bash
# crontab -e
15 1 * * * /opt/orthanc/dicom-mover/cron-job/reset_mover.sh > /dev/null 2>&1
```

---

## ☕ Dukungan & Konsultasi

Proyek ini bersifat terbuka dan gratis untuk membantu faskes di seluruh Indonesia mengoptimalkan integrasi radiologi PACS dan SatuSehat Kemenkes.

* 💬 **Bantuan Setup & Remote Asistensi**:  
  Jika tim IT rumah sakit Anda membutuhkan diskusi, panduan implementasi, atau bantuan asistensi teknis, silakan hubungi:  
  👉 **Telegram**: [@AGUSAZIS](https://t.me/AGUSAZIS)

* ☕ **Traktir Kopi (Dukungan Sukarela)**:  
  Jika repositori ini membantu kelancaran operasional faskes Anda dan menghemat waktu riset tim IT, dukungan sukarela secangkir kopi sangat diapresiasi:  
  👉 **Saweria**: [saweria.co/agusazis15](https://saweria.co/agusazis15)

---

## 👥 Pengakuan dan Kredit (Credits)
* **SIMGOSv2**: Dikembangkan oleh Kementerian Kesehatan Republik Indonesia ([Dokumentasi Resmi SIMGOSv2](https://docs.simgos2.simpel.web.id)).
* **dicom-mover Engine**: Dikembangkan dan dirilis oleh tim **SIMpel Development** ([https://git.simpel.web.id/pub/dicom-mover](https://git.simpel.web.id/pub/dicom-mover)).
* **Orthanc PACS**: Dikembangkan oleh Tim Orthanc / Osimis ([orthanc-server.com](https://www.orthanc-server.com/)).
* **Integration and Orchestration**: Dipelihara oleh Instalasi SIRS dan IT Rumah Sakit untuk faskes pengguna SIMGOSv2 di Indonesia.
