from flask import Blueprint, render_template, request, redirect, url_for, session, jsonify
import cloudinary
import cloudinary.uploader
import cloudinary.api
import json
import os

admin_bp = Blueprint('admin', __name__)

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "cortis1234"

CONFIG_PATH = "config.json"

FOLDER_NAMES = {
    "common": "日常系列",
    "rare": "演唱會系列",
    "super_rare": "特典系列",
    "limited": "限定系列",
    "meme_cute": "可愛梗圖",
    "meme_savage": "嗆聲梗圖",
    "meme_abstract": "抽象梗圖",
    "soup": "心靈雞湯",
}

def load_config():
    if not os.path.exists(CONFIG_PATH):
        default = {
            "main_labels": [
                {"label": "🎴 抽小卡", "text": "抽小卡"},
                {"label": "😂 抽梗圖", "text": "抽梗圖"},
                {"label": "🍵 抽雞湯", "text": "抽雞湯"},
                {"label": "📖 說明", "text": "說明"}
            ],
            "menus": {}
        }
        save_config(default)
        return default
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def collect_all_folders(config):
    """從 config 收集所有需要顯示的資料夾"""
    all_folders = set()

    def collect_from_items(items):
        for item in items:
            folder = item.get("folder") or item.get("text", "")
            if folder and folder not in ["說明", "help"]:
                all_folders.add(folder)
            if item.get("children"):
                collect_from_items(item["children"])

    # 主選單沒有子選單的按鈕
    for label_item in config.get("main_labels", []):
        text = label_item["text"]
        if text not in ["說明", "help"] and text not in config.get("menus", {}):
            all_folders.add(text)

    # 子選單和子子選單
    for items in config.get("menus", {}).values():
        collect_from_items(items)

    return all_folders

@admin_bp.route('/admin')
def admin_index():
    if not session.get('logged_in'):
        return redirect(url_for('admin.admin_login'))

    config = load_config()
    all_folders = collect_all_folders(config)

    folder_info = {}
    for folder in all_folders:
        try:
            result = cloudinary.api.resources_by_asset_folder(folder, max_results=100)
            photos = result["resources"]
            folder_info[folder] = {
                "name": FOLDER_NAMES.get(folder, folder),
                "count": len(photos),
                "photos": [{"url": p["secure_url"], "id": p["public_id"]} for p in photos]
            }
        except:
            folder_info[folder] = {
                "name": FOLDER_NAMES.get(folder, folder),
                "count": 0,
                "photos": []
            }

    return render_template('admin.html', folder_info=folder_info)

@admin_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin.admin_index'))
        return render_template('login.html', error="帳號或密碼錯誤！")
    return render_template('login.html', error=None)

@admin_bp.route('/admin/logout')
def admin_logout():
    session.pop('logged_in', None)
    return redirect(url_for('admin.admin_login'))

@admin_bp.route('/admin/upload', methods=['POST'])
def admin_upload():
    if not session.get('logged_in'):
        return jsonify({"success": False, "error": "未登入"})
    folder = request.form.get('folder')
    files = request.files.getlist('photos')
    uploaded = []
    for file in files:
        if file.filename:
            try:
                result = cloudinary.uploader.upload(
                    file,
                    folder=folder,
                    use_asset_folder_as_public_id_prefix=True
                )
                uploaded.append(result["secure_url"])
                print(f"✅ 上傳成功：{result['secure_url']}")
            except Exception as e:
                print(f"❌ 上傳失敗：{e}")
                return jsonify({"success": False, "error": str(e)}), 400
    return jsonify({"success": True, "uploaded": len(uploaded)})

@admin_bp.route('/admin/delete', methods=['POST'])
def admin_delete():
    if not session.get('logged_in'):
        return jsonify({"success": False, "error": "未登入"})
    public_id = request.form.get('public_id')
    cloudinary.uploader.destroy(public_id)
    return jsonify({"success": True})

