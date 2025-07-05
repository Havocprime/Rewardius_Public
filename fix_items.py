import json

YOUR_REAL_USER_ID = "777039317918679070"

with open("items.json", "r") as f:
    items = json.load(f)

for item in items:
    owner = item.get("owner")
    if isinstance(owner, str):
        if owner.lower() in ["ez", "havocprime"]:
            item["owner"] = YOUR_REAL_USER_ID
    else:
        item["owner"] = YOUR_REAL_USER_ID  # Default if owner was None

with open("items.json", "w") as f:
    json.dump(items, f, indent=4)

print("✅ Owners fixed and saved.")
