import pyvisa

def identify_kikusui_visa(resource_string):
    """
    Mengidentifikasi Kikusui PCR500M menggunakan PyVISA.
    Contoh resource_string: 'ASRL3::INSTR' atau 'COM3' (tergantung OS dan backend).
    """
    rm = pyvisa.ResourceManager()
    
    try:
        print(f"Mencoba membuka koneksi ke: {resource_string}...")
        # Membuka koneksi ke instrumen
        instrument = rm.open_resource(resource_string)
        
        # Konfigurasi parameter komunikasi serial (sesuaikan dengan setting di panel PCR500M)
        instrument.baud_rate = 9600       # Default umum (bisa 1200 - 19200 bps)
        instrument.data_bits = 8
        instrument.parity = pyvisa.constants.Parity.none
        instrument.stop_bits = pyvisa.constants.StopBits.one
        instrument.read_termination = '\n'
        instrument.write_termination = '\n'
        instrument.timeout = 3000         # Timeout dalam milidetik (3 detik)
        
        # Mengirim perintah identifikasi SCPI (*IDN?) dan membaca hasilnya
        idn_response = instrument.query('*IDN?')
        
        print("\n[SUKSES] Terhubung ke Kikusui PCR500M!")
        print(f"Identitas Alat: {idn_response.strip()}")
        
        # Tutup koneksi
        instrument.close()
        
    except pyvisa.VisaIOError as e:
        print(f"\n[ERROR VISA] Gagal terhubung ke instrumen: {e}")
    except Exception as e:
        print(f"\n[ERROR LAINNYA] Terjadi kesalahan: {e}")

if __name__ == "__main__":
    # Ganti 'COM3' atau 'ASRL3::INSTR' sesuai dengan port COM di komputer Anda
    PORT_VISA = 'COM3' 
    identify_kikusui_visa(PORT_VISA)