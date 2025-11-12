import hashlib
import json
import os

class NFT:
    def __init__(self, merkle_root, wallet_address):
        self.merkle_root = merkle_root
        self.wallet_address = wallet_address
        self.nft_token = self.generate_nft()

    def generate_nft(self):
        """Generate a unique NFT token using the Merkle root and wallet address."""
        unique_data = f"{self.merkle_root}{self.wallet_address}"
        nft_token = hashlib.sha256(unique_data.encode()).hexdigest()
        self.store_nft_metadata(nft_token)
        return nft_token

    def store_nft_metadata(self, nft_token):
        """Store NFT metadata in a JSON file."""
        metadata = {
            "nft_token": nft_token,
            "merkle_root": self.merkle_root,
            "wallet_address": self.wallet_address
        }
        os.makedirs("nft_metadata", exist_ok=True)
        metadata_path = os.path.join("nft_metadata", f"{nft_token}.json")
        with open(metadata_path, "w") as f:
            json.dump(metadata, f, indent=4)
