# voucher_redemption_system
A project in Advance Programming

# Porject Background

# How to Run the System

The system consists of two parts: the backend API server and the front-end UI.

## Step 1:
Open a terminal and run:
python cdc_api.py

Do NOT close this terminal. If the API server stops, the system will stop working.

## Step 2:
Open a separate terminal and run:
python CDC_ui.py

This launches the Flet-based UI program for household and merchant operations.
You can also open several terminal and run the programs simultaneously to check the flow between them. 

---------------------------------------
# Source Files Description

## cdc_api.py
Flask-based API server.

## CDC_ui.py
Flet-based user interface.
Provides household and merchant interface and connects to backend API.

-------------------------------------------------
# Data Files Description

There is already some data in the files to make it easier for you to test if needed.

## activations.json
Stores barcode-based activation records.

Example:
{
"barcode": "1866497212352",
"household_id": "H0001",
"voucher_codes": ["V10-0003-H0001","V10-0004-H0001"],
"total_amount": 20,
"timestamp": "2026-02-05 20:05:47",
"status": "pending"
}

Purpose:
Maps barcode to selected vouchers for later redemption.

## households.csv
Stores FIN and Household_ID mapping.

Format:
FIN,Household_ID

Purpose:
Ensures each household has a unique system ID.

## merchants.csv
Stores merchant registration information.

Includes:
Merchant_ID
Merchant_Name
UEN
Bank details
Registration date
Status

## RedeemXXXXXXXX.csv
Hourly redemption export file.
Used for reimbursement processing.

## transactions.csv
Complete transaction log.
Records every redeemed voucher with:
Transaction_ID
Household_ID
Merchant_ID
Voucher_Code
Amount
Payment_Status
Remarks

Provides full audit trail.

## voucher_state.json
Stores voucher usage status per household.

Structure:
Each household contains:
  80 vouchers of $2
  32 vouchers of $5
  45 vouchers of $10

Each voucher is represented as:
  0 = unused
  1 = used

This prevents double redemption.

------------------------------------
# Voucher Code Format

Each voucher follows the format:
V{denomination}-{index}-{household_id}

Example:
V10-0003-H0001

Activation generates a unique barcode that maps to a list of voucher codes.
During redemption:
  Barcode is validated
  Voucher status is checked
  Voucher state is updated
  Transaction is logged
  System Design Summary

----------------------------------------------
# System Architecture

## The system follows a layered architecture:
  Presentation layer (Flet UI)
  Application layer (Flask API)
  Business logic layer (OOP managers and domain models)
  Persistence layer (CSV and JSON flat files)

## Key managers:
  HouseholdManager
  MerchantManager
  ActivationManager
  TransactionManager

This design ensures separation of concerns, traceability, and data consistency.
