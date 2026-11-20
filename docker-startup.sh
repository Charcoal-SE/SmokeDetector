#!/bin/sh

# For use with Dockerfile

check_ready() {
  # Expect the config file
  if [ -r ~/SmokeDetector/config ]; then
    return 0
  fi

  return 1
}

cd ~smokey/SmokeDetector

# Fetch GitHub host key if using SSH
if [ -r "$HOME/.ssh/id_rsa" ] || ! git config --get core.sshCommand; then
  if ! ssh-keygen -F github.com >/dev/null 2>&1; then
    ssh-keyscan 2>/dev/null github.com >> ~/.ssh/known_hosts
  fi
fi

while ! check_ready; do
  sleep 1
done

exec uv run python3 nocrash.py "$@"
