import socket
import logging
import re
import os
import time
import threading
from datetime import datetime
from pydicom.dataset import Dataset, FileMetaDataset
from pydicom.sequence import Sequence
from pydicom.uid import ImplicitVRLittleEndian, generate_uid, UID

# ==============================================================================
# CONFIGURATION VIA ENVIRONMENT VARIABLES
# ==============================================================================
INSTITUTION_NAME = os.getenv("INSTITUTION_NAME", "RSUD dr. H. Jusuf SK")
STATION_AETITLE  = os.getenv("STATION_AETITLE", "ORTHANC")
HL7_HOST         = os.getenv("HL7_HOST", "0.0.0.0")
HL7_PORT         = int(os.getenv("HL7_PORT", "2575"))
WORKLIST_DIR     = os.getenv("WORKLIST_DIR", "/mnt/worklists")
DICOM_CHARSET    = os.getenv("DICOM_CHARSET", "ISO_IR 192")
WRITE_DELAY_SEC  = float(os.getenv("WRITE_DELAY_SEC", "0.2"))
UID_ROOT_PREFIX  = os.getenv("DICOM_UID_ROOT", "").strip()

# Konfigurasi Log
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def format_dicom_name(raw_name):
    """
    Standar DICOM PN (Person Name): FamilyName^GivenName^MiddleName^Prefix^Suffix
    Fungsi ini membersihkan ID SIMGOS tapi tetap mempertahankan format baku DICOM.
    """
    if not raw_name:
        return ""
    clean_str = raw_name.strip()
    
    # 1. Hancurkan ID SIMGOS jika terbawa (misal: "176^dr. Rudy...")
    if '^' in clean_str:
        clean_str = clean_str.split('^')[-1]
        
    clean_str = clean_str.strip()
    if not clean_str:
        return ""
    
    # 2. Ekstrak Prefix (dr.)
    prefix = ""
    if "dr." in clean_str.lower():
        prefix = "dr."
        clean_str = re.sub(r'(?i)dr\.\s*', '', clean_str)

    # 3. Pisahkan Suffix (Gelar Spesialis di belakang koma)
    parts = clean_str.split(',')
    main_name = parts[0].strip()
    suffix = parts[1].strip() if len(parts) > 1 else ""
    
    # 4. Pisahkan Last Name (Family) dan First Name (Given)
    name_tokens = main_name.split(' ')
    last_name = name_tokens[-1] if len(name_tokens) > 1 else main_name
    first_name = " ".join(name_tokens[:-1]) if len(name_tokens) > 1 else ""

    # 5. Rakit ke standar DICOM PN yang disukai Modality
    formatted_name = f"{last_name}^{first_name}^^{prefix}^{suffix}"
    
    return formatted_name.rstrip('^') 

