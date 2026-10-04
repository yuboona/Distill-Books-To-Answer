#!/bin/bash
# Resilient full Tongjian download via local proxy. Safe to re-run.
set -u
PROXY="${PROXY:-http://127.0.0.1:7890}"
ROOT="/Users/zhangzhe/ai-career-90d/05-shi-shi-qiu-shi"
OUT="$ROOT/corpus/raw/zizhi_tongjian/volumes"
LOG="$ROOT/.download_tmp/fetch_tongjian_loop.log"
mkdir -p "$OUT" "$(dirname "$LOG")"

export http_proxy="$PROXY" https_proxy="$PROXY" HTTP_PROXY="$PROXY" HTTPS_PROXY="$PROXY"
export NO_PROXY="localhost,127.0.0.1"

echo "$(date) start proxy=$PROXY" | tee -a "$LOG"

for i in $(seq -w 0 294); do
  # seq -w may give 000..294
  n=$((10#$i))
  f=$(printf "%s/卷%03d.txt" "$OUT" "$n")
  if [[ -f "$f" && $(wc -c < "$f") -gt 500 ]]; then
    echo "skip $f" >> "$LOG"
    continue
  fi
  url=$(printf "https://raw.githubusercontent.com/kanripo/KR2b0007/master/KR2b0007_%03d.txt" "$n")
  ok=0
  for attempt in 1 2 3 4 5; do
    echo "$(date +%H:%M:%S) get $n attempt $attempt" | tee -a "$LOG"
    if curl -fsSL --max-time 120 -A "shi-shi-qiu-shi/0.2" -o "$f.part" "$url"; then
      sz=$(wc -c < "$f.part" | tr -d ' ')
      if [[ "$sz" -gt 1000 ]]; then
        mv "$f.part" "$f"
        echo "OK $f ($sz)" | tee -a "$LOG"
        ok=1
        break
      fi
    fi
    sleep $((attempt * 2))
  done
  if [[ "$ok" -ne 1 ]]; then
    echo "FAIL volume $n" | tee -a "$LOG"
  fi
done

# Build master concat
MASTER="$ROOT/corpus/raw/zizhi_tongjian/资治通鉴_全文.txt"
: > "$MASTER"
present=0
for n in $(seq 0 294); do
  f=$(printf "%s/卷%03d.txt" "$OUT" "$n")
  if [[ -f "$f" ]]; then
    present=$((present + 1))
    printf '\n\n===== 卷%03d =====\n\n' "$n" >> "$MASTER"
    cat "$f" >> "$MASTER"
  fi
done
echo "$(date) done present=$present/295 master=$(wc -c < "$MASTER")" | tee -a "$LOG"
