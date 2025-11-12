import hashlib
import os
import json

class Wallet:
    WALLET_DIR = "wallets"

    def __init__(self, username):
        self.username = username
        self.wallet_address = self.load_or_create_wallet()

    def generate_wallet_address(self):
        """Generate a unique wallet address using the username."""
        return hashlib.sha256(self.username.encode()).hexdigest()

    def load_or_create_wallet(self):
        """Load an existing wallet or create a new one if it doesn't exist."""
        os.makedirs(self.WALLET_DIR, exist_ok=True)
        wallet_path = os.path.join(self.WALLET_DIR, f"{self.username}.json")

        if os.path.exists(wallet_path):
            with open(wallet_path, "r") as f:
                data = json.load(f)
                return data["wallet_address"]

        wallet_address = self.generate_wallet_address()
        self.save_wallet(wallet_address)
        return wallet_address

    def save_wallet(self, wallet_address):
        """Save the wallet address to a file."""
        wallet_data = {
            "username": self.username,
            "wallet_address": wallet_address
        }
        wallet_path = os.path.join(self.WALLET_DIR, f"{self.username}.json")
        with open(wallet_path, "w") as f:
            json.dump(wallet_data, f, indent=4)

    def get_wallet_address(self):
        """Return the stored wallet address."""
        return self.wallet_address
