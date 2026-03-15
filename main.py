import json, requests, time, os
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
    if not os.path.exists(file): return []
    try:
        with open(file, 'r') as f: return json.load(f)
    except: return []

def save_db(file, data):
    with open(file, 'w') as f: json.dump(data, f)

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
    # Render-এ রিয়েল ক্লায়েন্ট আইপি পাওয়ার জন্য x-forwarded-for ব্যবহার করা হয়
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
    
    # SMS লজিক এখানে কল হবে (apis.json থেকে)
    return jsonify({"code": 200, "status": "ATTACK_SENT", "target": target})

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
