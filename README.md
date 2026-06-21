# Spotify Album Art Bulb Color

This script watches the currently playing Spotify track for your account and
sets a smart bulb to the dominant album-art color. Spotify's current-playback
API works whether playback is on the Mac Spotify app or on your Android phone,
as long as both use the same Spotify account.

## Setup

### 1. Local Python environment

Create and activate a virtual environment:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Copy the example config:

```sh
cp .env.example .env
```

### 2. Spotify Developer setup

The script uses Spotify's Web API with the Authorization Code with PKCE flow.
It needs only the app's public Client ID, not the Client Secret.

1. Go to `https://developer.spotify.com/dashboard` and log in.
2. Click `Create app`.
3. Use any app name and description, for example:

   ```text
   App name: Spotify Album Bulb
   App description: Sync bulb color to current Spotify album art
   ```

4. For `Which API/SDKs are you planning to use?`, select only:

   ```text
   Web API
   ```

   Do not select `Ads API`, `iOS`, `Android`, or `Web Playback SDK`.

5. Add this redirect URI exactly:

   ```text
   http://127.0.0.1:8888/callback
   ```

6. Create/save the app, then copy the app's `Client ID`.
7. Put it in `.env`:

   ```env
   SPOTIFY_CLIENT_ID=0123456789abcdef0123456789abcdef
   SPOTIFY_REDIRECT_URI=http://127.0.0.1:8888/callback
   POLL_SECONDS=1
   ```

Do not put your Spotify username, email, password, or Client Secret in
`SPOTIFY_CLIENT_ID`.

On first run, the script opens Spotify login in your browser and stores the
resulting refresh token in `.cache/spotify_token.json`.

### 3. Smart Life and Tuya Cloud setup

Use the Smart Life app as the mobile app for this bulb. The Wipro app can
control the bulb, but Tuya Cloud's account-link QR flow is designed for
Smart Life/Tuya-compatible app accounts.

1. Install `Smart Life` on Android.
2. Reset and pair the bulb in Smart Life.
3. Go to `https://platform.tuya.com/` and log in or create a Tuya Developer
   account.
4. In the left navigation, open `Cloud`.
5. Click `Create Cloud Project`.
6. Use these project settings:

   ```text
   Development Method: Smart Home
   Data Center: the data center matching your Smart Life account region
   ```

   To confirm the app account region in Smart Life, open:

   ```text
   Me -> Settings -> Account and Security -> Region
   ```

   For an India Smart Life account, use `India Data Center` and:

   ```env
   TUYA_ENDPOINT=https://openapi.tuyain.com
   ```

7. Authorize these API services when prompted:

   ```text
   Industry Basic Service
   Smart Home Basic Service
   Device Status Notification
   ```

8. Open the new cloud project's `Overview` page. Under `Authorization Key`,
   copy:

   ```env
   TUYA_ACCESS_ID=<Access ID>
   TUYA_ACCESS_SECRET=<Access Secret>
   ```

   Do not use the Project ID here.

9. Link Smart Life devices to the cloud project:

   ```text
   Cloud project -> Devices -> Link Tuya App Account -> Add App Account
   ```

10. Scan the QR code with the Smart Life app and confirm the link in the app.
11. In Tuya Cloud, open:

    ```text
    Cloud project -> Devices -> All Devices
    ```

12. Find the bulb and copy its `Device ID` into `.env`:

    ```env
    TUYA_DEVICE_ID=<bulb device id>
    ```

Your Tuya config should look like:

```env
LIGHT_BACKEND=tuya_cloud
TUYA_ENDPOINT=https://openapi.tuyain.com
TUYA_ACCESS_ID=<cloud project access id>
TUYA_ACCESS_SECRET=<cloud project access secret>
TUYA_DEVICE_ID=<bulb device id>
TUYA_ENSURE_ON_COLOR_MODE=false
```

Common Tuya endpoints:

```text
China Data Center: https://openapi.tuyacn.com
Western America Data Center: https://openapi.tuyaus.com
Eastern America Data Center: https://openapi-ueaz.tuyaus.com
Central Europe Data Center: https://openapi.tuyaeu.com
Western Europe Data Center: https://openapi-weaz.tuyaeu.com
India Data Center: https://openapi.tuyain.com
Singapore Data Center: https://openapi-sg.iotbing.com
```

### 4. Backend choice

Configure one light backend:

- `LIGHT_BACKEND=tuya_cloud`: requires a Tuya IoT Cloud project, the cloud
  `Access ID`, `Access Secret`, and the bulb `Device ID`. Pairing the bulb in
  Smart Life and linking that app account to Tuya Cloud is the recommended path
  for this bulb.
- `LIGHT_BACKEND=homeassistant`: requires the bulb to already be exposed as a
  Home Assistant `light.*` entity and a Home Assistant long-lived access token.

### 5. Validate credentials

Check Spotify and album-art color extraction without touching the bulb:

```sh
python spotify_album_bulb.py --once --dry-run
```

Check Tuya device access and inferred color command names:

```sh
python spotify_album_bulb.py --print-tuya-spec
```

Test direct bulb control:

```sh
python spotify_album_bulb.py --rgb '#00aaff'
```

## Run

Test Spotify and color extraction without changing the bulb:

```sh
python spotify_album_bulb.py --once --dry-run
```

Run continuously:

```sh
python spotify_album_bulb.py
```

By default, Spotify is polled every 1 second. If Spotify returns a rate-limit
response, the script sleeps for Spotify's `Retry-After` value before polling
again. Tune the normal polling interval in `.env`:

```env
POLL_SECONDS=1
```

Or override it from the command line:

```sh
python spotify_album_bulb.py --poll-seconds 2
```

The script ignores album-art colors that are too dark or gray to produce useful
bulb output. If no usable color is found, it uses a fallback color. Tune that in
`.env`:

```env
ALBUM_COLOR_MIN_LUMINANCE=0.08
ALBUM_COLOR_MIN_SATURATION=0.12
ALBUM_COLOR_FALLBACK=#ff6600
```

This bulb advertises Tuya `control_data` with a native `gradient` mode, but in
testing it accepted that command without changing color. The script therefore
uses the reliable direct color command, `colour_data_v2`, for each song change.
By default it sends only the color command, which is faster when the bulb is
already on and already in color mode. If color changes stop applying after you
manually switch the bulb to another mode, set this in `.env`:

```env
TUYA_ENSURE_ON_COLOR_MODE=true
```

Print the Tuya device specification to verify command names:

```sh
python spotify_album_bulb.py --print-tuya-spec
```

Set a manual color to test bulb control:

```sh
python spotify_album_bulb.py --rgb '#00aaff'
```

On the first run, the script opens Spotify login in your browser and stores a
refresh token under `.cache/spotify_token.json`.

## Notes

If the Wipro Next Smart Home app cannot be linked to a Tuya IoT project, direct
Tuya Cloud control will not work even if the bulb is Tuya-based internally. In
that case, expose the bulb through Home Assistant and use the `homeassistant`
backend.

## Reference Docs

- Spotify app setup and Client ID: `https://developer.spotify.com/documentation/web-api/concepts/apps`
- Spotify PKCE authorization flow: `https://developer.spotify.com/documentation/web-api/tutorials/code-pkce-flow`
- Tuya Smart Home cloud project and Smart Life account linking: `https://developer.tuya.com/en/docs/iot/Platform_Configuration_smarthome?id=Kamcgamwoevrx`
- Tuya cloud endpoints by data center: `https://developer.tuya.com/en/docs/iot/api-request?id=Ka4a8uuo1j4t4`
