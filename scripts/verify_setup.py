"""Read-only report for the actual Mac and CapCut build."""
import json
from capcut_mcp.paths import probe

if __name__ == '__main__':
    result = probe()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    ok = (result['supported_platform'] and result['process_check_ok']
          and bool(result['capcut_version']) and result['plaintext_drafts'] is True
          and bool(result['ffmpeg']) and bool(result['ffprobe']))
    raise SystemExit(0 if ok else 1)
