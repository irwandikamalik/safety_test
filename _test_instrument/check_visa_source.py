import pyvisa

def check_visa_resources():
    try:
        # Inisialisasi Resource Manager
        rm = pyvisa.ResourceManager()
        
        # Mendapatkan tuple/daftar semua resource yang terdeteksi
        resources = rm.list_resources()
        
        print("=== DAFTAR VISA RESOURCE YANG TERDETEKSI ===")
        if len(resources) == 0:
            print("Tidak ada instrumen yang terdeteksi!")
            print("Tips: Periksa koneksi kabel, pastikan driver (seperti NI-VISA atau pyvisa-py) sudah terpasang, dan alat dalam kondisi menyala.")
        else:
            for i, res in enumerate(resources, 1):
                print(f"{i}. {res}")
                
    except Exception as e:
        print(f"Terjadi kesalahan saat memindai resource: {e}")

if __name__ == "__main__":
    check_visa_resources()