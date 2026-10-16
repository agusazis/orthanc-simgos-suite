#!/bin/bash

DIR="/opt/orthanc/dicom-mover"
COMPOSE_DIR="/opt/orthanc"
FILE="$DIR/acn_last.txt"

mkdir -p "$DIR/logs"

MUNDUR_HARI=15
TANGGAL_MUNDUR=$(date -d "$MUNDUR_HARI days ago" +%y%m%d)
ACN_MUNDUR="${TANGGAL_MUNDUR}00000"

echo "[$(date)] Memulai proses Reset Auto-Sweep Dicom Mover..." >> "$DIR/logs/sweep.log"

# 1. Matikan sementara HANYA container dicom-mover
cd "$COMPOSE_DIR" || exit 1
docker compose stop dicom-mover
docker compose rm -f dicom-mover

# 2. Timpa file acn_last dengan ACN mundur
echo "$ACN_MUNDUR" > "$FILE"
echo "[$(date)] Berhasil memundurkan ACN menjadi $ACN_MUNDUR" >> "$DIR/logs/sweep.log"

# 3. Hidupkan kembali HANYA service dicom-mover
cd "$COMPOSE_DIR" || exit 1
docker compose up -d dicom-mover

echo "[$(date)] Auto-Sweep Selesai. Dicom Mover akan memproses ulang data dari $MUNDUR_HARI hari lalu." >> "$DIR/logs/sweep.log"
