#!/usr/bin/env python3
"""
app.py - 1-Click Launcher & Proxy for AMS Quick Scheduler
Starts a lightweight local HTTP server and automatically opens the schedule builder in your browser.
Includes a live Confex API proxy to bypass browser CORS restrictions when fetching late-breaking talks.
"""

import http.server
import json
import os
import socketserver
import ssl
import sys
import urllib.parse
import urllib.request
import webbrowser

PORT = 8080

class AppRequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        if parsed.path == "/api/fetch_confex":
            query = urllib.parse.parse_qs(parsed.query)
            endpoint = query.get("endpoint", [""])[0]
            if not endpoint:
                target_type = query.get("type", ["Paper"])[0]
                target_id = query.get("id", [""])[0]
                if target_id:
                    endpoint = f"{target_type}/{target_id}"

            if not endpoint:
                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(b'{"error": "Missing endpoint or id"}')
                return

            target_url = f"https://ams.confex.com/ams/107ANNUAL/meetingapi.cgi/{endpoint}"
            try:
                ctx = ssl._create_unverified_context()
                req = urllib.request.Request(target_url, headers={"User-Agent": "Mozilla/5.0"})
                with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
                    data = resp.read()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(data)
            except Exception as e:
                self.send_response(500)
                self.send_header("Content-Type", "application/json")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(json.dumps({"error": str(e)}).encode("utf-8"))
            return

        super().do_GET()

def main():
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    os.chdir(workspace_dir)

    json_file = os.path.join(workspace_dir, "ams_program.json")
    if not os.path.exists(json_file):
        print("ams_program.json not found! Running fetcher first...")
        import fetch_ams_program
        fetch_ams_program.build_program_dataset()

    url = f"http://localhost:{PORT}/"
    print("=" * 60)
    print("  AMS Quick Scheduler")
    print(f"  Local URL: {url}")
    print(f"  Live Confex Proxy: http://localhost:{PORT}/api/fetch_confex")
    print("=" * 60)
    print("Opening browser... (Press Ctrl+C in this terminal to stop)\n")

    # Open browser automatically
    try:
        webbrowser.open(url)
    except Exception:
        pass

    Handler = AppRequestHandler
    # Allow port reuse immediately
    socketserver.TCPServer.allow_reuse_address = True
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nServer stopped.")

if __name__ == "__main__":
    main()

