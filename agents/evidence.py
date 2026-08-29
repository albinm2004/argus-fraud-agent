"""Human-readable descriptions for the feature set, used to turn SHAP
attribution into an evidence chain a person (or a judge) can actually read.

Kaggle deliberately doesn't disclose exact semantics for the C1-C14 /
D1-D15 / M1-M9 columns (obfuscated for the competition), so descriptions
for those are honest about being general-purpose signals, not invented
precise meanings. The graph-proxy features are ours, so those get exact
descriptions.
"""

DESCRIPTIONS = {
    "card1_freq": "this card number appears in {v:.0f} other transactions in the training window",
    "addr1_freq": "this billing address appears in {v:.0f} other transactions in the training window",
    "card1_addr1_freq": "this exact card+address pairing appears in {v:.0f} transactions — a direct shared-instrument signal",
    "TransactionAmt": "transaction amount is {v:.2f}",
    "R_emaildomain": "recipient email domain code {v:.0f}",
    "P_emaildomain": "purchaser email domain code {v:.0f}",
    "card6": "card type code {v:.0f} (credit/debit/charge)",
    "card4": "card network code {v:.0f}",
    "DeviceType": "device type code {v:.0f}",
    "DeviceInfo": "device fingerprint code {v:.0f}",
    "ProductCD": "product category code {v:.0f}",
}
for i in range(1, 15):
    DESCRIPTIONS[f"C{i}"] = f"velocity/count signal C{i} = " + "{v:.1f} (Kaggle doesn't disclose exact semantics — treated as a general velocity signal)"
for i in range(1, 16):
    DESCRIPTIONS[f"D{i}"] = f"time-delta signal D{i} = " + "{v:.1f} days (exact reference event undisclosed by the dataset)"
for i in range(1, 10):
    DESCRIPTIONS[f"M{i}"] = f"match-flag signal M{i} = " + "{v:.0f}"


def describe_feature(name: str, value: float) -> str:
    template = DESCRIPTIONS.get(name)
    if template:
        try:
            return template.format(v=value)
        except (ValueError, TypeError):
            pass
    return f"{name} = {value:.3f}"
