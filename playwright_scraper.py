# playwright_scraper.py
import os
import json
import threading
import csv
from datetime import datetime, timezone  # <--- Add timezone here
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


from utils.index import (
    get_latest_session_folder,
    is_user_logged_in,
    parse_init_file,
    clean_symbol,
    determine_tradingview_prefix_and_symbol,
    build_tradingview_chart_url,
    login_to_tradingview,
    switch_timeframe_and_confirm,
    monitor_init_file_active_flag,
    switch_to_heikin_ashi,
    get_tf_labels,
    extract_volume_data,
)

SESSION_STATE_PATH = "auth_state.json"


def launch_tradingview_browser(session_folder, url, email, password, init_file):
    print("🌐 Launching browser...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        context = (
            browser.new_context(storage_state=SESSION_STATE_PATH)
            if os.path.exists(SESSION_STATE_PATH)
            else browser.new_context()
        )
        page = context.new_page()

        # 🔁 Monitor init.txt for "Active: false"
        stop_flag = {"stop": False}
        monitor_thread = threading.Thread(
            target=monitor_init_file_active_flag,
            args=(init_file, stop_flag),
            daemon=True,
        )
        monitor_thread.start()

        try:
            if not is_user_logged_in(page):
                login_to_tradingview(page, email, password)
                context.storage_state(path=SESSION_STATE_PATH)
                print("💾 Session saved for future runs.")
            else:
                print("✅ Already logged in. Skipping login.")

            print(f"➡️ Navigating to chart URL: {url}")
            page.goto(url, timeout=60000)
            page.wait_for_selector("#header-toolbar-symbol-search", timeout=15000)
            print("✅ Chart page loaded.")

        except Exception as e:
            print(f"❌ Login or navigation error: {e}")
            page.pause()
            return

        try:
            switch_to_heikin_ashi(page)

            print("🔍 Checking if indicator is loaded...")
            indicator_visible = page.locator(
                "div.title-l31H9iuA", has_text="Frank kyakusse Vol VIDYA"
            ).is_visible()

            if not indicator_visible:
                print("⚠️ Indicator 'Frank kyakusse Vol VIDYA' is NOT loaded.")
            else:
                print("✅ Indicator detected. Beginning data extraction...")

            tf_labels = get_tf_labels(init_file)

            # Determine the lowest timeframe label
            lowest_tf_label = tf_labels[0]

            CSV_PATH = f"{session_folder}/volume_data.csv"

            # Create CSV header if file doesn't exist
            if not os.path.exists(CSV_PATH):
                with open(CSV_PATH, "w", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow(
                        [
                            "Timestamp",
                            "Lower Buyer Volume",
                            "Lower Seller Volume",
                            "Lower Delta %",
                            "Base Buyer Volume",
                            "Base Seller Volume",
                            "Base Delta %",
                            "Higher Buyer Volume",
                            "Higher Seller Volume",
                            "Higher Delta %",
                        ]
                    )

            last_lowest_tf_data = None

            while not stop_flag["stop"]:
                current_tf_data = {}

                for tf_label in tf_labels:
                    try:
                        switch_timeframe_and_confirm(page, tf_label)
                        page.wait_for_timeout(3000)  # Give some time for data to load

                        data = extract_volume_data(page)
                        if data:
                            current_tf_data[tf_label] = data
                    except Exception as tf_err:
                        print(
                            f"❌ Error collecting data for timeframe {tf_label}: {tf_err}"
                        )

                # Check if the lowest timeframe data has changed
                if (
                    lowest_tf_label in current_tf_data
                    and current_tf_data[lowest_tf_label] != last_lowest_tf_data
                ):

                    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
                    row = [now]

                    for tf_label in tf_labels:
                        data = current_tf_data.get(tf_label, {})
                        row.extend(
                            [
                                data.get("buyer_volume", ""),
                                data.get("seller_volume", ""),
                                data.get("delta_percent", ""),
                            ]
                        )

                    with open(CSV_PATH, "a", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(row)

                    print(f"📥 CSV appended with new grouped data at {now}")
                    last_lowest_tf_data = current_tf_data[lowest_tf_label]
                else:
                    print(f"🔁 No change in {lowest_tf_label} data, waiting...")

                page.wait_for_timeout(
                    5000
                )  # Wait before checking again (adjust as needed)

        except Exception as e:
            print(f"⚠️ An error occurred during data extraction loop: {e}")

        print("\n🛑 Detected 'Active: false' or script ending. Closing browser...")
        browser.close()


if __name__ == "__main__":
    base_session_path = os.path.expandvars(
        r"%APPDATA%\MetaQuotes\Terminal\Common\Files"
    )

    try:
        session_folder = get_latest_session_folder(base_session_path)
        print(f"📂 Latest session folder: {session_folder}")

        init_file = session_folder / "init.txt"
        if not init_file.exists():
            raise FileNotFoundError(f"init.txt not found in {session_folder}")

        session_info = parse_init_file(init_file)
        print("✅ Parsed init.txt:", json.dumps(session_info, indent=2))

        email = session_info["UserEmail"]
        password = session_info["UserPassword"]
        mt5_symbol = session_info["Symbol"]

        clean_sym = clean_symbol(mt5_symbol)
        prefix, chart_symbol = determine_tradingview_prefix_and_symbol(clean_sym)
        chart_url = build_tradingview_chart_url(prefix, chart_symbol)

        print(f"🔗 Generated TradingView URL: {chart_url}")
        launch_tradingview_browser(
            session_folder, chart_url, email, password, init_file
        )

    except Exception as e:
        print("❌ Script Error:", e)