# ── Label 管理 ──────────────────────────────

@admin_bp.route('/admin/labels')
def admin_labels():
    if not session.get('logged_in'):
        return redirect(url_for('admin.admin_login'))
    config = load_config()
    all_folders = collect_all_folders(config)
    folders = [{"key": k, "name": FOLDER_NAMES.get(k, k)} for k in all_folders]
    return render_template('labels.html', config=config, folders=folders)

@admin_bp.route('/admin/labels/main/add', methods=['POST'])
def admin_main_add():
    if not session.get('logged_in'):
        return jsonify({"success": False})
    label = request.form.get('label')
    text = request.form.get('text')
    config = load_config()
    config['main_labels'].append({"label": label, "text": text})
    save_config(config)
    try:
        cloudinary.api.create_folder(text)
    except:
        pass
    return jsonify({"success": True})

@admin_bp.route('/admin/labels/main/delete', methods=['POST'])
def admin_main_delete():
    if not session.get('logged_in'):
        return jsonify({"success": False})
    index = int(request.form.get('index'))
    config = load_config()
    deleted_item = config['main_labels'][index]
    deleted_text = deleted_item['text']
    
    config['main_labels'].pop(index)
    
    # 同時刪除對應的子選單
    sub_items = config.get('menus', {}).pop(deleted_text, [])
    save_config(config)
    
    # 刪除主標題對應的 Cloudinary 資料夾
    try:
        cloudinary.api.delete_folder(deleted_text)
        print(f"✅ 已刪除主資料夾：{deleted_text}")
    except Exception as e:
        print(f"⚠️ 主資料夾刪除失敗：{e}")
    
    # 刪除所有子標題對應的 Cloudinary 資料夾
    def delete_folders(items):
        for item in items:
            folder = item.get("folder") or item.get("text", "")
            if folder:
                try:
                    cloudinary.api.delete_folder(folder)
                    print(f"✅ 已刪除子資料夾：{folder}")
                except Exception as e:
                    print(f"⚠️ 子資料夾刪除失敗：{e}")
            if item.get("children"):
                delete_folders(item["children"])
    
    delete_folders(sub_items)
    
    return jsonify({"success": True})

@admin_bp.route('/admin/labels/main/update', methods=['POST'])
def admin_main_update():
    if not session.get('logged_in'):
        return jsonify({"success": False})
    index = int(request.form.get('index'))
    label = request.form.get('label')
    text = request.form.get('text')
    config = load_config()
    old_text = config['main_labels'][index]['text']
    config['main_labels'][index] = {"label": label, "text": text}
    if old_text in config.get('menus', {}) and old_text != text:
        config['menus'][text] = config['menus'].pop(old_text)
    save_config(config)
    return jsonify({"success": True})

@admin_bp.route('/admin/labels/sub/add', methods=['POST'])
def admin_sub_add():
    if not session.get('logged_in'):
        return jsonify({"success": False})
    parent_text = request.form.get('parent_text')
    label = request.form.get('label')
    text = request.form.get('text')
    folder = request.form.get('folder', '')
    config = load_config()
    if 'menus' not in config:
        config['menus'] = {}
    if parent_text not in config['menus']:
        config['menus'][parent_text] = []
    config['menus'][parent_text].append({
        "label": label,
        "text": text,
        "folder": folder if folder else text,
        "children": []
    })
    save_config(config)
    try:
        target_folder = folder if folder else text
        cloudinary.api.create_folder(target_folder)
        print(f"✅ 成功建立資料夾：{target_folder}")
    except Exception as e:
        print(f"❌ 建立資料夾失敗：{e}")
    return jsonify({"success": True})

