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

while ! check_ready; do
  sleep 1
done

exec python3 nocrash.py "$@"
