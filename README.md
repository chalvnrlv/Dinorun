# DinoRun

![Screenshot 2025-07-02 013015](https://github.com/user-attachments/assets/2e34cac2-beba-4324-87d5-386265de2316)

---

## Fitur Utama

-   **Multiplayer Real-time:** Lihat pemain lain berlari dan melompat bersamamu di layar yang sama.
-   **Lobby Pra-Game:** Pemain masuk ke dalam lobby tunggu sebelum permainan dimulai.
-   **Sistem "Ready":** Game baru akan dimulai setelah minimal 2 pemain terhubung dan semuanya telah menekan tombol "Ready".
-   **Penugasan ID Otomatis:** Server secara otomatis memberikan ID unik untuk setiap pemain yang terhubung untuk menghindari konflik.
-   **Deteksi Game Over & Pemenang:** Server dapat mendeteksi ketika semua pemain telah kalah, menentukan pemenang berdasarkan skor tertinggi, dan menampilkannya.
-   **Reset Sesi Otomatis:** Setelah pemenang diumumkan selama beberapa detik, server akan secara otomatis mereset state-nya, memungkinkan semua pemain untuk memulai sesi permainan baru dari awal.
-   **Arsitektur Client-Server:** Menggunakan socket TCP untuk komunikasi antara klien (game) dan server (logika).
-   **Server Multi-threaded:** Server menggunakan `ThreadPoolExecutor` untuk menangani koneksi dari banyak klien secara bersamaan.
-   **Lingkungan Terkontainerisasi:** Server dan lingkungan pengembangannya dibungkus dalam Docker untuk portabilitas dan kemudahan deployment.

---

## Teknologi yang Digunakan

-   **Klien (Game):** Python & **Pygame**
-   **Server (Backend):** Python, `socket`, `concurrent.futures`
-   **Lingkungan & Deployment:** **Docker** & **Docker Compose**
-   **Protokol Komunikasi:** Protokol berbasis teks kustom di atas TCP.

---

## Arsitektur

Proyek ini terdiri dari dua bagian utama:

1.  **Server:**
    -   `server_thread_pool_http.py`: Bertindak sebagai lapisan jaringan. Script ini membuka socket TCP, mendengarkan koneksi, dan menggunakan thread pool untuk menangani setiap klien.
    -   `http.py`: Script ini mengelola semua logika dan state permainan, seperti daftar pemain, status lobby, status ready, dan proses reset game.

2.  **Klien (`dinorun.py`):**
    -   Ini adalah aplikasi game yang dilihat dan dimainkan oleh pengguna.
    -   Dibuat dengan Pygame untuk menangani grafis, input, dan loop permainan.
    -   Memiliki `ClientInterface` yang bertanggung jawab untuk berkomunikasi dengan server, mengirim state, dan menerima state.

Komunikasi terjadi melalui perintah berbasis teks sederhana seperti `register`, `set_ready`, `update_player`, dan `game_over`.

---

## Cara Menjalankan

Untuk menjalankan proyek ini, Anda memerlukan **Docker**, **Docker Compose**, dan **Python 3** terpasang di komputer Anda.

### Prasyarat

1.  Pastikan **Docker Desktop** sudah terpasang dan berjalan.
2.  Install **Python 3** di komputer Anda.
3.  Install library **Pygame** secara lokal dengan membuka terminal (CMD/PowerShell/Terminal) dan menjalankan:
    ```bash
    pip install pygame
    ```

### Langkah-langkah

**1. Clone Repository**

```bash
git clone https://github.com/chalvnrlv/Dinorun.git
cd Dinorun
```

**2. Jalankan Server (via Docker)**

Server game harus dijalankan melalui Docker Compose untuk memastikan lingkungan yang benar.

```bash
# Masuk ke direktori environment
cd envir

# Bangun dan jalankan kontainer
docker-compose up --build
```
Biarkan terminal ini tetap berjalan. Anda akan melihat log dari server `mesin1` yang menandakan ia siap menerima koneksi.

**3. Jalankan Klien Game**

Klien game harus dijalankan **langsung di komputer Anda** (bukan di dalam Docker) agar window permainannya dapat muncul.

-   Buka terminal **baru**.
-   Arahkan ke direktori root proyek (`dinorun/`).
-   Jalankan script `dinorun.py`:

    ```bash
    python dinorun.py
    ```

Sebuah window game akan muncul, dan Anda akan terhubung ke lobby.

**4. Bermain Multiplayer!**

-   Untuk merasakan pengalaman multiplayer, buka terminal **baru lagi** (sekarang Anda punya 3 terminal yang berjalan).
-   Di terminal ketiga, jalankan lagi `python dinorun.py`.
-   Klien kedua akan muncul dan masuk ke lobby. Anda akan melihat status kedua pemain di layar masing-masing.
-   Tekan tombol **'R'** di kedua jendela game. Setelah semua siap, permainan akan dimulai!

---

## Struktur Direktori

```
└── dinorun/
    ├── dinorun.py                 # Klien game (dijalankan di komputer host)
    ├── http.py                    # Logika utama state game (berjalan di server)
    ├── server_thread_pool_http.py   # Server TCP multi-threaded (berjalan di server)
    ├── envir/                       # Direktori untuk konfigurasi environment
    │   ├── docker-compose.yml     # Mendefinisikan layanan server
    │   └── Dockerfile             # Dockerfile
    └── README.md                  # KAMU DISINIII
```
