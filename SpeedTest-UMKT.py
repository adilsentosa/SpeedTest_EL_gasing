import logging
import csv
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import speedtest
import socket
import os

# Aktifkan logging untuk debugging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Variabel untuk menyimpan nama gedung terakhir yang digunakan
last_building_name = {}

# Fungsi untuk mendapatkan IP lokal
def get_local_ip():
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        return local_ip
    except Exception as e:
        logger.error(f"Error getting local IP: {e}")
        return "Tidak dapat mengambil IP lokal"

# Fungsi untuk melakukan speedtest
async def speedtest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    building_name = " ".join(context.args) if context.args else last_building_name.get(user_id, "Tidak Diketahui")
    last_building_name[user_id] = building_name

    await update.message.reply_text(f"Menjalankan speed test untuk {building_name}, harap tunggu...")

    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download_speed = st.download() / 10**6  # Konversi ke Mbps
        upload_speed = st.upload() / 10**6      # Konversi ke Mbps
        ping = st.results.ping
        ip_public = st.results.server["host"]
        ip_local = get_local_ip()

        result = f"""
        📊 Hasil Speedtest 📊
        - Lokasi: {building_name}
        - IP Public: {ip_public}
        - IP Local: {ip_local}
        - Kecepatan Download: {download_speed:.2f} Mbps
        - Kecepatan Upload: {upload_speed:.2f} Mbps
        - Ping: {ping:.2f} ms
        """

        await update.message.reply_text(result)

        # Simpan hasil ke dalam file CSV
        with open("rekap_speedtest.csv", mode="a", newline="") as file:
            writer = csv.writer(file)
            if file.tell() == 0:
                writer.writerow(["Tanggal", "Gedung", "IP Public", "IP Local", "Download (Mbps)", "Upload (Mbps)", "Ping (ms)"])

            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), building_name, ip_public, ip_local, f"{download_speed:.2f}", f"{upload_speed:.2f}", f"{ping:.2f}"])

    except Exception as e:
        logger.error(f"Error during speed test: {e}")
        await update.message.reply_text("Terjadi kesalahan saat melakukan speed test.")

# Fungsi untuk mengirim file CSV rekap
async def rekapcsv_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    building_name = " ".join(context.args) if context.args else None

    if not os.path.exists("rekap_speedtest.csv"):
        await update.message.reply_text("Belum ada data rekap speedtest yang tersimpan.")
        return

    filtered_data = []
    with open("rekap_speedtest.csv", mode="r") as file:
        reader = csv.reader(file)
        headers = next(reader)

        for row in reader:
            if not building_name or row[1] == building_name:
                filtered_data.append(row)

    if building_name and not filtered_data:
        await update.message.reply_text(f"Tidak ada data rekap untuk gedung: {building_name}")
        return

    with open("rekap_filtered.csv", mode="w", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(filtered_data)

    with open("rekap_filtered.csv", "rb") as file:
        await update.message.reply_document(document=file, filename="rekap_filtered.csv")

# Fungsi untuk memulai bot
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Halo! Kirim /speedtest <Nama_Gedung> untuk menjalankan tes kecepatan internet atau /rekapcsv <Nama_Gedung> untuk mendapatkan file rekap CSV berdasarkan gedung.')

# Fungsi utama untuk menjalankan bot
def main() -> None:
    app = ApplicationBuilder().token("7401155869:AAGMhxzxnX8OSrmlsRVT3fPO_OyWsexNFTY").build()  # Ganti dengan token bot Anda

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("speedtest", speedtest_command))
    app.add_handler(CommandHandler("rekapcsv", rekapcsv_command))

    app.run_polling()

if __name__ == '__main__':
    main()
