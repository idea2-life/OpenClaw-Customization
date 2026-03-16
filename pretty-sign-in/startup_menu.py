#!/usr/bin/env python3
# Pretty Sign-in — VPS startup menu for OpenClaw environments
# Renders an inline menu at cursor position (Claude Code style).
# On login, presents options to launch claude, openclaw tui, or type a
# custom command. Add to ~/.bashrc with a TTY guard — see CHANGE LOG.
#
# VERSION: v0.0.4
# ------------------------------------------------------------------------
import sys
import os
import tty
import termios
import subprocess

MENU_ITEMS = [
    ("Run claude",        "claude"),
    ("Run openclaw tui",  "openclaw tui"),
    ("Run ...",            None),       # inline-editable custom command
]

# ANSI codes
DIM     = "\033[2m"
BOLD    = "\033[1m"
RESET   = "\033[0m"
CYAN    = "\033[36m"
HIDE_CURSOR = "\033[?25l"
SHOW_CURSOR = "\033[?25h"
CLEAR_LINE  = "\033[2K"
UP          = "\033[A"
BLOCK_CURSOR = "█"

CUSTOM_IDX = 2  # index of the inline-editable item


def read_key():
    """Read a single keypress (handles arrow key escape sequences)."""
    fd = sys.stdin.fileno()
    old = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        ch = os.read(fd, 1)
        if ch == b'\x1b':
            seq = os.read(fd, 2)
            if seq == b'[A': return 'up'
            if seq == b'[B': return 'down'
            return 'esc'
        if ch in (b'\r', b'\n'): return 'enter'
        if ch == b'\x7f' or ch == b'\x08': return 'backspace'
        if ch == b'\x03': return 'esc'  # Ctrl-C
        return ch.decode(errors='replace')
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old)


def render(idx, typing_buf=None):
    """Draw the menu inline. When typing_buf is not None, the custom item
    shows an editable input field instead of '...'."""
    lines = []
    lines.append(f"  {DIM}What would you like to do?{RESET}")
    lines.append("")
    for i, (label, _) in enumerate(MENU_ITEMS):
        if i == CUSTOM_IDX and typing_buf is not None:
            # Inline text input: "Run " prefix stays, user types the rest
            lines.append(f"  {CYAN}{BOLD}❯ Run {typing_buf}{RESET}{BLOCK_CURSOR}")
        elif i == idx:
            lines.append(f"  {CYAN}{BOLD}❯ {label}{RESET}")
        else:
            lines.append(f"    {DIM}{label}{RESET}")
    lines.append("")
    if typing_buf is not None:
        lines.append(f"  {DIM}type command · enter run · esc back{RESET}")
    else:
        lines.append(f"  {DIM}↑/↓ navigate · enter select · q quit{RESET}")
    return lines


def redraw(frame, total_lines):
    """Overwrite the previous frame in-place."""
    sys.stdout.write(UP * total_lines)
    for line in frame:
        sys.stdout.write(f"\r{CLEAR_LINE}{line}\n")
    sys.stdout.flush()


def main():
    current = 0
    typing_buf = None  # None = navigation mode, str = typing mode
    total_lines = len(render(0))

    sys.stdout.write(HIDE_CURSOR)
    sys.stdout.flush()

    # First draw
    frame = render(current)
    sys.stdout.write("\n".join(frame) + "\n")
    sys.stdout.flush()

    try:
        while True:
            key = read_key()

            # --- Typing mode (custom command input) ---
            if typing_buf is not None:
                if key == 'enter':
                    if typing_buf.strip():
                        current = CUSTOM_IDX
                        break
                    # empty input — ignore enter
                    continue
                elif key == 'esc':
                    typing_buf = None
                    sys.stdout.write(HIDE_CURSOR)
                    sys.stdout.flush()
                elif key == 'backspace':
                    typing_buf = typing_buf[:-1]
                elif key in ('up', 'down'):
                    # If buffer is empty, allow navigating away
                    if not typing_buf:
                        typing_buf = None
                        sys.stdout.write(HIDE_CURSOR)
                        sys.stdout.flush()
                        if key == 'up':
                            current = (current - 1) % len(MENU_ITEMS)
                        else:
                            current = (current + 1) % len(MENU_ITEMS)
                    else:
                        continue
                elif len(key) == 1 and key.isprintable():
                    typing_buf += key
                else:
                    continue
                redraw(render(current, typing_buf), total_lines)
                continue

            # --- Navigation mode ---
            if key == 'up':
                current = (current - 1) % len(MENU_ITEMS)
            elif key == 'down':
                current = (current + 1) % len(MENU_ITEMS)
            elif key == 'enter':
                if current == CUSTOM_IDX:
                    # Enter typing mode
                    typing_buf = ""
                    sys.stdout.write(SHOW_CURSOR)
                    sys.stdout.flush()
                else:
                    break
            elif key in ('q', 'esc'):
                current = None
                break
            elif current == CUSTOM_IDX and len(key) == 1 and key.isprintable():
                # Start typing immediately when on the custom item
                typing_buf = key
                sys.stdout.write(SHOW_CURSOR)
                sys.stdout.flush()
            else:
                continue

            redraw(render(current, typing_buf), total_lines)
    finally:
        sys.stdout.write(SHOW_CURSOR)
        sys.stdout.flush()

    # Clear the menu
    sys.stdout.write(UP * total_lines)
    for _ in range(total_lines):
        sys.stdout.write(f"\r{CLEAR_LINE}\n")
    sys.stdout.write(UP * total_lines)
    sys.stdout.flush()

    if current is None:
        return

    if current == CUSTOM_IDX and typing_buf:
        cmd = typing_buf.strip()
        print(f"  {DIM}→ {cmd}{RESET}\n")
        subprocess.run(cmd, shell=True)
    else:
        label, cmd = MENU_ITEMS[current]
        if cmd:
            print(f"  {DIM}→ {label}{RESET}\n")
            subprocess.run(cmd, shell=True)


# ------------------------------------------------------------------------
# CHANGE LOG
# v0.0.1_1: initial curses-based startup menu with 3 options
# v0.0.2:   inline ANSI menu (no fullscreen), Claude Code style
# v0.0.3:   third option shows "..." → inline editable input on select
# v0.0.4:   "Run ..." label; "Run " prefix stays visible while typing;
#           header comments describe purpose + VPS context
# bashrc snippet:
#   if [ -t 0 ] && [ -z "$STARTUP_MENU_SHOWN" ]; then
#       export STARTUP_MENU_SHOWN=1
#       python3 "$HOME/resources/OpenClaw/startup_menu.py"
#   fi
# ------------------------------------------------------------------------

if __name__ == "__main__":
    main()
