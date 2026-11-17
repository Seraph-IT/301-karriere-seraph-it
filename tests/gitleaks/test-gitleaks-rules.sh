#!/usr/bin/env bash
# Checks this repository's gitleaks setup with synthetic values.
#
# What the test pins down:
#   1. Real secret patterns still fire: GitHub PAT, AWS access key, private key block,
#      generic-api-key behind "token:" (40 and 22 characters) and behind "password:".
#   2. A Keeper record UID (exactly 22 characters [A-Za-z0-9_-]) directly behind a key
#      ending in _uid in any case (_UID, _uid, _Uid) does not fire, in YAML, shell, Python
#      and JSON. A real token pattern behind such a key (40 characters, ghp_ prefix) still fires.
#   3. Counter-check: without the "keeper-uid-allowlist" block the same UIDs fire.
#   4. The history scan only covers HEAD and its ancestors: a finding on another branch
#      stays silent with --log-opts=HEAD, fires once it is on HEAD, and the old default
#      (no --log-opts, i.e. all refs) would have reported it.
#   5. Every gitleaks history scan in the workflows passes --log-opts=HEAD and none --all.
#
# All values are synthetic and assembled at runtime, so this file itself does not trip
# the repository scan.
#
# Usage: tests/gitleaks/test-gitleaks-rules.sh [path/to/.gitleaks.toml]
# The gitleaks binary comes from $GITLEAKS or from PATH.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CONFIG="${1:-$ROOT/.gitleaks.toml}"
GL="${GITLEAKS:-gitleaks}"
TMP="$(mktemp -d)"
trap 'rm -rf -- "$TMP"' EXIT

ok=0
fail=0
pass() { ok=$((ok + 1)); echo "ok   $*"; }
bad() { fail=$((fail + 1)); echo "FAIL $*"; }

[ -f "$CONFIG" ] || { echo "FAIL config missing: $CONFIG"; exit 1; }
"$GL" version >/dev/null

# Directory scan without git; 8.18 only knows "detect --no-git".
scan_dir() { # dir config report
  if "$GL" dir --help >/dev/null 2>&1; then
    "$GL" dir "$1" --config "$2" --no-banner --redact --exit-code 0 \
      --report-format json --report-path "$3" >/dev/null 2>&1
  else
    "$GL" detect --no-git --source "$1" --config "$2" --no-banner --redact --exit-code 0 \
      --report-format json --report-path "$3" >/dev/null 2>&1
  fi
}

# fired <report> <file> -> 0 if the report has at least one finding for that file
fired() { grep -Eq "\"File\": \"([^\"]*/)?$2\"" "$1"; }

# Synthetic building blocks (assembled, never a literal pattern in the repository)
A36="aB3dE5fG7hJ9kL1mN2pQ4rS6tU8vW0xY2zC4"
UID22="Qm7xKp2Lw9_RtZ4vN8cY-a"
UID23="${UID22}b"
TOK40="Xk9fQ2mZ7pL4wR8tV3nB6yH1sD5gJ0cA9eU2iO7"
TOK22="Hq4Zx8Lm2Pw7Rt3Vn9Ks6Y"
AWS="AKI""A""QX7M2RZ4KD5WN3TB"
GHP="gh""p_${A36}"
PEMHDR="-----BEGIN RSA PRIV""ATE KEY-----"
PEMEND="-----END RSA PRIV""ATE KEY-----"
PEMB64="MIIEowIBAAKCAQEAu1SU1LfVLPHCozMxH2Mo4lgOEePzNm0tRgeLezV6ffAt0gunVTLw7onLRnrq0/IzW7yWR7QkrmBL7jTKEn5u+qKhbwKfBstIs+bMY2Zkp18gnTxKLxoS2tFczGkPLPgizskuemMghRniWaoLcyehkd3qqGElvW/VDL5AaWTg0nLVkjRo9z+40RQzuVaE8AkAFmxZzow3x+VJYKdjykkJ0iT9wCS0DRTXu269V264Vf/3jvredZiKRkgwlL9xNAwxXFg0x/XFw005UWVRIkdgcKWTjpBP2dPwVZ4WWC+9aGVd+Gyn1o0CLelf4rEjGoXbAAEgAqeGUxrcIlbjXfbcmw"

mk() { mkdir -p "$(dirname "$1")"; printf '%s\n' "$2" > "$1"; }

F="$TMP/cases"
# must fire
mk "$F/ghp.yml"          "github_token: ${GHP}"
mk "$F/aws.sh"           "AWS_ACCESS_KEY_ID=${AWS}"
mk "$F/key.pem"          "$(printf '%s\n%s\n%s' "$PEMHDR" "$PEMB64" "$PEMEND")"
mk "$F/token40.yml"      "token: ${TOK40}"
mk "$F/token22.yml"      "token: ${TOK22}"
mk "$F/password22.yml"   "password: ${TOK22}"
mk "$F/uid23.yml"        "svc_token_uid: ${UID23}"
mk "$F/uid_ghp.yml"      "psk_keeper_uid: ${GHP}"
mk "$F/uid_tok40.yml"    "svc_token_uid: ${TOK40}"
# must stay silent
mk "$F/foo_uid.yml"      "FOO_UID: ${UID22}"
mk "$F/uid_yaml.yml"     "svc_token_uid: ${UID22}"
mk "$F/uid_yamlq.yml"    "GITEA_TOKEN_UID: \"${UID22}\""
mk "$F/uid_shell.sh"     "export API_KEY_UID='${UID22}'"
mk "$F/uid_python.py"    "SECRET_UID = \"${UID22}\""
mk "$F/uid_json.json"    "{\"ksm_token_uid\": \"${UID22}\"}"
mk "$F/uid_psk.yml"      "    psk_keeper_uid: \"${UID22}\"   # IT/Kunden/x/zabbix/agent-psk-x"
mk "$F/uid_mixed.yml"    "Svc_Token_Uid: ${UID22}"

