# Two Beans App

Sistem manajemen inventaris gudang untuk Two Beans Coffee. Stok dicatat per lokasi, yaitu gudang utama yang juga roastery, gudang cabang dan outlet. Perpindahan barang tercatat lewat pengiriman antarlokasi, permintaan supply ke gudang utama dan pembelian ke supplier.

Proyek ini dibuat untuk UAS Web Application Development (WAD05).

| Bagian | Teknologi |
| --- | --- |
| Backend | FastAPI, SQLAlchemy, Alembic, PostgreSQL |
| Frontend | Vue 3, Vite, Vue Router, Pinia |
| Deploy | Vercel (frontend dan API satu origin) dan Neon |

| Tautan | Alamat |
| --- | --- |
| Aplikasi | https://twobeansapp.vercel.app |
| Dokumentasi API (Swagger) | https://twobeansapp.vercel.app/docs |

## Fitur per peran

| Peran | Yang bisa dilakukan |
| --- | --- |
| Admin | Melihat semua lokasi, mengelola master data (lokasi, kategori, supplier, produk) dan menyetujui akun baru beserta peran dan lokasinya |
| Manager gudang utama (roastery) | Melihat stok dan nilai semua lokasi, menyetujui permintaan supply, mengirim barang, membuat pembelian ke supplier dan penjualan |
| Manager gudang cabang | Mengelola stok lokasinya, mengajukan permintaan ke gudang utama, mengirim dan menerima barang, menambah customer serta penjualan ke customer |
| Manager outlet | Sama dengan manager gudang cabang untuk outletnya. Penjualan outlet boleh tanpa customer (pembeli umum) |
| Deliveryman | Melihat pengiriman yang ditugaskan kepadanya beserta surat jalan, tanpa nilai rupiah |

Semua perubahan stok lewat dokumen dan dicatat di buku besar `stok_mutasi`, jadi Stock Card setiap produk bisa ditelusuri dan stok tidak pernah minus. Dokumen lokasi lain dijawab 404 untuk manager.

## Petunjuk penggunaan

