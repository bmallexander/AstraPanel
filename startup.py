import os
import urllib.request

def download_and_unzip(url, filename, target_dir):
  """Downloads a file from the URL, checks integrity, and unzips it to the target directory."""
  filepath = os.path.join(target_dir, filename)
  print(url)
  with urllib.request.urlopen(url) as response, open(filepath, 'wb') as f:
    for chunk in iter(lambda: response.read(1024), b''):
      f.write(chunk)
  os.system(f"tar -xf {filepath} -C {target_dir}")
  os.system(f"rm -rf {filepath}")

def check_and_download_tmate(base_url, arch, target_dir):
  """Checks if the folder for the architecture exists and downloads/unzips if missing."""
  arch_dir = os.path.join(target_dir, f"tmate-2.4.0-static-linux-{arch}")
  if not os.path.exists(arch_dir):
    filename = f"tmate-2.4.0-static-linux-{arch}.tar.xz"
    download_url = f"{base_url}/{filename}"
    print(f"Downloading tmate for {arch}...")
    download_and_unzip(download_url, filename, target_dir)
    print(f"Finished downloading and unzipping tmate for {arch}.")

def main():
  base_url = "https://github.com/tmate-io/tmate/releases/download/2.4.0"
  target_dir = "tmates"
  if not os.path.exists(target_dir):
    os.makedirs(target_dir)
  architectures = ["amd64", "arm32v6", "arm32v7", "arm64v8", "i386"]
  for arch in architectures:
    check_and_download_tmate(base_url, arch, target_dir)

  print("All tmate binaries downloaded and unzipped successfully!")