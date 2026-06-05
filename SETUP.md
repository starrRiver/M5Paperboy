# M5Paperboy Setup Guide

A step-by-step checklist. You do not need any coding background — just follow each step in order.

---

## Part 1 — Get an Anthropic API Key (5 minutes)

1. Go to **https://console.anthropic.com** and sign up / log in.
2. Click your profile icon (top right) → **API Keys** → **Create Key**.
3. Name it `m5paperboy`. Copy the key — it starts with `sk-ant-...`.
4. Keep this somewhere safe (Notes app is fine). You will need it in Part 3.

---

## Part 2 — Set up GitHub (10 minutes)

### 2a. Create a GitHub account
- Go to **https://github.com** and sign up (free).
- Your username matters — you'll use it in the device firmware URL.

### 2b. Create a new repository
1. Click the **+** icon (top right) → **New repository**.
2. Repository name: `M5Paperboy`
3. Set to **Public** (required for free GitHub Pages hosting).
4. Tick **Add a README file**.
5. Click **Create repository**.

### 2c. Upload the project files
1. On your new repo page, click **Add file** → **Upload files**.
2. Drag in everything from the `M5Paperboy` folder on your Desktop:
   - `fetch_news.py`
   - `requirements.txt`
   - The `.github` folder (drag the whole folder)
   - The `docs` folder (drag the whole folder)
3. Scroll down, click **Commit changes**.

### 2d. Enable GitHub Pages
1. In your repo, go to **Settings** → **Pages** (left sidebar).
2. Under **Source**, choose `Deploy from a branch`.
3. Branch: `main`, folder: `/docs`.
4. Click **Save**.
5. After ~1 minute, your articles will be live at:
   `https://YOUR_GITHUB_USERNAME.github.io/M5Paperboy/articles.json`

### 2e. Add your API key as a secret
1. In your repo, go to **Settings** → **Secrets and variables** → **Actions**.
2. Click **New repository secret**.
3. Name: `ANTHROPIC_API_KEY`
4. Value: paste your `sk-ant-...` key.
5. Click **Add secret**.

### 2f. Run the workflow manually (first test)
1. In your repo, click the **Actions** tab.
2. Click **Daily News Fetch** on the left.
3. Click **Run workflow** → **Run workflow**.
4. Wait ~2 minutes. A green tick means it worked.
5. Visit `https://YOUR_GITHUB_USERNAME.github.io/M5Paperboy/articles.json` — you should see today's articles.

---

## Part 3 — Flash the M5Paper S3 (15 minutes)

### 3a. Install M5Burner
1. Go to **https://docs.m5stack.com/en/download** and download **M5Burner** for Mac.
2. Open it. Connect your M5Paper S3 via USB-C.
3. In M5Burner, find **UIFlow2** for M5Paper S3 and click **Burn**. Wait for it to finish.

### 3b. Edit the firmware file
Open the file `firmware/main.py` (in your M5Paperboy Desktop folder) in **TextEdit**:

1. Find this line:
   ```
   WIFI_SSID     = "YOUR_WIFI_NAME"
   ```
   Replace `YOUR_WIFI_NAME` with your actual WiFi network name (case-sensitive).

2. Find:
   ```
   WIFI_PASSWORD = "YOUR_WIFI_PASSWORD"
   ```
   Replace with your WiFi password.

3. Find:
   ```
   ARTICLES_URL  = "https://YOUR_GITHUB_USERNAME.github.io/M5Paperboy/articles.json"
   ```
   Replace `YOUR_GITHUB_USERNAME` with your actual GitHub username.

4. Save the file.

### 3c. Upload main.py to the device
1. Download **Thonny** from **https://thonny.org** (free, beginner-friendly Python editor).
2. Open Thonny. Go to **Tools** → **Options** → **Interpreter**.
3. Select **MicroPython (ESP32)** and the correct USB port (usually `/dev/cu.usbserial-...`).
4. Click **OK**.
5. Open `firmware/main.py` in Thonny (File → Open).
6. Go to **File** → **Save copy** → **MicroPython device** → save as `main.py`.
7. Press the reset button on the M5Paper S3.

---

## Part 4 — Using M5Paperboy

- **On startup**: the device connects to WiFi and loads today's articles automatically.
- **Button A** (left): previous article
- **Button B** (middle): next article
- **Button C** (right): refresh — fetches the latest `articles.json` from the internet

The GitHub Action runs every morning at 7am Melbourne time and updates the articles automatically.

---

## Troubleshooting

| Problem | Fix |
|---|---|
| GitHub Action fails (red X) | Check the API key secret is named exactly `ANTHROPIC_API_KEY` |
| Device shows "WiFi failed" | Double-check SSID and password spelling in main.py |
| Device shows "Fetch failed" | Confirm GitHub Pages is enabled and the URL in main.py is correct |
| articles.json shows old content | Trigger the Action manually (Step 2f) |
