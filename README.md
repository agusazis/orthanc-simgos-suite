# Orthanc PACS & SIMGOS Integration Suite

Repositori ini menyediakan solusi *turnkey* (siap pakai) untuk integrasi **PACS Orthanc**, **SIMRS SIMGOS**, dan **Kemenkes SatuSehat** berbasis Docker Compose.

Arsitektur ini dirancang khusus untuk mengatasi keterbatasan integrasi HL7 dan web viewer bawaan SIMGOS serta menyediakan pipeline pengiriman citra radiologi yang stabil, aman, dan berkinerja tinggi di lingkungan rumah sakit.

---

## 📌 Alur Kerja Sistem (Data Flow)

```text
[ Dokter SIMRS SIMGOS ]
       │
       ▼ (1. Order Pemeriksaan Radiologi)
[ HL7 MLLP Port 2575 ] ───▶ (2. Microservice hl7-listener)
                                   │
                                   ▼ (3. Generate DICOM MWL *.wl)
                       [ Storage /worklists ]
                                   │
                                   ▼ (4. C-FIND Worklist Query)
                        [ Mesin Modalitas (CR/CT/USG) ]
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
   (Auto-Auth Basic Header)                                       (Query C-MOVE otomatis)
               │                                                               │
               ▼                                                               ▼
   [ Dokter Buka Viewer SIMGOS ]                                    [ Router SatuSehat ]
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
   Penerima pesan HL7 order dari SIMGOS. Menangani format MSH khusus SIMGOS, memformat nama dokter sesuai standar DICOM PN (`Family^Given^^Prefix^Suffix`), dan menulis file Modality Worklist (MWL) secara *atomic*.
4. **`nginx-proxy` (Reverse Proxy Auto-Auth)**:
   Meneruskan request web viewer dari antarmuka SIMGOS di port 80 dengan menyuntikkan *Basic Authentication* secara transparan ke Orthanc, sekaligus memblokir akses ke antarmuka admin Orthanc Explorer dari luar.
5. **`dicom-mover` (Kemenkes SatuSehat Bridge)**:
   Engine sinkronisasi otomatis yang membaca order selesai di database SIMGOS, menarik gambar dari Orthanc melalui C-MOVE, dan meneruskannya ke Router SatuSehat Kemenkes.

---

## 🚀 Panduan Cepat Deployment

### 1. Prasyarat Server
* **Sistem Operasi**: Linux (Ubuntu Server 22.04 / 24.04 LTS direkomendasikan).
* **RAM / CPU**: Minimal 4 GB RAM, 2-4 Core vCPU.
* **Storage Rekomendasi**:
  * Drive SSD lokal (misal: `/var/lib/pacs-local`) untuk database PostgreSQL dan worklist aktif.
  * Drive NFS NAS / ZFS Storage (misal: `/mnt/pacs-data`) untuk menampung file citra DICOM berkapasitas besar.
* **Docker & Docker Compose**:
  ```bash
  curl -fsSL https://get.docker.com -o get-docker.sh
  sudo sh get-docker.sh
  sudo usermod -aG docker $USER
  ```

### 2. Kloning & Persiapan Konfigurasi
```bash
git clone https://github.com/username/orthanc-simgos-suite.git /opt/orthanc
cd /opt/orthanc

# Buat file konfigurasi lingkungan dari template
cp .env.example .env
chmod 600 .env
```

### 3. Sesuaikan Variabel di `.env`
Buka file `.env` menggunakan editor teks favorit Anda (`nano .env`):
* Ganti `INSTITUTION_NAME` dengan nama Rumah Sakit Anda.
* Ganti `DICOM_UID_ROOT` dengan format `1.2.360.[KODE_RS_KEMENKES]`.
* Tentukan password untuk database dan Orthanc.
* Hitung header Basic Auth untuk Nginx:
  ```bash
  echo -n 'orthanc_simrs:PASSWORD_ANDA' | base64
  ```
  Salin hasilnya ke baris `ORTHANC_BASIC_AUTH="Basic [HASIL_BASE64]"`.
* Sesuaikan IP Modalitas rontgen/CT pada `ORTHANC_DICOM_MODALITIES`.
* Sesuaikan kredensial database SIMGOS untuk `dicom-mover`.

### 4. Buat Direktori Penyimpanan di Host
```bash
sudo mkdir -p /var/lib/pacs-local/pg-data
sudo mkdir -p /var/lib/pacs-local/worklists
sudo mkdir -p /mnt/pacs-data/orthanc-storage
sudo chmod -R 777 /var/lib/pacs-local/worklists
```

### 5. Jalankan Sistem
```bash
docker compose up -d --build
```

Verifikasi seluruh container berjalan normal:
```bash
docker compose ps
```

---

## 🔧 Konfigurasi SIMGOS

### 1. Pengaturan HL7 Listener di SIMGOS
Pada modul konfigurasi integrasi radiologi/LIS SIMGOS:
* **HL7 Host / IP**: IP Server PACS (contoh: `172.168.1.19`)
* **HL7 Port**: `2575`
* **Format Pesan**: HL7 2.x (ORM / OBR)

### 2. Pengaturan URL Viewer di SIMGOS
Untuk tombol "Buka Citra / Hasil" pada rekam medis elektronik:
* **OHIF Viewer**:
  `http://[IP_SERVER_PACS]/ohif/viewer?StudyInstanceUIDs=1.2.360.[KODE_RS].[ACCESSION_NUMBER]`
* **Stone Web Viewer**:
  `http://[IP_SERVER_PACS]/stone-webviewer/index.html?study=1.2.360.[KODE_RS].[ACCESSION_NUMBER]`

---

## 🏥 Pengaturan Mesin Modalitas (Rontgen / CT / USG)

Masukkan parameter berikut pada konsol mesin radiologi:
* **DICOM Host / IP**: IP Server PACS (contoh: `172.168.1.19`)
* **Storage Port**: `4242`
* **Worklist Port**: `4242`
* **Called AE Title**: `ORTHANC`
* **Calling AE Title**: Sesuaikan dengan AET yang Anda daftarkan di `.env` (contoh: `ELEVA1`, `CT1`).

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

## 🧹 Pemeliharaan & Housekeeping Otomatis

### 1. Retensi File Worklist (MWL Cleanup)
File order worklist yang berumur lebih dari 2 hari dapat dibersihkan otomatis melalui cronjob host:
```bash
# Tambahkan ke crontab (crontab -e):
0 1 * * * find /var/lib/pacs-local/worklists -type f -name "*.wl" -mtime +2 -delete
```

### 2. Auto-Sweep Dicom Mover
Untuk memastikan data radiologi yang tertinggal (misal akibat koneksi internet terputus) tetap terkirim ke Kemenkes, pasang script auto-sweep pada crontab user:
```bash
# Mundur 15 hari setiap pukul 01:15 WITA
15 1 * * * /opt/orthanc/dicom-mover/cron-job/reset_mover.sh > /dev/null 2>&1
```

---

## 📄 Lisensi & Kontribusi
Dikembangkan dan dipelihara oleh Instalasi SIRS & IT Rumah Sakit. Terbuka untuk kontribusi, fork, dan penyempurnaan bersama komunitas Faskes Indonesia.
