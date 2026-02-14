import requests
import base64
import re
import socket
import time
import concurrent.futures
import datetime

# --- CONFIG ---
SOURCE_URLS = [
    "https://raw.githubusercontent.com/mahdibland/V2RayAggregator/master/Eternity",
    "https://raw.githubusercontent.com/barry-far/V2ray-Config/main/Sub1.txt"
]
OUTPUT_SUB = "sub.txt"
OUTPUT_HTML = "index.html"
TOP_N = 40
TIMEOUT = 1.5
MAX_WORKERS = 50

# --- HTML TEMPLATE ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>V2Ray Status Dashboard</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: sans-serif; background: #0d1117; color: #c9d1d9; max-width: 800px; margin: 0 auto; padding: 20px; }}
        h1 {{ color: #58a6ff; text-align: center; }}
        .update-time {{ text-align: center; color: #8b949e; margin-bottom: 20px; }}
        .card {{ background: #161b22; border: 1px solid #30363d; border-radius: 6px; padding: 20px; margin-bottom: 20px; }}
        .btn {{ display: block; width: 100%; padding: 10px; background: #238636; color: white; border: none; border-radius: 6px; font-size: 16px; cursor: pointer; text-decoration: none; text-align: center; }}
        .btn:hover {{ background: #2ea043; }}
        table {{ width: 100%; border-collapse: collapse; margin-top: 10px; }}
        th, td {{ padding: 10px; text-align: left; border-bottom: 1px solid #21262d; }}
        th {{ color: #8b949e; }}
        .latency {{ color: #3fb950; font-weight: bold; }}
        .copy-btn {{ background: #1f6feb; font-size: 12px; padding: 5px 10px; width: auto; display: inline-block; }}
    </style>
</head>
<body>
    <h1>🚀 Active Server Dashboard</h1>
    <div class="update-time">Last Updated: {timestamp} (UTC)</div>

    <div class="card">
        <h3>📋 Quick Action</h3>
        <p>Use this link in v2rayNG / v2rayN:</p>
        <code style="display:block; background:#000; padding:10px; border-radius:5px; word-break:break-all;">
            https://raw.githubusercontent.com/kopyie/v2ray-scanner/refs/heads/main/sub.txt
        </code>
    </div>

    <div class="card">
        <h3>✅ Top {count} Working Servers</h3>
        <table>
            <thead>
                <tr>
                    <th>#</th>
                    <th>IP Address</th>
                    <th>Port</th>
                    <th>Ping</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
    </div>
</body>
</html>
"""

def get_servers():
    all_lines = []
    print("Downloading lists...")
    for url in SOURCE_URLS:
        try:
            resp = requests.get(url, timeout=10)
            content = resp.text.strip()
            # Basic Base64 check
            if "vmess://" not in content and len(content) > 100 and " " not in content:
                try:
                    content = base64.b64decode(content).decode('utf-8', errors='ignore')
                except:
                    pass
            all_lines.extend(content.splitlines())
        except:
            pass
    return list(set(all_lines)) # Remove duplicates

def parse_config(line):
    # Find IP and Port
    match = re.search(r"[:/@]([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})[:](\d+)", line)
    if match:
        return {"ip": match.group(1), "port": int(match.group(2)), "config": line}
    return None

def check_speed(server):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        start = time.time()
        result = sock.connect_ex((server['ip'], server['port']))
        sock.close()
        if result == 0:
            latency = int((time.time() - start) * 1000)
            return (latency, server)
    except:
        pass
    return None

def main():
    # 1. Get List
    raw_lines = get_servers()
    parsed_servers = []
    for line in raw_lines[:1500]: # Limit scan
        res = parse_config(line)
        if res: parsed_servers.append(res)
    
    print(f"Scanning {len(parsed_servers)} candidates...")

    # 2. Scan
    valid_proxies = []
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = executor.map(check_speed, parsed_servers)
        for r in results:
            if r: valid_proxies.append(r)
    
    # 3. Sort & Select
    valid_proxies.sort(key=lambda x: x[0])
    top_proxies = valid_proxies[:TOP_N]
    
    print(f"Found {len(top_proxies)} working servers.")

    # 4. Generate SUB.TXT (Base64)
    final_text = "\n".join([x[1]['config'] for x in top_proxies])
    b64_sub = base64.b64encode(final_text.encode("utf-8")).decode("utf-8")
    with open(OUTPUT_SUB, "w") as f:
        f.write(b64_sub)

    # 5. Generate INDEX.HTML (Dashboard)
    table_rows = ""
    for i, (lat, srv) in enumerate(top_proxies):
        table_rows += f"""
        <tr>
            <td>{i+1}</td>
            <td>{srv['ip']}</td>
            <td>{srv['port']}</td>
            <td class="latency">{lat} ms</td>
        </tr>
        """
    
    # Get Username/Repo from environment or placeholder
    # NOTE: You must replace 'YOUR_USERNAME' and 'YOUR_REPO' manually below if running locally
    # But GitHub Pages will host it at username.github.io/repo
    
    html_content = HTML_TEMPLATE.format(
        timestamp=datetime.datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        count=len(top_proxies),
        table_rows=table_rows,
        username="YOUR_GITHUB_USERNAME", # <--- CHANGE THIS later or let user handle it
        repo="YOUR_REPO_NAME"           # <--- CHANGE THIS
    )
    
    with open(OUTPUT_HTML, "w") as f:
        f.write(html_content)

if __name__ == "__main__":
    main()
