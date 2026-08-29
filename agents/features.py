"""Shared feature engineering — used by training, scoring, and the red-team
attack, so all three stay consistent with each other by construction."""
import pandas as pd

TX_COLS = [
    "TransactionID", "isFraud", "TransactionDT", "TransactionAmt",
    "ProductCD", "card1", "card2", "card3", "card4", "card5", "card6",
    "addr1", "addr2", "dist1", "dist2", "P_emaildomain", "R_emaildomain",
] + [f"C{i}" for i in range(1, 15)] + [f"D{i}" for i in range(1, 16)] + [f"M{i}" for i in range(1, 10)]

ID_COLS = ["TransactionID", "DeviceType", "DeviceInfo", "id_01", "id_02", "id_05", "id_06"]

CAT_COLS = ["ProductCD", "card4", "card6", "P_emaildomain", "R_emaildomain",
            "M1", "M2", "M3", "M4", "M5", "M6", "M7", "M8", "M9",
            "DeviceType", "DeviceInfo"]

DROP_COLS = ["TransactionID", "isFraud", "TransactionDT"]

# Perturbable, judgment-relevant continuous features a fraudster could
# realistically shape (amount, recency/velocity deltas, counts) — used by
# the red-team attack. Deliberately excludes graph-proxy and card/addr
# identity fields: those aren't something a single fraudulent actor can
# cheaply fabricate transaction-to-transaction.
PERTURBABLE_COLS = ["TransactionAmt"] + [f"C{i}" for i in range(1, 15)] + [f"D{i}" for i in range(1, 16)]


def load_raw(raw_dir="data/raw/ieee-fraud-detection"):
    tx = pd.read_csv(f"{raw_dir}/train_transaction.csv", usecols=TX_COLS)
    idn = pd.read_csv(f"{raw_dir}/train_identity.csv", usecols=ID_COLS)
    return tx.merge(idn, on="TransactionID", how="left").sort_values("TransactionDT").reset_index(drop=True)


def add_graph_proxy_features(train_df, full_df):
    out = full_df.copy()
    for col in ["card1", "addr1"]:
        freq = train_df[col].value_counts()
        out[f"{col}_freq"] = out[col].map(freq).fillna(0)
    card_addr = train_df["card1"].astype(str) + "_" + train_df["addr1"].astype(str)
    card_addr_freq = card_addr.value_counts()
    full_card_addr = out["card1"].astype(str) + "_" + out["addr1"].astype(str)
    out["card1_addr1_freq"] = full_card_addr.map(card_addr_freq).fillna(0)
    return out


def encode_categoricals(df):
    df = df.copy()
    for c in CAT_COLS:
        df[c] = df[c].astype("category").cat.codes
    return df


def build_dataset(raw_dir="data/raw/ieee-fraud-detection", split=0.8):
    df = load_raw(raw_dir)
    split_idx = int(len(df) * split)
    train_df = df.iloc[:split_idx]
    df = add_graph_proxy_features(train_df, df)
    df = encode_categoricals(df)
    feature_cols = [c for c in df.columns if c not in DROP_COLS]
    return df, feature_cols, split_idx
