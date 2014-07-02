#!/usr/bin/env python
import os
import sys

try:
    import kallithea
    KALLITHEA_HOOK_VER = '_TMPL_'
    os.environ['KALLITHEA_HOOK_VER'] = KALLITHEA_HOOK_VER
    from kallithea.lib.hooks import handle_git_pre_receive as _handler
except ImportError:
    if os.environ.get('RC_DEBUG_GIT_HOOK'):
        import traceback
        print traceback.format_exc()
    kallithea = None


def main():
    if kallithea is None:
        # exit with success if we cannot import kallithea !!
        # this allows simply push to this repo even without
        # kallithea
        sys.exit(0)

    repo_path = os.path.abspath('.')
    push_data = sys.stdin.readlines()
    # os.environ is modified here by a subprocess call that
    # runs git and later git executes this hook.
    # Environ gets some additional info from kallithea system
    # like IP or username from basic-auth
    _handler(repo_path, push_data, os.environ)
    sys.exit(0)

if __name__ == '__main__':
    main()
