# utils/index.py
import re
import urllib.parse
import csv
import time
from datetime import datetime, timezone
from pathlib import Path
from playwright.sync_api import TimeoutError as PlaywrightTimeoutError, Page

TIMEFRAME_MAP = {
    "M1": "1 minute",
    "M5": "5 minutes",
    "M15": "15 minutes",
    "M30": "30 minutes",
    "H1": "1 hour",
    "H4": "4 hours",
    "D1": "1 day",
    "W1": "1 week",
    "MN1": "1 month",
}


def monitor_init_file_active_flag(init_file_path, stop_flag):
    print("👀 Monitoring init.txt for Active: false...")
    while not stop_flag["stop"]:
        try:
            try:
                with open(init_file_path, "r", encoding="utf-16") as f:
                    lines = f.readlines()
            except UnicodeError:
                with open(init_file_path, "r", encoding="utf-8") as f:
                    lines = f.readlines()

            for line in lines:
                if line.strip().startswith("Active:") and "false" in line.lower():
                    print("🛑 Detected Active: false in init.txt. Stopping...")
                    stop_flag["stop"] = True
                    return
        except Exception as e:
            print(f"⚠️ Error reading init.txt: {e}")

        time.sleep(3)


def is_user_logged_in(page):
    print("🔍 Checking login status...")
    try:
        page.goto("https://www.tradingview.com/", timeout=60000)
        page.wait_for_load_state("networkidle")

        user_logged_in_selector = "button.tv-header__user-menu-button--logged"
        page.wait_for_selector(user_logged_in_selector, timeout=8000)
        return True
    except PlaywrightTimeoutError:
        return False


def get_latest_session_folder(base_path):
    folders = [f for f in Path(base_path).iterdir() if f.is_dir()]
    if not folders:
        raise FileNotFoundError("No session folders found.")
    return max(folders, key=lambda f: f.stat().st_mtime)


def parse_init_file(init_path):
    data = {}
    with open(init_path, "r", encoding="utf-16") as f:
        content = f.read()
    lines = content.splitlines()
    for line in lines:
        if ":" in line:
            key, value = line.split(":", 1)
            data[key.strip()] = value.strip()
    return data


def clean_symbol(mt5_symbol):
    if not mt5_symbol:
        return ""
    upper_only = "".join(re.findall(r"[A-Z]", mt5_symbol.upper()))
    for suffix in ["M", "R", "PRO"]:
        if upper_only.endswith(suffix):
            upper_only = upper_only[: -len(suffix)]
            break
    return upper_only


def determine_tradingview_prefix_and_symbol(symbol):
    symbol = symbol.upper()
    if any(k in symbol for k in ["BTC", "ETH", "DOGE", "SOL", "BNB", "XRP"]):
        return "INDEX", f"{symbol}USD"
    if symbol in ["XAUUSD", "XAGUSD", "WTI", "BRENT"]:
        return "OANDA", symbol
    if re.fullmatch(r"[A-Z]{6}", symbol):
        return "OANDA", symbol
    if symbol in ["SPX", "NDX", "DJI", "DAX", "UK100", "USOIL"]:
        return "TVC", symbol
    return "FXCM", symbol


def build_tradingview_chart_url(prefix, symbol):
    combined = f"{prefix}:{symbol}"
    encoded = urllib.parse.quote(combined)
    return f"https://www.tradingview.com/chart/?symbol={encoded}"


def login_to_tradingview(page, email, password):
    print("🔐 Logging in to TradingView...")
    page.goto("https://www.tradingview.com/", timeout=60000)
    page.wait_for_load_state("networkidle")

    user_menu_selector = "button.js-header-user-menu-button"
    page.wait_for_selector(user_menu_selector, timeout=15000)
    page.click(user_menu_selector)

    signin_btn_selector = 'button[data-name="header-user-menu-sign-in"]'
    page.wait_for_selector(signin_btn_selector, timeout=15000)
    page.click(signin_btn_selector)

    email_btn_selector = 'button[name="Email"]'
    page.wait_for_selector(email_btn_selector, timeout=15000)
    page.click(email_btn_selector)

    page.wait_for_selector("input#id_username", timeout=15000)
    page.fill("input#id_username", email)
    page.fill("input#id_password", password)

    sign_in_btn_selector = 'button:has-text("Sign in")'
    page.click(sign_in_btn_selector)

    try:
        page.wait_for_selector(
            'button.tv-header__user-menu-button--logged[aria-label="Open user menu"]',
            timeout=30000,
        )
        print("✅ Login successful.")
    except PlaywrightTimeoutError:
        print("❌ Login failed or timed out.")