def parse_and_create_wl(clean_data):
    try:
        segments = re.split(r'[\r\n]+', clean_data.strip())
        
        patient_name, patient_id, patient_birthdate, patient_sex = "", "", "", ""
        doctor_name = "" 
        
        # 1. Ambil Identitas Pasien & Dokter
        for seg in segments:
            fields = seg.split('|')
            if seg.startswith('PID'):
                if len(fields) > 5:
                    patient_name = fields[5].replace('^', ' ').strip()
                if len(fields) > 3:
                    full_id = fields[3]
                    patient_id = full_id.split('^')[0] if '^' in full_id else full_id
                if len(fields) > 7 and fields[7]:
                    patient_birthdate = fields[7][:8] 
                if len(fields) > 8:
                    patient_sex = fields[8]
            
            elif seg.startswith('PV1'):
                # Ambil nama mentah dari index 8 atau 7
                if len(fields) > 8 and fields[8].strip() and fields[8].strip() != '^':
                    doctor_name = fields[8]
                elif len(fields) > 7 and fields[7].strip() and fields[7].strip() != '^':
                    doctor_name = fields[7]
                    
        # Terapkan formatter DICOM yang benar
        dicom_doctor_name = format_dicom_name(doctor_name)

        # 2. Proses OBR dan ZDS
        orders = []
        current_order = None
        is_order = False

        for seg in segments:
            fields = seg.split('|')
            
            if seg.startswith('OBR'):
                is_order = True
                if current_order:
                    orders.append(current_order)
                
                accession = fields[2] if len(fields) > 2 and fields[2] else ""
                if not accession and len(fields) > 3:
                    accession = fields[3]
                
                obr_date = datetime.now().strftime('%Y%m%d')
                obr_time = datetime.now().strftime('%H%M%S')
                if len(fields) > 7 and fields[7]:
                    raw_dt = fields[7]
                    if len(raw_dt) >= 8:
                        obr_date = raw_dt[:8]
                    if len(raw_dt) >= 14:
                        obr_time = raw_dt[8:14]

                study_desc = "RIS Order"
                if len(fields) > 4:
                    raw_desc = fields[4]
                    study_desc = raw_desc.split('^')[1] if '^' in raw_desc else raw_desc
                modality = fields[24].strip() if len(fields) > 24 and fields[24] else "CR"

                current_order = {
                    'accession': accession,
                    'study_desc': study_desc,
                    'modality': modality,
                    'date': obr_date,
                    'time': obr_time,
                    'uid': "" 
                }

            elif seg.startswith('ZDS') and current_order:
                if len(fields) > 1 and fields[1]:
                    current_order['uid'] = fields[1].strip()

        if current_order:
            orders.append(current_order)

        # 3. PEMBANGUNAN DICOM MWL
        for order in orders:
            if not order['accession']: 
                continue

            ds = Dataset()
            ds.SpecificCharacterSet = DICOM_CHARSET
            ds.InstitutionName = INSTITUTION_NAME
            ds.ReferringPhysicianName = dicom_doctor_name 
            ds.PatientName = patient_name
            ds.PatientID = patient_id
            ds.PatientBirthDate = patient_birthdate
            ds.PatientSex = patient_sex
            ds.AccessionNumber = order['accession']
            ds.RequestedProcedureID = order['accession']
            ds.RequestedProcedureDescription = order['study_desc']
            
            if order['uid']:
                ds.StudyInstanceUID = order['uid']
            elif UID_ROOT_PREFIX:
                ds.StudyInstanceUID = f"{UID_ROOT_PREFIX}.{order['accession']}"
            else:
                ds.StudyInstanceUID = generate_uid()
            
            step = Dataset()
            step.ScheduledStationAETitle = STATION_AETITLE
            step.ScheduledProcedureStepStartDate = order['date']
            step.ScheduledProcedureStepStartTime = order['time']
            step.Modality = order['modality']
            step.ScheduledProcedureStepID = order['accession']
            step.ScheduledProcedureStepDescription = order['study_desc']
            step.ScheduledPerformingPhysicianName = dicom_doctor_name
            
            ds.ScheduledProcedureStepSequence = Sequence([step])
            
            file_meta = FileMetaDataset()
            file_meta.MediaStorageSOPClassUID = UID('1.2.840.10008.5.1.4.31') 
            file_meta.MediaStorageSOPInstanceUID = generate_uid()
            file_meta.TransferSyntaxUID = ImplicitVRLittleEndian
            ds.file_meta = file_meta
            
            # --- ATOMIC WRITE (Standar Enterprise) ---
            # Tulis ke file temporary dulu, lalu rename.
            # Menghindari modality membaca file yang baru ditulis setengah.
            os.makedirs(WORKLIST_DIR, exist_ok=True)
            temp_filename = os.path.join(WORKLIST_DIR, f"{order['accession']}.tmp")
            final_filename = os.path.join(WORKLIST_DIR, f"{order['accession']}.wl")
            
            ds.save_as(temp_filename, enforce_file_format=True, little_endian=True, implicit_vr=True)
            os.rename(temp_filename, final_filename)
            
            logging.info(f"✅ Order {order['accession']} Tersimpan | Inst: {INSTITUTION_NAME} | DICOM PN: {dicom_doctor_name}")

            # Jeda agar file system sempat menulis indeks file ke disk fisik
            if WRITE_DELAY_SEC > 0:
                time.sleep(WRITE_DELAY_SEC)

        return is_order
    except Exception as e:
        logging.error(f"Error pembuatan WL: {e}")
        return False

def handle_client(client_socket):
    try:
        buffer = b""
        while True:
            raw_data = client_socket.recv(4096)
            if not raw_data:
                break 
            
            buffer += raw_data
            
            # Deteksi frame MLLP standard (\x0b ... \x1c\x0d)
            while b'\x0b' in buffer and b'\x1c\x0d' in buffer:
                start_idx = buffer.find(b'\x0b')
                end_idx = buffer.find(b'\x1c\x0d')
                
                if start_idx != -1 and end_idx != -1:
                    if start_idx > end_idx:
                        buffer = buffer[start_idx:]
                        continue
                        
                    msg_data = buffer[start_idx+1 : end_idx]
                    buffer = buffer[end_idx+2 :] 
                    
                    clean_data = msg_data.decode('utf-8', errors='ignore').strip()
                    parse_and_create_wl(clean_data)
                    
                    try:
                        # Kloning MSH untuk response ACK yang presisi bagi SIMGOS
                        segments = re.split(r'[\r\n]+', clean_data)
                        msh_lines = [seg for seg in segments if seg.startswith('MSH')]
                        if msh_lines:
                            msh_fields = msh_lines[0].split('|')
                            if len(msh_fields) >= 7:
                                msh_fields[2], msh_fields[4] = msh_fields[4], msh_fields[2]
                                msh_fields[3], msh_fields[5] = msh_fields[5], msh_fields[3]
                            if len(msh_fields) >= 10:
                                trigger = msh_fields[8].split('^')[1] if '^' in msh_fields[8] else "O01"
                                msh_fields[8] = f"ACK^{trigger}"
                            ack_msh = "|".join(msh_fields)
                            msg_id = msh_fields[9] if len(msh_fields) > 9 else "UNKNOWN_ID"
                            ack_text = f"{ack_msh}\rMSA|AA|{msg_id}\r"
                            final_response = b'\x0b' + ack_text.encode('ascii', errors='ignore') + b'\x1c\x0d'
                            
                            client_socket.sendall(final_response)
                            logging.info(f"➡️  ACK Dikembalikan ke SIMGOS (ID: {msg_id})")
                    except Exception as ack_err:
                        logging.error(f"Gagal merakit ACK: {ack_err}")
                        
    except Exception as e:
        logging.error(f"Koneksi bermasalah: {e}")
    finally:
        client_socket.close()

def start_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HL7_HOST, HL7_PORT))
    server.listen(10)
    logging.info(f"🚀 HL7 Listener Siap di {HL7_HOST}:{HL7_PORT} (Inst: {INSTITUTION_NAME}, AET: {STATION_AETITLE})...")
    while True:
        client, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(client,))
        thread.start()

if __name__ == "__main__":
    start_server()
