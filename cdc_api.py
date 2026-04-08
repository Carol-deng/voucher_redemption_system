from flask import Flask, request, jsonify
from flask_cors import CORS
import csv
import json
import os
import re
import random
import base64
from datetime import datetime
from typing import Dict, List, Optional
import barcode
from barcode.writer import ImageWriter
from io import BytesIO

app = Flask(__name__)
CORS(app)

# ================== Configuration ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

PATH_HOUSEHOLDS = os.path.join(DATA_DIR, "households.csv")
PATH_VOUCHER_STATE = os.path.join(DATA_DIR, "voucher_state.json")
PATH_ACTIVATIONS = os.path.join(DATA_DIR, "activations.json")
PATH_BARCODES = os.path.join(DATA_DIR, "barcodes")
PATH_TRANSACTIONS = os.path.join(DATA_DIR, "transactions.csv")
PATH_MERCHANTS = os.path.join(DATA_DIR, "merchants.csv")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(PATH_BARCODES, exist_ok=True)

# ================== OOP Classes ==================

class Voucher:
    """Represents a single voucher with denomination and status"""
    def __init__(self, code: str, denomination: int, household_id: str, index: int):
        self.code = code
        self.denomination = denomination
        self.household_id = household_id
        self.index = index
        self.is_used = False
    
    def use(self):
        """Mark voucher as used"""
        self.is_used = True
    
    def to_dict(self):
        """Convert voucher to dictionary"""
        return {
            "code": self.code,
            "denomination": self.denomination,
            "status": "used" if self.is_used else "available"
        }

class Household:
    """Represents a household with vouchers"""
    FIN_NRIC_PATTERN = re.compile(r"^[STFGM]\d{7}[A-Z]$")
    
    def __init__(self, household_id: str, fin: str):
        self.household_id = household_id
        self.fin = fin
        self.vouchers: Dict[int, List[Voucher]] = {}  # denomination -> list of vouchers
        self._initialize_vouchers()
    
    def _initialize_vouchers(self):
        """Initialize vouchers with default denominations"""
        voucher_config = {2: 80, 5: 32, 10: 45}
        for denom, count in voucher_config.items():
            self.vouchers[denom] = []
            for i in range(count):
                code = f"V{denom:02d}-{i+1:04d}-{self.household_id}"
                voucher = Voucher(code, denom, self.household_id, i)
                self.vouchers[denom].append(voucher)
    
    def get_balance(self) -> int:
        """Calculate total available balance"""
        total = 0
        for denom, voucher_list in self.vouchers.items():
            for voucher in voucher_list:
                if not voucher.is_used:
                    total += denom
        return total
    
    def get_available_vouchers(self) -> List[Voucher]:
        """Get all available (unused) vouchers"""
        available = []
        for voucher_list in self.vouchers.values():
            for voucher in voucher_list:
                if not voucher.is_used:
                    available.append(voucher)
        return available
    
    def get_voucher_by_code(self, code: str) -> Optional[Voucher]:
        """Find voucher by code"""
        for voucher_list in self.vouchers.values():
            for voucher in voucher_list:
                if voucher.code == code:
                    return voucher
        return None
    
    def get_breakdown(self) -> Dict:
        """Get breakdown of available vouchers by denomination"""
        breakdown = {}
        for denom, voucher_list in self.vouchers.items():
            available = sum(1 for v in voucher_list if not v.is_used)
            breakdown[str(denom)] = {
                "available": available,
                "value": available * denom
            }
        return breakdown
    
    def to_state_dict(self) -> Dict:
        """Convert to state dictionary for persistence"""
        state = {}
        for denom, voucher_list in self.vouchers.items():
            state[str(denom)] = [1 if v.is_used else 0 for v in voucher_list]
        return state
    
    def load_state(self, state: Dict):
        """Load voucher state from dictionary"""
        for denom_str, status_list in state.items():
            denom = int(denom_str)
            if denom in self.vouchers:
                for i, status in enumerate(status_list):
                    if i < len(self.vouchers[denom]):
                        self.vouchers[denom][i].is_used = (status == 1)
    
    @staticmethod
    def validate_fin(fin: str) -> bool:
        """Validate FIN/NRIC format"""
        return bool(Household.FIN_NRIC_PATTERN.match(fin))

