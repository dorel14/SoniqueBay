#!/usr/bin/env python3
with open('.env', 'rb') as f:
    content = f.read()
    lines = content.split(b'\n')
    for i, line in enumerate(lines, 1):
        if b'POSTGRES_PASSWORD' in line:
            print(f'Line {i} (raw bytes): {line}')
            print(f'Line {i} (decoded utf-8): {line.decode("utf-8", errors="replace")}')
            print(f'Hex: {line.hex()}')
