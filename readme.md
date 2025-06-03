# TradingView Volume Scraper

This project provides a **Playwright-based scraper** designed to extract real-time volume data from TradingView. It automates browser interactions to log in, navigate to specific charts, switch timeframes, set the chart type to Heikin Ashi, and then continuously extract data from a custom indicator. The extracted data is then saved to a CSV file.

---

## Features

- **Automated Login:** Securely logs into TradingView using credentials provided in an `init.txt` file.
- **Dynamic Chart Navigation:** Constructs TradingView chart URLs based on MT5 symbols from the `init.txt` file.
- **Timeframe Switching:** Cycles through user-defined timeframes (Lower, Base, Higher) specified in `init.txt`.
- **Heikin Ashi Chart Type:** Automatically sets the chart style to Heikin Ashi for consistent data extraction.
- **Custom Indicator Data Extraction:** Specifically targets and extracts "Buyer Volume," "Seller Volume," and "Delta Volume %" from the "Frank kyakusse Vol VIDYA" indicator.
- **Real-time CSV Export:** Appends extracted data to a CSV file, only recording new entries when the lowest timeframe's data changes.
- **External Control:** Monitors the `init.txt` file for an "Active: false" flag, allowing for graceful termination of the scraping process.

---

## How It Works

The scraper operates in two main parts:

### `playwright_scraper.py`

This is the main script that orchestrates the browser automation.

1.  **Session Management:** It first attempts to load a saved browser session (`auth_state.json`) to avoid repeated logins. If no session exists, it performs a fresh login and saves the session state.
2.  **`init.txt` Monitoring:** A separate thread continuously monitors the `init.txt` file for a signal to stop the scraping process. This provides an external way to control the script.
3.  **Chart Navigation:** It navigates to the pre-built TradingView chart URL for the specified symbol.
4.  **Chart Setup:** It switches the chart type to **Heikin Ashi** and verifies the presence of the "Frank kyakusse Vol VIDYA" indicator.
5.  **Data Loop:** It enters a loop where it:
    - Iterates through the defined timeframes (Lower, Base, Higher).
    - Switches the chart to the current timeframe.
    - Calls the `extract_volume_data` function to pull information from the indicator.
    - Compares the data from the **lowest timeframe** with the previously recorded data.
    - If the lowest timeframe's data has changed, it records a new row with data from all three timeframes into `volume_data.csv`.
    - Waits for a specified interval before repeating.
6.  **Termination:** The loop continues until the "Active: false" flag is detected in `init.txt`, at which point the browser is closed.

### `utils/index.py`

This file contains helper functions that support the main scraper:

- **`monitor_init_file_active_flag`**: Reads the `init.txt` file to check for the "Active" status.
- **`is_user_logged_in`**: Verifies if a user is already logged into TradingView.
- **`get_latest_session_folder`**: Locates the most recent MT5 session folder, where the `init.txt` file is expected to reside.
- **`parse_init_file`**: Parses the `init.txt` file to extract login credentials, the MT5 symbol, and defined timeframes.
- **`clean_symbol`**: Cleans up MT5 symbols to make them compatible with TradingView's symbol format (e.g., removing suffixes like "M", "R", "PRO").
- **`determine_tradingview_prefix_and_symbol`**: Maps cleaned MT5 symbols to appropriate TradingView prefixes (e.g., OANDA, TVC, INDEX) and formats the symbol for chart URLs.
- **`build_tradingview_chart_url`**: Constructs the final TradingView chart URL.
- **`login_to_tradingview`**: Contains the Playwright steps to navigate to the login page and enter credentials.
- **`parse_timeframes_from_init`**: Extracts the specific timeframe codes (e.g., M1, H1) from `init.txt`.
- **`get_tf_labels`**: Converts the timeframe codes from `init.txt` into human-readable labels used by TradingView (e.g., "1 minute", "1 hour").
- **`switch_timeframe_and_confirm`**: Automates the clicks required to change the chart timeframe on TradingView and confirms the switch.
- **`switch_to_heikin_ashi`**: Automates the clicks to change the chart style to Heikin Ashi.
- **`extract_volume_data`**: Locates the specific indicator on the TradingView chart and extracts the buyer volume, seller volume, and delta percentage values.

---

## Setup and Usage

### Prerequisites

- **Python 3.x**
- **Playwright:** Install with `pip install playwright`
- **Playwright Browsers:** Install browser binaries with `playwright install`
- **TradingView Account:** You need a TradingView account with access to the "Frank kyakusse Vol VIDYA" indicator.
- **MT5 Session Folder:** The script expects an MT5 session folder containing an `init.txt` file with the following structure:

  ```
  UserEmail: your_email@example.com
  UserPassword: your_password
  Symbol: XAUUSDm
  BaseTF: H1
  LowerTF: M15
  HigherTF: D1
  Active: true
  ```

  Ensure the `Active:` flag is set to `true` to start the script. Change it to `false` to stop it.

### Installation

1.  Clone this repository or download the files.
2.  Navigate to the project directory in your terminal.
3.  Install dependencies:
    ```bash
    pip install playwright
    playwright install
    ```

### Running the Scraper

1.  Ensure your `init.txt` file is correctly configured within the latest MT5 session folder (typically found under `%APPDATA%\MetaQuotes\Terminal\Common\Files`).
2.  Run the main script:
    ```bash
    python playwright_scraper.py
    ```

The browser will launch, perform the automated actions, and begin writing data to `volume_data.csv` within your MT5 session folder.

---

## Troubleshooting

- **"init.txt not found"**: Ensure the `init.txt` file is in the correct and most recent MT5 session folder.
- **Login Issues**: Verify your `UserEmail` and `UserPassword` in `init.txt` are correct. TradingView might occasionally prompt for CAPTCHAs or other security checks that Playwright cannot bypass automatically.
- **Indicator Not Found**: Ensure the "Frank kyakusse Vol VIDYA" indicator is applied to your TradingView chart and its name matches exactly.
- **Playwright TimeoutErrors**: These usually indicate that a selector was not found within the given timeout. This could be due to slow internet, TradingView page changes, or incorrect selectors. Adjust `timeout` values or inspect element selectors if TradingView's UI changes.
- **`Active: false` not stopping the script**: Double-check that the `init.txt` file is accessible and that the `Active:` line is formatted exactly as expected (e.g., `Active: false`).

---

Feel free to open an issue if you encounter any problems or have suggestions for improvements!