def parse_timeframes_from_init(file_path):
    timeframes = {}
    with open(file_path, "r", encoding="utf-16") as f:
        for line in f:
            if line.startswith("BaseTF:"):
                timeframes["base"] = line.split(":", 1)[1].strip()
            elif line.startswith("LowerTF:"):
                timeframes["lower"] = line.split(":", 1)[1].strip()
            elif line.startswith("HigherTF:"):
                timeframes["higher"] = line.split(":", 1)[1].strip()
    return timeframes


def get_tf_labels(init_path):
    tf_keys = parse_timeframes_from_init(init_path)
    return [
        TIMEFRAME_MAP[tf_keys[k]]
        for k in ("lower", "base", "higher")
        if tf_keys.get(k) in TIMEFRAME_MAP
    ]


def switch_timeframe_and_confirm(page: Page, tf_label: str):
    print(f"🔄 Switching to {tf_label}...")
    try:
        # Step 1: Click the currently active TF toggle button
        toggle_button_selector = (
            'div#header-toolbar-intervals button[aria-haspopup="menu"]'
        )
        toggle = page.wait_for_selector(toggle_button_selector, timeout=5000)
        toggle.scroll_into_view_if_needed()
        toggle.click()

        # Step 2: Click the dropdown menu item with matching label
        menu_item_selector = f'//div[@role="row" and contains(., "{tf_label}")]'
        item = page.wait_for_selector(menu_item_selector, timeout=5000)
        item.scroll_into_view_if_needed()
        item.click()

        # Step 3: Confirm by checking aria-label or data-tooltip on the toggle button
        expected_label = tf_label.lower()
        page.wait_for_timeout(1000)  # wait briefly for the toggle to update
        actual_label = page.get_attribute(toggle_button_selector, "aria-label") or ""

        if expected_label in actual_label.lower():
            print(f"✅ {tf_label} activated.")
        else:
            print(f"⚠️ Toggle did not reflect {tf_label}. Found: {actual_label}")

    except PlaywrightTimeoutError:
        print(f"❌ Failed to switch to {tf_label}")
    except Exception as e:
        print(f"❌ Unexpected error while switching TF: {e}")


def switch_to_heikin_ashi(page: Page):
    print("🕹️ Switching to Heikin Ashi chart type...")
    try:
        style_button_selector = (
            'div#header-toolbar-chart-styles button[aria-haspopup="menu"]'
        )
        button = page.wait_for_selector(style_button_selector, timeout=5000)
        button.scroll_into_view_if_needed()
        button.click()

        menu_item_selector = '//div[@role="row" and contains(., "Heikin Ashi")]'
        item = page.wait_for_selector(menu_item_selector, timeout=5000)
        item.scroll_into_view_if_needed()
        item.click()

        # Confirm via aria-label or tooltip on chart style button
        page.wait_for_timeout(1000)
        updated_label = page.get_attribute(style_button_selector, "aria-label") or ""

        if "heikin ashi" in updated_label.lower():
            print("✅ Heikin Ashi chart style selected.")
        else:
            print(
                f"⚠️ Style button label mismatch after switching. Found: {updated_label}"
            )
    except PlaywrightTimeoutError:
        print("❌ Failed to select Heikin Ashi style.")
    except Exception as e:
        print(f"❌ Unexpected error while selecting candle type: {e}")


def extract_volume_data(page):
    try:
        print("📊 Extracting volume data...")

        # Locate the correct indicator container
        container = page.locator("div[data-name='legend-source-item']").filter(
            has_text="Frank kyakusse Vol VIDYA"
        )

        if not container.is_visible():
            print("❌ Indicator container not visible.")
            return None

        # Extract values using direct selectors from nested elements
        buyer_selector = (
            "div[data-test-id-value-title='Buyer Volume'] .valueValue-l31H9iuA"
        )
        seller_selector = (
            "div[data-test-id-value-title='Seller Volume'] .valueValue-l31H9iuA"
        )
        delta_selector = (
            "div[data-test-id-value-title='Delta Volume %'] .valueValue-l31H9iuA"
        )

        buyer_volume = container.locator(buyer_selector).inner_text(timeout=3000)
        seller_volume = container.locator(seller_selector).inner_text(timeout=3000)
        delta_percent = container.locator(delta_selector).inner_text(timeout=3000)

        # Clean the extracted strings (remove commas if present)
        buyer_volume = buyer_volume.replace(",", "")
        seller_volume = seller_volume.replace(",", "")
        delta_percent = delta_percent.replace(",", "")

        print(
            f"🧾 Extracted Buyer: {buyer_volume}, Seller: {seller_volume}, Delta: {delta_percent}"
        )

        return {
            "buyer_volume": buyer_volume,
            "seller_volume": seller_volume,
            "delta_percent": delta_percent,
        }

    except Exception as e:
        print("❌ Failed to extract volume data:", e)
        return None
