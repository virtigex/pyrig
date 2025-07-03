import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import sys
import zipfile
import io
import wave
import numpy as np
import librosa
import os

MAIN_LINK = 'https://audio.stickerburr.net/files/index.html'
RECORD_DIR = 'log-wa6tow'

os.makedirs(RECORD_DIR, exist_ok=True)

visited = set()

headers = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

def find_audio_links_recursive(base_url, root_domain):
    """
    Recursively scans HTML pages starting from base_url,
    prints all audio file URLs, and visits linked pages.
    """
    if base_url in visited:
        return
    visited.add(base_url)

    try:
        response = requests.get(base_url, timeout=10, headers=headers)
        response.raise_for_status()
    except Exception as e:
        print(f"[ERROR] Failed to fetch {base_url}: {e}")
        return

    soup = BeautifulSoup(response.text, 'html.parser')
    audio_extensions = ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a']

    # Find and print audio links
    for link in soup.find_all('a', href=True):
        href = link['href']
        absolute_url = urljoin(base_url, href)
        parsed = urlparse(absolute_url)
        if any(parsed.path.lower().endswith(ext) for ext in audio_extensions):
            print(f"[AUDIO] {absolute_url}")

    # Recursively follow links to other HTML pages on the same domain
    for link in soup.find_all('a', href=True):
        href = link['href']
        absolute_url = urljoin(base_url, href)
        parsed = urlparse(absolute_url)

        # Stay within the same domain
        if parsed.netloc != root_domain:
            continue

        # Avoid visiting non-HTML resources
        #url = parsed.path.lower()
        #if any(url.endswith(ext) for ext in audio_extensions):
        #    continue
        if absolute_url.split('.')[-1] in ['zip']:
            try:
                zip_resp = requests.get(absolute_url, timeout=20, headers=headers)
                zip_resp.raise_for_status()
                with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
                    for name in zf.namelist():
                        if name.lower().endswith('.wav'):
                            with zf.open(name) as wav_file:
                                with wave.open(wav_file, 'rb') as wf:
                                    nframes = wf.getnframes()
                                    framerate = wf.getframerate()
                                    print(f"[WAV] {name}: {nframes} samples, {framerate} Hz")
                                    save_path = os.path.join(RECORD_DIR, os.path.basename(name))
                                    with open(save_path, 'wb') as out_f:
                                        out_f.write(zf.read(name))
                                    print(f"[SAVED] {save_path}")
                                    # Read WAV data into numpy array
                                    wav_file.seek(0)
                                    y, sr = librosa.load(wav_file, sr=None, mono=True)

                                    # Simple energy-based speech detection
                                    energy = np.mean(y ** 2)
                                    threshold = 0.01  # This value may need tuning

                                    if energy > threshold:
                                        print(f"[SPEECH] {name}: likely speech (energy={energy:.5f})")
                                    else:
                                        print(f"[NOISE] {name}: likely noise (energy={energy:.5f})")

            except Exception as e:
                print(f"[ERROR] Failed to process zip {absolute_url}: {e}")
            continue

        find_audio_links_recursive(absolute_url, root_domain)

if __name__ == "__main__":
    start_url = MAIN_LINK
    parsed_start = urlparse(start_url)
    domain = parsed_start.netloc
    if not parsed_start.scheme.startswith("http"):
        print("[ERROR] URL must start with http:// or https://")
        sys.exit(1)

    print(f"[INFO] Starting recursive scan from {start_url} on domain {domain}")
    find_audio_links_recursive(start_url, domain)

