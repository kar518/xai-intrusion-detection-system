from pathlib import Path

import pandas as pd
from sklearn.model_selection import train_test_split


ROOT = Path(__file__).resolve().parents[2]

INPUT_FILE = ROOT / "data" / "processed" / "cleaned_data.csv"
OUTPUT_DIR = ROOT / "data" / "processed"

RANDOM_STATE = 42
TEST_SIZE = 0.20


def main():
    print("Loading cleaned dataset...")
    df = pd.read_csv(INPUT_FILE, low_memory=False)

    # Keep only attack flows.
    attacks = df[df["Attack"] == 1].copy()

    print(f"Total attack flows: {len(attacks):,}")
    print("\nAttack distribution:")
    print(attacks["Label"].value_counts().to_string())

    # Extremely small classes cannot reliably be stratified.
    # Keep them in the dataset, but separate them for now.
    counts = attacks["Label"].value_counts()

    stratifiable_labels = counts[counts >= 2].index
    stratifiable = attacks[attacks["Label"].isin(stratifiable_labels)].copy()
    tiny = attacks[~attacks["Label"].isin(stratifiable_labels)].copy()

    train_df, test_df = train_test_split(
        stratifiable,
        test_size=TEST_SIZE,
        random_state=RANDOM_STATE,
        stratify=stratifiable["Label"],
    )

    # Tiny classes remain in training so the classifier can at least
    # see them. They will not be used for the stratified test set.
    train_df = pd.concat([train_df, tiny], ignore_index=True)

    train_path = OUTPUT_DIR / "attack_train.csv"
    test_path = OUTPUT_DIR / "attack_test.csv"

    train_df.to_csv(train_path, index=False)
    test_df.to_csv(test_path, index=False)

    print("\n" + "=" * 70)
    print("ATTACK-TYPE SPLIT COMPLETE")
    print("=" * 70)

    print(f"Training attack flows: {len(train_df):,}")
    print(f"Testing attack flows:  {len(test_df):,}")

    print("\nTRAIN:")
    print(train_df["Label"].value_counts().to_string())

    print("\nTEST:")
    print(test_df["Label"].value_counts().to_string())

    print(f"\nTraining file: {train_path}")
    print(f"Testing file:  {test_path}")


if __name__ == "__main__":
    main()
