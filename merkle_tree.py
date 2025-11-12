import hashlib
import os

def calculate_merkle_root(file_path):
    """Compute the Merkle root of a file's contents."""
    if not os.path.exists(file_path):
        print("ERROR: File does not exist.")
        return None

    try:
        with open(file_path, "rb") as f:
            file_data = f.read()
        if not file_data:
            return None

        # Split file into chunks (modify as needed)
        chunk_size = 1024  
        chunks = [file_data[i:i + chunk_size] for i in range(0, len(file_data), chunk_size)]

        # Hash each chunk
        hashed_chunks = [hashlib.sha256(chunk).hexdigest() for chunk in chunks]

        # Compute Merkle root
        while len(hashed_chunks) > 1:
            if len(hashed_chunks) % 2 == 1:
                hashed_chunks.append(hashed_chunks[-1])  # Duplicate last hash if odd number

            new_level = []
            for i in range(0, len(hashed_chunks), 2):
                new_hash = hashlib.sha256((hashed_chunks[i] + hashed_chunks[i+1]).encode()).hexdigest()
                new_level.append(new_hash)

            hashed_chunks = new_level

        return hashed_chunks[0]
    except Exception as e:
        print(f"ERROR: Exception in calculating Merkle root: {e}")
        return None
