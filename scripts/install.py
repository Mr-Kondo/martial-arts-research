#!/usr/bin/env python3
"""Install or update the checked-out release, without changing app settings."""
import json
from pathlib import Path
import sys
from skill_installation import destinations, install, parser


def main(argv=None):
    args = parser('スキルをコピー配置・更新する').parse_args(argv)
    try:
        results = install(Path(__file__).resolve().parents[1], destinations(args.target, args.project, args.user))
    except (OSError, ValueError, RecursionError) as error:
        print(json.dumps({'status': 'error', 'message': str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps({'status': 'ok', 'results': results}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