R="$TMP/with.json"
scan_dir "$F" "$CONFIG" "$R"
for f in ghp.yml aws.sh key.pem token40.yml token22.yml password22.yml uid23.yml uid_ghp.yml uid_tok40.yml; do
  if fired "$R" "$f"; then pass "fires: $f"; else bad "silent but must fire: $f"; fi
done
# GITLEAKS_UID_RULE=absent is only for a repository whose config cannot take the UID block
# yet; the workflow says so explicitly and the UID cases are then skipped, not passed.
if [ "${GITLEAKS_UID_RULE:-}" = absent ]; then
  if grep -q '^# BEGIN keeper-uid-allowlist' "$CONFIG"; then
    bad "GITLEAKS_UID_RULE=absent but the block is present: drop the variable"
  else
    echo "skip UID cases: GITLEAKS_UID_RULE=absent (no keeper-uid-allowlist block yet)"
  fi
else
  for f in foo_uid.yml uid_yaml.yml uid_yamlq.yml uid_shell.sh uid_python.py uid_json.json uid_psk.yml uid_mixed.yml; do
    if fired "$R" "$f"; then bad "fires but must stay silent: $f"; else pass "silent: $f"; fi
  done
fi

# Counter-check: the same config without the UID block
if [ "${GITLEAKS_UID_RULE:-}" = absent ]; then
  :
elif ! grep -q '^# BEGIN keeper-uid-allowlist' "$CONFIG"; then
  bad "block keeper-uid-allowlist missing in $CONFIG"
else
  sed '/^# BEGIN keeper-uid-allowlist/,/^# END keeper-uid-allowlist/d' "$CONFIG" > "$TMP/without.toml"
  R2="$TMP/without.json"
  scan_dir "$F" "$TMP/without.toml" "$R2"
  for f in uid_yaml.yml uid_yamlq.yml uid_shell.sh uid_python.py uid_json.json uid_mixed.yml; do
    if fired "$R2" "$f"; then pass "counter-check fires without block: $f"; else bad "counter-check silent without block: $f"; fi
  done
fi

# History of HEAD: a finding on another branch stays silent, on HEAD it fires
G="$TMP/git"
git init -q "$G"
git -C "$G" symbolic-ref HEAD refs/heads/main
git -C "$G" -c user.name=t -c user.email=t@example.invalid commit -q --allow-empty -m start
git -C "$G" checkout -q -b other
mk "$G/other.yml" "token: ${TOK40}"
git -C "$G" add other.yml
git -C "$G" -c user.name=t -c user.email=t@example.invalid commit -q -m other
git -C "$G" checkout -q main
if "$GL" git --help >/dev/null 2>&1; then SUB=(git "$G"); else SUB=(detect --source "$G"); fi
scan_git() { # report [extra args]
  local rep="$1"; shift
  "$GL" "${SUB[@]}" --config "$CONFIG" --no-banner --redact --exit-code 0 \
    --report-format json --report-path "$rep" "$@" >/dev/null 2>&1
}
scan_git "$TMP/h0.json"
if fired "$TMP/h0.json" other.yml; then pass "default scan (all refs) sees the other branch"; else bad "default scan does not see the other branch"; fi
scan_git "$TMP/h1.json" --log-opts=HEAD
if fired "$TMP/h1.json" other.yml; then bad "HEAD scan sees the other branch"; else pass "HEAD scan: other branch silent"; fi
git -C "$G" -c user.name=t -c user.email=t@example.invalid merge -q --no-edit other
scan_git "$TMP/h2.json" --log-opts=HEAD
if fired "$TMP/h2.json" other.yml; then pass "HEAD scan: finding on HEAD fires"; else bad "HEAD scan misses finding on HEAD"; fi

# Every gitleaks history scan in the workflows uses --log-opts=HEAD and never --all
WF=0
for w in "$ROOT"/.github/workflows/*.y*ml "$ROOT"/.gitea/workflows/*.y*ml; do
  [ -f "$w" ] || continue
  while IFS= read -r line; do
    WF=$((WF + 1))
    case "$line" in
      *--all*) bad "--all in $(basename "$w"): $line" ;;
      *--log-opts=HEAD*) pass "HEAD only: $(basename "$w")" ;;
      *) bad "no --log-opts=HEAD in $(basename "$w"): $line" ;;
    esac
  done < <(sed -e ':a' -e '/\\$/N; s/\\\n[[:space:]]*/ /; ta' "$w" \
           | grep -E '(^|[/" ])gitleaks"? +(git|detect)( |$)' | grep -v -e '--help' -e '--no-git' || true)
done
[ "$WF" -gt 0 ] || bad "no gitleaks history scan found in the workflows"

echo "gitleaks rule test: $ok ok, $fail failed"
[ "$fail" -eq 0 ]
