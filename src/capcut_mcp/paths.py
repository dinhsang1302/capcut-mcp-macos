"""macOS-native discovery. Candidate locations must be verified on disk.

Process-inspection errors refuse writes rather than claiming CapCut is closed.
"""
from __future__ import annotations
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys

DRAFT_DIR_NAME = 'com.lveditor.draft'
ENV_DRAFT_ROOT = 'CAPCUT_MCP_DRAFT_ROOT'
ENV_APP = 'CAPCUT_MCP_APP'
META_FILE = 'root_meta_info.json'


class ProcessInspectionError(RuntimeError):
    """The process state is unknown, so writing is unsafe."""


def _is_dir(path: Path) -> bool:
    try:
        return path.is_dir()
    except OSError:
        return False


def _is_file(path: Path) -> bool:
    try:
        return path.is_file()
    except OSError:
        return False


def _application_bundles():
    if explicit := os.environ.get(ENV_APP):
        yield Path(explicit).expanduser()
        return
    for folder in [Path('/Applications'), Path.home()/'Applications']:
        for name in ['CapCut.app', 'Capcut.app', 'JianyingPro.app', '剪映专业版.app']:
            yield folder/name


def _bundle_info(bundle: Path) -> dict:
    try:
        with (bundle/'Contents'/'Info.plist').open('rb') as stream:
            info = plistlib.load(stream)
        return info if isinstance(info, dict) else {}
    except (OSError, ValueError, plistlib.InvalidFileException):
        return {}


def installed_version() -> str | None:
    for bundle in _application_bundles():
        info = _bundle_info(bundle)
        if version := info.get('CFBundleShortVersionString') or info.get('CFBundleVersion'):
            return str(version)
    return None


def _candidate_roots():
    home = Path.home()
    bases = [home/'Movies', home/'Library'/'Application Support']
    for bundle in _application_bundles():
        identifier = _bundle_info(bundle).get('CFBundleIdentifier')
        if identifier and re.fullmatch(r'[A-Za-z0-9_.-]+', identifier):
            container = home/'Library'/'Containers'/identifier/'Data'
            bases += [container/'Movies', container/'Library'/'Application Support']
    for base in bases:
        for name in ['CapCut', 'Capcut', 'JianyingPro']:
            yield base/name/'User Data'/'Projects'/DRAFT_DIR_NAME
            yield base/name/'Projects'/DRAFT_DIR_NAME


def find_draft_root(explicit: str | None = None) -> Path:
    if supplied := explicit or os.environ.get(ENV_DRAFT_ROOT):
        root = Path(supplied).expanduser()
        if _is_file(root/META_FILE):
            return root
        raise FileNotFoundError(f'No {META_FILE} under configured draft root {root}')
    found = {}
    for candidate in _candidate_roots():
        if _is_file(candidate/META_FILE):
            found[str(candidate.resolve())] = candidate
    if len(found) == 1:
        return next(iter(found.values()))
    if len(found) > 1:
        raise FileNotFoundError('Multiple draft stores. Set CAPCUT_MCP_DRAFT_ROOT explicitly: ' + ', '.join(found))
    raise FileNotFoundError('No verified draft store. Set CAPCUT_MCP_DRAFT_ROOT to the folder containing root_meta_info.json; default candidates vary by CapCut build.')


def running_pids() -> list[int]:
    if sys.platform != 'darwin':
        raise ProcessInspectionError('macOS only: cannot verify CapCut process state on this platform.')
    try:
        result = subprocess.run(['/bin/ps', '-axo', 'pid=,comm='], capture_output=True, text=True, timeout=15, check=True)
    except (OSError, subprocess.SubprocessError) as exc:
        raise ProcessInspectionError(f'Cannot inspect processes; refusing writes: {exc}') from exc
    names = {'capcut', 'jianyingpro', '剪映专业版'}
    bundles = {p.name.casefold() for p in _application_bundles()}
    pids = []; parsed = 0
    for line in result.stdout.splitlines():
        match = re.match(r'^\s*(\d+)\s+(.+?)\s*$', line)
        if not match:
            if line.strip():
                raise ProcessInspectionError('Unrecognised process row; refusing writes.')
            continue
        parsed += 1
        executable = Path(match.group(2))
        if executable.name.casefold() in names or bundles.intersection(part.casefold() for part in executable.parts):
            pids.append(int(match.group(1)))
    if not parsed:
        raise ProcessInspectionError('Empty/unrecognised process listing; refusing writes.')
    return sorted(set(pids))


def list_projects(draft_root: Path | None = None) -> list[dict]:
    root = draft_root or find_draft_root()
    meta = json.loads((root/META_FILE).read_text(encoding='utf-8-sig'))
    projects = []
    for entry in meta.get('all_draft_store', []):
        if entry.get('tm_draft_removed'):
            continue
        raw = entry.get('draft_fold_path') or ''
        foreign = bool(re.match(r'^[A-Za-z]:[\\/]', raw)) or raw.startswith(('\\\\', '//'))
        folder = Path(raw).expanduser() if raw else None
        if folder is not None and not foreign and not folder.is_absolute():
            folder = root/folder
        projects.append({'name':entry.get('draft_name') or (folder.name if folder else ''),
                         'path':str(folder) if folder else '', 'draft_id':entry.get('draft_id'),
                         'modified_us':entry.get('tm_draft_modified') or 0,
                         'duration_s':round((entry.get('tm_duration') or 0)/1_000_000, 3),
                         'available':bool(folder and not foreign and _is_file(folder/'draft_content.json'))})
    return sorted(projects, key=lambda p:p['modified_us'], reverse=True)


