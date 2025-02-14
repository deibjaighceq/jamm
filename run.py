import asyncio
import base64
import hashlib
import json
import random
import ssl
import subprocess
import sys
import time
import os
import uuid
from datetime import datetime

import aiohttp
import requests
from colorama import Fore, Style, init
from websockets_proxy import Proxy, proxy_connect


def get_hash():
    build_fp = subprocess.check_output(["getprop", "ro.build.fingerprint"]).decode().strip()
    system_fp = subprocess.check_output(["getprop", "ro.system.build.fingerprint"]).decode().strip()
    return hashlib.sha256((build_fp + system_fp).encode()).hexdigest()

def run(cmd):
    try:
        return subprocess.run(
            cmd, shell=True, capture_output=True, check=True, encoding="utf-8"
        ).stdout.strip()
    except:
        return None


def guid():
    if sys.platform == "darwin":
        return run(
            "ioreg -d2 -c IOPlatformExpertDevice | awk -F\\\" '/IOPlatformUUID/{print $(NF-1)}'",
        )

    if sys.platform == "win32" or sys.platform == "cygwin" or sys.platform == "msys":
        return run("wmic csproduct get uuid").split("\n")[2].strip()

    if sys.platform.startswith("linux"):
        return run("cat /var/lib/dbus/machine-id") or run("cat /etc/machine-id") or get_hash()

    if sys.platform.startswith("openbsd") or sys.platform.startswith("freebsd"):
        return run("cat /etc/hostid") or run("kenv -q smbios.system.uuid")

init(autoreset=True)

BANNER = """
_________ ____________________                            
__  ____/______  /__  ____/____________ _______________
_  / __ _  _ \\  __/  / __ __  ___/  __ `/_  ___/_  ___/
/ /_/ / /  __/ /_ / /_/ / _  /   / /_/ /_(__  )_(__  ) 
\\____/  \\___/\\__/ \\____/  /_/    \\__,_/ /____/ /____/  
"""

EDGE_USERAGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.2365.57",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.2365.52",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 Edg/122.0.2365.46",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.2277.128",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.2277.112",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.2277.98",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36 Edg/121.0.2277.83",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.2210.133",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.2210.121",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.2210.91"
]

HTTP_STATUS_CODES = {
    200: "OK",
    201: "Created", 
    202: "Accepted",
    204: "No Content",
    400: "Bad Request",
    401: "Unauthorized",
    403: "Forbidden", 
    404: "Not Found",
    500: "Internal Server Error",
    502: "Bad Gateway",
    503: "Service Unavailable",
    504: "Gateway Timeout"
}

