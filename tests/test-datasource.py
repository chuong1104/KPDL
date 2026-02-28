from datasets import load_dataset

# Chỉ tải 5 records đầu (streaming mode - không tải toàn bộ)
review_ds = load_dataset(
    "McAuley-Lab/Amazon-Reviews-2023",
    "raw_review_Electronics",
    split="full",
    streaming=True,
    trust_remote_code=True
)

print("=== REVIEW SCHEMA ===")
for i, record in enumerate(review_ds):
    if i >= 2:
        break
    print(f"\n--- Record {i+1} ---")
    for k, v in record.items():
        print(f"  {k:20s} ({type(v).__name__:8s}): {str(v)[:100]}")

# Metadata
meta_ds = load_dataset(
    "McAuley-Lab/Amazon-Reviews-2023",
    "raw_meta_Electronics",
    split="full",
    streaming=True,
    trust_remote_code=True
)

print("\n=== META SCHEMA ===")
for i, record in enumerate(meta_ds):
    if i >= 2:
        break
    print(f"\n--- Record {i+1} ---")
    for k, v in record.items():
        print(f"  {k:20s} ({type(v).__name__:8s}): {str(v)[:100]}")