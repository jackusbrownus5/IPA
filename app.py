import os
import tempfile
import zipfile
import plistlib
from flask import Flask, request, jsonify, send_from_directory
import threading
import time

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 300 * 1024 * 1024

BASE_URL = os.environ.get("BASE_URL", "https://ipa-installer.onrender.com")

def extract_info_plist(ipa_path):
    try:
        with zipfile.ZipFile(ipa_path, 'r') as z:
            for name in z.namelist():
                if name.startswith('Payload/') and name.endswith('.app/Info.plist'):
                    return plistlib.loads(z.read(name))
    except Exception as e:
        print("Error reading IPA:", e)
    return None

def create_manifest(plist_info, ipa_url):
    bundle_id = plist_info.get('CFBundleIdentifier', 'com.example.unknown')
    version = plist_info.get('CFBundleShortVersionString') or plist_info.get('CFBundleVersion', '1.0')
    title = plist_info.get('CFBundleDisplayName') or plist_info.get('CFBundleName') or 'App'
    manifest = {
        "items": [{
            "assets": [{"kind": "software-package", "url": ipa_url}],
            "metadata": {
                "bundle-identifier": bundle_id,
                "bundle-version": version,
                "kind": "software",
                "title": title
            }
        }]
    }
    return plistlib.dumps(manifest)

def schedule_delete(*paths, delay=300):
    def delete_files():
        time.sleep(delay)
        for p in paths:
            try:
                os.remove(p)
            except:
                pass
    threading.Thread(target=delete_files, daemon=True).start()

@app.route('/upload', methods=['POST'])
def upload():
    if 'ipa' not in request.files:
        return jsonify({"error": "No IPA selected"}), 400
    f = request.files['ipa']
    if not f.filename.lower().endswith('.ipa'):
        return jsonify({"error": "File must be .ipa"}), 400

    tmp_fd, tmp_path = tempfile.mkstemp(suffix='.ipa')
    os.close(tmp_fd)
    f.save(tmp_path)

    info = extract_info_plist(tmp_path)
    if not info:
        os.remove(tmp_path)
        return jsonify({"error": "Info.plist not found"}), 400

    ipa_name = f"{info.get('CFBundleIdentifier','app')}-{info.get('CFBundleVersion','1.0')}.ipa"
    ipa_path = os.path.join(UPLOAD_DIR, ipa_name)
    os.rename(tmp_path, ipa_path)

    ipa_url = f"{BASE_URL}/files/{ipa_name}"
    manifest_bytes = create_manifest(info, ipa_url)
    manifest_name = ipa_name.replace('.ipa', '.plist')
    manifest_path = os.path.join(UPLOAD_DIR, manifest_name)
    with open(manifest_path, 'wb') as m:
        m.write(manifest_bytes)

    install_link = f"itms-services://?action=download-manifest&url={BASE_URL}/files/{manifest_name}"

    schedule_delete(ipa_path, manifest_path, delay=300)

    return jsonify({
        "title": info.get('CFBundleDisplayName') or info.get('CFBundleName'),
        "install_link": install_link
    })

@app.route('/files/<path:filename>')
def serve_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
