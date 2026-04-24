#!/usr/bin/env bash
# Claudia OS — Claude Code status line

input=$(cat)

# --- ANSI colors ---
RESET="\033[0m"
DIM="\033[2m"
BOLD="\033[1m"
CYAN="\033[36m"
YELLOW="\033[33m"
GREEN="\033[32m"
MAGENTA="\033[35m"
WHITE="\033[97m"

# --- Context window ---
used_pct=$(echo "$input" | jq -r '.context_window.used_percentage // empty')

ctx_line=""
if [ -n "$used_pct" ]; then
  used_int=$(printf "%.0f" "$used_pct")

  bar_width=50
  filled=$(( used_int * bar_width / 100 ))
  [ "$filled" -gt "$bar_width" ] && filled=$bar_width
  empty=$(( bar_width - filled ))

  # Color de la barra según uso
  if [ "$used_int" -lt 50 ]; then
    BAR_COLOR="$GREEN"
  elif [ "$used_int" -lt 80 ]; then
    BAR_COLOR="$YELLOW"
  else
    BAR_COLOR="\033[31m"  # rojo
  fi

  bar=""
  i=0
  while [ $i -lt $filled ]; do
    bar="${bar}━"
    i=$(( i + 1 ))
  done
  empty_bar=""
  i=0
  while [ $i -lt $empty ]; do
    empty_bar="${empty_bar}╌"
    i=$(( i + 1 ))
  done

  ctx_line="${DIM}Contexto${RESET} ${BAR_COLOR}${bar}${RESET}${DIM}${empty_bar} ${RESET}${BAR_COLOR}${used_int}%${RESET}"
fi

# --- Rate limits with countdown timers ---
five_pct=$(echo "$input" | jq -r '.rate_limits.five_hour.used_percentage // empty')
five_resets=$(echo "$input" | jq -r '.rate_limits.five_hour.resets_at // empty')
week_pct=$(echo "$input" | jq -r '.rate_limits.seven_day.used_percentage // empty')
week_resets=$(echo "$input" | jq -r '.rate_limits.seven_day.resets_at // empty')

fmt_countdown() {
  local secs=$1
  if [ "$secs" -le 0 ]; then
    echo "now"
    return
  fi
  local h=$(( secs / 3600 ))
  local m=$(( (secs % 3600) / 60 ))
  if [ "$h" -gt 0 ]; then
    printf "%dh%02dm" "$h" "$m"
  else
    printf "%dm" "$m"
  fi
}

to_epoch() {
  local ts="$1"
  if echo "$ts" | grep -qE '^[0-9]+$'; then
    echo "$ts"
  else
    date -d "$ts" +%s 2>/dev/null || date -j -f "%Y-%m-%dT%H:%M:%S" "$ts" +%s 2>/dev/null || echo ""
  fi
}

# Color de uso según porcentaje
use_color() {
  local pct=$1
  if [ "$pct" -lt 50 ]; then
    printf "$GREEN"
  elif [ "$pct" -lt 80 ]; then
    printf "$YELLOW"
  else
    printf "\033[31m"
  fi
}

rate_str=""
if [ -n "$five_pct" ]; then
  five_fmt=$(printf "%.0f" "$five_pct")
  five_color=$(use_color "$five_fmt")
  if [ -n "$five_resets" ]; then
    now=$(date +%s)
    resets_epoch=$(to_epoch "$five_resets")
    if [ -n "$resets_epoch" ]; then
      remaining=$(( resets_epoch - now ))
      countdown=$(fmt_countdown "$remaining")
      rate_str="${DIM}5h${RESET} ${five_color}${five_fmt}%${RESET} ${DIM}\xe2\x86\xbb${countdown}${RESET}"
    else
      rate_str="${DIM}5h${RESET} ${five_color}${five_fmt}%${RESET}"
    fi
  else
    rate_str="${DIM}5h${RESET} ${five_color}${five_fmt}%${RESET}"
  fi
fi
if [ -n "$week_pct" ]; then
  week_fmt=$(printf "%.0f" "$week_pct")
  week_color=$(use_color "$week_fmt")
  if [ -n "$week_resets" ]; then
    now=$(date +%s)
    resets_epoch=$(to_epoch "$week_resets")
    if [ -n "$resets_epoch" ]; then
      remaining=$(( resets_epoch - now ))
      countdown=$(fmt_countdown "$remaining")
      week_part="${DIM}7d${RESET} ${week_color}${week_fmt}%${RESET} ${DIM}\xe2\x86\xbb${countdown}${RESET}"
    else
      week_part="${DIM}7d${RESET} ${week_color}${week_fmt}%${RESET}"
    fi
  else
    week_part="${DIM}7d${RESET} ${week_color}${week_fmt}%${RESET}"
  fi
  [ -n "$rate_str" ] && rate_str="${rate_str} ${DIM}\xe2\x94\x82${RESET} ${week_part}" || rate_str="$week_part"
fi

# --- Model ---
model=$(echo "$input" | jq -r '.model.display_name // "Claude"')

# --- Git branch ---
cwd=$(echo "$input" | jq -r '.workspace.current_dir // .cwd // ""')
git_branch=""
if [ -n "$cwd" ]; then
  git_branch=$(git -C "$cwd" --no-optional-locks symbolic-ref --short HEAD 2>/dev/null \
    || git -C "$cwd" --no-optional-locks rev-parse --short HEAD 2>/dev/null)
fi

# --- Assemble output ---

# Line 1: context bar
if [ -n "$ctx_line" ]; then
  printf "%b\n" "$ctx_line"
fi

# Line 2: uso + modelo + git
line2="${DIM}Uso${RESET}  "
if [ -n "$rate_str" ]; then
  line2="${line2}${rate_str}"
else
  line2="${line2}${DIM}${model}${RESET}"
fi

if [ -n "$rate_str" ]; then
  line2="${line2}  ${DIM}${model}${RESET}"
fi
if [ -n "$git_branch" ]; then
  line2="${line2}  ${CYAN}${git_branch}${RESET}"
fi

printf "%b\n" "$line2"
