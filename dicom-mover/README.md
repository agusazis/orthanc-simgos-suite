Docker ini memiliki fungsi untuk mengambil accession number pada service request kemudian memerintahkan pacs untuk mengirim dicom ke `dicom-router` atau sebagai alternatif untuk mengirim kembali dicom ke dicom-router

## DAFTARKAN DICOM ROUTER DI PACS

- AETITLE: DCMROUTER

## BUAT USER AKSES KE DB

**Buat User: dicom-router**

Untuk pengguna simgos
- berikan hak akses `SELECT` di db `kemkes-ihs` table `service_request` 
- berikan hak akses `SELECT` di db `layanan` table `tindakan_medis`

## SETTING FILE .ENV

```
nano .env
```

## JALANKAN DOCKER COMPOSE

```
docker compose up -d
```

> PASTIKAN SUDAH MELAKUKAN INSTALASI DOCKER