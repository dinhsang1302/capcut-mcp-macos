"""Back up and configure the native macOS entry point and empty arguments."""
import argparse
import copy
from datetime import datetime
import json
from pathlib import Path
import re
import tempfile
import tomllib


def configure(config: Path, executable: Path) -> dict:
    executable = executable.resolve()
    if not executable.is_file():
        raise FileNotFoundError(f'Missing executable: {executable}')
    original = config.read_bytes() if config.exists() else b''
    text = original.decode('utf-8-sig')
    before = tomllib.loads(text)
    if 'url' in before.get('mcp_servers', {}).get('capcut', {}):
        raise ValueError('CapCut currently uses a URL transport. Review it manually; no changes made.')
    command = executable.as_posix()
    expected = copy.deepcopy(before)
    expected.setdefault('mcp_servers', {}).setdefault('capcut', {})['command'] = command
    expected['mcp_servers']['capcut']['args'] = []
    if before == expected:
        return {'changed': False, 'config': str(config), 'backup': None}
    nl = '\r\n' if '\r\n' in text else '\n'
    line = 'command = ' + json.dumps(command, ensure_ascii=False)
    if 'capcut' not in before.get('mcp_servers', {}):
        separator = ('' if text.endswith('\n') else nl) + nl if text else ''
        updated = text + separator + '[mcp_servers.capcut]' + nl + line + nl + 'args = []' + nl
    else:
        header = re.search(r'(?m)^[ \t]*\[mcp_servers\.capcut\][ \t]*(?:#[^\r\n]*)?(?=\r?$)', text)
        if not header:
            raise ValueError('Nonstandard CapCut declaration. Back up and edit manually; no changes made.')
        start = header.end()
        next_header = re.search(r'(?m)^[ \t]*\[', text[start:])
        end = start + next_header.start() if next_header else len(text)
        section = text[start:end]
        cmd = re.search(r'(?m)^[ \t]*command[ \t]*=[^\r\n]*', section)
        if cmd:
            previous_line = cmd.group(0)
            # Complex/multiline values require manual review, not guessed text edits.
            parsed = tomllib.loads('[x]\n' + previous_line).get('x', {}).get('command')
            if parsed != before['mcp_servers']['capcut']['command']:
                raise ValueError('Complex command value; edit manually. No changes made.')
            section = section[:cmd.start()] + line + section[cmd.end():]
        else:
            section = nl + line + section
        args_line = re.search(r'(?m)^[ \t]*args[ \t]*=[^\r\n]*', section)
        if args_line:
            parsed = tomllib.loads('[x]\n' + args_line.group(0)).get('x', {}).get('args')
            if parsed != before['mcp_servers']['capcut'].get('args'):
                raise ValueError('Complex args value; edit manually. No changes made.')
            section = section[:args_line.start()] + 'args = []' + section[args_line.end():]
        else:
            section = nl + 'args = []' + section
        updated = text[:start] + section + text[end:]
    after = tomllib.loads(updated)
    if after != expected:
        raise ValueError('Unrelated settings would change; no changes made.')
    payload = (b'\xef\xbb\xbf' if original.startswith(b'\xef\xbb\xbf') else b'') + updated.encode('utf-8')
    config.parent.mkdir(parents=True, exist_ok=True)
    backup = None
    if config.exists():
        if config.read_bytes() != original:
            raise RuntimeError('Config changed during operation; retry after checking it.')
        backup = config.with_name(config.name + '.bak-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
        with backup.open('xb') as stream:
            stream.write(original)
        assert backup.read_bytes() == original
    temporary = None
    try:
        with tempfile.NamedTemporaryFile(dir=config.parent, suffix='.capcut-tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write(payload)
        if config.exists() and config.read_bytes() != original:
            raise RuntimeError('Config changed before write; no overwrite performed.')
        temporary.replace(config)
        assert tomllib.loads(config.read_bytes().decode('utf-8-sig')) == expected
    finally:
        if temporary and temporary.exists():
            temporary.unlink()
    return {'changed': True, 'config': str(config), 'backup': str(backup) if backup else None}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--config', type=Path, default=Path.home()/'.codex'/'config.toml')
    parser.add_argument('--exe', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(configure(args.config, args.exe), ensure_ascii=False))
