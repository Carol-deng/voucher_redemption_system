# voucher_redemption_system

## 📌 项目简介

本项目基于新加坡 CDC Voucher 政策背景，设计并实现了一个完整的电子消费券兑换系统。系统支持家庭账户注册、商户注册、消费券申领与核销，并通过后端 API 与前端交互实现数据流转。项目采用分层架构设计，结合 OOP 与数据结构优化，实现了高可扩展性与数据一致性，适用于真实业务场景中的电子券管理与交易系统。

---

## 📖 Project Background

This project is developed based on Singapore’s CDC Voucher Scheme, where households receive government-issued vouchers to support daily expenses. The vouchers are distributed in multiple tranches and can be redeemed across registered merchants.

The system simulates a real-world voucher redemption ecosystem, including:

* Household registration and voucher claiming
* Merchant onboarding and reimbursement tracking
* Voucher activation, validation, and redemption
* Transaction recording and audit trail

The key challenge lies in designing efficient in-memory data structures and ensuring data consistency across operations, especially under system restarts.

---

## ⚙️ System Architecture

The system follows a layered architecture:

* **Presentation Layer**: Flet UI
* **Application Layer**: Flask API
* **Business Logic Layer**: OOP managers
* **Persistence Layer**: CSV and JSON

### Key Components

* HouseholdManager
* MerchantManager
* ActivationManager
* TransactionManager

### Design Advantages

* Separation of concerns
* Scalability
* Traceability
* Data consistency

---

## 🚀 How to Run the System

The system consists of two parts: backend API and frontend UI.

### Step 1: Start Backend API

```bash
python cdc_api.py
```

⚠️ Do NOT close this terminal.

---

### Step 2: Start Frontend UI

```bash
python CDC_ui.py
```

* Launches Flet-based UI
* Supports household and merchant operations
* Multiple instances can simulate workflow

---

## 📂 Source Files Description

### cdc_api.py

Flask-based backend API that handles business logic and data processing.

### CDC_ui.py

Flet-based frontend interface that connects to backend APIs.

---

## 🗄️ Data Files Description

### activations.json

Stores barcode activation records and maps vouchers to households.

### households.csv

Maps FIN to Household ID to ensure unique identification.

### merchants.csv

Contains merchant registration and banking information.

### transactions.csv

Full transaction log for audit purposes.

### RedeemXXXXXXXX.csv

Hourly redemption export for reimbursement processing.

### voucher_state.json

Tracks voucher usage per household to prevent double redemption.

---

## 🧾 Voucher Code Format

Each voucher follows the format:

```
V{denomination}-{index}-{household_id}
```

Example:

```
V10-0003-H0001
```

### Redemption Flow

1. Barcode validation
2. Voucher status check
3. State update
4. Transaction logging

---

## 🔄 System Workflow

1. Household registers and claims vouchers
2. System generates voucher codes and barcode
3. Merchant scans or inputs barcode
4. Backend validates and processes redemption
5. Transaction recorded for audit

---

## 💡 Key Features

* Modular OOP design
* Efficient in-memory data handling
* Persistent storage with flat files
* Prevention of double redemption
* Full transaction traceability
* Real-world government voucher simulation

---

## 🏷️ Tech Stack

* Python
* Flask
* Flet
* CSV / JSON
* Object-Oriented Programming
