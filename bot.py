from web3 import Web3
from web3.exceptions import TransactionNotFound
try:
    from web3.exceptions import ContractLogicError, ContractCustomError
except ImportError:
    ContractLogicError = ContractCustomError = Exception
from eth_account import Account
from aiohttp import ClientResponseError, ClientSession, ClientTimeout, BasicAuth
from aiohttp_socks import ProxyConnector
from datetime import datetime
from colorama import *
import asyncio, random, re, os, sys, json, pytz, urllib.request

wib = pytz.timezone('Asia/Jakarta')

class NoteSystems:
    def __init__(self) -> None:
        self.CHAIN_ID = 46630
        # canonical testnet RPC (verified: head hash matches explorer.testnet.chain.robinhood.com).
        # rpc.testnet.chain.robinhood.com is a STALE FORK - txs mined there never reach the real chain.
        self.RPC_URL = "https://robinhood-testnet.drpc.org"
        self.EXPLORER = "https://explorer.testnet.chain.robinhood.com/tx/"
        self.EXPLORER_API = "https://explorer.testnet.chain.robinhood.com/api?"

        # --- Note Systems testnet (deployment 11, chain id 46630) ---
        self.NOTECORE = "0xE47BBec63D836643F8FBC50e61011c9eb278a55e"
        self.NOTELEGS = "0x55Ab2256aD96EB139282b16D901c82cE050685b7"
        self.SERIES_REGISTRY = "0xCB07bEe08722bB55ee75Ab6c8D973e65F6937243"
        self.ROLL_POLICY = "0x1163Ed84289bbD33Bc19A6e616e6300A24965D45"
        self.USDG = "0x433947311e248C9fEc39c69Fac2a305661CCb907"
        self.NOTE_TOKEN = "0xf486a40c15040465256a2F871886062430d8D172"
        self.SNOTE = "0x3Dd4812aE47981a97011b584E2DaCF3Af3ed1Fc0"

        # Mock stock tokens (testnet faucet)
        self.STOCKS = {
            "AAPL": "0x84f5E66636a75E2d65f4651e7B54682e6A572CAb",
            "AMZN": "0x189311a9B8E9e020b347813088822354fECcD900",
            "COIN": "0x05cAFA1C45f6175ecA86c96A30b9DB9686d14De7",
            "HOOD": "0x713ecbb623b879e5C6e51978c32b41dfe25de58D",
            "META": "0xD2B2cc2d8C66CD1E969D202b0F0F68eE2708fF9f",
            "MSFT": "0x6B6a2487f496cf7a79082Ae255D8d6EB235032CE",
            "NVDA": "0x238d2dF6750e47eCd93147bD2c1253cbf6E7aC1E",
            "TSLA": "0x8E2Ea3Bb2c548464f98b987E26dE5dfC65A0FEe7",
        }

        # Minimal ERC20 ABI (balances + approve + faucet)
        self.TOKEN_ABI = [
            {"type": "function", "name": "balanceOf", "stateMutability": "view",
             "inputs": [{"name": "account", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}]},
            {"type": "function", "name": "allowance", "stateMutability": "view",
             "inputs": [{"name": "owner", "type": "address"}, {"name": "spender", "type": "address"}],
             "outputs": [{"name": "", "type": "uint256"}]},
            {"type": "function", "name": "approve", "stateMutability": "nonpayable",
             "inputs": [{"name": "spender", "type": "address"}, {"name": "amount", "type": "uint256"}],
             "outputs": [{"name": "", "type": "bool"}]},
            {"type": "function", "name": "decimals", "stateMutability": "view",
             "inputs": [], "outputs": [{"name": "", "type": "uint8"}]},
            {"type": "function", "name": "symbol", "stateMutability": "view",
             "inputs": [], "outputs": [{"name": "", "type": "string"}]},
            {"type": "function", "name": "faucet", "stateMutability": "nonpayable", "inputs": [], "outputs": []},
            {"type": "function", "name": "faucetCooldownRemaining", "stateMutability": "view",
             "inputs": [{"name": "account", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}]},
        ]

        # NoteCore: INoteCore + INoteCoreViews + position/accounting views
        self.NOTECORE_ABI = [
            {"type": "function", "name": "seriesCount", "stateMutability": "view",
             "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
            {"type": "function", "name": "seriesStatus", "stateMutability": "view",
             "inputs": [{"name": "seriesId", "type": "uint256"}], "outputs": [{"name": "", "type": "uint8"}]},
            {"type": "function", "name": "getSeries", "stateMutability": "view",
             "inputs": [{"name": "seriesId", "type": "uint256"}],
             "outputs": [{"name": "", "type": "tuple", "components": [
                 {"name": "underlying", "type": "address"},
                 {"name": "feed", "type": "address"},
                 {"name": "autocallBps", "type": "uint16"},
                 {"name": "barrierBps", "type": "uint16"},
                 {"name": "couponFloorBps", "type": "uint16"},
                 {"name": "couponCapBps", "type": "uint16"},
                 {"name": "refBps", "type": "uint16"},
                 {"name": "couponFeeBps", "type": "uint16"},
                 {"name": "notionalFeeBps", "type": "uint16"},
                 {"name": "subscriptionEnd", "type": "uint40"},
                 {"name": "notionalCap", "type": "uint128"},
                 {"name": "minTicket", "type": "uint128"},
                 {"name": "observations", "type": "uint40[]"},
                 {"name": "status", "type": "uint8"},
                 {"name": "couponBps", "type": "uint16"},
                 {"name": "nextObs", "type": "uint32"},
                 {"name": "breached", "type": "bool"},
                 {"name": "s0", "type": "uint256"},
                 {"name": "lastPrice", "type": "uint256"},
                 {"name": "totalCouponDeposits", "type": "uint256"},
                 {"name": "totalShieldStock", "type": "uint256"},
                 {"name": "totalShieldPrefund", "type": "uint256"},
                 {"name": "matchedNotional", "type": "uint256"},
                 {"name": "couponIndex", "type": "uint256"},
                 {"name": "quoteEscrow", "type": "uint256"},
                 {"name": "stockEscrow", "type": "uint256"},
             ]}]},
            {"type": "function", "name": "legId", "stateMutability": "pure",
             "inputs": [{"name": "seriesId", "type": "uint256"}, {"name": "leg", "type": "uint8"}],
             "outputs": [{"name": "", "type": "uint256"}]},
            {"type": "function", "name": "accruedCoupon", "stateMutability": "view",
             "inputs": [{"name": "seriesId", "type": "uint256"}, {"name": "account", "type": "address"}],
             "outputs": [{"name": "", "type": "uint256"}]},
            {"type": "function", "name": "claim", "stateMutability": "nonpayable",
             "inputs": [{"name": "seriesId", "type": "uint256"}], "outputs": [{"name": "quoteOut", "type": "uint256"}]},
            {"type": "function", "name": "redeem", "stateMutability": "nonpayable",
             "inputs": [{"name": "seriesId", "type": "uint256"}, {"name": "units", "type": "uint256"}],
             "outputs": [{"name": "quoteOut", "type": "uint256"}, {"name": "stockOut", "type": "uint256"}]},
            {"type": "function", "name": "redeemShield", "stateMutability": "nonpayable",
             "inputs": [{"name": "seriesId", "type": "uint256"}, {"name": "units", "type": "uint256"}],
             "outputs": [{"name": "quoteOut", "type": "uint256"}, {"name": "stockOut", "type": "uint256"}]},
            {"type": "function", "name": "refund", "stateMutability": "nonpayable",
             "inputs": [{"name": "seriesId", "type": "uint256"}],
             "outputs": [{"name": "quoteOut", "type": "uint256"}, {"name": "stockOut", "type": "uint256"}]},
            {"type": "function", "name": "settle", "stateMutability": "nonpayable",
             "inputs": [{"name": "seriesId", "type": "uint256"}, {"name": "account", "type": "address"}], "outputs": []},
            {"type": "function", "name": "depositCoupon", "stateMutability": "nonpayable",
             "inputs": [{"name": "seriesId", "type": "uint256"}, {"name": "quoteAmount", "type": "uint256"}], "outputs": []},
            {"type": "function", "name": "depositShield", "stateMutability": "nonpayable",
             "inputs": [{"name": "seriesId", "type": "uint256"}, {"name": "stockAmount", "type": "uint256"},
                        {"name": "prefundQuote", "type": "uint256"}], "outputs": []},
            {"type": "function", "name": "requiredPrefund", "stateMutability": "view",
             "inputs": [{"name": "seriesId", "type": "uint256"}, {"name": "stockAmount", "type": "uint256"}],
             "outputs": [{"name": "", "type": "uint256"}]},
            {"type": "function", "name": "getPosition", "stateMutability": "view",
             "inputs": [{"name": "seriesId", "type": "uint256"}, {"name": "account", "type": "address"}],
             "outputs": [{"name": "", "type": "tuple", "components": [
                 {"name": "couponDeposit", "type": "uint256"},
                 {"name": "shieldStock", "type": "uint256"},
                 {"name": "shieldPrefund", "type": "uint256"},
                 {"name": "refundCouponQuote", "type": "uint256"},
                 {"name": "refundPrefundQuote", "type": "uint256"},
                 {"name": "refundStock", "type": "uint256"},
                 {"name": "claimable", "type": "uint256"},
                 {"name": "couponIndexPaid", "type": "uint256"},
                 {"name": "settled", "type": "bool"},
             ]}]},
        ]

        # RollPolicy (issuance calendar / open series discovery)
        self.ROLL_POLICY_ABI = [
            {"type": "function", "name": "openSeriesOf", "stateMutability": "view",
             "inputs": [{"name": "underlying", "type": "address"}],
             "outputs": [{"name": "ids", "type": "uint256[]"}]},
            {"type": "function", "name": "lastSeries", "stateMutability": "view",
             "inputs": [{"name": "underlying", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}]},
            {"type": "function", "name": "seriesOf", "stateMutability": "view",
             "inputs": [{"name": "underlying", "type": "address"}],
             "outputs": [{"name": "", "type": "tuple[]", "components": [
                 {"name": "seriesId", "type": "uint256"}, {"name": "subscriptionEnd", "type": "uint40"}]}]},
        ]

        # NoteLegs ERC-1155
        self.LEGS_ABI = [
            {"type": "function", "name": "balanceOf", "stateMutability": "view",
             "inputs": [{"name": "account", "type": "address"}, {"name": "id", "type": "uint256"}],
             "outputs": [{"name": "", "type": "uint256"}]},
            {"type": "function", "name": "balanceOfBatch", "stateMutability": "view",
             "inputs": [{"name": "accounts", "type": "address[]"}, {"name": "ids", "type": "uint256[]"}],
             "outputs": [{"name": "", "type": "uint256[]"}]},
            {"type": "function", "name": "setApprovalForAll", "stateMutability": "nonpayable",
             "inputs": [{"name": "operator", "type": "address"}, {"name": "approved", "type": "bool"}], "outputs": []},
            {"type": "function", "name": "isApprovedForAll", "stateMutability": "view",
             "inputs": [{"name": "account", "type": "address"}, {"name": "operator", "type": "address"}],
             "outputs": [{"name": "", "type": "bool"}]},
        ]

        # sNOTE (ERC-4626)
        self.SNOTE_ABI = [
            {"type": "function", "name": "balanceOf", "stateMutability": "view",
             "inputs": [{"name": "account", "type": "address"}], "outputs": [{"name": "", "type": "uint256"}]},
            {"type": "function", "name": "totalAssets", "stateMutability": "view", "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
            {"type": "function", "name": "totalSupply", "stateMutability": "view", "inputs": [], "outputs": [{"name": "", "type": "uint256"}]},
            {"type": "function", "name": "previewDeposit", "stateMutability": "view",
             "inputs": [{"name": "assets", "type": "uint256"}], "outputs": [{"name": "", "type": "uint256"}]},
            {"type": "function", "name": "deposit", "stateMutability": "nonpayable",
             "inputs": [{"name": "assets", "type": "uint256"}, {"name": "receiver", "type": "address"}],
             "outputs": [{"name": "", "type": "uint256"}]},
        ]

        self.proxies = []
        self.proxy_index = 0
        self.account_proxies = {}
        self.used_nonce = {}
        self.account_web3 = {}

        self.option = 1
        self.use_proxy = False
        self.rotate_proxy = False
        self.min_delay = 5
        self.max_delay = 15
        self.loop_hours = 24
        self.underlyings = []
        self.coupon_amount = 100
        self.stock_amount = 10
        self.auto = True

        # constants
        self.LEG_COUPON = 0
        self.LEG_SHIELD = 1
        self.STATUS = {0: "None", 1: "Subscription", 2: "Live", 3: "Autocalled", 4: "Matured", 5: "Cancelled", 6: "Unwound"}

    DEFAULTS = {
        "option": 7,
        "underlyings": "all",
        "coupon_amount": 10,
        "stock_amount": 1,
        "min_delay": 4,
        "max_delay": 6,
        "loop_hours": 24,
        "use_proxy": False,
        "rotate_proxy": False,
    }

    def load_config(self):
        cfg = dict(self.DEFAULTS)
        path = "config.json"
        if os.path.exists(path):
            try:
                with open(path, "r") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    cfg.update({k: v for k, v in data.items() if k in self.DEFAULTS})
            except Exception as e:
                self.log(f"{Fore.YELLOW + Style.BRIGHT}Warning: config.json invalid, using defaults ({e}){Style.RESET_ALL}")
        return cfg

    def parse_auto_args(self, cfg):
        args = sys.argv[1:]
        i = 0
        while i < len(args):
            a = args[i].lower()
            if a in ("--option", "-o") and i + 1 < len(args):
                cfg["option"] = int(args[i + 1]); i += 2; continue
            if a in ("--underlyings", "-u") and i + 1 < len(args):
                cfg["underlyings"] = args[i + 1]; i += 2; continue
            if a in ("--coupon", "-c") and i + 1 < len(args):
                cfg["coupon_amount"] = float(args[i + 1]); i += 2; continue
            if a in ("--stock", "-s") and i + 1 < len(args):
                cfg["stock_amount"] = float(args[i + 1]); i += 2; continue
            if a in ("--min-delay",) and i + 1 < len(args):
                cfg["min_delay"] = int(args[i + 1]); i += 2; continue
            if a in ("--max-delay",) and i + 1 < len(args):
                cfg["max_delay"] = int(args[i + 1]); i += 2; continue
            if a in ("--loop", "-l") and i + 1 < len(args):
                cfg["loop_hours"] = float(args[i + 1]); i += 2; continue
            if a == "--proxy":
                cfg["use_proxy"] = True; i += 1; continue
            if a == "--no-proxy":
                cfg["use_proxy"] = False; i += 1; continue
            if a == "--rotate":
                cfg["rotate_proxy"] = True; i += 1; continue
            if a == "--no-rotate":
                cfg["rotate_proxy"] = False; i += 1; continue
            i += 1
        return cfg

    def apply_config(self, cfg):
        symbols = list(self.STOCKS.keys())
        raw = str(cfg["underlyings"]).strip().upper()
        if raw in ("", "ALL"):
            self.underlyings = symbols
        else:
            self.underlyings = [s.strip() for s in raw.split(",") if s.strip() in symbols]

        self.option = int(cfg["option"])
        if self.option not in range(1, 8):
            self.log(f"{Fore.YELLOW + Style.BRIGHT}Warning: option {self.option} invalid, fallback to 7{Style.RESET_ALL}")
            self.option = 7
        self.coupon_amount = float(cfg["coupon_amount"])
        self.stock_amount = float(cfg["stock_amount"])
        self.min_delay = max(0, int(cfg["min_delay"]))
        self.max_delay = max(self.min_delay, int(cfg["max_delay"]))
        self.loop_hours = max(0.0, float(cfg["loop_hours"]))
        self.use_proxy = bool(cfg["use_proxy"])
        self.rotate_proxy = bool(cfg["rotate_proxy"])

    def print_auto_config(self):
        labels = {1: "Faucet", 2: "Auto Subscribe COUPON", 3: "Auto Subscribe SHIELD",
                  4: "Claim Coupons", 5: "Redeem / Refund Terminal", 6: "Check Balances",
                  7: "Run All (Farming Loop)"}
        self.log(f"{Fore.GREEN + Style.BRIGHT}Auto Mode :{Style.RESET_ALL} option {self.option} ({labels[self.option]})")
        self.log(f"{Fore.GREEN + Style.BRIGHT}Underlyings:{Style.RESET_ALL} {Fore.WHITE + Style.BRIGHT}{', '.join(self.underlyings)}{Style.RESET_ALL}")
        self.log(f"{Fore.GREEN + Style.BRIGHT}Coupon    :{Style.RESET_ALL} {self.coupon_amount} USDG")
        self.log(f"{Fore.GREEN + Style.BRIGHT}Shield    :{Style.RESET_ALL} {self.stock_amount} shares")
        self.log(f"{Fore.GREEN + Style.BRIGHT}Delay     :{Style.RESET_ALL} {self.min_delay}-{self.max_delay}s")
        self.log(f"{Fore.GREEN + Style.BRIGHT}Loop      :{Style.RESET_ALL} {self.loop_hours}h")
        self.log(f"{Fore.GREEN + Style.BRIGHT}Proxy     :{Style.RESET_ALL} {'ON' if self.use_proxy else 'OFF'}")

    def clear_terminal(self):
        if not sys.stdout.isatty():
            return
        os.system('cls' if os.name == 'nt' else 'clear')

    def log(self, message):
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}{message}",
            flush=True
        )

    def welcome(self):
        print(
            f"""
        {Fore.GREEN + Style.BRIGHT}Note Systems{Fore.BLUE + Style.BRIGHT} Testnet Auto BOT
            """
            f"""
        {Fore.GREEN + Style.BRIGHT}Multi-Account Farming | Robinhood Chain Testnet (46630)
            """
        )

    def format_seconds(self, seconds):
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{int(hours):02}:{int(minutes):02}:{int(seconds):02}"

    async def load_proxies(self):
        filename = "proxy.txt"
        try:
            if not os.path.exists(filename):
                self.log(f"{Fore.RED + Style.BRIGHT}File {filename} Not Found.{Style.RESET_ALL}")
                return
            with open(filename, 'r') as f:
                self.proxies = [line.strip() for line in f.read().splitlines() if line.strip()]

            if not self.proxies:
                self.log(f"{Fore.RED + Style.BRIGHT}No Proxies Found.{Style.RESET_ALL}")
                return

            self.log(
                f"{Fore.GREEN + Style.BRIGHT}Proxies Total  : {Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT}{len(self.proxies)}{Style.RESET_ALL}"
            )
        except Exception as e:
            self.log(f"{Fore.RED + Style.BRIGHT}Failed To Load Proxies: {e}{Style.RESET_ALL}")
            self.proxies = []

    def check_proxy_schemes(self, proxies):
        schemes = ["http://", "https://", "socks4://", "socks5://"]
        if any(proxies.startswith(scheme) for scheme in schemes):
            return proxies
        return f"http://{proxies}"

    def get_next_proxy_for_account(self, token):
        if token not in self.account_proxies:
            if not self.proxies:
                return None
            proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
            self.account_proxies[token] = proxy
            self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return self.account_proxies[token]

    def rotate_proxy_for_account(self, token):
        if not self.proxies:
            return None
        proxy = self.check_proxy_schemes(self.proxies[self.proxy_index])
        self.account_proxies[token] = proxy
        self.proxy_index = (self.proxy_index + 1) % len(self.proxies)
        return proxy

    def build_proxy_config(self, proxy=None):
        if not proxy:
            return None, None, None

        if proxy.startswith("socks"):
            connector = ProxyConnector.from_url(proxy)
            return connector, None, None

        elif proxy.startswith("http"):
            match = re.match(r"http://(.*?):(.*?)@(.*)", proxy)
            if match:
                username, password, host_port = match.groups()
                clean_url = f"http://{host_port}"
                auth = BasicAuth(username, password)
                return None, clean_url, auth
            else:
                return None, proxy, None

        raise Exception("Unsupported Proxy Type.")

    def generate_address(self, account: str):
        try:
            return Account.from_key(account).address
        except Exception as e:
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}Status    :{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} Generate Address Failed {Style.RESET_ALL}"
                f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}"
            )
            return None

    def mask_account(self, account):
        try:
            return account[:6] + '*' * 6 + account[-6:]
        except Exception:
            return None

    async def get_web3_with_check(self, address: str, retries=5, timeout=30):
        if address in self.account_web3:
            return self.account_web3[address]

        request_kwargs = {"timeout": timeout}

        proxy = self.get_next_proxy_for_account(address) if self.use_proxy else None

        if self.use_proxy and proxy:
            request_kwargs["proxies"] = {"http": proxy, "https": proxy}

        last_err = None
        for attempt in range(retries):
            try:
                web3 = Web3(Web3.HTTPProvider(self.RPC_URL, request_kwargs=request_kwargs))
                web3.eth.get_block_number()
                self.account_web3[address] = web3
                return web3
            except Exception as e:
                last_err = e
                await asyncio.sleep(min(3 * (attempt + 1), 10))
        raise Exception(f"Failed to Connect to Canonical RPC ({self.RPC_URL}): {str(last_err)}")

    async def send_raw_transaction_with_retries(self, account, web3, tx, retries=5):
        for attempt in range(retries):
            try:
                signed_tx = web3.eth.account.sign_transaction(tx, account)
                raw_tx = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
                return web3.to_hex(raw_tx)
            except TransactionNotFound:
                pass
            except Exception as e:
                self.log(
                    f"{Fore.CYAN + Style.BRIGHT}   Message  :{Style.RESET_ALL}"
                    f"{Fore.YELLOW + Style.BRIGHT} [Attempt {attempt + 1}] Send TX Error: {str(e)} {Style.RESET_ALL}"
                )
            await asyncio.sleep(2 ** attempt)
        raise Exception("Transaction Hash Not Found After Maximum Retries")

    async def wait_for_receipt_with_retries(self, web3, tx_hash, retries=5):
        for attempt in range(retries):
            try:
                return await asyncio.to_thread(web3.eth.wait_for_transaction_receipt, tx_hash, timeout=300)
            except TransactionNotFound:
                pass
            except Exception as e:
                self.log(
                    f"{Fore.CYAN + Style.BRIGHT}   Message  :{Style.RESET_ALL}"
                    f"{Fore.YELLOW + Style.BRIGHT} [Attempt {attempt + 1}] Wait for Receipt Error: {str(e)} {Style.RESET_ALL}"
                )
            await asyncio.sleep(2 ** attempt)
        raise Exception("Transaction Receipt Not Found After Maximum Retries")

    def build_tx(self, web3, address, data, value=0, gas_multiplier=1.3):
        gas_price = web3.eth.gas_price
        return {
            "from": address,
            "to": getattr(data, "address", None),
            "data": data._encode_transaction_data(),
            "value": value,
            "gas": int(data.estimate_gas({"from": address, "value": value}) * gas_multiplier),
            "gasPrice": gas_price,
            "nonce": self.used_nonce[address],
            "chainId": self.CHAIN_ID,
        }

    def execute_contract_call_ok(self, receipt):
        return receipt is not None and getattr(receipt, "status", 1) == 1

    def _fetch_tx_from_explorer(self, tx_hash):
        url = f"{self.EXPLORER_API}module=transaction&action=gettxinfo&txhash={tx_hash}"
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=20) as r:
                data = json.loads(r.read().decode())
            result = data.get("result")
            if isinstance(result, dict) and result.get("blockNumber"):
                return result
        except Exception:
            pass
        return None

    async def verify_tx_canonical(self, tx_hash, label="TX"):
        for attempt in range(4):
            info = await asyncio.to_thread(self._fetch_tx_from_explorer, tx_hash)
            if info is not None:
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}   Index    :{Style.RESET_ALL}"
                    f"{Fore.GREEN+Style.BRIGHT} {label} confirmed on canonical explorer {Style.RESET_ALL}"
                    f"{Fore.WHITE+Style.BRIGHT}(block {info['blockNumber']}){Style.RESET_ALL}"
                )
                return info
            await asyncio.sleep(2)
        self.log(
            f"{Fore.CYAN+Style.BRIGHT}   Index    :{Style.RESET_ALL}"
            f"{Fore.RED+Style.BRIGHT} {label} NOT found on canonical explorer - tx likely did NOT land on the real chain{Style.RESET_ALL}"
        )
        return None

    KNOWN_SELECTORS = {
        # aliases observed on the LIVE deployed NoteCore (newer than the published ABI)
        "0xbb6c27fe": "BelowMinTicket",
        "0xfb8f41b2": "InsufficientAllowance",
        "0xe450d38c": "InsufficientBalance",
        # MockUSDG / MockStockToken (verified deploy-side)
        "0x12272bab": "FaucetCooldown",
        "0x9a149268": "NotAdmin",
        "0xe18d7b16": "ERC20InsufficientBalance",
        "0xe88b3fc8": "ERC20InsufficientAllowance",
        # published NoteCore errors that the deployed build still matches
        "0x92a64bec": "SubscriptionClosed",
        "0x3d144835": "BelowMinTicket",
        "0x4357f493": "InsufficientPrefund",
        "0xc3f186fe": "ExcessPrefund",
        "0x279e2b77": "InvalidStatus",
        "0xebc7befa": "InvalidSeries",
        "0x0fe92738": "TooEarly",
        "0x86988c75": "InvalidParams",
        "0x3989c557": "ZeroAmount",
        "0xfd353f1c": "NothingToClaim",
        "0xa1929b7d": "NothingToRefund",
        "0xb63c82ed": "CoreDeprecated",
        "0x566139c4": "ReentrancyGuardReentrantCall",
    }

    def describe_revert(self, e):
        data = ""
        try:
            data = getattr(e, "data", None) or getattr(e, "payload", None) or ""
            if not isinstance(data, str):
                data = str(e)
            if not data.startswith("0x"):
                data = ""
        except Exception:
            data = ""
        if not data:
            return "Reverted (no custom error data)"
        data = data[2:]
        sel = "0x" + data[:8]
        name = self.KNOWN_SELECTORS.get(sel, "")
        words = [data[i * 64:(i + 1) * 64] for i in range((len(data) - 8) // 64)]
        args = []
        for w in words:
            if not w.strip("0"):
                args.append("0")
            elif w[:24] == "0" * 24:
                args.append("0x" + w[24:])
            else:
                args.append(hex(int(w, 16)))
        if name:
            hint = ""
            if name in ("BelowMinTicket",):
                hint = " (minimum ticket per series)"
            elif name in ("InsufficientAllowance",):
                hint = " (approve a full amount to NoteCore)"
            elif name in ("InsufficientBalance",):
                hint = " (top-up wallet, faucet/{symbol})"
            return f"{name}{hint}: {', '.join(args)}"
        return f"UnknownRevert({sel}) args=[{', '.join(args)}]"

    async def execute_contract_call(self, account, address, contract, fn, value=0, label="TX"):
        try:
            contract_web3 = getattr(contract, "w3", None) or getattr(contract, "web3", None)
            tx = self.build_tx(contract_web3, address, fn, value)
            tx_hash = await self.send_raw_transaction_with_retries(account, contract_web3, tx)
            receipt = await self.wait_for_receipt_with_retries(contract_web3, tx_hash)
            block_number = receipt.blockNumber
            self.used_nonce[address] += 1
            if not self.execute_contract_call_ok(receipt):
                self.log(
                    f"{Fore.CYAN+Style.BRIGHT}   {label:<9}:{Style.RESET_ALL}"
                    f"{Fore.RED+Style.BRIGHT} Reverted On-Chain (status 0) {Style.RESET_ALL}"
                )
                return None, None
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}   {label:<9}:{Style.RESET_ALL}"
                f"{Fore.GREEN+Style.BRIGHT} Success {Style.RESET_ALL}"
            )
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}   Block    :{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {block_number} {Style.RESET_ALL}"
            )
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}   Tx Hash  :{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {tx_hash} {Style.RESET_ALL}"
            )
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}   Explorer :{Style.RESET_ALL}"
                f"{Fore.WHITE+Style.BRIGHT} {self.EXPLORER}{tx_hash} {Style.RESET_ALL}"
            )
            await self.verify_tx_canonical(tx_hash, label=label)
            return tx_hash, block_number
        except Exception as e:
            self.log(
                f"{Fore.CYAN+Style.BRIGHT}   {label:<9}:{Style.RESET_ALL}"
                f"{Fore.RED+Style.BRIGHT} {self.describe_revert(e)} {Style.RESET_ALL}"
            )
            return None, None

    async def get_token_balance(self, address, token_address, decimals=18):
        web3 = await self.get_web3_with_check(address)
        contract = web3.eth.contract(address=Web3.to_checksum_address(token_address), abi=self.TOKEN_ABI)
        try:
            balance = contract.functions.balanceOf(address).call()
            return balance / (10 ** decimals)
        except Exception as e:
            self.log(f"{Fore.RED + Style.BRIGHT}   Fetch balance failed: {e}{Style.RESET_ALL}")
            return None

    async def get_native_balance(self, address):
        web3 = await self.get_web3_with_check(address)
        return web3.eth.get_balance(address) / 1e18

    async def approving_token(self, account, address, route_address, asset_address, amount_wei):
        try:
            web3 = await self.get_web3_with_check(address)
            token_contract = web3.eth.contract(address=Web3.to_checksum_address(asset_address), abi=self.TOKEN_ABI)
            allowance = token_contract.functions.allowance(address, route_address).call()

            if allowance < amount_wei:
                approve_data = token_contract.functions.approve(route_address, amount_wei)
                tx = self.build_tx(web3, address, approve_data)
                tx_hash = await self.send_raw_transaction_with_retries(account, web3, tx)
                receipt = await self.wait_for_receipt_with_retries(web3, tx_hash)
                self.used_nonce[address] += 1
                if not self.execute_contract_call_ok(receipt):
                    raise Exception("Approve reverted on-chain (status 0)")
                self.log(f"{Fore.CYAN+Style.BRIGHT}   Approve  :{Style.RESET_ALL}"
                         f"{Fore.GREEN+Style.BRIGHT} Success {Style.RESET_ALL}")
                await self.verify_tx_canonical(tx_hash, label="Approve")
            return True
        except Exception as e:
            raise Exception(f"Approving Token Contract Failed: {self.describe_revert(e)}")

    async def claim_token_faucet(self, account, address, token_address, symbol, decimals):
        web3 = await self.get_web3_with_check(address)
        token_checksum = Web3.to_checksum_address(token_address)
        contract = web3.eth.contract(address=token_checksum, abi=self.TOKEN_ABI)

        remaining = contract.functions.faucetCooldownRemaining(address).call()
        if remaining > 0:
            self.log(f"{Fore.CYAN+Style.BRIGHT}   Faucet   :{Style.RESET_ALL}"
                     f"{Fore.YELLOW+Style.BRIGHT} {symbol} already claimed, cooldown {remaining//3600}h{Style.RESET_ALL}")
            return False

        try:
            faucet_fn = contract.functions.faucet()
            tx = self.build_tx(web3, address, faucet_fn)
            tx_hash = await self.send_raw_transaction_with_retries(account, web3, tx)
            receipt = await self.wait_for_receipt_with_retries(web3, tx_hash)
            self.used_nonce[address] += 1
        except Exception as e:
            self.log(f"{Fore.CYAN+Style.BRIGHT}   Faucet   :{Style.RESET_ALL}"
                     f"{Fore.RED+Style.BRIGHT} {symbol} send failed: {self.describe_revert(e)}{Style.RESET_ALL}")
            return False

        if not self.execute_contract_call_ok(receipt):
            self.log(f"{Fore.CYAN+Style.BRIGHT}   Faucet   :{Style.RESET_ALL}"
                     f"{Fore.RED+Style.BRIGHT} {symbol} tx reverted on-chain (status 0){Style.RESET_ALL}")
            return False

        verified = contract.functions.faucetCooldownRemaining(address).call()
        balance = await self.get_token_balance(address, token_address, decimals)
        if verified == 0:
            self.log(f"{Fore.CYAN+Style.BRIGHT}   Faucet   :{Style.RESET_ALL}"
                     f"{Fore.RED+Style.BRIGHT} {symbol} mined but cooldown untouched - tx did NOT land on canonical chain{Style.RESET_ALL}")
            return False

        self.log(f"{Fore.CYAN+Style.BRIGHT}   Faucet   :{Style.RESET_ALL}"
                 f"{Fore.GREEN+Style.BRIGHT} {symbol} Success {Style.RESET_ALL}"
                 f"{Fore.WHITE+Style.BRIGHT} (balance {balance if balance is not None else '?'} {symbol}){Style.RESET_ALL}")
        info = await self.verify_tx_canonical(tx_hash, label="Faucet")
        return info is not None

    async def find_subscription_series(self, address, underlying_symbol):
        web3 = await self.get_web3_with_check(address)
        underlying = Web3.to_checksum_address(self.STOCKS[underlying_symbol])
        roll = web3.eth.contract(address=Web3.to_checksum_address(self.ROLL_POLICY), abi=self.ROLL_POLICY_ABI)
        core = web3.eth.contract(address=Web3.to_checksum_address(self.NOTECORE), abi=self.NOTECORE_ABI)

        try:
            ids = roll.functions.openSeriesOf(underlying).call()
        except Exception as e:
            self.log(f"{Fore.YELLOW + Style.BRIGHT}   openSeriesOf failed for {underlying_symbol}: {str(e)[:100]}{Style.RESET_ALL}")
            return None

        now = web3.eth.get_block("latest")["timestamp"]
        best = None
        for series_id in ids:
            try:
                view = core.functions.getSeries(series_id).call()
            except Exception:
                continue
            status = view[13]
            subscription_end = view[9]
            if status == 1 and subscription_end > now:
                if best is None or subscription_end > best[1]:
                    best = (series_id, subscription_end, view)
        return best

    async def deposit_coupon(self, account, address, series_id, amount):
        web3 = await self.get_web3_with_check(address)
        core = web3.eth.contract(address=Web3.to_checksum_address(self.NOTECORE), abi=self.NOTECORE_ABI)
        quote_decimals = 6
        amount_wei = int(amount * 10 ** quote_decimals)

        try:
            series_view = core.functions.getSeries(series_id).call()
            min_ticket = series_view[11]
        except Exception:
            min_ticket = 0
        if min_ticket and amount_wei < min_ticket:
            self.log(f"{Fore.YELLOW + Style.BRIGHT}   Status   : Coupon amount {amount} USDG below minTicket"
                     f" {min_ticket / 10 ** quote_decimals} USDG, skip{Style.RESET_ALL}")
            return None, None

        balance = await self.get_token_balance(address, self.USDG, quote_decimals)
        if balance is None or balance < amount:
            self.log(f"{Fore.YELLOW + Style.BRIGHT}   Status   : Insufficient USDG ({balance} < {amount}), trying faucet{Style.RESET_ALL}")
            await self.claim_token_faucet(account, address, self.USDG, "USDG", quote_decimals)
            balance = await self.get_token_balance(address, self.USDG, quote_decimals)
            if balance is None or balance < amount:
                self.log(f"{Fore.RED + Style.BRIGHT}   Status   : Still insufficient USDG after faucet, skip deposit{Style.RESET_ALL}")
                return None, None

        await self.approving_token(account, address, self.NOTECORE, self.USDG, amount_wei)

        deposit = core.functions.depositCoupon(series_id, amount_wei)
        return await self.execute_contract_call(account, address, core, deposit, label="Deposit")

    async def deposit_shield(self, account, address, series_id, stock_symbol, stock_amount, prefund_headroom_bps=10):
        web3 = await self.get_web3_with_check(address)
        core = web3.eth.contract(address=Web3.to_checksum_address(self.NOTECORE), abi=self.NOTECORE_ABI)
        stock = Web3.to_checksum_address(self.STOCKS[stock_symbol])
        stock_wei = int(stock_amount * 10 ** 18)

        stock_balance = await self.get_token_balance(address, stock, 18)
        if stock_balance is None or stock_balance < stock_amount:
            self.log(f"{Fore.YELLOW + Style.BRIGHT}   Status   : Insufficient {stock_symbol} ({stock_balance} < {stock_amount}), trying faucet{Style.RESET_ALL}")
            await self.claim_token_faucet(account, address, stock, stock_symbol, 18)
            stock_balance = await self.get_token_balance(address, stock, 18)
            if stock_balance is None or stock_balance < stock_amount:
                self.log(f"{Fore.RED + Style.BRIGHT}   Status   : Still insufficient {stock_symbol}, skip SHIELD deposit{Style.RESET_ALL}")
                return None, None

        prefund = core.functions.requiredPrefund(series_id, stock_wei).call()
        prefund += (prefund * prefund_headroom_bps + 9999) // 10000

        usdg_balance = await self.get_token_balance(address, self.USDG, 6)
        if usdg_balance is None or usdg_balance * 1e6 < prefund:
            self.log(f"{Fore.YELLOW + Style.BRIGHT}   Status   : Insufficient USDG for SHIELD prefund, trying faucet{Style.RESET_ALL}")
            await self.claim_token_faucet(account, address, self.USDG, "USDG", 6)
            usdg_balance = await self.get_token_balance(address, self.USDG, 6)
            if usdg_balance is None or usdg_balance * 1e6 < prefund:
                self.log(f"{Fore.RED + Style.BRIGHT}   Status   : Still insufficient USDG for prefund, skip SHIELD deposit{Style.RESET_ALL}")
                return None, None

        await self.approving_token(account, address, self.NOTECORE, stock, stock_wei)
        await self.approving_token(account, address, self.NOTECORE, self.USDG, prefund)

        deposit = core.functions.depositShield(series_id, stock_wei, prefund)
        return await self.execute_contract_call(account, address, core, deposit, label="Deposit")

    async def claim_coupon(self, account, address, series_id, amount_wei):
        web3 = await self.get_web3_with_check(address)
        core = web3.eth.contract(address=Web3.to_checksum_address(self.NOTECORE), abi=self.NOTECORE_ABI)
        claim_fn = core.functions.claim(series_id)
        return await self.execute_contract_call(account, address, core, claim_fn, label="Claim")

    async def is_approved_legs(self, address):
        web3 = await self.get_web3_with_check(address)
        legs = web3.eth.contract(address=Web3.to_checksum_address(self.NOTELEGS), abi=self.LEGS_ABI)
        return legs.functions.isApprovedForAll(address, self.NOTECORE).call()

    async def get_leg_balances(self, address, series_ids):
        web3 = await self.get_web3_with_check(address)
        legs = web3.eth.contract(address=Web3.to_checksum_address(self.NOTELEGS), abi=self.LEGS_ABI)
        id_legs = ([(series_id << 1) | self.LEG_COUPON for series_id in series_ids] +
                   [(series_id << 1) | self.LEG_SHIELD for series_id in series_ids])
        accounts = [address] * (len(series_ids) * 2)
        try:
            balances = legs.functions.balanceOfBatch(accounts, id_legs).call()
        except Exception:
            balances = []
            for sid in id_legs:
                try:
                    balances.append(legs.functions.balanceOf(address, sid).call())
                except Exception:
                    balances.append(0)
        coupons = {}
        shields = {}
        for i, series_id in enumerate(series_ids):
            coupons[series_id] = balances[i]
            shields[series_id] = balances[len(series_ids) + i]
        return coupons, shields

    async def process_option_faucet(self, account, address):
        self.log(f"{Fore.CYAN+Style.BRIGHT}Faucet    :{Style.RESET_ALL}")
        quote_decimals = 6
        await self.claim_token_faucet(account, address, self.USDG, "USDG", quote_decimals)
        for symbol in self.underlyings:
            await self.claim_token_faucet(account, address, self.STOCKS[symbol], symbol, 18)
            await asyncio.sleep(random.randint(self.min_delay, self.max_delay))
        native = await self.get_native_balance(address)
        self.log(f"{Fore.CYAN+Style.BRIGHT}   ETH     :{Style.RESET_ALL}"
                 f"{Fore.WHITE+Style.BRIGHT} {native:.6f} test ETH{Style.RESET_ALL}"
                 f"{Fore.YELLOW+Style.BRIGHT}  (top up via https://faucet.testnet.chain.robinhood.com if low){Style.RESET_ALL}")

    async def process_option_subscribe_coupon(self, account, address):
        self.log(f"{Fore.CYAN+Style.BRIGHT}Subscribe :{Style.RESET_ALL} COUPON (USDG)")
        for symbol in self.underlyings:
            self.log(f"{Fore.GREEN+Style.BRIGHT} ● {Style.RESET_ALL}"
                     f"{Fore.BLUE+Style.BRIGHT}{symbol}{Style.RESET_ALL}")
            found = await self.find_subscription_series(address, symbol)
            if found is None:
                self.log(f"{Fore.YELLOW+Style.BRIGHT}   Status   : No open subscription series for {symbol}{Style.RESET_ALL}")
                continue
            series_id, sub_end, view = found
            barrier_bps = view[3]
            coupon_bps = view[14]
            self.log(f"{Fore.CYAN+Style.BRIGHT}   Series   :{Style.RESET_ALL}"
                     f"{Fore.WHITE+Style.BRIGHT} #{series_id} barrier {barrier_bps/100:.1f}% coupon {coupon_bps/100:.2f}%/obs{Style.RESET_ALL}")
            await self.deposit_coupon(account, address, series_id, self.coupon_amount)
            await asyncio.sleep(random.randint(self.min_delay, self.max_delay))

    async def process_option_subscribe_shield(self, account, address):
        self.log(f"{Fore.CYAN+Style.BRIGHT}Subscribe :{Style.RESET_ALL} SHIELD (stock + prefund)")
        for symbol in self.underlyings:
            self.log(f"{Fore.GREEN+Style.BRIGHT} ● {Style.RESET_ALL}"
                     f"{Fore.BLUE+Style.BRIGHT}{symbol}{Style.RESET_ALL}")
            found = await self.find_subscription_series(address, symbol)
            if found is None:
                self.log(f"{Fore.YELLOW+Style.BRIGHT}   Status   : No open subscription series for {symbol}{Style.RESET_ALL}")
                continue
            series_id, sub_end, view = found
            barrier_bps = view[3]
            s0 = view[17]
            last_price = view[18]
            self.log(f"{Fore.CYAN+Style.BRIGHT}   Series   :{Style.RESET_ALL}"
                     f"{Fore.WHITE+Style.BRIGHT} #{series_id} barrier {barrier_bps/100:.1f}% s0 {(s0/1e8):.2f} last {(last_price/1e8):.2f}{Style.RESET_ALL}")
            await self.deposit_shield(account, address, series_id, symbol, self.stock_amount)
            await asyncio.sleep(random.randint(self.min_delay, self.max_delay))

    async def process_option_claim(self, account, address, all_series_ids):
        self.log(f"{Fore.CYAN+Style.BRIGHT}Claim     :{Style.RESET_ALL} accrued coupons")
        web3 = await self.get_web3_with_check(address)
        core = web3.eth.contract(address=Web3.to_checksum_address(self.NOTECORE), abi=self.NOTECORE_ABI)

        coupons, shields = await self.get_leg_balances(address, all_series_ids)
        claimed_any = False
        for series_id in all_series_ids:
            if coupons.get(series_id, 0) > 0:
                accrued = core.functions.accruedCoupon(series_id, address).call()
                if accrued > 0:
                    self.log(f"{Fore.GREEN+Style.BRIGHT} ● {Style.RESET_ALL}"
                             f"{Fore.BLUE+Style.BRIGHT}Claim{Style.RESET_ALL}"
                             f"{Fore.WHITE+Style.BRIGHT} #{series_id} {accrued/1e6:.4f} USDG{Style.RESET_ALL}")
                    await self.claim_coupon(account, address, series_id, accrued)
                    claimed_any = True
                    await asyncio.sleep(random.randint(self.min_delay, self.max_delay))
            if shields.get(series_id, 0) > 0:
                pos = core.functions.getPosition(series_id, address).call()
                claimable = pos[6]
                if claimable > 0:
                    self.log(f"{Fore.GREEN+Style.BRIGHT} ● {Style.RESET_ALL}"
                             f"{Fore.BLUE+Style.BRIGHT}Claim{Style.RESET_ALL}"
                             f"{Fore.WHITE+Style.BRIGHT} #{series_id} {claimable/1e6:.4f} USDG (SHIELD){Style.RESET_ALL}")
                    await self.claim_coupon(account, address, series_id, claimable)
                    claimed_any = True
                    await asyncio.sleep(random.randint(self.min_delay, self.max_delay))
        if not claimed_any:
            self.log(f"{Fore.YELLOW+Style.BRIGHT}   Status   : No accrued coupons available{Style.RESET_ALL}")

    async def process_option_balances(self, account, address, all_series_ids):
        self.log(f"{Fore.CYAN+Style.BRIGHT}Balances  :{Style.RESET_ALL}")
        native = await self.get_native_balance(address)
        usdg = await self.get_token_balance(address, self.USDG, 6)
        note = await self.get_token_balance(address, self.NOTE_TOKEN, 18)
        snote = await self.get_token_balance(address, self.SNOTE, 18)
        self.log(f"{Fore.CYAN+Style.BRIGHT}   ETH     :{Style.RESET_ALL}{Fore.WHITE+Style.BRIGHT} {native:.6f}{Style.RESET_ALL}")
        self.log(f"{Fore.CYAN+Style.BRIGHT}   USDG    :{Style.RESET_ALL}{Fore.WHITE+Style.BRIGHT} {usdg:.4f}{Style.RESET_ALL}")
        self.log(f"{Fore.CYAN+Style.BRIGHT}   NOTE    :{Style.RESET_ALL}{Fore.WHITE+Style.BRIGHT} {note:.4f}{Style.RESET_ALL}")
        self.log(f"{Fore.CYAN+Style.BRIGHT}   sNOTE   :{Style.RESET_ALL}{Fore.WHITE+Style.BRIGHT} {snote:.4f}{Style.RESET_ALL}")
        for symbol in self.underlyings:
            bal = await self.get_token_balance(address, self.STOCKS[symbol], 18)
            self.log(f"{Fore.CYAN+Style.BRIGHT}   {symbol:<6}:{Style.RESET_ALL}{Fore.WHITE+Style.BRIGHT} {bal:.4f}{Style.RESET_ALL}")

        if all_series_ids:
            coupons, shields = await self.get_leg_balances(address, all_series_ids)
            for series_id in all_series_ids:
                if coupons.get(series_id, 0) or shields.get(series_id, 0):
                    self.log(f"{Fore.CYAN+Style.BRIGHT}   Leg #{series_id:<5}:{Style.RESET_ALL}"
                             f"{Fore.GREEN+Style.BRIGHT} COUPON {coupons.get(series_id,0)/1e6:.4f}{Style.RESET_ALL}"
                             f"{Fore.BLUE+Style.BRIGHT} / SHIELD {shields.get(series_id,0)/1e6:.4f}{Style.RESET_ALL}")

    async def process_option_redeem(self, account, address, all_series_ids):
        self.log(f"{Fore.CYAN+Style.BRIGHT}Redeem    :{Style.RESET_ALL} terminal positions (exit / resets streak)")
        web3 = await self.get_web3_with_check(address)
        core = web3.eth.contract(address=Web3.to_checksum_address(self.NOTECORE), abi=self.NOTECORE_ABI)
        coupons, shields = await self.get_leg_balances(address, all_series_ids)
        for series_id in all_series_ids:
            status = core.functions.seriesStatus(series_id).call()
            if status not in (3, 4, 5, 6):
                continue
            coupon_units = coupons.get(series_id, 0)
            shield_units = shields.get(series_id, 0)
            if coupon_units > 0 and status in (3, 4):
                self.log(f"{Fore.GREEN+Style.BRIGHT} ● {Style.RESET_ALL}Core #{series_id} COUPON units {coupon_units/1e6:.4f}")
                redeem_fn = core.functions.redeem(series_id, coupon_units)
                await self.execute_contract_call(account, address, core, redeem_fn, label="Redeem")
                await asyncio.sleep(random.randint(self.min_delay, self.max_delay))
            if shield_units > 0:
                self.log(f"{Fore.GREEN+Style.BRIGHT} ● {Style.RESET_ALL}Core #{series_id} SHIELD units {shield_units/1e6:.4f}")
                redeem_fn = core.functions.redeemShield(series_id, shield_units)
                await self.execute_contract_call(account, address, core, redeem_fn, label="Redeem")
                await asyncio.sleep(random.randint(self.min_delay, self.max_delay))
            try:
                pos = core.functions.getPosition(series_id, address).call()
                if pos[3] > 0 or pos[4] > 0 or pos[5] > 0:
                    self.log(f"{Fore.GREEN+Style.BRIGHT} ● {Style.RESET_ALL}Core #{series_id} refund pending")
                    refund_fn = core.functions.refund(series_id)
                    await self.execute_contract_call(account, address, core, refund_fn, label="Refund")
                    await asyncio.sleep(random.randint(self.min_delay, self.max_delay))
            except Exception:
                pass

    async def process_account(self, account, address, all_series_ids):
        try:
            web3 = await self.get_web3_with_check(address)
        except Exception as e:
            self.log(f"{Fore.RED+Style.BRIGHT}Status  : Web3 Not Connected - {str(e)}{Style.RESET_ALL}")
            return
        self.used_nonce[address] = web3.eth.get_transaction_count(address, "pending")

        if self.option == 1:
            await self.process_option_faucet(account, address)
        elif self.option == 2:
            await self.process_option_subscribe_coupon(account, address)
        elif self.option == 3:
            await self.process_option_subscribe_shield(account, address)
        elif self.option == 4:
            await self.process_option_claim(account, address, all_series_ids)
        elif self.option == 5:
            await self.process_option_redeem(account, address, all_series_ids)
        elif self.option == 6:
            await self.process_option_balances(account, address, all_series_ids)
        elif self.option == 7:
            self.log(f"{Fore.CYAN+Style.BRIGHT}Run All   :{Style.RESET_ALL} faucet -> claim -> subscribe")
            await self.process_option_faucet(account, address)
            await asyncio.sleep(random.randint(self.min_delay, self.max_delay))
            await self.process_option_claim(account, address, all_series_ids)
            await asyncio.sleep(random.randint(self.min_delay, self.max_delay))
            await self.process_option_subscribe_coupon(account, address)
            await asyncio.sleep(random.randint(self.min_delay, self.max_delay))
            await self.process_option_subscribe_shield(account, address)

    def ask_underlyings(self):
        symbols = list(self.STOCKS.keys())
        print(f"{Fore.GREEN + Style.BRIGHT}Pick Underlyings: {Style.RESET_ALL}{Fore.WHITE+Style.BRIGHT}{', '.join(symbols)}{Style.RESET_ALL}")
        while True:
            raw = input(f"{Fore.YELLOW + Style.BRIGHT}Comma-separated or 'all' -> {Style.RESET_ALL}").strip().upper()
            if raw in ("", "ALL"):
                self.underlyings = symbols
                break
            chosen = [s.strip() for s in raw.split(",") if s.strip().upper() in symbols]
            if chosen:
                self.underlyings = chosen
                break
            print(f"{Fore.RED + Style.BRIGHT}Invalid symbols. Choose from: {', '.join(symbols)}{Style.RESET_ALL}")

    def ask_amount(self, label, default):
        while True:
            try:
                raw = input(f"{Fore.YELLOW + Style.BRIGHT}Enter {label} [{default}] -> {Style.RESET_ALL}").strip()
                value = float(raw) if raw else default
                if value > 0:
                    return value
                print(f"{Fore.RED + Style.BRIGHT}{label} must be > 0.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter a float or decimal number.{Style.RESET_ALL}")

    def print_delay_question(self):
        while True:
            try:
                min_delay = int(input(f"{Fore.YELLOW + Style.BRIGHT}Min Delay For Each Tx -> {Style.RESET_ALL}").strip())
                if min_delay >= 0:
                    self.min_delay = min_delay
                    break
                print(f"{Fore.RED + Style.BRIGHT}Min Delay must be >= 0.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter a number.{Style.RESET_ALL}")
        while True:
            try:
                max_delay = int(input(f"{Fore.YELLOW + Style.BRIGHT}Max Delay For Each Tx -> {Style.RESET_ALL}").strip())
                if max_delay >= self.min_delay:
                    self.max_delay = max_delay
                    break
                print(f"{Fore.RED + Style.BRIGHT}Max Delay must be >= Min Delay.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter a number.{Style.RESET_ALL}")

    def print_loop_question(self):
        while True:
            try:
                raw = input(f"{Fore.YELLOW + Style.BRIGHT}Loop Interval (hours, 0 = run once) [24] -> {Style.RESET_ALL}").strip()
                loop_hours = float(raw) if raw else 24
                if loop_hours >= 0:
                    self.loop_hours = loop_hours
                    break
                print(f"{Fore.RED + Style.BRIGHT}Loop hours must be >= 0.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter a number.{Style.RESET_ALL}")

    async def check_connection(self, proxy_url=None):
        connector, proxy, proxy_auth = self.build_proxy_config(proxy_url)
        try:
            async with ClientSession(connector=connector, timeout=ClientTimeout(total=10)) as session:
                async with session.get(url="https://api.ipify.org?format=json", proxy=proxy, proxy_auth=proxy_auth) as response:
                    response.raise_for_status()
                    return True
        except (Exception, ClientResponseError) as e:
            self.log(f"{Fore.CYAN+Style.BRIGHT}Status    :{Style.RESET_ALL}"
                     f"{Fore.RED+Style.BRIGHT} Connection Not 200 OK {Style.RESET_ALL}"
                     f"{Fore.MAGENTA+Style.BRIGHT}-{Style.RESET_ALL}"
                     f"{Fore.YELLOW+Style.BRIGHT} {str(e)} {Style.RESET_ALL}")
            return None

    async def process_check_connection(self, address: str):
        while True:
            proxy = self.get_next_proxy_for_account(address) if self.use_proxy else None
            self.log(f"{Fore.CYAN+Style.BRIGHT}Proxy     :{Style.RESET_ALL}"
                     f"{Fore.WHITE + Style.BRIGHT} {proxy} {Style.RESET_ALL}")
            is_valid = await self.check_connection(proxy)
            if not is_valid:
                if self.rotate_proxy:
                    self.rotate_proxy_for_account(address)
                    await asyncio.sleep(1)
                    continue
                return False
            return True

    async def print_timer(self):
        for remaining in range(random.randint(self.min_delay, self.max_delay), 0, -1):
            print(
                f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
                f"{Fore.BLUE + Style.BRIGHT}Wait For{Style.RESET_ALL}"
                f"{Fore.WHITE + Style.BRIGHT} {remaining} {Style.RESET_ALL}"
                f"{Fore.BLUE + Style.BRIGHT}Seconds For Next Tx...{Style.RESET_ALL}",
                end="\r", flush=True
            )
            await asyncio.sleep(1)

    def print_question(self):
        while True:
            try:
                print(f"{Fore.GREEN + Style.BRIGHT}Select Option:{Style.RESET_ALL}")
                print(f"{Fore.WHITE + Style.BRIGHT}1. Faucet (USDG & Stock Tokens){Style.RESET_ALL}")
                print(f"{Fore.WHITE + Style.BRIGHT}2. Auto Subscribe COUPON{Style.RESET_ALL}")
                print(f"{Fore.WHITE + Style.BRIGHT}3. Auto Subscribe SHIELD{Style.RESET_ALL}")
                print(f"{Fore.WHITE + Style.BRIGHT}4. Claim Coupons{Style.RESET_ALL}")
                print(f"{Fore.WHITE + Style.BRIGHT}5. Redeem / Refund Terminal (exit){Style.RESET_ALL}")
                print(f"{Fore.WHITE + Style.BRIGHT}6. Check Balances & Positions{Style.RESET_ALL}")
                print(f"{Fore.WHITE + Style.BRIGHT}7. Run All (Farming Loop){Style.RESET_ALL}")
                option = int(input(f"{Fore.BLUE + Style.BRIGHT}Choose [1-7] -> {Style.RESET_ALL}").strip())

                if option in range(1, 8):
                    labels = {1: "Faucet", 2: "Auto Subscribe COUPON", 3: "Auto Subscribe SHIELD",
                              4: "Claim Coupons", 5: "Redeem / Refund Terminal", 6: "Check Balances",
                              7: "Run All (Farming Loop)"}
                    print(f"{Fore.GREEN + Style.BRIGHT}{labels[option]} Selected.{Style.RESET_ALL}")
                    self.option = option
                    break
                print(f"{Fore.RED + Style.BRIGHT}Please enter a number between 1 and 7.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter a number (1-7).{Style.RESET_ALL}")

        if self.option in (1, 2, 3, 6, 7):
            self.ask_underlyings()
        if self.option in (2, 7):
            self.coupon_amount = self.ask_amount("Coupon Amount [USDG]", 100)
        if self.option in (3, 7):
            self.stock_amount = self.ask_amount("Shield Stock Amount [shares]", 10)

        self.print_delay_question()
        self.print_loop_question()

        while True:
            try:
                print(f"{Fore.WHITE + Style.BRIGHT}1. Run With Proxy{Style.RESET_ALL}")
                print(f"{Fore.WHITE + Style.BRIGHT}2. Run Without Proxy{Style.RESET_ALL}")
                proxy_choice = int(input(f"{Fore.BLUE + Style.BRIGHT}Choose [1/2] -> {Style.RESET_ALL}").strip())
                if proxy_choice in [1, 2]:
                    self.use_proxy = proxy_choice == 1
                    print(f"{Fore.GREEN + Style.BRIGHT}Run {'With' if self.use_proxy else 'Without'} Proxy Selected.{Style.RESET_ALL}")
                    break
                print(f"{Fore.RED + Style.BRIGHT}Please enter either 1 or 2.{Style.RESET_ALL}")
            except ValueError:
                print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter a number (1 or 2).{Style.RESET_ALL}")

        if self.use_proxy:
            while True:
                rotate = input(f"{Fore.BLUE + Style.BRIGHT}Rotate Invalid Proxy? [y/n] -> {Style.RESET_ALL}").strip().lower()
                if rotate in ["y", "n"]:
                    self.rotate_proxy = rotate == "y"
                    break
                print(f"{Fore.RED + Style.BRIGHT}Invalid input. Enter 'y' or 'n'.{Style.RESET_ALL}")

    def load_all_series_ids(self):
        try:
            accounts = self._load_accounts()
            if not accounts:
                return []
            private_key = accounts[0]
            address = self.generate_address(private_key)
            if not address:
                return []
            web3 = Web3(Web3.HTTPProvider(self.RPC_URL, request_kwargs={"timeout": 30}))
            core = web3.eth.contract(address=Web3.to_checksum_address(self.NOTECORE), abi=self.NOTECORE_ABI)
            count = core.functions.seriesCount().call()
            return list(range(1, count + 1))
        except Exception as e:
            self.log(f"{Fore.YELLOW+Style.BRIGHT}Warning: could not enumerate series ids: {str(e)[:120]}{Style.RESET_ALL}")
            return []

    @staticmethod
    def load_dotenv(path=".env"):
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#") or "=" not in line:
                        continue
                    if line.startswith("export "):
                        line = line[7:].strip()
                    key, value = line.split("=", 1)
                    key = key.strip()
                    value = value.strip().strip('"').strip("'")
                    os.environ.setdefault(key, value)
            return True
        except Exception:
            return False

    def _load_accounts(self):
        raw = os.environ.get("NOTE_ACCOUNTS", "").strip()
        if raw:
            return [k.strip() for k in re.split(r"[,\s;]+", raw) if k.strip()]
        for key in ("ACCOUNTS", "PRIVATE_KEYS", "ACCOUNT_KEYS"):
            raw = os.environ.get(key, "").strip()
            if raw:
                return [k.strip() for k in re.split(r"[,\s;]+", raw) if k.strip()]
        if os.path.exists("accounts.txt"):
            with open("accounts.txt", "r") as file:
                return [line.strip() for line in file if line.strip() and not line.startswith("#")]
        return []

    async def main(self):
        self.load_dotenv()

        accounts = self._load_accounts()
        if not accounts:
            self.log(f"{Fore.RED}No accounts found. Set NOTE_ACCOUNTS in .env or export it.{Style.RESET_ALL}")
            return

        if self.auto:
            cfg = self.load_config()
            env_map = {
                "NOTE_OPTION": ("option", int),
                "NOTE_UNDERLYINGS": ("underlyings", str),
                "NOTE_COUPON": ("coupon_amount", float),
                "NOTE_STOCK": ("stock_amount", float),
                "NOTE_MIN_DELAY": ("min_delay", int),
                "NOTE_MAX_DELAY": ("max_delay", int),
                "NOTE_LOOP": ("loop_hours", float),
                "NOTE_PROXY": ("use_proxy", lambda v: v.strip().lower() in ("1", "true", "yes", "y", "on")),
            }
            for key, (field, cast) in env_map.items():
                if key in os.environ:
                    try:
                        cfg[field] = cast(os.environ[key])
                    except ValueError:
                        self.log(f"{Fore.YELLOW + Style.BRIGHT}Warning: bad value for {key}{Style.RESET_ALL}")
            cfg = self.parse_auto_args(cfg)
            self.apply_config(cfg)
            self.print_auto_config()
        else:
            self.print_question()

        if self.use_proxy:
            await self.load_proxies()

        while True:
            self.clear_terminal()
            self.welcome()
            self.log(f"{Fore.GREEN + Style.BRIGHT}Account's Total: {Style.RESET_ALL}"
                     f"{Fore.WHITE + Style.BRIGHT}{len(accounts)}{Style.RESET_ALL}")

            all_series_ids = self.load_all_series_ids()
            self.log(f"{Fore.GREEN + Style.BRIGHT}Series Found: {Style.RESET_ALL}"
                     f"{Fore.WHITE + Style.BRIGHT}{len(all_series_ids)}{Style.RESET_ALL}")

            separator = "=" * 25
            for account in accounts:
                if not account:
                    continue
                address = self.generate_address(account)
                self.log(f"{Fore.CYAN + Style.BRIGHT}{separator}[{Style.RESET_ALL}"
                         f"{Fore.WHITE + Style.BRIGHT} {self.mask_account(address)} {Style.RESET_ALL}"
                         f"{Fore.CYAN + Style.BRIGHT}]{separator}{Style.RESET_ALL}")

                if not address:
                    self.log(f"{Fore.RED + Style.BRIGHT}Status    : Invalid Private Key{Style.RESET_ALL}")
                    continue

                is_valid = True
                if self.use_proxy:
                    is_valid = await self.process_check_connection(address)
                if is_valid:
                    await self.process_account(account, address, all_series_ids)
                await asyncio.sleep(3)

            if self.loop_hours <= 0:
                break

            self.log(f"{Fore.CYAN + Style.BRIGHT}={Style.RESET_ALL}" * 72)
            seconds = int(self.loop_hours * 3600)
            while seconds > 0:
                formatted_time = self.format_seconds(seconds)
                print(
                    f"{Fore.CYAN+Style.BRIGHT}[ Wait for{Style.RESET_ALL}"
                    f"{Fore.WHITE+Style.BRIGHT} {formatted_time} {Style.RESET_ALL}"
                    f"{Fore.CYAN+Style.BRIGHT}... ]{Style.RESET_ALL}"
                    f"{Fore.WHITE+Style.BRIGHT} | {Style.RESET_ALL}"
                    f"{Fore.BLUE+Style.BRIGHT}All Accounts Have Been Processed. Next Loop Soon.{Style.RESET_ALL}",
                    end="\r"
                )
                await asyncio.sleep(1)
                seconds -= 1

        self.log(f"{Fore.GREEN+Style.BRIGHT}Done. Loop finished.{Style.RESET_ALL}")

if __name__ == "__main__":
    try:
        bot = NoteSystems()
        bot.auto = True
        asyncio.run(bot.main())
    except KeyboardInterrupt:
        print(
            f"{Fore.CYAN + Style.BRIGHT}[ {datetime.now().astimezone(wib).strftime('%x %X %Z')} ]{Style.RESET_ALL}"
            f"{Fore.WHITE + Style.BRIGHT} | {Style.RESET_ALL}"
            f"{Fore.RED + Style.BRIGHT}[ EXIT ] Note Systems Testnet - BOT{Style.RESET_ALL}"
        )
