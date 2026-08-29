"""Quick EDA pass over IEEE-CIS to sanity-check the graph/entity plan.

Run: python scripts/eda_summary.py
Writes a short summary to stdout (and docs/eda_findings.md documents the
numbers from the first run, dated, so they don't have to be regenerated
just to read them).
"""
import pandas as pd

RAW = "data/raw/ieee-fraud-detection"

ENTITY_COLS = [
    "TransactionID", "isFraud", "TransactionDT", "TransactionAmt",
    "card1", "card2", "card3", "card4", "card5", "card6",
    "addr1", "addr2", "P_emaildomain", "R_emaildomain",
]


def main():
    tx = pd.read_csv(f"{RAW}/train_transaction.csv", usecols=ENTITY_COLS)
    idn = pd.read_csv(f"{RAW}/train_identity.csv", usecols=["TransactionID", "DeviceType", "DeviceInfo"])

    print(f"transactions: {len(tx):,}")
    print(f"fraud rate: {tx['isFraud'].mean() * 100:.3f}%")
    print(f"unique card1: {tx['card1'].nunique():,}")
    print(f"unique addr1: {tx['addr1'].nunique():,}  (missing {tx['addr1'].isna().mean() * 100:.1f}%)")
    print(f"unique P_emaildomain: {tx['P_emaildomain'].nunique():,}  (missing {tx['P_emaildomain'].isna().mean() * 100:.1f}%)")
    print(f"transactions with identity/device match: {tx['TransactionID'].isin(idn['TransactionID']).mean() * 100:.1f}%")


if __name__ == "__main__":
    main()
