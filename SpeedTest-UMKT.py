import logging
import csv
import matplotlib.pyplot as plt
from datetime import datetime
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes
import speedtest
import socket
import os

# Aktifkan logging untuk debugging dengan encoding UTF-8
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', 
    level=logging.INFO,
    encoding='utf-8'
)
logger = logging.getLogger(__name__)

# Variabel untuk menyimpan nama gedung terakhir yang digunakan
last_building_name = {}

# Fungsi untuk mendapatkan IP lokal
def get_local_ip():
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        logger.info("IP lokal berhasil diambil: %s", local_ip)
        return local_ip
    except Exception as e:
        logger.error(f"Error getting local IP: {e}")
        return "Tidak dapat mengambil IP lokal"

# Fungsi untuk melakukan speedtest
async def speedtest_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.message.from_user.id
    building_name = " ".join(context.args) if context.args else last_building_name.get(user_id, "Tidak Diketahui")
    last_building_name[user_id] = building_name
    logger.info("Menjalankan speedtest untuk gedung: %s oleh user ID: %s", building_name, user_id)

    await update.message.reply_text(f"Menjalankan speed test untuk {building_name}, harap tunggu...")

    try:
        st = speedtest.Speedtest()
        st.get_best_server()
        download_speed = st.download() / 10**6  # Konversi ke Mbps
        upload_speed = st.upload() / 10**6      # Konversi ke Mbps
        ping = st.results.ping
        ip_public = st.results.server["host"]
        ip_local = get_local_ip()

        logger.info("Speedtest berhasil: Download %.2f Mbps, Upload %.2f Mbps, Ping %.2f ms", download_speed, upload_speed, ping)

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

        # Simpan hasil ke dalam file CSV dengan encoding UTF-8
        with open("rekap_speedtest.csv", mode="a", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            if file.tell() == 0:
                writer.writerow(["Tanggal", "Gedung", "IP Public", "IP Local", "Download (Mbps)", "Upload (Mbps)", "Ping (ms)"])
            writer.writerow([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), building_name, ip_public, ip_local, f"{download_speed:.2f}", f"{upload_speed:.2f}", f"{ping:.2f}"])
            logger.info("Hasil speedtest berhasil disimpan ke rekap_speedtest.csv")

    except Exception as e:
        logger.error(f"Error during speed test: {e}")
        await update.message.reply_text("Terjadi kesalahan saat melakukan speed test.")

# Fungsi untuk mengirim file CSV rekap
async def rekapcsv_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    building_name = " ".join(context.args) if context.args else None
    logger.info("Mengambil rekap CSV untuk gedung: %s", building_name or "Semua Gedung")

    if not os.path.exists("rekap_speedtest.csv"):
        await update.message.reply_text("Belum ada data rekap speedtest yang tersimpan.")
        logger.warning("File rekap_speedtest.csv tidak ditemukan")
        return

    filtered_data = []
    with open("rekap_speedtest.csv", mode="r", encoding="utf-8") as file:
        reader = csv.reader(file)
        headers = next(reader)

        for row in reader:
            if not building_name or row[1] == building_name:
                filtered_data.append(row)

    if building_name and not filtered_data:
        await update.message.reply_text(f"Tidak ada data rekap untuk gedung: {building_name}")
        logger.info("Tidak ada data rekap yang sesuai untuk gedung: %s", building_name)
        return

    with open("rekap_filtered.csv", mode="w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(filtered_data)
        logger.info("File rekap_filtered.csv berhasil dibuat untuk gedung: %s", building_name or "Semua Gedung")

    with open("rekap_filtered.csv", "rb") as file:
        await update.message.reply_document(document=file, filename="rekap_filtered.csv")
        logger.info("File rekap_filtered.csv berhasil dikirim ke pengguna")

# Fungsi untuk membuat dan mengirim grafik batang
async def grafik_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.info("Membuat grafik rekap speedtest")

    if not os.path.exists("rekap_speedtest.csv"):
        await update.message.reply_text("Belum ada data rekap speedtest yang tersimpan.")
        logger.warning("File rekap_speedtest.csv tidak ditemukan")
        return

    # Membaca data dari CSV
    dates, download_speeds, upload_speeds, pings = [], [], [], []
    with open("rekap_speedtest.csv", mode="r", encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader)  # Skip header
        for row in reader:
            dates.append(datetime.strptime(row[0], "%Y-%m-%d %H:%M:%S").strftime('%Y-%m-%d %H:%M'))
            download_speeds.append(float(row[4]))
            upload_speeds.append(float(row[5]))
            pings.append(float(row[6]))

    # Membuat grafik batang
    bar_width = 0.25
    x = range(len(dates))

    plt.figure(figsize=(12, 6))
    plt.bar(x, download_speeds, width=bar_width, label='Download (Mbps)', color='b', align='center')
    plt.bar([i + bar_width for i in x], upload_speeds, width=bar_width, label='Upload (Mbps)', color='g', align='center')
    plt.bar([i + bar_width * 2 for i in x], pings, width=bar_width, label='Ping (ms)', color='r', align='center')

    # Menyelaraskan sumbu x dengan label tanggal
    plt.xticks([i + bar_width for i in x], dates, rotation=45, ha='right')
    plt.xlabel('Tanggal')
    plt.ylabel('Kecepatan')
    plt.title('Rekap Speedtest')
    plt.legend()
    plt.grid(True)
    plt.tight_layout()

    # Simpan grafik
    plt.savefig("rekap_speedtest.png")
    plt.close()
    logger.info("Grafik rekap_speedtest.png berhasil disimpan")

    # Kirim grafik ke pengguna
    with open("rekap_speedtest.png", "rb") as file:
        await update.message.reply_photo(photo=file, caption="Grafik rekap speedtest")
        logger.info("Grafik rekap_speedtest.png berhasil dikirim ke pengguna")

# Fungsi untuk memulai bot
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text('Halo! Kirim /speedtest <Nama_Gedung> untuk menjalankan tes kecepatan internet, /rekapcsv <Nama_Gedung> untuk mendapatkan file rekap CSV berdasarkan gedung, atau /grafik untuk melihat grafik hasil speedtest.')
    logger.info("Perintah /start dijalankan oleh pengguna")

# Fungsi utama untuk menjalankan bot
def main() -> None:
    app = ApplicationBuilder().token("7401155869:AAGMhxzxnX8OSrmlsRVT3fPO_OyWsexNFTY").build()  # Ganti dengan token bot Anda

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("speedtest", speedtest_command))
    app.add_handler(CommandHandler("rekapcsv", rekapcsv_command))
    app.add_handler(CommandHandler("grafik", grafik_command))

    app.run_polling()
    logger.info("Bot berjalan dengan polling")

if __name__ == '__main__':
    main()