def resolve_project(name_or_path: str, draft_root: Path | None = None) -> Path:
    direct = Path(name_or_path).expanduser()
    if _is_file(direct/'draft_content.json'):
        return direct
    projects = list_projects(draft_root); wanted = name_or_path.strip().casefold()
    matches = [p for p in projects if p['name'].casefold() == wanted]
    matches = matches or [p for p in projects if wanted in p['name'].casefold()]
    if len(matches) > 1:
        raise ValueError('Ambiguous project name. Use its absolute folder path.')
    if not matches:
        raise FileNotFoundError(f'No CapCut project named {name_or_path!r}')
    if not matches[0]['available']:
        raise FileNotFoundError('Registered project has no available local draft: ' + matches[0]['path'])
    return Path(matches[0]['path'])


def _find_in_capcut_apps(glob_pattern: str) -> str | None:
    for bundle in _application_bundles():
        contents = bundle/'Contents'
        if not _is_dir(contents):
            continue
        for hit in sorted(contents.glob(glob_pattern)):
            if _is_file(hit):
                return str(hit)
        resources = contents/'Resources'
        if _is_dir(resources):
            for hit in sorted(resources.rglob(Path(glob_pattern).name)):
                if _is_file(hit):
                    return str(hit)
    return None


def find_denoise_model() -> str | None:
    return _find_in_capcut_apps('Resources/audiosami/unet_denoise_*.model')


def find_bundled_font() -> str | None:
    return (_find_in_capcut_apps('Resources/Font/SystemFont/NotoSans-Regular.ttf')
            or _find_in_capcut_apps('Resources/Font/SystemFont/en.ttf'))


def binary(name: str) -> str:
    if name not in {'ffmpeg', 'ffprobe'}:
        raise ValueError('Unsupported executable name')
    if configured := os.environ.get('CAPCUT_MCP_' + name.upper()):
        path = Path(configured).expanduser()
        if not path.is_absolute() or not _is_file(path) or not os.access(path, os.X_OK):
            raise FileNotFoundError(f'Configured {name} is not an absolute executable file: {path}')
        return str(path)
    if discovered := shutil.which(name):
        return discovered
    # GUI Codex may not inherit Homebrew shell PATH.
    for prefix in ['/opt/homebrew/bin', '/usr/local/bin']:
        path = Path(prefix)/name
        if _is_file(path) and os.access(path, os.X_OK):
            return str(path)
    raise FileNotFoundError(f'{name} missing. Install it or set CAPCUT_MCP_{name.upper()} to its absolute executable path.')


def probe(explicit_root: str | None = None) -> dict:
    report = {'platform':'macOS', 'supported_platform':sys.platform == 'darwin',
              'capcut_version':installed_version(), 'running_pids':None,
              'process_check_ok':False, 'draft_root':None, 'projects':0,
              'plaintext_drafts':None, 'draft_schema_version':None,
              'ffmpeg':None, 'ffprobe':None, 'denoise_model':find_denoise_model(), 'warnings':[]}
    try:
        report['running_pids'] = running_pids(); report['process_check_ok'] = True
    except ProcessInspectionError as exc:
        report['warnings'].append(str(exc))
    for name in ['ffmpeg','ffprobe']:
        try:
            result = subprocess.run([binary(name), '-version'], capture_output=True, text=True, timeout=15, check=True)
            report[name] = result.stdout.splitlines()[0]
        except (OSError, subprocess.SubprocessError, IndexError) as exc:
            report['warnings'].append(f'{name}: {exc}')
    try:
        root = find_draft_root(explicit_root); report['draft_root'] = str(root)
        projects = list_projects(root); report['projects'] = len(projects)
        for project in projects:
            if not project['available']:
                continue
            try:
                data = json.loads((Path(project['path'])/'draft_content.json').read_text(encoding='utf-8-sig'))
                if not isinstance(data, dict) or not isinstance(data.get('tracks'), list) or not isinstance(data.get('materials'), dict):
                    raise ValueError('Unrecognised draft structure')
                report['plaintext_drafts'] = True; report['draft_schema_version'] = data.get('version')
                report['app_version_in_draft'] = data.get('new_version')
            except (OSError, UnicodeError, ValueError) as exc:
                report['plaintext_drafts'] = False; report['warnings'].append(f'Draft is not readable/recognised: {exc}')
            break
    except (OSError, UnicodeError, ValueError) as exc:
        report['warnings'].append(str(exc))
    if report['plaintext_drafts'] is None:
        report['warnings'].append('No local draft tested. Create a sample project before editing.')
    if report['running_pids']:
        report['warnings'].append('CapCut is running. Quit it normally before saving.')
    if not report['capcut_version']:
        report['warnings'].append('App bundle not identified. Set CAPCUT_MCP_APP if moved/renamed.')
    return report
