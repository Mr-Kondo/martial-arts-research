#!/usr/bin/env python3
"""Remove only unchanged copies tracked by the installation manifest."""
import json
import sys
from skill_installation import destinations, parser, uninstall


def main(argv=None):
    args = parser('変更のない管理済みスキルだけを削除する').parse_args(argv)
    try:
        results = uninstall(destinations(args.target, args.project, args.user))
    except (OSError, ValueError, RecursionError) as error:
        print(json.dumps({'status': 'error', 'message': str(error)}, ensure_ascii=False))
        return 1
    print(json.dumps({'status': 'ok', 'results': results}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    sys.exit(main())
