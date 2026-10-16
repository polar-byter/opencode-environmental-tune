#!/bin/sh
# Mouse entry point: show first-launch preparation, then start the Python GUI.
set -eu
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
temporary=$(mktemp -d)
worker=
cleanup() {
    if [ -n "$worker" ] && kill -0 "$worker" 2>/dev/null; then
        kill -TERM "-$worker" 2>/dev/null || true
        wait "$worker" 2>/dev/null || true
    fi
    rm -rf -- "$temporary"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM
language=${LC_ALL:-${LC_MESSAGES:-${LANG:-en}}}
case "$language" in
    ru*) title='OpenCode Kit — подготовка'; message='Подготовка закреплённого Python. Первый запуск занимает несколько минут. Дождитесь окна установки.'; failure='Не удалось подготовить Python. Проверьте интернет и свободное место. Подробности:' ;;
    *) title='OpenCode Kit — setup'; message='Preparing pinned Python. The first launch takes several minutes. Please wait for the setup wizard.'; failure='Python setup failed. Check your internet connection and free disk space. Details:' ;;
esac
setsid sh "$script_dir/bootstrap.sh" --kit-runtime-path >"$temporary/path" 2>"$temporary/log" &
worker=$!
if command -v zenity >/dev/null 2>&1 && [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
    if ! (
        while kill -0 "$worker" 2>/dev/null; do printf '# %s\n' "$message"; sleep 1; done
        printf '100\n'
    ) | zenity --progress --pulsate --auto-close --title="$title" --text="$message" --width=560 2>/dev/null; then
        # Closing first-launch progress cancels its whole build process group.
        exit 130
    fi
fi
if ! wait "$worker"; then
    worker=
    cat "$temporary/log" >&2
    if command -v zenity >/dev/null 2>&1 && [ -n "${DISPLAY:-}${WAYLAND_DISPLAY:-}" ]; then
        { printf '%s\n\n' "$failure"; tail -n 45 "$temporary/log"; } | zenity --text-info --title="$title" --width=700 --height=450 2>/dev/null || true
    fi
    exit 1
fi
worker=
# bootstrap also supplies the exact runtime to every inherited subprocess.
rm -rf -- "$temporary"
trap - EXIT
exec sh "$script_dir/bootstrap.sh" "$@"
