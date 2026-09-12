#!/bin/bash
cd "$(dirname "$0")" || exit 1
/bin/bash scripts/install.sh
result=$?
if [[ $result -ne 0 ]]; then
    printf '\nSetup stopped. Read the message above, then double-click this file to resume.\n'
fi
if [[ -t 0 ]]; then read -r -p 'Press Return to close this installer. ' _; fi
exit "$result"
