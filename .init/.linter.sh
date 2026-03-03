#!/bin/bash
cd /home/kavia/workspace/code-generation/secure-notes-hub-236390-236416/notes_app_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