def colorful_log(proxy, device_id, message_type, message_content, is_sent=False, mode=None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    color = Fore.GREEN if is_sent else Fore.BLUE
    is_err = message_type == "ERROR"
    action_color = Fore.RED if message_type == "ERROR" else Fore.WHITE
    prefix = "" if message_type == "ERROR" else "🔵" if is_sent else "🚀"
    
    if is_err:
        log_message = (
            f"{Fore.GREEN}{timestamp}"
            f"{action_color} | {message_type} | "
            f"{Fore.BLUE}🚫 Error with proxy {proxy}:"
            f" {message_content}"
        )
        print(log_message)
        return
    
    log_message = (
        f"{Fore.GREEN}{timestamp}"
        f"{action_color} | {message_type} | "
        f"{color}{prefix} {message_content} "
    )
    
    print(log_message)

async def connect_to_wss(socks5_proxy, user_id, mode):
    device_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, socks5_proxy))
    
    random_user_agent = random.choice(EDGE_USERAGENTS)
    
    colorful_log(
        proxy=socks5_proxy,  
        device_id=device_id, 
        message_type="INITIALIZATION", 
        message_content=f"User Agent: {random_user_agent}",
        mode=mode
    )

    has_received_action = False
    is_authenticated = False
    
    while True:
        try:
            await asyncio.sleep(random.randint(1, 10) / 10)
            custom_headers = {
                "User-Agent": random_user_agent,
                "Origin": "chrome-extension://lkbnfiajjmbhnfledhphioinpickokdi" if mode == "extension" else None
            }
            custom_headers = {k: v for k, v in custom_headers.items() if v is not None}
            
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            urilist = [
                #"wss://proxy.wynd.network:4444/",
                #"wss://proxy.wynd.network:4650/",
                "wss://proxy2.wynd.network:4444/",
                "wss://proxy2.wynd.network:4650/",
                #"wss://proxy3.wynd.network:4444/",
                #"wss://proxy3.wynd.network:4650/"
            ]
            uri = random.choice(urilist)
            server_hostname = "proxy.wynd.network"
            proxy = Proxy.from_url(socks5_proxy)
            
            async with proxy_connect(uri, proxy=proxy, ssl=ssl_context, server_hostname=server_hostname,
                                     extra_headers=custom_headers) as websocket:
                async def send_ping():
                    while True:
                        if has_received_action:
                            send_message = json.dumps(
                                {"id": str(uuid.uuid5(uuid.NAMESPACE_DNS, socks5_proxy)), 
                                 "version": "1.0.0", 
                                 "action": "PING", 
                                 "data": {}})
                            
                            colorful_log(
                                proxy=socks5_proxy,  
                                device_id=device_id, 
                                message_type="SENDING PING", 
                                message_content=send_message,
                                is_sent=True,
                                mode=mode
                            )
                            
                            await websocket.send(send_message)
                        await asyncio.sleep(1)

                await asyncio.sleep(1)
                ping_task = asyncio.create_task(send_ping())

                while True:
                    if is_authenticated and not has_received_action:
                        colorful_log(
                            proxy=socks5_proxy,
                            device_id=device_id,
                            message_type="AUTHENTICATED | WAIT UNTIL THE PING GATE OPENS",
                            message_content="Waiting for " + ("HTTP_REQUEST" if mode == "extension" else "OPEN_TUNNEL"),
                            mode=mode
                        )
                    
                    response = await websocket.recv()
                    message = json.loads(response)
                    
                    colorful_log(
                        proxy=socks5_proxy, 
                        device_id=device_id, 
                        message_type="RECEIVED", 
                        message_content=json.dumps(message),
                        mode=mode
                    )

                    if message.get("action") == "AUTH":
                        auth_response = {
                            "id": message["id"],
                            "origin_action": "AUTH",
                            "result": {
                                "browser_id": device_id,
                                "user_id": user_id,
                                "user_agent": random_user_agent,
                                "timestamp": int(time.time()),
                                "device_type": "extension" if mode == "extension" else "desktop",
                                "version": "4.26.2" if mode == "extension" else "4.30.0"
                            }
                        }
                        
                        if mode == "extension":
                            auth_response["result"]["extension_id"] = "lkbnfiajjmbhnfledhphioinpickokdi"
                        
                        colorful_log(
                            proxy=socks5_proxy,  
                            device_id=device_id, 
                            message_type="AUTHENTICATING", 
                            message_content=json.dumps(auth_response),
                            is_sent=True,
                            mode=mode
                        )
                        
                        await websocket.send(json.dumps(auth_response))
                        is_authenticated = True
                    
                    elif message.get("action") in ["HTTP_REQUEST", "OPEN_TUNNEL"]:
                        has_received_action = True
                        request_data = message["data"]
                        
                        headers = {
                            "User-Agent": custom_headers["User-Agent"],
                            "Content-Type": "application/json; charset=utf-8"
                        }
                        
                        async with aiohttp.ClientSession() as session:
                            async with session.get(request_data["url"], headers=headers) as api_response:
                                content = await api_response.text()
                                encoded_body = base64.b64encode(content.encode()).decode()
                                
                                status_text = HTTP_STATUS_CODES.get(api_response.status, "")
                                
                                http_response = {
                                    "id": message["id"],
                                    "origin_action": message["action"],
                                    "result": {
                                        "url": request_data["url"],
                                        "status": api_response.status,
                                        "status_text": status_text,
                                        "headers": dict(api_response.headers),
                                        "body": encoded_body
                                    }
                                }
                                
                                colorful_log(
                                    proxy=socks5_proxy,
                                    device_id=device_id,
                                    message_type="OPENING PING ACCESS",
                                    message_content=json.dumps(http_response),
                                    is_sent=True,
                                    mode=mode
                                )
                                
                                await websocket.send(json.dumps(http_response))

                    elif message.get("action") == "PONG":
                        pong_response = {"id": message["id"], "origin_action": "PONG"}
                        
                        colorful_log(
                            proxy=socks5_proxy, 
                            device_id=device_id, 
                            message_type="SENDING PONG", 
                            message_content=json.dumps(pong_response),
                            is_sent=True,
                            mode=mode
                        )
                        
                        await websocket.send(json.dumps(pong_response))
                        
        except Exception as e:
            colorful_log(
                proxy=socks5_proxy, 
                device_id=device_id, 
                message_type="ERROR", 
                message_content=str(e),
                mode=mode
            )

