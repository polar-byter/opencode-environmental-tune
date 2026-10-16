"""Build a reproducible, architecture-independent Debian desktop package."""
import argparse
import gzip
import hashlib
import io
from pathlib import Path
import re
import tarfile

from .installer import payload

SHARE = 'usr/share/opencode-kit'
LAUNCHER = b'#!/bin/sh\nexec sh /usr/share/opencode-kit/install.sh "$@"\n'
# Build prerequisites for the exact private CPython, not the distro's Python version.
DEPENDENCIES = ('ca-certificates, curl, xz-utils, build-essential, pkg-config, '
                'libssl-dev, zlib1g-dev, libbz2-dev, libreadline-dev, libsqlite3-dev, '
                'libffi-dev, liblzma-dev, tk-dev, uuid-dev, util-linux, xdg-utils, zenity')
DESKTOP = '''[Desktop Entry]
Type=Application
Name=OpenCode Kit
Name[ru]=OpenCode Kit — новый проект
Comment=Create a project and configure its AI models
Comment[ru]=Создать проект и настроить модели ИИ
Exec=/usr/bin/opencode-kit-installer
TryExec=/usr/bin/opencode-kit-installer
Icon=opencode-kit
Terminal=false
Categories=Development;
StartupNotify=false
'''


def archive(files):
    """Return a deterministic tar.gz with explicit root ownership and modes."""
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w', format=tarfile.USTAR_FORMAT) as output:
        directories = {parent.as_posix() for name in files for parent in Path(name).parents if parent.as_posix() != '.'}
        for name in sorted(directories):
            entry = tarfile.TarInfo(name + '/')
            entry.type, entry.mode = tarfile.DIRTYPE, 0o755
            output.addfile(entry)
        for name, (data, mode) in sorted(files.items()):
            entry = tarfile.TarInfo(name)
            entry.mode, entry.size = mode, len(data)
            output.addfile(entry, io.BytesIO(data))
    return gzip.compress(stream.getvalue(), mtime=0)


def build(source, destination, version='0.2.0'):
    """Package only the installer allowlist; never read user keys or task journals."""
    if not re.fullmatch(r'[0-9]+(?:\.[0-9]+)*(?:-[0-9]+)?', version):
        raise ValueError('Use a numeric Debian version, for example 0.1.0 or 0.1.0-1.')
    source, destination = Path(source).resolve(), Path(destination)
    files = {f'{SHARE}/{name}': (content, 0o755 if name.endswith('.sh') else 0o644)
             for name, content in payload(source).items()}
    for name in ('install.py', 'LICENSE'):
        files[f'{SHARE}/{name}'] = ((source / name).read_bytes(), 0o644)
    files['usr/bin/opencode-kit-installer'] = (LAUNCHER, 0o755)
    files['usr/share/applications/opencode-kit.desktop'] = (DESKTOP.encode(), 0o644)
    files['usr/share/icons/hicolor/256x256/apps/opencode-kit.png'] = (
        (source / 'kit/configurator/assets/app-256.png').read_bytes(), 0o644)
    files['usr/share/doc/opencode-kit/copyright'] = ((source / 'LICENSE').read_bytes(), 0o644)
    control = (f'Package: opencode-kit\nVersion: {version}\nArchitecture: all\n'
        'Maintainer: Dmitry Kim <shtolce159@email.com>\n'
        'Section: devel\nPriority: optional\n'
        f'Depends: {DEPENDENCIES}\n'
        f'Installed-Size: {(sum(len(data) for data, mode in files.values()) + 1023) // 1024}\n'
        'Homepage: https://github.com/polar-byter/opencode-environmental-tune\n'
        'Description: Graphical project setup for the OpenCode orchestration kit\n'
        ' Create a project folder, configure AI models and open OpenCode Desktop.\n')
    checksums = ''.join(hashlib.md5(data).hexdigest() + '  ' + name + '\n' for name, (data, mode) in sorted(files.items()))
    members = {'debian-binary': b'2.0\n', 'control.tar.gz': archive({
        'control': (control.encode(), 0o644), 'md5sums': (checksums.encode(), 0o644)}), 'data.tar.gz': archive(files)}
    result = bytearray(b'!<arch>\n')
    for name, data in members.items():
        result.extend(f'{name + "/":<16}{0:<12}{0:<6}{0:<6}{"100644":<8}{len(data):<10}`\n'.encode('ascii'))
        result.extend(data)
        if len(data) % 2:
            result.extend(b'\n')
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(result)
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--version', default='0.2.0')
    args = parser.parse_args()
    print(build(args.source, args.output, args.version))


if __name__ == '__main__':
    main()
