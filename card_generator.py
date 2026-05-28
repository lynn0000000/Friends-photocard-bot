from PIL import Image, ImageDraw, ImageFont
import os, requests
from io import BytesIO
import cloudinary
import cloudinary.api

cloudinary.config(
    cloud_name = "dit5qaskn",
    api_key = "884238881999119",
    api_secret = "AuRL0GbacVjVqft9s1Smc9iQWsQ"
)

def get_photos_from_folder(folder):
    try:
        result = cloudinary.api.resources_by_asset_folder(
            folder,
            max_results=100
        )
        return [r["secure_url"] for r in result["resources"]]
    except Exception as e:
        print(f"資料夾 {folder} 抓取失敗：{e}")
        return []

PHOTOS = {
    "common":        get_photos_from_folder("common"),
    "rare":          get_photos_from_folder("rare"),
    "super_rare":    get_photos_from_folder("super_rare"),
    "limited":       get_photos_from_folder("limited"),
    "meme_cute":     get_photos_from_folder("meme_cute"),
    "meme_savage":   get_photos_from_folder("meme_savage"),
    "meme_abstract": get_photos_from_folder("meme_abstract"),
    "soup":          get_photos_from_folder("soup"),
}

CARD_W = 650
CARD_H = 1004

RARITIES = {
    "common": {
        "name": "日常系列",
        "label": "COMMON",
        "bg": (240, 237, 232),
        "border": (58, 48, 40),
        "text": (58, 48, 40),
    },
    "rare": {
        "name": "演唱會系列",
        "label": "★ RARE",
        "bg": (245, 240, 255),
        "border": (91, 63, 158),
        "text": (91, 63, 158),
    },
    "super_rare": {
        "name": "特典系列",
        "label": "★★ SUPER RARE",
        "bg": (253, 248, 236),
        "border": (154, 114, 0),
        "text": (122, 88, 0),
    },
    "limited": {
        "name": "限定系列",
        "label": "★★★ LIMITED",
        "bg": (13, 13, 13),
        "border": (232, 224, 208),
        "text": (232, 224, 208),
    },
    "soup": {
        "name": "心靈雞湯系列",
        "label": "🍵 SOUL SOUP",
        "bg": (255, 245, 230),
        "border": (180, 120, 50),
        "text": (140, 80, 20),
    }
}

def get_font(size, bold=False):
    font_paths = [
        "C:/Windows/Fonts/msjh.ttc",
        "C:/Windows/Fonts/msjhbd.ttc",
        "C:/Windows/Fonts/mingliu.ttc",
        "C:/Windows/Fonts/kaiu.ttf",
    ]
    for path in font_paths:
        if os.path.exists(path):
            try:
                return ImageFont.truetype(path, size)
            except:
                continue
    return ImageFont.load_default()

def fetch_photo(url):
    res = requests.get(url)
    img = Image.open(BytesIO(res.content)).convert("RGB")
    return img

def draw_card(rarity_key, photo_url, card_number):
    rarity = RARITIES[rarity_key]
    border_color = rarity["border"]
    text_color = rarity["text"]

    img = Image.new("RGB", (CARD_W, CARD_H), rarity["bg"])
    draw = ImageDraw.Draw(img)

    if rarity_key == "soup":
        photo_left = 0
        photo_top = 0
        photo_right = CARD_W
        photo_bottom = CARD_H
    else:
        photo_left = 40
        photo_top = 110
        photo_right = CARD_W - 40
        photo_bottom = CARD_H - 180

    photo_w = photo_right - photo_left
    photo_h = photo_bottom - photo_top

    try:
        photo = fetch_photo(photo_url)
        if rarity_key == "soup":
            img = photo
        else:
            pw, ph = photo.size
            target_ratio = photo_w / photo_h
            source_ratio = pw / ph
            if source_ratio > target_ratio:
                new_w = int(ph * target_ratio)
                left = (pw - new_w) // 2
                photo = photo.crop((left, 0, left + new_w, ph))
            else:
                new_h = int(pw / target_ratio)
                top = (ph - new_h) // 2
                photo = photo.crop((0, top, pw, top + new_h))
            photo = photo.resize((photo_w, photo_h), Image.LANCZOS)
            img.paste(photo, (photo_left, photo_top))
    except Exception as e:
        print(f"照片載入失敗：{e}")

    if rarity_key not in ["soup"]:
        font_title = get_font(36, bold=True)
        font_sub = get_font(18)
        font_series = get_font(28)
        font_small = get_font(20)
        font_tiny = get_font(16)

        draw.rounded_rectangle(
            [10, 10, CARD_W-10, CARD_H-10],
            radius=24, outline=border_color, width=5
        )
        draw.rounded_rectangle(
            [22, 22, CARD_W-22, CARD_H-22],
            radius=18, outline=border_color, width=1
        )
        draw.text((CARD_W//2, 52), "CORTIS",
                  fill=text_color, font=font_title, anchor="mm")
        draw.text((CARD_W//2, 80), "COLOR OUTSIDE THE LINES",
                  fill=text_color, font=font_sub, anchor="mm")
        draw.line([(40, 100), (CARD_W-40, 100)], fill=border_color, width=1)
        draw.line([(40, photo_bottom+10), (CARD_W-40, photo_bottom+10)],
                  fill=border_color, width=1)
        draw.text((CARD_W//2, photo_bottom+40), rarity["name"],
                  fill=text_color, font=font_series, anchor="mm")
        draw.line([(40, photo_bottom+60), (CARD_W-40, photo_bottom+60)],
                  fill=border_color, width=1)
        draw.text((44, photo_bottom+80), f"NO. {card_number:03d}",
                  fill=text_color, font=font_small)
        draw.text((CARD_W-44, photo_bottom+80), "COER COLLECTION",
                  fill=text_color, font=font_small, anchor="ra")
        draw.text((CARD_W//2, CARD_H-38), rarity["label"],
                  fill=text_color, font=font_tiny, anchor="mm")
        corner_size = 14
        for cx, cy in [(38, 28), (CARD_W-52, 28), (38, CARD_H-42), (CARD_W-52, CARD_H-42)]:
            draw.rectangle([cx, cy, cx+corner_size, cy+corner_size],
                           outline=border_color, width=1)

    return img, rarity["name"]