async def main():
    print(f"{Fore.CYAN}{BANNER}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Te Mi | DamoBot{Style.RESET_ALL}")
    
    print(f"{Fore.GREEN}Select Mode:{Style.RESET_ALL}")
    print("1. Extension Mode 2x")
    print("2. Desktop Mode Not Available")
    
    while True:
        mode_choice = input("Enter your choice (1/2): ").strip()
        if mode_choice in ['1', '2']:
            break
        print(f"{Fore.RED}Invalid choice. Please enter 1 or 2.{Style.RESET_ALL}")
    
    mode = "extension" if mode_choice == "1" else "desktop"
    
    print(f"{Fore.GREEN}Selected mode: {mode}{Style.RESET_ALL}")
    
    # Read the user ID from userid.txt
    if os.path.exists('userid.txt'):
        with open('userid.txt', 'r') as user_id_file:
            _user_id = user_id_file.read().strip()
            if not _user_id:
                print(f"{Fore.RED}User  ID is empty in userid.txt.{Style.RESET_ALL}")
                sys.exit(1)
    else:
        print(f"{Fore.RED}userid.txt not found. Please create the file and enter your user ID.{Style.RESET_ALL}")
        sys.exit(1)
    
    print(f"{Fore.YELLOW}User  ID loaded from userid.txt: {_user_id}{Style.RESET_ALL}")
    
    with open('proxy_list.txt', 'r') as file:
        local_proxies = file.read().splitlines()
    
    print(f"{Fore.YELLOW}Total Proxies: {len(local_proxies)}{Style.RESET_ALL}")
    
    tasks = [asyncio.ensure_future(connect_to_wss(i, _user_id, mode)) for i in local_proxies]
    await asyncio.gather(*tasks)
    
    
def authenticate():
    uuid = guid()
    DB_URL = "https://pastebin.com/raw/LaSTZhf9"
    try:
        db = requests.get(DB_URL).text.splitlines()
        uuid_str = f"UUID: {uuid}"
        if uuid not in db:
            print(
                f"{Fore.RED}+--------- Authentication Failed ---------+\n|{Style.RESET_ALL}{'UUID is not registered!'.center(41)}{Fore.RED}|\n|{Style.RESET_ALL}{uuid_str.center(41)}{Fore.RED}|\n|{Fore.GREEN}{'Please send this to the seller!'.center(41)}{Fore.RED}|\n+{'-'*41}+{Style.RESET_ALL}"
            )
            sys.exit(1)
        else:
            print("Welcome!")
    except Exception as e:
        print(e)
        print("Authentication failed. Please check your internet connection.")
        sys.exit(1)
     
if __name__ == '__main__':
    authenticate()
    asyncio.run(main())
    
