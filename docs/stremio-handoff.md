# Playing Stremio streams in mpv-object-audio

Stremio's own player is a plain libmpv: it does not load the object-audio engine, so an Atmos or DTS:X stream plays as its core bed at best and the heights stay silent. This page sets Stremio up to hand every stream to [`mpv-object-audio`](https://github.com/praveenchandrahas/mpv-object-audio) instead, with the theatre's video settings, the DSP profile switching and seek-bar thumbnails. It is how the author's laptop is set up (Kubuntu 24.04, Google Chrome), and it changes nothing inside Stremio's own code.

## How Stremio hands a stream over

On Linux, Stremio's only external-player option is **M3U Playlist**. When you press play, it writes a small playlist file (`playlist.m3u8`) holding the stream's address and asks the desktop to open it:

- the **desktop app** (the Flatpak `com.stremio.Stremio`, which builds the GTK/WebKit shell from [stremio-linux-shell](https://github.com/Stremio/stremio-linux-shell)) writes it to `~/Downloads/Stremio/playlist.m3u8` and opens it through the desktop portal (fixed in 1.1.2; read in the shell's source, 2026-11-26);
- **Stremio Web** in a browser downloads it like any other file.

Either way, whatever opens playlists on your desktop gets the stream. So there are two things to set: where the playlist lands, and what opens it.

The address in the playlist can carry keys of your add-ons' configuration. Treat the file as private; the watcher below moves it out of the downloads folder into `$XDG_RUNTIME_DIR` (memory only, readable by you only).

## Which Stremio to use

The author uses **Stremio Web installed as a Chrome app**. The Flatpak brings the whole GNOME runtime with it (a large download on a KDE desktop), and building the shell natively on 24.04 is not an option: it asks for libadwaita 1.8 and 24.04 has 1.5. The Flatpak works with the same handler (step 4b) if you prefer it; the watcher in step 4a would then watch `~/Downloads/Stremio` instead.

## 1. A Chrome profile for Stremio

Chrome's download folder and the "Ask where to save each file" switch are per profile, not per site. A profile of its own lets Stremio's playlists land in one folder without a dialog, while your normal profile keeps asking.

```bash
mkdir -p "$HOME/Stremio Downloads"
google-chrome --profile-directory=Stremio https://web.stremio.com
```

In that window:

- `chrome://settings/downloads`: **Location** `~/Stremio Downloads`, **Ask where to save each file** off.
- Sign in to Stremio, then **Settings → Player → Play in external player → M3U Playlist**.
- Install it as an app (the install icon at the right of the address bar). Use that app from now on.

An installed web app belongs to the profile that installed it. To check which one, run:

```bash
grep -H '^Exec=' $(grep -l 'Name=Stremio' ~/.local/share/applications/chrome-*.desktop)
```

`--profile-directory=Stremio` is right. Anything else (`Default`, `Profile 1`) uses that profile's download settings: uninstall it from the app's menu (**⋮ → Uninstall**) and install it again from the Stremio profile.

## 2. Check the player

```bash
command -v mpv-object-audio      # must print a path
```

## 3. Optional: thumbnails on the seek bar

A stream has no place in the film library, so [seekthumbs](https://github.com/praveenchandrahas/seekthumbs) builds its thumbnails while it plays and drops them when mpv closes. Turn that on once:

```bash
seekthumbs install-viewer --live            # packaged install; or: python3 seekthumbs.py install-viewer --live in the repository
```

On the author's rig a 157-minute 4K stream read about 2 MB per thumbnail, about 2 GB for the whole film, and playback did not change while it ran ([seekthumbs usage](https://praveenchandrahas.github.io/seekthumbs/usage/)).

## 4a. The watcher (recommended): play as soon as the playlist lands

A systemd path unit watches `~/Stremio Downloads`. When a playlist appears, a script takes the first web address out of it, moves the file to `$XDG_RUNTIME_DIR/stremio-last.m3u8`, and starts `mpv-object-audio` with the address as its own transient unit. No click, no "open with" dialog.

Paste the whole block:

```bash
OA="$(command -v mpv-object-audio)"
if [ -z "$OA" ]; then
  echo "mpv-object-audio not found"
else
mkdir -p ~/.local/bin ~/.config/systemd/user ~/"Stremio Downloads"

cat > ~/.local/bin/stremio-watch <<EOF
#!/bin/bash
PLAYER="$OA"
EOF
cat >> ~/.local/bin/stremio-watch <<'EOF'
DIR="$HOME/Stremio Downloads"
shopt -s nullglob
sleep 0.5
for f in "$DIR"/playlist*.m3u "$DIR"/playlist*.m3u8; do
  url="$(tr -d '\r' < "$f" | grep -m1 -E '^https?://')"
  mv -f "$f" "$XDG_RUNTIME_DIR/stremio-last.m3u8"
  if [ -n "$url" ]; then
    systemd-run --user --collect --quiet "$PLAYER" --force-window=yes -- "$url"
  else
    echo "no web link found in $f"
  fi
done
EOF
chmod +x ~/.local/bin/stremio-watch

cat > ~/.config/systemd/user/stremio-watch.service <<'EOF'
[Unit]
Description=Play new Stremio playlists

[Service]
Type=oneshot
ExecStart=%h/.local/bin/stremio-watch
EOF

cat > ~/.config/systemd/user/stremio-watch.path <<'EOF'
[Unit]
Description=Watch for Stremio playlists

[Path]
PathExistsGlob=%h/Stremio Downloads/playlist*.m3u*

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable stremio-watch.path
systemctl --user restart stremio-watch.path
systemctl --user is-active stremio-watch.path
fi
```

The last line prints `active`. Then press play on a stream in Stremio.

- **It acts on any matching file** in `~/Stremio Downloads`: every `playlist*.m3u`/`.m3u8` there is moved away and its first web address played. Keep nothing else of that name in that folder.
- **Do not also click the download** in Chrome, or two players start.
- **mpv's output** (and seekthumbs' `seekthumbs live:` lines) go to the journal, since the player runs as a systemd unit: `journalctl --user -n 50 --no-pager`.
- **Undo:** `systemctl --user disable --now stremio-watch.path`, then delete `~/.local/bin/stremio-watch` and the two unit files.

## 4b. Without the watcher: make the player the playlist handler

If you would rather click the download (or you use the Flatpak, which opens the playlist itself), register `mpv-object-audio` as the handler for playlists. No sudo; your other players are untouched.

```bash
OA="$(command -v mpv-object-audio)"
mkdir -p ~/.local/share/applications
cat > ~/.local/share/applications/stremio-mpv.desktop <<EOF
[Desktop Entry]
Type=Application
Name=Stremio to mpv-object-audio
Exec=$OA --force-window=yes -- %f
Terminal=false
NoDisplay=true
MimeType=application/vnd.apple.mpegurl;audio/x-mpegurl;application/x-mpegurl;
EOF
for t in application/vnd.apple.mpegurl audio/x-mpegurl application/x-mpegurl; do
  xdg-mime default stremio-mpv.desktop "$t"
  echo "$t -> $(xdg-mime query default "$t")"
done
```

All three lines end in `stremio-mpv.desktop`. Every `.m3u`/`.m3u8` on the computer then opens in this player. The entry is hidden from menus (`NoDisplay`), so check it with `xdg-mime`, not in System Settings. mpv opens the playlist and plays the address in it, so seekthumbs' stream thumbnails work here too (checked: a script in mpv sees the address, not the file). The playlists stay in the downloads folder.

## What you lose against Stremio's own player

- **Resume, watch progress, next-episode autoplay:** the playlist carries only the address, so Stremio does not learn how far you watched.
- **Subtitles from add-ons:** not passed over; subtitles inside the file still work.
- **Streams Stremio serves itself** (addresses on `127.0.0.1:11470`, from its own streaming server) need Stremio (or Stremio Service) running while they play, and seekthumbs builds no thumbnails for them: every seek there would fetch new pieces of the stream.

## What has been checked

On the author's laptop, 2026-11-26: Stremio Web as a Chrome app in its own profile, the watcher above, `mpv-object-audio` starting by itself on play, and seekthumbs' stream thumbnails on the seek bar with uosc. One machine and one evening of use; resume and subtitles were not tried, and the Flatpak route (4b with the Flatpak) was read in Stremio's source, not run.
