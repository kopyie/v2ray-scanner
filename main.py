import requests
import base64
import re
import socket
import time
import concurrent.futures
import json

# --- CONFIGURATION ---
SOURCE_URL = "https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/refs/heads/main/V2Ray-Config-By-EbraSha.txt"
OUTPUT_FILE = "sub.txt"
TOP_N = 40          # Keep top 40 best servers
TIMEOUT = 2         # 2 seconds max latency
MAX_WORKERS = 100   # Scan 100 servers at the same time

def parse_config(line):
    """Extracts IP and Port from mixed config formats"""
    try:
        # Regex to find IP (IPv4) and Port
        # Matches: @192.168.1.1:443 or /192.168.1.1:443
        ip_match = re.search(r"[:/@]([0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3})[:](\d+)", line)
        if ip_match:
            return (ip_match.group(1), int(ip_match.group(2)), line)
    except:
        pass
    return None

def check_speed(server_data):
    """Pings the server. Returns (latency, config_line)"""
    ip, port, original_line = server_data
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        start = time.time()
        # TCP Handshake (Ping)
        result = sock.connect_ex((ip, port))
        sock.close()
        
        if result == 0:
            latency = (time.time() - start) * 1000
            return (latency, original_line)
    except:
        pass
    return (99999, original_line) # Return high latency if failed

def main():
    print("--- 1. Downloading Huge List ---")
    try:
        resp = requests.get(SOURCE_URL, timeout=15)
        raw_lines = [line.strip() for line in resp.text.splitlines() if line.strip()]
        print(f"Total raw configs: {len(raw_lines)}")

        # Parse IPs first
        parsed_list = []
        for line in raw_lines:
            res = parse_config(line)
            if res:
                parsed_list.append(res)
        
        # Limit to 1500 to prevent GitHub ban (optional, but safe)
        scan_target = parsed_list[:1500]
        print(f"--- 2. Scanning {len(scan_target)} servers with {MAX_WORKERS} threads ---")

        valid_proxies = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            # Start all pings
            results = executor.map(check_speed, scan_target)
            
            # Collect results
            for latency, config in results:
                if latency < 99999: # If reachable
                    valid_proxies.append((latency, config))

        print(f"--- 3. Found {len(valid_proxies)} alive servers ---")

        # Sort by fastest (Lowest latency first)
        valid_proxies.sort(key=lambda x: x[0])

        # Pick Top N
        best_proxies = valid_proxies[:TOP_N]
        print(f"Selected Top {len(best_proxies)}. Fastest: {best_proxies[0][0]:.0f}ms")

        # Encode to Base64 (Standard Subscription Format)
        final_text = "\n".join([x[1] for x in best_proxies])
        b64_content = base64.b64encode(final_text.encode("utf-8")).decode("utf-8")

        # Save to file
        with open(OUTPUT_FILE, "w") as f:
            f.write(b64_content)
        
        print(f"Success! Saved to {OUTPUT_FILE}")

    except Exception as e:
        print(f"Critical Error: {e}")

if __name__ == "__main__":
    main()
