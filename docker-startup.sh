#!/bin/sh

# For use with Dockerfile

check_ready() {
  # Force "ready"
  if [ -e ~/ready ]; then
    return 0
  fi

  # Expect both SSH key and config file
  if [ -r ~/.ssh/id_rsa -a -r ~/SmokeDetector/config ]; then
    if [ $(stat -c %a ~/.ssh/id_rsa) != 600 ]; then
      # SSH will surely complain about this
      return 1
    else
      return 0
    fi
  fi
  return 1
}

cd ~smokey/SmokeDetector

while ! check_ready; do
  sleep 1
done

exec python3 nocrash.py