class BankInfo:
    """Represents bank information"""
    BANK_CODES = {
        "DBS Bank Ltd": {"code": "7171", "branch": "001", "swift": "DBSSSGSG"},
        "OCBC Bank": {"code": "7339", "branch": "501", "swift": "OCBCSGSG"},
        "UOB Bank": {"code": "7761", "branch": "001", "swift": "UOVBSGSG"},
        "POSB Bank": {"code": "7171", "branch": "081", "swift": "DBSSSGSG"},
        "Maybank Singapore": {"code": "7091", "branch": "001", "swift": "MBBESGSG"},
        "Standard Chartered Bank": {"code": "7302", "branch": "001", "swift": "SCBLSGSG"},
        "HSBC Singapore": {"code": "7375", "branch": "146", "swift": "HSBCSGSG"},
        "Citibank Singapore": {"code": "9465", "branch": "001", "swift": "CITISGSG"},
    }
    
    def __init__(self, bank_name: str):
        if bank_name not in self.BANK_CODES:
            raise ValueError(f"Invalid bank: {bank_name}")
        self.bank_name = bank_name
        info = self.BANK_CODES[bank_name]
        self.code = info["code"]
        self.branch = info["branch"]
        self.swift = info["swift"]

class Merchant:
    """Represents a merchant"""
    def __init__(self, merchant_id: str, name: str, uen: str, bank_info: BankInfo,
                 account_number: str, account_holder: str, registration_date: str):
        self.merchant_id = merchant_id
        self.name = name
        self.uen = uen
        self.bank_info = bank_info
        self.account_number = account_number
        self.account_holder = account_holder
        self.registration_date = registration_date
        self.status = "Active"
    
    def to_dict(self):
        """Convert merchant to dictionary"""
        return {
            "Merchant_ID": self.merchant_id,
            "Merchant_Name": self.name,
            "UEN": self.uen,
            "Bank_Name": self.bank_info.bank_name,
            "Bank_Code": self.bank_info.code,
            "Branch_Code": self.bank_info.branch,
            "Account_Number": self.account_number,
            "Account_Holder_Name": self.account_holder,
            "Registration_Date": self.registration_date,
            "Status": self.status
        }
    
    @staticmethod
    def validate_account_number(account_number: str) -> bool:
        """Validate account number is exactly 9 digits"""
        return account_number.isdigit() and len(account_number) == 9

class Transaction:
    """Represents a transaction"""
    def __init__(self, transaction_id: str, household_id: str, merchant_id: str,
                 voucher_codes: List[str], total_amount: int, timestamp: str):
        self.transaction_id = transaction_id
        self.household_id = household_id
        self.merchant_id = merchant_id
        self.voucher_codes = voucher_codes
        self.total_amount = total_amount
        self.timestamp = timestamp
        self.status = "Completed"
    
    def to_csv_rows(self) -> List[List]:
        """Convert transaction to CSV rows (one row per voucher)"""
        rows = []
        for i, code in enumerate(self.voucher_codes):
            # Extract denomination from voucher code
            denom = int(code.split("-")[0][1:])
            is_final = (i == len(self.voucher_codes) - 1)
            rows.append([
                self.transaction_id,
                self.household_id,
                self.merchant_id,
                self.timestamp,
                code,
                f"${denom}.00",
                f"${self.total_amount}.00",
                self.status,
                "Final denomination used" if is_final else str(i + 1)
            ])
        return rows

