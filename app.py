from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage, QuickReply, QuickReplyButton, MessageAction, FollowEvent
from admin import admin_bp
import cloudinary
import cloudinary.api
import json
import random

app = Flask(__name__)
app.secret_key = "cortis_secret_key_2024"
app.jinja_env.filters['enumerate_filter'] = enumerate
app.register_blueprint(admin_bp)

LINE_CHANNEL_ACCESS_TOKEN = "ujdeAR3vg69UCK5O1PzsAUJZ7+2+F/LhSfFNFhxXS2Ub9qPCOAP8YIyF6kqkQVSTKWx+Ub6TLM86iaKWzQWsT8/Ydhxni6lLiebM0r2fgIZogZ9Vs0OeScbflivz25boSv1Z7gqpvVCow86BtIz0hQdB04t89/1O/w1cDnyilFU="
LINE_CHANNEL_SECRET = "24bcf7e8a3ea43d79b9bc3f92f5e1ca7"

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(LINE_CHANNEL_SECRET)

cloudinary.config(
    cloud_name = "dit5qaskn",
    api_key = "884238881999119",
    api_secret = "AuRL0GbacVjVqft9s1Smc9iQWsQ"
)

MSG_HELP = "🎴 有點東西 使用說明\n\n主選單按鈕直接點就好！"
MSG_UNKNOWN = "敲什麼敲！點下方按鈕來抽卡啦 😤🎴"
MSG_NO_PHOTO = "目前這個系列還沒有照片，請稍後再試！"

def load_config():
    with open("config.json", encoding="utf-8") as f:
        return json.load(f)

def get_photos(folder):
    try:
        result = cloudinary.api.resources_by_asset_folder(folder, max_results=100)
        return [r["secure_url"] for r in result["resources"]]
    except:
        return []

def collect_photos_from_items(items):
    """遞迴收集一組選單項目下所有照片"""
    all_photos = []
    for item in items:
        folder = item.get("folder", "")
        if folder:
            all_photos.extend(get_photos(folder))
        if item.get("children"):
            all_photos.extend(collect_photos_from_items(item["children"]))
    return all_photos

def make_quick_reply(items):
    return QuickReply(items=[
        QuickReplyButton(action=MessageAction(label=item["label"], text=item["text"]))
        for item in items
    ])

def main_quick_reply():
    config = load_config()
    # 主選單加上「全部隨機」按鈕
    labels = config["main_labels"] + [{"label": "🎲 全部隨機", "text": "__全部隨機__"}]
    return make_quick_reply(labels)

def find_menu_item(menus, text):
    for menu_key, items in menus.items():
        for item in items:
            if item["text"] == text:
                return item, menu_key, None
            for child in item.get("children", []):
                if child["text"] == text:
                    return child, menu_key, item
    return None, None, None

def reply_with_photo(event, img_url):
    line_bot_api.reply_message(
        event.reply_token,
        ImageSendMessage(
            original_content_url=img_url,
            preview_image_url=img_url,
            quick_reply=main_quick_reply()
        )
    )

def draw_random_from_photos(event, photos):
    if not photos:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=MSG_NO_PHOTO, quick_reply=main_quick_reply())
        )
        return
    reply_with_photo(event, random.choice(photos))

@app.route("/webhook", methods=["POST"])
def webhook():
    signature = request.headers["X-Line-Signature"]
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return "OK"

@handler.add(FollowEvent)
def handle_follow(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(
            text="👋 歡迎來到有點東西！\n點下方按鈕開始抽卡吧！",
            quick_reply=main_quick_reply()
        )
    )

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    config = load_config()
    menus = config.get("menus", {})
    msg = event.message.text.strip()

    # 主選單全部隨機 → 抽所有系列所有照片
    if msg == "__全部隨機__":
        all_photos = []
        for items in menus.values():
            all_photos.extend(collect_photos_from_items(items))
        # 也包含沒有子選單的主標題
        for label_item in config["main_labels"]:
            t = label_item["text"]
            if t not in menus and t not in ["說明", "help"]:
                all_photos.extend(get_photos(t))
        draw_random_from_photos(event, all_photos)
        return

    # 子選單隨機（格式：{parent}_隨機）
    if msg.endswith("_隨機"):
        parent_text = msg.replace("_隨機", "")
        if parent_text in menus:
            photos = collect_photos_from_items(menus[parent_text])
            draw_random_from_photos(event, photos)
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=MSG_NO_PHOTO, quick_reply=main_quick_reply())
            )
        return

    # 子子選單隨機（格式：{sub_label}_子隨機）
    if msg.endswith("_子隨機"):
        sub_label = msg.replace("_子隨機", "")
        for items in menus.values():
            for item in items:
                if item["label"] == sub_label and item.get("children"):
                    photos = collect_photos_from_items(item["children"])
                    draw_random_from_photos(event, photos)
                    return
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=MSG_NO_PHOTO, quick_reply=main_quick_reply())
        )
        return

    # 檢查主選單指令
    for label_item in config["main_labels"]:
        if msg == label_item["text"]:
            if msg in menus:
                children = menus[msg]
                random_btn = {"label": "🎲 隨機", "text": f"{msg}_隨機"}
                back_btn = {"label": "🔙 返回", "text": "說明"}
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(
                        text="請選擇類別：",
                        quick_reply=make_quick_reply(children + [random_btn, back_btn])
                    )
                )
            elif msg == "說明":
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=MSG_HELP, quick_reply=main_quick_reply())
                )
            else:
                photos = get_photos(msg)
                if not photos:
                    line_bot_api.reply_message(
                        event.reply_token,
                        TextSendMessage(text=MSG_NO_PHOTO, quick_reply=main_quick_reply())
                    )
                else:
                    reply_with_photo(event, random.choice(photos))
            return

    # 檢查子選單指令
    menu_item, parent_key, parent_item = find_menu_item(menus, msg)
    if menu_item:
        children = menu_item.get("children", [])
        if children:
            # 有子子選單 → 顯示子子選單 + 隨機按鈕
            random_btn = {"label": "🎲 隨機", "text": f"{menu_item['label']}_子隨機"}
            back_btn = {"label": "🔙 返回", "text": "說明"}
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"請選擇{menu_item['label']}的系列：",
                    quick_reply=make_quick_reply(children + [random_btn, back_btn])
                )
            )
        else:
            folder = menu_item.get("folder", "")
            photos = get_photos(folder) if folder else []
            if not photos:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=MSG_NO_PHOTO, quick_reply=main_quick_reply())
                )
                return
            reply_with_photo(event, random.choice(photos))
        return

    # 其他訊息
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=MSG_UNKNOWN, quick_reply=main_quick_reply())
    )

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)