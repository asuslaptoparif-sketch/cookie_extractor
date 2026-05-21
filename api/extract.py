import json
import instaloader
import pyotp
from http.server import BaseHTTPRequestHandler

class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"status": "active", "message": "Cookie Extractor API is running"}).encode())

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        post_data = self.rfile.read(content_length)
        
        try:
            body = json.loads(post_data.decode('utf-8'))
            username = body.get('username', '')
            password = body.get('password', '')
            two_fa = body.get('two_fa', '')
            
            if not username or not password:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "Username and Password required"}).encode())
                return

            # Extraction Logic
            L = instaloader.Instaloader(quiet=True)
            ua = "Instagram 314.0.0.38.109 Android (13/TP1A.220624.014; 440dpi; 1080x2212; Google; Pixel 7; cheetah; cheetah; en_US; 555627237)"
            L.context._session.headers.update({
                "User-Agent": ua,
                "Accept-Language": "en-US,en;q=0.9",
            })
            
            try:
                L.login(username, password)
            except instaloader.TwoFactorAuthRequiredException:
                if not two_fa or two_fa == "-":
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": "2FA Required"}).encode())
                    return
                try:
                    import time
                    time.sleep(2) # Small delay before 2FA
                    totp = pyotp.TOTP(two_fa.replace(" ", ""))
                    L.two_factor_login(totp.now())
                except Exception as e:
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"status": "error", "message": f"2FA Error: {str(e)}"}).encode())
                    return
            except Exception as e:
                err = str(e).lower()
                if "checkpoint" in err: msg = "Checkpoint Required"
                elif "bad_credentials" in err: msg = "Invalid Credentials"
                elif "feedback_required" in err: msg = "Feedback Required (IP Blocked by Instagram)"
                else: msg = str(e)[:100]
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": msg}).encode())
                return

            # Multi-stage aggressive cookie capture to force 'rur'
            try:
                import time
                import random
                
                # Endpoints that are highly likely to trigger 'rur' setting
                test_urls = [
                    "https://i.instagram.com/api/v1/accounts/current_user/?edit=true",
                    "https://www.instagram.com/api/v1/web/accounts/edit/",
                    "https://www.instagram.com/"
                ]
                
                for url in test_urls:
                    # Check if rur exists and has a value
                    current_cookies = L.context._session.cookies.get_dict()
                    if current_cookies.get('rur'):
                        break
                    
                    time.sleep(random.uniform(2, 4))
                    headers = {
                        "X-IG-App-ID": "936619743392459",
                        "User-Agent": ua,
                        "Accept": "*/*",
                        "X-Requested-With": "XMLHttpRequest",
                        "Referer": "https://www.instagram.com/",
                        "X-CSRFToken": current_cookies.get('csrftoken', '')
                    }
                    
                    try:
                        resp = L.context._session.get(url, headers=headers, timeout=12, allow_redirects=True)
                        
                        # Manually extract rur from response headers if it's there
                        for cookie in resp.cookies:
                            if cookie.name.lower() == 'rur' and cookie.value:
                                L.context._session.cookies.set(cookie.name, cookie.value, domain=cookie.domain, path=cookie.path)
                        
                        # Extra check: sometimes it's in the 'Set-Cookie' header but not in the jar
                        set_cookie = resp.headers.get('Set-Cookie', '')
                        if 'rur=' in set_cookie and not L.context._session.cookies.get_dict().get('rur'):
                            import re
                            match = re.search(r'rur=([^;]+)', set_cookie)
                            if match:
                                L.context._session.cookies.set('rur', match.group(1), domain='.instagram.com', path='/')
                    except:
                        continue
            except:
                pass

            cookies = L.context._session.cookies.get_dict()
            # Final fallback: if rur is still missing, try to set a dummy/default one or just filter empty ones
            cookies = {k: v for k, v in cookies.items() if v} 
            
            if 'sessionid' in cookies:
                cookie_str = "; ".join([f"{k}={v}" for k, v in cookies.items()])
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "success", "cookie": cookie_str}).encode())
            else:
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"status": "error", "message": "SessionID not found"}).encode())

        except Exception as e:
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps({"status": "error", "message": str(e)}).encode())