class VoucherActivation:
    """Represents a voucher activation (barcode generation)"""
    def __init__(self, barcode: str, household_id: str, voucher_codes: List[str], 
                 total_amount: int, timestamp: str):
        self.barcode = barcode
        self.household_id = household_id
        self.voucher_codes = voucher_codes
        self.total_amount = total_amount
        self.timestamp = timestamp
        self.status = "pending"
        self.redeemed_at = None
        self.merchant_id = None
        self.transaction_id = None
    
    def redeem(self, merchant_id: str, transaction_id: str):
        """Mark activation as redeemed"""
        self.status = "redeemed"
        self.merchant_id = merchant_id
        self.transaction_id = transaction_id
        self.redeemed_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    def to_dict(self):
        """Convert to dictionary"""
        data = {
            "barcode": self.barcode,
            "household_id": self.household_id,
            "voucher_codes": self.voucher_codes,
            "total_amount": self.total_amount,
            "timestamp": self.timestamp,
            "status": self.status
        }
        if self.redeemed_at:
            data["redeemed_at"] = self.redeemed_at
            data["merchant_id"] = self.merchant_id
            data["transaction_id"] = self.transaction_id
        return data

# ================== Manager Classes (Data Structures) ==================

class HouseholdManager:
    """Manages households using HashMap (dict) for O(1) lookup"""
    def __init__(self):
        self.households: Dict[str, Household] = {}  # household_id -> Household
        self.fin_to_household_id: Dict[str, str] = {}  # FIN -> household_id (HashMap)
    
    def register_household(self, fin: str) -> tuple:
        """Register new household or return existing"""
        fin = fin.strip().upper()
        
        if not Household.validate_fin(fin):
            return None, "Invalid FIN/NRIC format"
        
        # Check if already exists (O(1) lookup)
        if fin in self.fin_to_household_id:
            household_id = self.fin_to_household_id[fin]
            return self.households[household_id], None
        
        # Generate new household ID
        household_id = self._generate_household_id()
        household = Household(household_id, fin)
        
        # Store in HashMaps
        self.households[household_id] = household
        self.fin_to_household_id[fin] = household_id
        
        return household, None
    
    def get_household(self, household_id: str) -> Optional[Household]:
        """Get household by ID (O(1) lookup)"""
        return self.households.get(household_id)
    
    def _generate_household_id(self) -> str:
        """Generate next household ID"""
        if not self.households:
            return "H0001"
        max_num = max(int(hid[1:]) for hid in self.households.keys())
        return f"H{max_num + 1:04d}"
    
    def save_to_disk(self):
        """Persist households to disk"""
        # Save household list
        with open(PATH_HOUSEHOLDS, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["FIN", "Household_ID"])
            for fin, hid in self.fin_to_household_id.items():
                writer.writerow([fin, hid])
        
        # Save voucher states
        state_dict = {}
        for hid, household in self.households.items():
            state_dict[hid] = household.to_state_dict()
        
        with open(PATH_VOUCHER_STATE, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, indent=2)
    
    def load_from_disk(self):
        """Load households from disk"""
        # Load household list
        if os.path.exists(PATH_HOUSEHOLDS):
            with open(PATH_HOUSEHOLDS, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    fin = row.get("FIN", "").strip()
                    hid = row.get("Household_ID", "").strip()
                    if fin and hid:
                        household = Household(hid, fin)
                        self.households[hid] = household
                        self.fin_to_household_id[fin] = hid
        
        # Load voucher states
        if os.path.exists(PATH_VOUCHER_STATE):
            with open(PATH_VOUCHER_STATE, encoding="utf-8") as f:
                try:
                    state_dict = json.load(f)
                    for hid, state in state_dict.items():
                        if hid in self.households:
                            self.households[hid].load_state(state)
                except json.JSONDecodeError:
                    pass

class MerchantManager:
    """Manages merchants using HashMap (dict) for O(1) lookup"""
    def __init__(self):
        self.merchants: Dict[str, Merchant] = {}  # merchant_id -> Merchant
        self.account_index: Dict[tuple, str] = {}  # (bank, account) -> merchant_id
    
    def register_merchant(self, name: str, bank_name: str, account_number: str, 
                         account_holder: str) -> tuple:
        """Register new merchant or return existing"""
        # Validate account number
        if not Merchant.validate_account_number(account_number):
            return None, "Account number must be exactly 9 digits"
        
        # Create bank info
        try:
            bank_info = BankInfo(bank_name)
        except ValueError as e:
            return None, str(e)
        
        # Check for exact duplicate (all fields match)
        for merchant in self.merchants.values():
            if (merchant.name == name and 
                merchant.bank_info.bank_name == bank_name and
                merchant.account_number == account_number and
                merchant.account_holder == account_holder):
                return merchant, "already_registered"
        
        # Check if same bank+account exists (different merchant)
        account_key = (bank_name, account_number)
        if account_key in self.account_index:
            return None, "Some details are wrong"
        
        # Generate merchant ID and UEN
        merchant_id = self._generate_merchant_id()
        uen = f"{random.randint(200000000, 299999999)}{chr(random.randint(65, 90))}"
        registration_date = datetime.now().strftime("%Y-%m-%d")
        
        # Create merchant
        merchant = Merchant(merchant_id, name, uen, bank_info, account_number, 
                           account_holder, registration_date)
        
        # Store in HashMaps
        self.merchants[merchant_id] = merchant
        self.account_index[account_key] = merchant_id
        
        return merchant, None
    
    def get_merchant(self, merchant_id: str) -> Optional[Merchant]:
        """Get merchant by ID (O(1) lookup)"""
        return self.merchants.get(merchant_id)
    
    def _generate_merchant_id(self) -> str:
        """Generate next merchant ID"""
        if not self.merchants:
            return "M001"
        max_num = max(int(mid[1:]) for mid in self.merchants.keys())
        return f"M{max_num + 1:03d}"
    
    def save_to_disk(self):
        """Persist merchants to disk"""
        fieldnames = ["Merchant_ID", "Merchant_Name", "UEN", "Bank_Name", "Bank_Code",
                     "Branch_Code", "Account_Number", "Account_Holder_Name",
                     "Registration_Date", "Status"]
        
        with open(PATH_MERCHANTS, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for merchant in self.merchants.values():
                writer.writerow(merchant.to_dict())
    
    def load_from_disk(self):
        """Load merchants from disk"""
        if not os.path.exists(PATH_MERCHANTS):
            return
        
        with open(PATH_MERCHANTS, "r", newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                try:
                    bank_info = BankInfo(row["Bank_Name"])
                    merchant = Merchant(
                        row["Merchant_ID"],
                        row["Merchant_Name"],
                        row["UEN"],
                        bank_info,
                        row["Account_Number"],
                        row["Account_Holder_Name"],
                        row["Registration_Date"]
                    )
                    self.merchants[merchant.merchant_id] = merchant
                    account_key = (row["Bank_Name"], row["Account_Number"])
                    self.account_index[account_key] = merchant.merchant_id
                except Exception:
                    continue

class ActivationManager:
    """Manages voucher activations"""
    def __init__(self):
        self.activations: Dict[str, VoucherActivation] = {}  # barcode -> activation
    
    def create_activation(self, household_id: str, voucher_codes: List[str], 
                         total_amount: int) -> VoucherActivation:
        """Create new activation with barcode"""
        barcode_num = "".join([str(random.randint(0, 9)) for _ in range(13)])
        ean = barcode.get("ean13", barcode_num, writer=ImageWriter())
        
        # Generate barcode image
        buffer = BytesIO()
        ean.write(buffer)
        buffer.seek(0)
        barcode_image = base64.b64encode(buffer.read()).decode("utf-8")
        
        barcode_code = ean.get_fullcode()
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        activation = VoucherActivation(barcode_code, household_id, voucher_codes,
                                      total_amount, timestamp)
        activation.barcode_image = barcode_image
        
        self.activations[barcode_code] = activation
        return activation
    
    def get_activation(self, barcode: str) -> Optional[VoucherActivation]:
        """Get activation by barcode"""
        return self.activations.get(barcode)
    
    def save_to_disk(self):
        """Persist activations to disk"""
        data = [act.to_dict() for act in self.activations.values()]
        with open(PATH_ACTIVATIONS, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    def load_from_disk(self):
        """Load activations from disk"""
        if not os.path.exists(PATH_ACTIVATIONS):
            return
        
        with open(PATH_ACTIVATIONS, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                if not isinstance(data, list):
                    return
                
                for item in data:
                    # Validate required fields exist
                    if not all(key in item for key in ["barcode", "household_id", "voucher_codes", "total_amount", "timestamp"]):
                        continue
                    
                    try:
                        activation = VoucherActivation(
                            item["barcode"],
                            item["household_id"],
                            item["voucher_codes"],
                            item["total_amount"],
                            item["timestamp"]
                        )
                        activation.status = item.get("status", "pending")
                        activation.redeemed_at = item.get("redeemed_at")
                        activation.merchant_id = item.get("merchant_id")
                        activation.transaction_id = item.get("transaction_id")
                        self.activations[activation.barcode] = activation
                    except Exception:
                        # Skip malformed activation records
                        continue
            except (json.JSONDecodeError, Exception):
                # If file is corrupted, start fresh
                pass

class TransactionManager:
    """Manages transactions with efficient storage"""
    def __init__(self):
        self.transactions: Dict[str, Transaction] = {}  # transaction_id -> Transaction
        self.merchant_transactions: Dict[str, List[str]] = {}  # merchant_id -> [tx_ids]
    
    def create_transaction(self, household_id: str, merchant_id: str,
                          voucher_codes: List[str], total_amount: int) -> Transaction:
        """Create new transaction"""
        transaction_id = self._generate_transaction_id()
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        
        transaction = Transaction(transaction_id, household_id, merchant_id,
                                 voucher_codes, total_amount, timestamp)
        
        # Store in HashMap
        self.transactions[transaction_id] = transaction
        
        # Index by merchant
        if merchant_id not in self.merchant_transactions:
            self.merchant_transactions[merchant_id] = []
        self.merchant_transactions[merchant_id].append(transaction_id)
        
        return transaction
    
    def get_merchant_transactions(self, merchant_id: str) -> List[Transaction]:
        """Get all transactions for a merchant (O(1) lookup)"""
        tx_ids = self.merchant_transactions.get(merchant_id, [])
        return [self.transactions[tx_id] for tx_id in tx_ids if tx_id in self.transactions]
    
    def _generate_transaction_id(self) -> str:
        """Generate next transaction ID"""
        if not self.transactions:
            return "TX00001"
        max_num = max(int(tid[2:]) for tid in self.transactions.keys())
        return f"TX{max_num + 1:05d}"
    
    def save_to_disk(self, transaction: Transaction):
        """Persist single transaction to disk (append mode)"""
        headers = ["Transaction_ID", "Household_ID", "Merchant_ID", "Transaction_Date_Time",
                  "Voucher_Code", "Denomination_Used", "Amount_Redeemed", "Payment_Status", "Remarks"]
        
        # Save to main transactions.csv
        file_exists = os.path.exists(PATH_TRANSACTIONS)
        with open(PATH_TRANSACTIONS, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not file_exists:
                writer.writerow(headers)
            for row in transaction.to_csv_rows():
                writer.writerow(row)
        
        # Save to hourly file
        current_hour = datetime.now().strftime("%Y%m%d%H")
        hourly_file = os.path.join(DATA_DIR, f"Redeem{current_hour}.csv")
        
        hourly_exists = os.path.exists(hourly_file)
        with open(hourly_file, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if not hourly_exists:
                writer.writerow(headers)
            for row in transaction.to_csv_rows():
                writer.writerow(row)
    
    def load_from_disk(self):
        """Load transactions from disk"""
        if not os.path.exists(PATH_TRANSACTIONS):
            return
        
        try:
            with open(PATH_TRANSACTIONS, "r", newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                temp_transactions = {}
                
                for row in reader:
                    try:
                        tx_id = row.get("Transaction_ID")
                        if not tx_id:
                            continue
                        
                        if tx_id not in temp_transactions:
                            amount_str = row.get("Amount_Redeemed", "$0.00")
                            amount = int(amount_str.replace("$", "").replace(".00", "").replace(",", ""))
                            
                            temp_transactions[tx_id] = {
                                "household_id": row.get("Household_ID", ""),
                                "merchant_id": row.get("Merchant_ID", ""),
                                "timestamp": row.get("Transaction_Date_Time", ""),
                                "amount": amount,
                                "vouchers": []
                            }
                        temp_transactions[tx_id]["vouchers"].append(row.get("Voucher_Code", ""))
                    except Exception:
                        # Skip malformed rows
                        continue
                
                # Create Transaction objects
                for tx_id, data in temp_transactions.items():
                    try:
                        transaction = Transaction(
                            tx_id,
                            data["household_id"],
                            data["merchant_id"],
                            data["vouchers"],
                            data["amount"],
                            data["timestamp"]
                        )
                        self.transactions[tx_id] = transaction
                        
                        # Index by merchant
                        merchant_id = data["merchant_id"]
                        if merchant_id not in self.merchant_transactions:
                            self.merchant_transactions[merchant_id] = []
                        self.merchant_transactions[merchant_id].append(tx_id)
                    except Exception:
                        # Skip malformed transactions
                        continue
        except Exception:
            # If file is corrupted, start fresh
            pass

# ================== Initialize Global Managers ==================
household_manager = HouseholdManager()
merchant_manager = MerchantManager()
activation_manager = ActivationManager()
transaction_manager = TransactionManager()

# Load existing data
household_manager.load_from_disk()
merchant_manager.load_from_disk()
activation_manager.load_from_disk()
transaction_manager.load_from_disk()

# ================== API Endpoints ==================

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "ok", "message": "CDC Voucher API is running"})

# ================== Household APIs ==================

@app.route('/api/household/register', methods=['POST'])
def register_household():
    """Register a new household"""
    data = request.get_json()
    fin = data.get('fin', '')
    
    if not fin:
        return jsonify({"success": False, "error": "FIN/NRIC required"}), 400
    
    fin_upper = fin.strip().upper()
    
    # Check if already exists
    is_existing = fin_upper in household_manager.fin_to_household_id
    
    household, error = household_manager.register_household(fin)
    
    if error:
        return jsonify({"success": False, "error": error}), 400
    
    # Save only if new
    if not is_existing:
        household_manager.save_to_disk()
    
    return jsonify({
        "success": True,
        "existing": is_existing,
        "household_id": household.household_id,
        "message": "Household already registered" if is_existing else "Household registered successfully"
    }), 200 if is_existing else 201

@app.route('/api/household/<household_id>/balance', methods=['GET'])
def get_household_balance(household_id):
    """Get voucher balance for a household"""
    household = household_manager.get_household(household_id)
    
    if not household:
        return jsonify({"success": False, "error": "Household not found"}), 404
    
    return jsonify({
        "success": True,
        "household_id": household_id,
        "total_balance": household.get_balance(),
        "breakdown": household.get_breakdown(),
        "voucher_state": household.to_state_dict()
    })

@app.route('/api/household/<household_id>/vouchers', methods=['GET'])
def get_household_vouchers(household_id):
    """Get all vouchers for a household with their status"""
    household = household_manager.get_household(household_id)
    
    if not household:
        return jsonify({"success": False, "error": "Household not found"}), 404
    
    all_vouchers = []
    for voucher_list in household.vouchers.values():
        for voucher in voucher_list:
            all_vouchers.append(voucher.to_dict())
    
    return jsonify({
        "success": True,
        "household_id": household_id,
        "vouchers": all_vouchers
    })

# ================== Voucher Activation APIs ==================

@app.route('/api/voucher/activate', methods=['POST'])
def activate_vouchers():
    """Generate barcode for selected vouchers"""
    data = request.get_json()
    voucher_codes = data.get('voucher_codes', [])
    
    if not voucher_codes:
        return jsonify({"success": False, "error": "No vouchers selected"}), 400
    
    # Validate all vouchers
    household_id = None
    total_amount = 0
    
    for code in voucher_codes:
        # Extract household ID from code
        parts = code.split("-")
        if len(parts) != 3:
            return jsonify({"success": False, "error": f"Invalid voucher code: {code}"}), 400
        
        code_household_id = parts[2]
        
        if household_id is None:
            household_id = code_household_id
        elif household_id != code_household_id:
            return jsonify({"success": False, "error": "All vouchers must belong to same household"}), 400
        
        # Check household exists
        household = household_manager.get_household(household_id)
        if not household:
            return jsonify({"success": False, "error": "Household not found"}), 404
        
        # Check voucher availability
        voucher = household.get_voucher_by_code(code)
        if not voucher:
            return jsonify({"success": False, "error": f"Invalid voucher code: {code}"}), 400
        
        if voucher.is_used:
            return jsonify({"success": False, "error": f"Voucher {code} already used"}), 400
        
        total_amount += voucher.denomination
    
    # Create activation
    activation = activation_manager.create_activation(household_id, voucher_codes, total_amount)
    activation_manager.save_to_disk()
    
    return jsonify({
        "success": True,
        "barcode": activation.barcode,
        "barcode_image": activation.barcode_image,
        "voucher_codes": voucher_codes,
        "total_amount": total_amount
    })

# ================== Merchant APIs ==================

@app.route('/api/merchant/register', methods=['POST'])
def register_merchant():
    """Register a new merchant"""
    data = request.get_json()
    name = data.get('name', '').strip()
    bank = data.get('bank', '').strip()
    account_number = data.get('account_number', '').strip()
    holder_name = data.get('holder_name', '').strip()
    
    if not all([name, bank, account_number, holder_name]):
        return jsonify({"success": False, "error": "All fields required"}), 400
    
    merchant, error = merchant_manager.register_merchant(name, bank, account_number, holder_name)
    
    if error == "already_registered":
        return jsonify({
            "success": True,
            "existing": True,
            "merchant_id": merchant.merchant_id,
            "message": "You are already registered"
        }), 200
    
    if error:
        return jsonify({"success": False, "error": error}), 400
    
    merchant_manager.save_to_disk()
    
    return jsonify({
        "success": True,
        "existing": False,
        "merchant_id": merchant.merchant_id,
        "message": "Merchant registered successfully"
    }), 201

@app.route('/api/merchant/<merchant_id>', methods=['GET'])
def get_merchant(merchant_id):
    """Get merchant details"""
    merchant = merchant_manager.get_merchant(merchant_id)
    
    if not merchant:
        return jsonify({"success": False, "error": "Merchant not found"}), 404
    
    return jsonify({
        "success": True,
        "merchant": merchant.to_dict()
    })

@app.route('/api/merchant/<merchant_id>/redeem', methods=['POST'])
def redeem_vouchers(merchant_id):
    """Redeem vouchers using barcode"""
    data = request.get_json()
    barcode_input = data.get('barcode', '').strip()
    
    if not barcode_input:
        return jsonify({"success": False, "error": "Barcode required"}), 400
    
    # Verify merchant exists
    merchant = merchant_manager.get_merchant(merchant_id)
    if not merchant:
        return jsonify({"success": False, "error": "Merchant not found"}), 404
    
    # Find activation
    activation = activation_manager.get_activation(barcode_input)
    if not activation:
        return jsonify({"success": False, "error": "Invalid barcode"}), 400
    
    if activation.status == "redeemed":
        return jsonify({"success": False, "error": "Barcode already redeemed"}), 400
    
    # Get household
    household = household_manager.get_household(activation.household_id)
    if not household:
        return jsonify({"success": False, "error": "Household not found"}), 404
    
    # Validate and mark vouchers as used
    for code in activation.voucher_codes:
        voucher = household.get_voucher_by_code(code)
        if not voucher:
            return jsonify({"success": False, "error": f"Invalid voucher: {code}"}), 400
        
        if voucher.is_used:
            return jsonify({"success": False, "error": "One or more vouchers already redeemed"}), 400
        
        voucher.use()
    
    # Create transaction
    transaction = transaction_manager.create_transaction(
        activation.household_id,
        merchant_id,
        activation.voucher_codes,
        activation.total_amount
    )
    
    # Mark activation as redeemed
    activation.redeem(merchant_id, transaction.transaction_id)
    
    # Save everything
    household_manager.save_to_disk()
    activation_manager.save_to_disk()
    transaction_manager.save_to_disk(transaction)
    
    return jsonify({
        "success": True,
        "transaction_id": transaction.transaction_id,
        "amount_redeemed": transaction.total_amount,
        "vouchers_count": len(activation.voucher_codes),
        "message": "Redemption successful"
    })

@app.route('/api/merchant/<merchant_id>/transactions', methods=['GET'])
def get_merchant_transactions(merchant_id):
    """Get transaction history for a merchant"""
    transactions = transaction_manager.get_merchant_transactions(merchant_id)
    
    result = []
    for tx in transactions:
        result.append({
            "transaction_id": tx.transaction_id,
            "household_id": tx.household_id,
            "timestamp": tx.timestamp,
            "total_amount": f"${tx.total_amount}.00",
            "status": tx.status,
            "vouchers": [{"code": code, "denomination": f"${int(code.split('-')[0][1:])}.00"} 
                        for code in tx.voucher_codes]
        })
    
    return jsonify({
        "success": True,
        "transactions": result
    })

# ================== Analytics API ==================

@app.route('/api/analytics/summary', methods=['GET'])
def get_analytics_summary():
    """Get system analytics summary"""
    total_households = len(household_manager.households)
    total_merchants = len(merchant_manager.merchants)
    total_transactions = len(transaction_manager.transactions)
    
    # Calculate voucher statistics
    total_vouchers_issued = 0
    total_vouchers_used = 0
    total_value_issued = 0
    total_value_used = 0
    
    for household in household_manager.households.values():
        for denom, voucher_list in household.vouchers.items():
            total_vouchers_issued += len(voucher_list)
            total_value_issued += len(voucher_list) * denom
            used_count = sum(1 for v in voucher_list if v.is_used)
            total_vouchers_used += used_count
            total_value_used += used_count * denom
    
    usage_rate = round(total_vouchers_used / total_vouchers_issued * 100, 2) if total_vouchers_issued > 0 else 0
    
    return jsonify({
        "success": True,
        "summary": {
            "total_households": total_households,
            "total_merchants": total_merchants,
            "total_transactions": total_transactions,
            "vouchers": {
                "total_issued": total_vouchers_issued,
                "total_used": total_vouchers_used,
                "total_available": total_vouchers_issued - total_vouchers_used,
                "usage_rate": usage_rate
            },
            "value": {
                "total_issued": total_value_issued,
                "total_redeemed": total_value_used,
                "total_available": total_value_issued - total_value_used
            }
        }
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080, debug=True)
