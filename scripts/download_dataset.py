"""Pulls the IEEE-CIS Fraud Detection (or PaySim) dataset via the Kaggle API.

Requires KAGGLE_USERNAME / KAGGLE_KEY in .env, or a ~/.kaggle/kaggle.json.

Usage:
    python scripts/download_dataset.py --dataset ieee-cis
    python scripts/download_dataset.py --dataset paysim
"""
import argparse

DATASETS = {
    "ieee-cis": "c/ieee-fraud-detection",
    "paysim": "d/ealaxi/paysim1",
}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", choices=DATASETS.keys(), default="ieee-cis")
    args = parser.parse_args()
    print(f"TODO: kaggle {DATASETS[args.dataset]} download -p data/raw/ (competitions vs datasets API differs)")
