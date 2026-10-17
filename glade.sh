#!/bin/bash
# glade.sh — управление ботом The Glade
# Использование: ./glade.sh {start|stop|restart|status|logs}

BOT_DIR="/root/glade"
LOG_FILE="/var/log/glade.log"
PID_FILE="/var/run/glade.pid"
PYTHON="python3"

cd "$BOT_DIR" || exit 1

# Найти все PID бота (только наши — по cwd)
find_pids() {
    for pid in $(pgrep -f "bot\.py" 2>/dev/null); do
        cwd=$(readlink -f "/proc/$pid/cwd" 2>/dev/null)
        if [ "$cwd" = "$BOT_DIR" ]; then
            echo "$pid"
        fi
    done
}

is_running() {
    local pids
    pids=$(find_pids)
    [ -n "$pids" ]
}

# ============ START ============
do_start() {
    # Всегда сначала убиваем всех (защита от дублей)
    if is_running; then
        echo "⚠️  Найдены старые процессы: $(find_pids | tr '\n' ' ')"
        echo "🛑 Останавливаем..."
        do_stop >/dev/null 2>&1 || true
        sleep 2
        if is_running; then
            echo "❌ Не удалось убить старые процессы. Прерываю старт."
            echo "   PIDs: $(find_pids | tr '\n' ' ')"
            exit 1
        fi
    fi

    echo "🚀 Запуск бота..."
    nohup "$PYTHON" -u bot.py > "$LOG_FILE" 2>&1 &
    echo $! > "$PID_FILE"

    # Ждём до 10 секунд
    for i in {1..10}; do
        sleep 1
        if is_running; then
            break
        fi
    done

    if ! is_running; then
        echo "❌ Бот не запустился. Логи:"
        tail -20 "$LOG_FILE"
        rm -f "$PID_FILE"
        exit 1
    fi

    # Проверка на конфликт
    sleep 3
    if grep -q "Conflict" "$LOG_FILE" 2>/dev/null; then
        echo "❌ КОНФЛИКТ ТОКЕНА!"
        echo "   Другой бот с тем же токеном работает где-то ещё."
        echo "   Проверь: ps aux | grep bot.py"
        echo "   Убей вручную: pkill -9 -f 'bot.py'"
        echo ""
        echo "Последние логи:"
        tail -20 "$LOG_FILE"
        do_stop >/dev/null 2>&1
        exit 1
    fi

    if ! grep -q "Run polling for bot" "$LOG_FILE" 2>/dev/null; then
        echo "⚠️  Процесс жив, но polling не запустился. Логи:"
        tail -20 "$LOG_FILE"
        do_stop >/dev/null 2>&1 || true
        exit 1
    fi

    echo "✅ Бот запущен (PID: $(find_pids | tr '\n' ' '))"
    echo "   Логи: $0 logs"
}

# ============ STOP ============
do_stop() {
    if ! is_running; then
        echo "ℹ️  Бот не запущен"
        rm -f "$PID_FILE"
        return 0
    fi

    local pids
    pids=$(find_pids)
    echo "🛑 Остановка (PID: $(echo "$pids" | tr '\n' ' '))..."

    # Шлём TERM именно найденным PID (а не по -f $BOT_DIR/bot.py)
    for pid in $pids; do
        kill -TERM "$pid" 2>/dev/null || true
    done

    # Ждём до 15 секунд
    for i in {1..15}; do
        sleep 1
        if ! is_running; then
            echo "✅ Остановлен за ${i}s"
            rm -f "$PID_FILE"
            return 0
        fi
    done

    # Не остановился — kill -9 по найденным PID
    echo "⚠️  Не остановился за 15s, убиваем жёстко..."
    pids=$(find_pids)
    for pid in $pids; do
        kill -9 "$pid" 2>/dev/null || true
    done
    sleep 2

    if is_running; then
        echo "❌ Не удалось убить: $(find_pids | tr '\n' ' ')"
        exit 1
    fi

    rm -f "$PID_FILE"
    echo "✅ Убит жёстко"
}

# ============ STATUS ============
do_status() {
    local pids
    pids=$(find_pids)

    if [ -n "$pids" ]; then
        echo "✅ Бот работает"
        for pid in $pids; do
            local uptime mem
            uptime=$(ps -o etime= -p "$pid" 2>/dev/null | tr -d ' ')
            mem=$(ps -o rss= -p "$pid" 2>/dev/null | awk '{printf "%.1f MB", $1/1024}')
            echo "   PID $pid — uptime: $uptime, память: $mem"
        done
        echo "   Логи: $0 logs"

        # Последние ошибки
        if grep -q "Conflict" "$LOG_FILE" 2>/dev/null; then
            echo ""
            echo "⚠️  В логах есть CONFLICT!"
        fi
    else
        echo "❌ Бот не запущен"
    fi
}

# ============ LOGS ============
do_logs() {
    if [ ! -f "$LOG_FILE" ]; then
        echo "Лог не найден: $LOG_FILE"
        exit 1
    fi
    tail -f "$LOG_FILE"
}

# ============ ROUTER ============
case "$1" in
    start)   do_start ;;
    stop)    do_stop ;;
    restart) do_stop; sleep 1; do_start ;;
    status)  do_status ;;
    logs)    do_logs ;;
    *)
        echo "The Glade Bot Manager"
        echo ""
        echo "Использование: $0 {start|stop|restart|status|logs}"
        echo ""
        echo "  start   — запустить бота"
        echo "  stop    — остановить"
        echo "  restart — перезапустить"
        echo "  status  — статус"
        echo "  logs    — логи (Ctrl+C — выйти)"
        exit 1
        ;;
esac
