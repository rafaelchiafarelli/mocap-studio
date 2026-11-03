"""Reads single members of a remote zip through HTTP range requests, so a 23 GB archive isn't downloaded whole."""
import os, time, urllib.request, zipfile


class RangeFile:
    """The file interface zipfile needs, served by byte ranges."""

    def __init__(self, url, chunk=1 << 20):
        self.url, self.pos, self.chunk = url, 0, chunk
        self.size = int(urllib.request.urlopen(urllib.request.Request(url, method="HEAD"), timeout=60).headers["content-length"])
        self.base, self.buf = 0, b""

    def seekable(self):
        return True

    def seek(self, offset, whence=0):
        self.pos = {0: offset, 1: self.pos + offset, 2: self.size + offset}[whence]
        return self.pos

    def tell(self):
        return self.pos

    def _fetch(self, start, n):
        for attempt in range(8):
            try:
                req = urllib.request.Request(self.url, headers={"Range": f"bytes={start}-{start + n - 1}"})
                return urllib.request.urlopen(req, timeout=120).read()
            except OSError:
                time.sleep(5 * (attempt + 1))  # Zenodo limits requests per minute
        raise OSError(f"range {start}+{n} failed: {self.url}")

    def read(self, n=-1):
        if n < 0:
            n = self.size - self.pos
        n = min(n, self.size - self.pos)
        if n <= 0:
            return b""
        if not (self.base <= self.pos and self.pos + n <= self.base + len(self.buf)):
            self.buf = self._fetch(self.pos, max(n, self.chunk))
            self.base = self.pos
        out = self.buf[self.pos - self.base:self.pos - self.base + n]
        self.pos += len(out)
        return out


def open_zip(url):
    return zipfile.ZipFile(RangeFile(url))


def extract(archive, names, out_dir):
    """Copies members to out_dir, keeping their paths; a file already there is not read again."""
    done = []
    for name in names:
        dest = os.path.join(out_dir, name)
        if not os.path.exists(dest):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            data = archive.read(name)
            with open(dest + ".part", "wb") as f:
                f.write(data)
            os.replace(dest + ".part", dest)
        done.append(dest)
    return done
