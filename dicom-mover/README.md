# DICOM Mover (SatuSehat Bridge)

> **Repositori Resmi Upstream**: [https://git.simpel.web.id/pub/dicom-mover](https://git.simpel.web.id/pub/dicom-mover)  
> Dikembangkan oleh **SIMpel Development** (Pengembang SIMGOSv2).

Layanan ini berfungsi untuk mengambil nomor aksesi (*accession number*) pada order yang selesai di database SIMGOSv2, kemudian memerintahkan PACS Orthanc via C-MOVE untuk mengirimkan citra DICOM ke `dicom-router` SatuSehat Kemenkes.

---

## 1. DAFTARKAN DICOM ROUTER DI PACS

- AETITLE: `ROUTER_SS` (atau `DCMROUTER`)
- Port default: `11112`

## 2. HAK AKSES DATABASE SIMGOSv2

Buat user database (contoh: `dicommover`) di MySQL SIMGOSv2 dengan hak akses baca:
- Hak akses `SELECT` di database `kemkes-ihs` tabel `service_request`
- Hak akses `SELECT` di database `layanan` tabel `tindakan_medis`

## 3. KONFIGURASI

Pengaturan kredensial database dan AETitle disentralisasi pada file root `.env` di direktori utama `/opt/orthanc/.env`.