Alur utama di bawah bisa dicoba di aplikasi live atau di lokal dengan [akun demo](#akun-demo).

1. Login sebagai `manager.pusat@example.com` (Outlet Pusat Kota). Buka **Permintaan**, buat permintaan supply ke gudang utama. Statusnya langsung diajukan.
2. Login sebagai `manager.roastery@example.com` (Gudang Utama). Buka **Permintaan** lalu setujui. Jumlah yang disetujui boleh lebih kecil dari yang diminta. Draf pengiriman terbentuk otomatis.
3. Masih sebagai manager gudang utama, buka **Pengiriman**, lengkapi deliveryman dan kendaraan lalu kirim. Stok gudang utama berkurang dan surat jalan bisa dicetak dari detail pengiriman.
4. Login sebagai `kurir@example.com` untuk melihat pengiriman yang ditugaskan dan surat jalannya.
5. Login lagi sebagai manager outlet, buka **Pengiriman** lalu terima barangnya. Stok outlet bertambah sesuai jumlah yang diterima dan permintaan berstatus selesai.
6. Buka **Penjualan**, isi produk lalu tekan "Simpan lalu posting". Stok berkurang dan nota bisa dibuka dari daftar penjualan.
7. Pantau hasilnya di **Dashboard**, **Monitoring** (matriks stok semua lokasi) dan **Stock** (Stock Card per produk).
8. Login sebagai admin, buka **User** lalu setujui akun `calon.manager@example.com` dengan memberi peran dan lokasi.

Manager gudang utama juga bisa membuat **Pembelian** ke supplier. Pembelian dipesan lalu diterima. Saat diterima, stok gudang utama bertambah dan HPP produk diperbarui ke harga beli terakhir.

## Materi kuliah yang diterapkan

| Pertemuan | Diterapkan di |
| --- | --- |
| 3–4 Safe rendering, fetch async, empat keadaan request | Tidak ada `v-html` di seluruh frontend. `services/ApiClient.js` selalu memeriksa `response.ok`. `LoadingState`, `ErrorState` dan `EmptyState` dipakai bersama `useList` dan `useDetail` |
| 5 Vue dashboard | Komponen, props, computed dan watch di semua halaman, store Pinia (`auth`, `toast`) dan guard Vue Router |
| 6 FastAPI | Path dan query parameter bertipe, validasi Pydantic (422) dengan pesan per field, error 404 dan 409 lewat `ErrorHandler` |
| 7 Kontrak REST API | Tabel route `routes/api.py` dengan `summary` dan tag di setiap endpoint, schema request dan response dipisah, Enum, pagination `Page`, rate limit slowapi |
| 9 PostgreSQL, SQLAlchemy, Alembic | Model gaya `Mapped`, migration `0001` sampai `0003`, transaksi commit/rollback, eager loading `joinedload` dan `selectinload`, constraint CHECK, UNIQUE dan foreign key |
| 10 Autentikasi dan OWASP | bcrypt dengan hash dummy, sesi server-side di cookie HttpOnly + SameSite=Strict, token CSRF, `OriginGuard`, BOLA dijawab 404, akses per peran dan lokasi, `SECRET_KEY` gagal cepat bila kurang dari 32 karakter |
| 11–12 Testing | 210 test pytest termasuk OWASP Top 10 A01 sampai A10 di `tests/test_security_owasp.py`, linting ruff |
| 13–14 Deployment | Vercel Services (Vue SPA dan FastAPI di satu domain) dengan PostgreSQL di Neon |

## Menjalankan di komputer sendiri

### Prasyarat

- Python 3.12
- Node.js 22.18 atau 24.12 ke atas
- PostgreSQL 16 yang sudah berjalan
- Git

```bash
git clone https://github.com/azharkhairaa/two-beans-app.git
cd two-beans-app
```

### 1. Backend

macOS dan Linux:

```bash
cd backend
python3.12 -m venv venv
source venv/bin/activate
pip install -r requirements-dev.txt
cp .env.example .env
```

Windows (PowerShell):

```powershell
cd backend
py -3.12 -m venv venv
venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
Copy-Item .env.example .env
```

Buka `backend/.env` lalu sesuaikan dua nilai ini.

| Variabel | Isi |
| --- | --- |
| `DATABASE_URL` | User dan password PostgreSQL lokal, misalnya `postgresql+psycopg://postgres:postgres@localhost:5432/two_beans` |
| `SECRET_KEY` | Hasil `python -c "import secrets; print(secrets.token_urlsafe(36))"` |

Variabel lain sudah punya nilai bawaan untuk lokal dan dijelaskan di `.env.example`. File `.env` tidak ikut repo.

Buat database, jalankan migration dan isi data demo. Perintahnya sama di semua OS selama venv aktif. Ganti `-U postgres` dengan user PostgreSQL Anda bila berbeda.

```bash
psql -U postgres -c "CREATE DATABASE two_beans;"
alembic upgrade head
python -m app.seeders
uvicorn app.main:app --reload --port 8000
```

Sebagai ganti migration dan seeder, database juga bisa dipulihkan dari dump `database/two_beans.sql` ke database kosong dengan `psql -U postgres -d two_beans -f database/two_beans.sql` dari root repo.

Seeder mengosongkan semua tabel lalu mengisi lokasi, akun demo, produk dan riwayat 60 hari. API berjalan di http://localhost:8000 dan Swagger di http://localhost:8000/docs.

### 2. Frontend

Buka terminal baru.

```bash
cd frontend
npm install
npm run dev
```

Aplikasi terbuka di http://localhost:5173. Vite meneruskan `/api`, `/docs` dan `/openapi.json` ke backend sehingga cookie sesi tetap satu origin seperti di Vercel.

Kalau port 8000 atau 5173 sudah dipakai, salin `frontend/.env.example` menjadi `frontend/.env.local` lalu ubah `VITE_API_TARGET` dan `WEB_PORT`. Jalankan uvicorn dengan port yang sama, lalu tambahkan origin frontend yang baru ke `ALLOWED_ORIGINS` di `backend/.env`.

### Akun demo

Password semua akun demo di lokal adalah `twobeans2026`.

| Email | Peran | Lokasi |
| --- | --- | --- |
| `admin@example.com` | Admin | Semua lokasi |
| `manager.roastery@example.com` | Manager gudang | Gudang Utama Roastery (GU-01) |
| `manager.barat@example.com` | Manager gudang | Gudang Cabang Barat (GC-01) |
| `manager.timur@example.com` | Manager gudang | Gudang Cabang Timur (GC-02) |
| `manager.pusat@example.com` | Manager outlet | Outlet Pusat Kota (OT-01) |
| `manager.kampus@example.com` | Manager outlet | Outlet Kampus (OT-02) |
| `kurir@example.com` | Deliveryman | Tanpa lokasi |
| `calon.manager@example.com` | Belum ada | Menunggu persetujuan admin |

Di aplikasi live, password admin sudah diganti dan dicantumkan di dokumen pengumpulan. Akun lain memakai password di atas.

## Pengujian

Test memakai database terpisah yang namanya wajib berakhiran `_test`, sesuai `TEST_DATABASE_URL` di `backend/.env`.

```bash
cd backend
psql -U postgres -c "CREATE DATABASE two_beans_test;"
pytest
ruff check .
```

Build frontend dicek dengan `npm run build` di folder `frontend`.

## Deploy ke Vercel dan Neon

1. Buat project di Neon (region Singapore, Postgres 16). Salin dua connection string, yaitu URL pooled (host berakhiran `-pooler`) untuk Vercel dan URL direct untuk laptop.
2. Dari folder `backend` dengan venv aktif, isi skema dan data demo ke Neon memakai URL direct. Perintah `read -rs` membuat URL tidak tampil di layar dan tidak masuk riwayat shell.

   ```bash
   read -rs "NEON_DIRECT?URL direct Neon: " && echo && DATABASE_URL="$NEON_DIRECT" alembic upgrade head && DATABASE_URL="$NEON_DIRECT" python -m app.seeders --yes; unset NEON_DIRECT
   ```

   Contoh di atas untuk zsh. Di bash, ganti bagian awalnya dengan `read -rsp "URL direct Neon: " NEON_DIRECT`. Seeder menolak menulis ke database non-lokal tanpa `--yes`.
3. Di Vercel, import repo ini dengan Root Directory tetap di root. `vercel.json` sudah membagi service `web` (`frontend/`) dan `api` (`backend/`).
4. Isi Environment Variables sebelum menekan Deploy.

   | Variabel | Isi |
   | --- | --- |
   | `APP_ENV` | `production` |
   | `COOKIE_SECURE` | `true` |
   | `DATABASE_URL` | URL pooled Neon |
   | `SECRET_KEY` | Nilai acak baru, jangan menyalin dari `.env` lokal |
   | `ALLOWED_ORIGINS` | Domain production, misalnya `https://twobeansapp.vercel.app`. Domain bawaan Vercel sudah diizinkan otomatis, jadi variabel ini wajib bila nama domain diganti |

5. Sesudah deploy pertama, ubah Function Region ke Singapore (`sin1`) di Settings, Functions lalu Redeploy.
6. Ganti password admin lewat halaman Profil karena password demo tertulis di kode publik.

Setiap push ke `main` otomatis di-deploy ulang. Bila ada migration baru, jalankan `alembic upgrade head` ke Neon lebih dulu sebelum push.

## Troubleshooting

| Gejala | Penanganan |
| --- | --- |
| Backend gagal start dengan pesan konfigurasi | Periksa `backend/.env`. `SECRET_KEY` minimal 32 karakter dan `DATABASE_URL` harus PostgreSQL |
| `connection refused` ke port 5432 | Service PostgreSQL belum berjalan |
| `venv\Scripts\Activate.ps1` diblokir di Windows | Jalankan `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` sekali. Cara lain adalah mengaktifkan venv dari Command Prompt dengan `venv\Scripts\activate.bat` |
| POST dijawab 403 "Origin tidak diizinkan" | Origin frontend belum ada di `ALLOWED_ORIGINS`. Untuk mencoba POST lewat Swagger lokal, tambahkan `http://localhost:8000` |
| Login dijawab 429 | Terlalu banyak percobaan. Tunggu satu menit. Bila akun terkunci sesudah 5 kali salah password, tunggu 15 menit |
| pytest berhenti dengan pesan `_test` | `TEST_DATABASE_URL` harus menunjuk database berakhiran `_test` supaya data pengembangan tidak terhapus |
| Request pertama di aplikasi live lambat | Compute Neon sedang tidur dan bangun dalam beberapa detik |

## Struktur repo

| Lokasi | Isi |
| --- | --- |
| `backend/app/routes/api.py` | Tabel route beserta hak akses setiap endpoint |
| `backend/app/controllers/` | Controller per resource |
| `backend/app/services/` | Aturan bisnis, termasuk `MutasiStok` sebagai satu-satunya pengubah stok |
| `backend/app/models/` | Model SQLAlchemy |
| `backend/app/schemas/` | Validasi request dan bentuk response |
| `backend/app/policies/` | Hak akses per peran dan lokasi |
| `backend/app/core/` | Konfigurasi, sesi, keamanan dan error handler |
| `backend/alembic/versions/` | Migration database |
| `backend/app/seeders/` | Data demo |
| `backend/tests/` | Test pytest |
| `frontend/src/views/` | Halaman Vue per fitur |
| `frontend/src/components/`, `composables/`, `services/`, `stores/` | Komponen, logika form dan daftar, client API serta store Pinia |
| `vercel.json` | Konfigurasi Vercel Services untuk service `web` dan `api` |
