from card_generator import draw_card, PHOTOS
import cloudinary
import cloudinary.uploader
import json, os

cloudinary.config(
    cloud_name = "dit5qaskn",
    api_key = "884238881999119",
    api_secret = "AuRL0GbacVjVqft9s1Smc9iQWsQ"
)

# 讀取已經生成過的網址記錄
if os.path.exists("card_urls.json"):
    with open("card_urls.json") as f:
        existing = json.load(f)
else:
    existing = {k: [] for k in PHOTOS.keys()}

# 讀取來源照片記錄
if os.path.exists("source_urls.json"):
    with open("source_urls.json") as f:
        old_sources = json.load(f)
else:
    old_sources = {k: [] for k in PHOTOS.keys()}

card_urls = existing.copy()

for rarity_key, photos in PHOTOS.items():
    new_photos = [p for p in photos if p not in old_sources.get(rarity_key, [])]
    
    if not new_photos:
        print(f"{rarity_key}：沒有新照片，跳過")
        continue
    
    print(f"\n{rarity_key}：發現 {len(new_photos)} 張新照片！")
    
    for i, photo_url in enumerate(new_photos):
        img, series_name = draw_card(rarity_key, photo_url, len(card_urls[rarity_key]) + i + 1)
        
        os.makedirs("cards", exist_ok=True)
        path = f"cards/new_{rarity_key}_{i}.png"
        img.save(path)
        
        result = cloudinary.uploader.upload(path)
        url = result["secure_url"]
        card_urls[rarity_key].append(url)
        print(f"  ✅ {series_name} 新增完成")

with open("card_urls.json", "w") as f:
    json.dump(card_urls, f, indent=2)

with open("source_urls.json", "w") as f:
    json.dump(dict(PHOTOS), f, indent=2)

print("\n🎉 完成！")