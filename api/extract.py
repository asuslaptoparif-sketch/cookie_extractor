from http.server import BaseHTTPRequestHandler
import json
import instaloader
import pyotp
import urllib.parse

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers['Content-Length'])
        post_data = self.rfile.read(content_length)
        
        try:
            body = json.loads(post_data.decode('utf-8'))
            username = body.get('username', '')
            password = body.get('password', '')
            two_fa = body.get('two_fa', '')
            
            if not username or not password:
                self.send_response(400)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "Username and Password required"}).encode())
                return

            # Extraction Logic
            L = instaloader.Instaloader(quiet=True)
            L.context._session.headers.update({
                "User-Agent": "Instagram 314.0.0.38.109 Android (13/TP1A.220624.014; 440dpi; 1080x2212; Google; Pixel 7; cheetah; cheetah; en_US; 555627237)"
            })
            
            try:
                L.login(username, password)
            except instaloader.TwoFactorAuthRequiredException:
                if not two_fa or two_fa == "-":
                    self.send_response(200)
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": "2FA Required"}).encode())
                    return
                totp = pyotp.TOTP(two_fa.replace(" ", ""))
                L.two_factor_login(totp.now())
            except Exception as e:
                err = str(e).lower()
                msg = "Login Failed"
                if "checkpoint" in err: msg = "Checkpoint Required"
                elif "bad_credentials" in err: msg = "Invalid Credentials"
                else: msg = str(e)[:100]
                
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": msg}).encode())
                return

            cookies = L.context._session.cookies.get_dict()
            if 'sessionid' in cookies:
                cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "cookie": cookie_str}).encode())
            else:
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "SessionID not found"}).encode())

        except Exception as e:
            self.send_response(500)
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())
PY;
