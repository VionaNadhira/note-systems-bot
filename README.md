# Note Systems Testnet Auto BOT

Multi-account farming bot untuk **Note Systems** di **Robinhood Chain Testnet** (chain id `46630`).

Bot jalan otomatis tiap `loop_hours` jam: faucet token → claim kupon yang sudah accrued → subscribe COUPON → subscribe SHIELD untuk semua underlying yang dipilih.

---

## Fitur

| Opsi | Fungsi |
|---|---|
| `1` | Faucet — klaim USDG + semua stock token |
| `2` | Auto Subscribe COUPON — deposit USDG ke series subscription |
| `3` | Auto Subscribe SHIELD — deposit stock + prefund USDG |
| `4` | Claim Coupons — klaim kupon yang sudah accrued (COUPON & SHIELD) |
| `5` | Redeem / Refund — redeem posisi terminal, refund sisa |
| `6` | Check Balances — saldo token, ETH, dan leg NFT |
| `7` | Run All — faucet → claim → subscribe coupon → subscribe shield |

Tambahan:
- Multi-akun (loop sequential, semua key dari env)
- Rotating proxy (`socks4` / `socks5` / `http` dengan auth)
- Random delay antar transaksi
- Verifikasi tiap tx di explorer canonical (menangkap tx yang hilang di fork RPC)
- Decode custom error on-chain ke nama yang bisa dibaca

---

## Requirements

- Python 3.10+
- `python3-venv` (`sudo apt install python3-venv`)

## Instalasi

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Konfigurasi

Bot membaca setting dari tiga sumber, dengan prioritas **env > `config.json` > default**.

### 1. Private key — wajib, lewat `.env`

```bash
cp .env.example .env
```

Isi `NOTE_ACCOUNTS` dengan private key dipisah koma:

```
NOTE_ACCOUNTS=0xaaa...,0xbbb...,0xccc...
```

Alternatif tanpa `.env`:

```bash
export NOTE_ACCOUNTS="0xaaa...,0xbbb..."
```

`accounts.txt` (satu key per baris) juga masih didukung sebagai fallback.

### 2. Setting bot — `config.json`

```json
{
  "option": 7,
  "underlyings": "all",
  "coupon_amount": 10,
  "stock_amount": 1,
  "min_delay": 4,
  "max_delay": 6,
  "loop_hours": 24,
  "use_proxy": false,
  "rotate_proxy": false
}
```

| Key | Tipe | Arti |
|---|---|---|
| `option` | `1`-`7` | Opsi yang dijalankan tiap loop |
| `underlyings` | `"all"` / `"AAPL,TSLA"` | Symbol yang diproses |
| `coupon_amount` | float | Deposit COUPON dalam USDG |
| `stock_amount` | float | Deposit SHIELD dalam jumlah share |
| `min_delay` / `max_delay` | int | Rentang jeda (detik) antar tx |
| `loop_hours` | float | Interval loop, `0` = jalan sekali |
| `use_proxy` | bool | Pakai proxy dari `proxy.txt` |
| `rotate_proxy` | bool | Ganti proxy kalau koneksi gagal |

### 3. Override via CLI

```bash
python bot.py -o 3 -u AAPL,TSLA -c 25 -s 5 -l 0 --proxy --rotate
```

| Flag | Short | Default |
|---|---|---|
| `--option` | `-o` | `7` |
| `--underlyings` | `-u` | `all` |
| `--coupon` | `-c` | `10` |
| `--stock` | `-s` | `1` |
| `--min-delay` | — | `4` |
| `--max-delay` | — | `6` |
| `--loop` | `-l` | `24` |
| `--proxy` / `--no-proxy` | — | off |
| `--rotate` / `--no-rotate` | — | off |

### 4. Override via env

`NOTE_OPTION`, `NOTE_UNDERLYINGS`, `NOTE_COUPON`, `NOTE_STOCK`, `NOTE_MIN_DELAY`, `NOTE_MAX_DELAY`, `NOTE_LOOP`, `NOTE_PROXY`.

### 5. Proxy — opsional

`proxy.txt`, satu per baris. Skema `http://`, `https://`, `socks4://`, `socks5://` diterima; kredensial ditulis `http://user:pass@host:port`.

## Menjalankan

```bash
source venv/bin/activate
python bot.py
```

Tidak ada prompt interaktif — setting diambil dari config di atas.

### Cron / systemd

```cron
0 */12 * * * cd /path/ke/note-bot && ./venv/bin/python bot.py >> bot.log 2>&1
```

---

## Kontrak

| Nama | Alamat |
|---|---|
| NoteCore | `0xE47BBec63D836643F8FBC50e61011c9eb278a55e` |
| NoteLegs (ERC-1155) | `0x55Ab2256aD96EB139282b16D901c82cE050685b7` |
| SeriesRegistry | `0xCB07bEe08722bB55ee75Ab6c8D973e65F6937243` |
| RollPolicy | `0x1163Ed84289bbD33Bc19A6e616e6300A24965D45` |
| USDG | `0x433947311e248C9fEc39c69Fac2a305661CCb907` |
| NOTE | `0xf486a40c15040465256a2F871886062430d8D172` |
| sNOTE | `0x3Dd4812aE47981a97011b584E2DaCF3Af3ed1Fc0` |

**RPC:** `https://robinhood-testnet.drpc.org`
**Explorer:** https://explorer.testnet.chain.robinhood.com
**Faucet ETH:** https://faucet.testnet.chain.robinhood.com

> `rpc.testnet.chain.robinhood.com` adalah fork yang sudah basi — transaksi yang di-mine di sana tidak pernah masuk ke chain asli. Bot memakai RPC canonical di atas dan memverifikasi setiap hash di explorer.

## Keamanan

- **Jangan commit `.env`, `accounts.txt`, atau `config.json`** — sudah masuk `.gitignore`.
- Set permission restricts: `chmod 600 .env`
- Testnet only. Jangan pernah pakai private key mainnet.

## Lisensi

For educational/testing purposes only.
