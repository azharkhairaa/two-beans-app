# Two Beans App

Sistem manajemen inventaris gudang untuk Two Beans Coffee. Stok dicatat per lokasi, yaitu gudang utama yang juga roastery, gudang cabang dan outlet. Perpindahan barang tercatat lewat pengiriman antarlokasi, permintaan supply ke gudang utama dan pembelian ke supplier.

Proyek ini dibuat untuk UAS Web Application Development (WAD05).

| Bagian | Teknologi |
| --- | --- |
| Backend | FastAPI, SQLAlchemy, Alembic, PostgreSQL |
| Frontend | Vue 3, Vite, Vue Router, Pinia |
| Deploy | Vercel (frontend dan API satu origin) dan Neon |

## Struktur repo

| Lokasi | Isi |
| --- | --- |
| `backend/` | API FastAPI |
| `frontend/` | SPA Vue |
| `vercel.json` | Konfigurasi Vercel Services untuk service `web` dan `api` |

Panduan instalasi lokal, akun demo dan langkah deploy dilengkapi setelah fitur utama selesai.