@admin_bp.route('/admin/labels/sub/delete', methods=['POST'])
def admin_sub_delete():
    if not session.get('logged_in'):
        return jsonify({"success": False})
    parent_text = request.form.get('parent_text')
    index = int(request.form.get('index'))
    config = load_config()
    
    # 取得要刪除的資料夾名稱
    deleted_item = config['menus'][parent_text][index]
    folder = deleted_item.get("folder") or deleted_item.get("text", "")
    
    config['menus'][parent_text].pop(index)
    save_config(config)
    
    # 自動刪除 Cloudinary 資料夾
    try:
        cloudinary.api.delete_folder(folder)
        print(f"✅ 已刪除資料夾：{folder}")
    except Exception as e:
        print(f"⚠️ 資料夾刪除失敗（可能裡面還有照片）：{e}")
    
    return jsonify({"success": True})

@admin_bp.route('/admin/labels/sub/update', methods=['POST'])
def admin_sub_update():
    if not session.get('logged_in'):
        return jsonify({"success": False})
    parent_text = request.form.get('parent_text')
    index = int(request.form.get('index'))
    label = request.form.get('label')
    text = request.form.get('text')
    folder = request.form.get('folder', '')
    config = load_config()
    config['menus'][parent_text][index]['label'] = label
    config['menus'][parent_text][index]['text'] = text
    config['menus'][parent_text][index]['folder'] = folder
    save_config(config)
    return jsonify({"success": True})

@admin_bp.route('/admin/labels/subsub/add', methods=['POST'])
def admin_subsub_add():
    if not session.get('logged_in'):
        return jsonify({"success": False})
    parent_text = request.form.get('parent_text')
    sub_index = int(request.form.get('sub_index'))
    label = request.form.get('label')
    text = request.form.get('text')
    folder = request.form.get('folder', '')
    config = load_config()
    config['menus'][parent_text][sub_index]['children'].append({
        "label": label,
        "text": text,
        "folder": folder if folder else text
    })
    save_config(config)
    try:
        target_folder = folder if folder else text
        cloudinary.api.create_folder(target_folder)
    except:
        pass
    return jsonify({"success": True})

@admin_bp.route('/admin/labels/subsub/delete', methods=['POST'])
def admin_subsub_delete():
    if not session.get('logged_in'):
        return jsonify({"success": False})
    parent_text = request.form.get('parent_text')
    sub_index = int(request.form.get('sub_index'))
    child_index = int(request.form.get('child_index'))
    config = load_config()
    
    # 取得要刪除的資料夾名稱
    deleted_item = config['menus'][parent_text][sub_index]['children'][child_index]
    folder = deleted_item.get("folder") or deleted_item.get("text", "")
    
    config['menus'][parent_text][sub_index]['children'].pop(child_index)
    save_config(config)
    
    # 自動刪除 Cloudinary 資料夾
    try:
        cloudinary.api.delete_folder(folder)
        print(f"✅ 已刪除資料夾：{folder}")
    except Exception as e:
        print(f"⚠️ 資料夾刪除失敗（可能裡面還有照片）：{e}")
    
    return jsonify({"success": True})

@admin_bp.route('/admin/labels/subsub/update', methods=['POST'])
def admin_subsub_update():
    if not session.get('logged_in'):
        return jsonify({"success": False})
    parent_text = request.form.get('parent_text')
    sub_index = int(request.form.get('sub_index'))
    child_index = int(request.form.get('child_index'))
    label = request.form.get('label')
    text = request.form.get('text')
    folder = request.form.get('folder', '')
    config = load_config()
    config['menus'][parent_text][sub_index]['children'][child_index] = {
        "label": label,
        "text": text,
        "folder": folder
    }
    save_config(config)
    return jsonify({"success": True})

@admin_bp.route('/admin/labels/get_folders')
def admin_get_folders():
    if not session.get('logged_in'):
        return jsonify({"success": False})
    config = load_config()
    all_folders = collect_all_folders(config)
    folders = [{"key": k, "name": FOLDER_NAMES.get(k, k)} for k in all_folders]
    return jsonify({"success": True, "folders": folders})