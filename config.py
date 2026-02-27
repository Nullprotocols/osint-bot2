# config.py - Complete configuration for OSINT Pro Bot on Render
# Fully updated with branding, command descriptions, and all settings

import os

# ==================== BOT TOKEN ====================
# Render ke environment variable se lega, nahi to placeholder
BOT_TOKEN = os.environ.get("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")

# ==================== OWNER & ADMINS ====================
OWNER_ID = 8104850843  # Owner ka Telegram user ID
INITIAL_ADMINS = [8104850843, 5987905091]  # Ye DB me automatically add honge

# ==================== FORCE JOIN CHANNELS ====================
FORCE_JOIN_CHANNELS = [
    {"name": "All Data Here", "link": "https://t.me/all_data_here", "id": -1003090922367},
    {"name": "OSINT Lookup", "link": "https://t.me/osint_lookup", "id": -1003698567122}
]

# ==================== LOG CHANNELS (per command) ====================
LOG_CHANNELS = {
    "num": -1003482423742,
    "ifsc": -1003624886596,
    "email": -1003431549612,
    "gst": -1003634866992,
    "vehicle": -1003237155636,
    "vchalan": -1003237155636,
    "pincode": -1003677285823,
    "insta": -1003498414978,
    "git": -1003576017442,
    "pak": -1003663672738,
    "ip": -1003665811220,
    "ffinfo": -1003588577282,
    "ffban": -1003521974255,
    "tg2num": -1003642820243,
    "tginfo": -1003643170105,
    "tginfopro": -1003643170105,
}

# ==================== GLOBAL BRANDING BLACKLIST ====================
GLOBAL_BLACKLIST = [
    "@patelkrish_99",
    "patelkrish_99",
    "t.me/anshapi",
    "anshapi",
    "@Kon_Hu_Mai",
    "Kon_Hu_Mai",
    "Dm to buy access",
    "Dm to buy access"
]

# ==================== BRANDING (for JSON output) ====================
BRANDING = {
    "developer": "@Nullprotocol_X",
    "powered_by": "NULL PROTOCOL"
}

# ==================== COMMANDS (WITH DESCRIPTIONS) ====================
COMMANDS = {
    "num": {
        "url": "https://num-free-rootx-jai-shree-ram-14-day.vercel.app/?key=lundkinger&number={}",
        "param": "10-digit number",
        "log": LOG_CHANNELS["num"],
        "desc": "Phone number basic lookup",
        "extra_blacklist": [
            "dm to buy",
            "owner",
            "@kon_hu_mai",
            "Ruk ja bhencho itne m kya unlimited request lega?? Paid lena h to bolo 100-400₹ @Simpleguy444"
        ]
    },
    "tg2num": {
        "url": "https://tg2num-owner-api.vercel.app/?userid={}",
        "param": "user id",
        "log": LOG_CHANNELS["tg2num"],
        "desc": "Telegram user ID to number (if available)",
        "extra_blacklist": [
            "code",
            "validity",
            "hours_remaining",
            "days_remaining",
            "expires_on",
            "https://t.me/AbdulBotzOfficial",
            "AbdulDevStoreBot",
            "@AbdulDevStoreBot",
            "credit"
        ]
    },
    "vehicle": {
        "url": "https://vehicle-info-aco-api.vercel.app/info?vehicle={}",
        "param": "RC number",
        "log": LOG_CHANNELS["vehicle"],
        "desc": "Vehicle registration details",
        "extra_blacklist": []
    },
    "vchalan": {
        "url": "https://api.b77bf911.workers.dev/vehicle?registration={}",
        "param": "RC number",
        "log": LOG_CHANNELS["vchalan"],
        "desc": "Pending & paid chalan info",
        "extra_blacklist": []
    },
    "ip": {
        "url": "https://abbas-apis.vercel.app/api/ip?ip={}",
        "param": "IP address",
        "log": LOG_CHANNELS["ip"],
        "desc": "IP geolocation & ISP details",
        "extra_blacklist": []
    },
    "email": {
        "url": "https://abbas-apis.vercel.app/api/email?mail={}",
        "param": "email",
        "log": LOG_CHANNELS["email"],
        "desc": "Email validation & domain info",
        "extra_blacklist": []
    },
    "ffinfo": {
        "url": "https://official-free-fire-info.onrender.com/player-info?key=DV_M7-INFO_API&uid={}",
        "param": "uid",
        "log": LOG_CHANNELS["ffinfo"],
        "desc": "Free Fire basic player info",
        "extra_blacklist": []
    },
    "ffban": {
        "url": "https://abbas-apis.vercel.app/api/ff-ban?uid={}",
        "param": "uid",
        "log": LOG_CHANNELS["ffban"],
        "desc": "Free Fire ban status check",
        "extra_blacklist": []
    },
    "pincode": {
        "url": "https://api.postalpincode.in/pincode/{}",
        "param": "6-digit pincode",
        "log": LOG_CHANNELS["pincode"],
        "desc": "Area & post office details",
        "extra_blacklist": []
    },
    "ifsc": {
        "url": "https://abbas-apis.vercel.app/api/ifsc?ifsc={}",
        "param": "IFSC code",
        "log": LOG_CHANNELS["ifsc"],
        "desc": "Bank branch details",
        "extra_blacklist": []
    },
    "gst": {
        "url": "https://api.b77bf911.workers.dev/gst?number={}",
        "param": "GST number",
        "log": LOG_CHANNELS["gst"],
        "desc": "GST registration info",
        "extra_blacklist": []
    },
    "insta": {
        "url": "https://mkhossain.alwaysdata.net/instanum.php?username={}",
        "param": "username",
        "log": LOG_CHANNELS["insta"],
        "desc": "Instagram public profile info",
        "extra_blacklist": []
    },
    "tginfo": {
        "url": "https://openosintx.vippanel.in/tgusrinfo.php?key=OpenOSINTX-FREE&user={}",
        "param": "username/userid",
        "log": LOG_CHANNELS["tginfo"],
        "desc": "Telegram basic info",
        "extra_blacklist": []
    },
    "tginfopro": {
        "url": "https://api.b77bf911.workers.dev/telegram?user={}",
        "param": "username/userid",
        "log": LOG_CHANNELS["tginfopro"],
        "desc": "Telegram advanced profile data",
        "extra_blacklist": []
    },
    "git": {
        "url": "https://abbas-apis.vercel.app/api/github?username={}",
        "param": "username",
        "log": LOG_CHANNELS["git"],
        "desc": "GitHub account details",
        "extra_blacklist": []
    },
    "pak": {
        "url": "https://abbas-apis.vercel.app/api/pakistan?number={}",
        "param": "number",
        "log": LOG_CHANNELS["pak"],
        "desc": "Pakistan phone lookup",
        "extra_blacklist": []
    },
}

# ==================== FOOTER FOR COMMAND LISTS (/start, /help) ====================
CMD_LIST_FOOTER = "\n\n────────────────────────────\n⚡ Fast • Accurate • Secure\n👨‍💻 DEVELOPED BY NULL PROTOCOL"

# ==================== REDIRECT BOT ====================
REDIRECT_BOT = "@osintfatherNullBot"
