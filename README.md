# GCC CarTV Playlist

This repo creates one M3U playlist for CarTV.

It starts with the complete IPTV-org GCC playlist and tries to add these public channels when compatible streams are available in IPTV-org:

- MBC Bollywood
- Zee Aflam / Zee Aflam HD
- Zee Cinema
- Zee Alwan
- Abu Dhabi Sports 1, 2, 3
- Sharjah Sports
- Dubai Sports 1, 2, 3
- Dubai Racing 1, 2, 3
- Yas TV

Premium or subscription-only beIN Sports streams are not included. If your TV provider gives you an authorized M3U entry, place those entries in `custom_authorized.m3u`. The builder will merge them into the final playlist.

## Fast setup

1. Create a new PUBLIC GitHub repository named `gcc-cartv`.
2. Upload every file from this package. Make sure the `.github/workflows/update.yml` path stays exactly the same.
3. Open the repository's **Actions** tab. Choose **Update CarTV playlist**. Press **Run workflow**.
4. After it finishes, your permanent playlist URL is:

   `https://raw.githubusercontent.com/YOUR_USERNAME/gcc-cartv/main/playlist.m3u`

Replace `YOUR_USERNAME` with your GitHub username.

Paste that URL into CarTV as an M3U playlist URL.

## Automatic updates

GitHub Actions rebuilds the playlist once per day from IPTV-org, so changes to public GCC feeds flow into your playlist.

## Notes

- A listed TV channel does not guarantee a public HLS/M3U feed exists.
- Zee Aflam has official live viewing through ZEE5, but a normal web page or DRM stream is not interchangeable with a CarTV M3U URL.
- Keep `custom_authorized.m3u` private if your provider URL contains a personal token. If it has a token, do not use a public GitHub repository.
