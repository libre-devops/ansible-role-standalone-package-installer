#!/usr/bin/env python3
"""Print the package name and version inside RPM and DEB files, as JSON.

Usage: package_info.py FILE...

The role runs this on the control node, so it can tell whether a host already has each package
before pushing anything, whatever the files are called. Microsoft names its RPMs
mdatp_101.23072.0021.x86_64.rpm, for example, which is not the usual name-version-release form.

RPM: the name, version and release from the package header (the epoch is left out, as
`rpm -q --queryformat '%{VERSION}-%{RELEASE}'` leaves it out). DEB: Package and Version from the
control file, read with the standard library. A file it cannot read gets empty strings, and the
role then pushes it every time and lets the package manager decide.
"""

import io
import json
import lzma
import struct
import sys
import tarfile

RPM_MAGIC = b"\xed\xab\xee\xdb"
HEADER_MAGIC = b"\x8e\xad\xe8\x01"
RPMTAG_NAME, RPMTAG_VERSION, RPMTAG_RELEASE = 1000, 1001, 1002
RPM_STRING = 6


def read_header(handle):
    """One RPM header structure: its tags, as {tag: (type, offset)}, and its data store."""
    intro = handle.read(16)
    if len(intro) != 16 or intro[:4] != HEADER_MAGIC:
        raise ValueError("not an RPM header")
    count, size = struct.unpack(">II", intro[8:16])
    index = handle.read(16 * count)
    store = handle.read(size)
    tags = {}
    for i in range(count):
        tag, kind, offset, _ = struct.unpack(">IIII", index[16 * i : 16 * i + 16])
        tags[tag] = (kind, offset)
    return tags, store, 16 + 16 * count + size


def rpm_string(tags, store, tag):
    kind, offset = tags[tag]
    if kind != RPM_STRING:
        raise ValueError(f"RPM tag {tag} is not a string")
    return store[offset : store.index(b"\0", offset)].decode()


def rpm_info(path):
    with open(path, "rb") as handle:
        if handle.read(96)[:4] != RPM_MAGIC:
            raise ValueError("not an RPM file")
        _, _, length = read_header(handle)  # the signature header
        handle.read((8 - length % 8) % 8)  # padded to a multiple of 8 bytes
        tags, store, _ = read_header(handle)
    name = rpm_string(tags, store, RPMTAG_NAME)
    return name, f"{rpm_string(tags, store, RPMTAG_VERSION)}-{rpm_string(tags, store, RPMTAG_RELEASE)}"


def deb_control(path):
    """The control file from a DEB, which is an ar archive holding control.tar.*."""
    with open(path, "rb") as handle:
        if handle.read(8) != b"!<arch>\n":
            raise ValueError("not a DEB file")
        while True:
            header = handle.read(60)
            if len(header) < 60:
                raise ValueError("no control archive")
            member = header[:16].decode().strip().rstrip("/")
            size = int(header[48:58].decode().strip())
            data = handle.read(size)
            handle.read(size % 2)
            if member.startswith("control.tar"):
                break
    if member.endswith(".xz"):
        data = lzma.decompress(data)
    elif member.endswith(".zst"):
        try:
            from compression import zstd  # Python 3.14 and later
        except ImportError:
            raise ValueError("zstd-compressed control archive needs Python 3.14 on the control node") from None
        data = zstd.decompress(data)
    with tarfile.open(fileobj=io.BytesIO(data)) as archive:
        for entry in archive.getmembers():
            if entry.name.lstrip("./") == "control":
                return archive.extractfile(entry).read().decode()
    raise ValueError("no control file")


def deb_info(path):
    fields = {}
    for line in deb_control(path).splitlines():
        if ":" in line and not line.startswith((" ", "\t")):
            key, value = line.split(":", 1)
            fields[key.strip()] = value.strip()
    return fields["Package"], fields["Version"]


def main() -> int:
    out = []
    for path in sys.argv[1:]:
        try:
            name, version = rpm_info(path) if path.endswith(".rpm") else deb_info(path)
            out.append({"path": path, "name": name, "version": version, "error": ""})
        except (OSError, ValueError, KeyError, tarfile.TarError, lzma.LZMAError) as error:
            out.append({"path": path, "name": "", "version": "", "error": str(error)})
    print(json.dumps(out))
    return 0


if __name__ == "__main__":
    sys.exit(main())
