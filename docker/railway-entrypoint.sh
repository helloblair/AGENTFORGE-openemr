#!/bin/sh
# Railway entrypoint — pre-populates sqlconf.php so the OpenEMR image
# skips auto_configure.php (which fails when tables already exist).
#
# Required env vars: MYSQL_HOST, MYSQL_USER, MYSQL_PASS, MYSQL_DATABASE
# Optional: MYSQL_PORT (default 3306)

set -e

SQLCONF="/var/www/localhost/htdocs/openemr/sites/default/sqlconf.php"
MYSQL_PORT="${MYSQL_PORT:-3306}"

# Only write if the DB is already set up (env vars present)
if [ -n "$MYSQL_HOST" ] && [ -n "$MYSQL_USER" ] && [ -n "$MYSQL_PASS" ]; then
    cat > "$SQLCONF" <<EOPHP
<?php
//  OpenEMR
//  MySQL Config
//  Written by Railway entrypoint — existing database, skip auto_configure.

\$host	= '${MYSQL_HOST}';
\$port	= '${MYSQL_PORT}';
\$login	= '${MYSQL_USER}';
\$pass	= '${MYSQL_PASS}';
\$dbase	= '${MYSQL_DATABASE:-openemr}';

\$sqlconf = array();
global \$sqlconf;
\$sqlconf["host"]= \$host;
\$sqlconf["port"] = \$port;
\$sqlconf["login"] = \$login;
\$sqlconf["pass"] = \$pass;
\$sqlconf["dbase"] = \$dbase;

//////////////////////////
//////////////////////////
//////////////////////////
//////DO NOT TOUCH THIS///
\$config = 1; /////////////
//////////////////////////
//////////////////////////
//////////////////////////
?>
EOPHP
    echo "[Railway] sqlconf.php written — skipping auto_configure."
else
    echo "[Railway] WARNING: MYSQL_HOST/USER/PASS not all set — sqlconf.php NOT written."
    echo "[Railway]   MYSQL_HOST=${MYSQL_HOST:-<unset>}"
    echo "[Railway]   MYSQL_USER=${MYSQL_USER:-<unset>}"
    echo "[Railway]   MYSQL_PASS=${MYSQL_PASS:+<set>}${MYSQL_PASS:-<unset>}"
fi

# Log PHP errors to stderr (Railway logs) but hide from browser
for phpdir in /etc/php82/conf.d /etc/php81/conf.d /etc/php8/conf.d; do
    if [ -d "$phpdir" ]; then
        cat > "$phpdir/railway.ini" <<'EOINI'
display_errors = Off
error_reporting = E_ALL
log_errors = On
error_log = /dev/stderr
EOINI
        echo "[Railway] PHP error logging configured via $phpdir/railway.ini"
        break
    fi
done

# Drop a lightweight diagnostic page so we can test PHP independently
cat > /var/www/localhost/htdocs/openemr/railway-health.php <<'EOPHP'
<?php
header('Content-Type: text/plain');
echo "OK\n";
echo "PHP " . phpversion() . "\n";

// Test DB if env vars present
$host = getenv('MYSQL_HOST') ?: '(unset)';
$port = getenv('MYSQL_PORT') ?: '3306';
$user = getenv('MYSQL_USER') ?: '(unset)';
$pass = getenv('MYSQL_PASS') ?: '';
$db   = getenv('MYSQL_DATABASE') ?: 'openemr';

echo "DB host: $host:$port\n";

if ($host !== '(unset)' && $user !== '(unset)') {
    try {
        $pdo = new PDO("mysql:host=$host;port=$port;dbname=$db", $user, $pass, [
            PDO::ATTR_TIMEOUT => 5,
        ]);
        $ver = $pdo->query("SELECT VERSION()")->fetchColumn();
        echo "DB connected: $ver\n";
    } catch (Exception $e) {
        echo "DB error: " . $e->getMessage() . "\n";
    }
} else {
    echo "DB: env vars not set, skipping connection test\n";
}
EOPHP
echo "[Railway] Diagnostic page written to /railway-health.php"

# Test DB connectivity from the shell before starting Apache
if [ -n "$MYSQL_HOST" ] && [ -n "$MYSQL_USER" ]; then
    echo "[Railway] Testing DB connectivity to ${MYSQL_HOST}:${MYSQL_PORT}..."
    if php -r "
        try {
            \$p = new PDO('mysql:host=${MYSQL_HOST};port=${MYSQL_PORT};dbname=${MYSQL_DATABASE:-openemr}','${MYSQL_USER}','${MYSQL_PASS}',[PDO::ATTR_TIMEOUT=>5]);
            echo 'DB OK: '.\$p->query('SELECT VERSION()')->fetchColumn().PHP_EOL;
        } catch(Exception \$e) {
            echo 'DB FAIL: '.\$e->getMessage().PHP_EOL;
        }
    "; then
        echo "[Railway] DB test complete."
    fi
fi

# Run diagnostic in background — waits for Apache, then tests
(
    echo "[Railway] Waiting for Apache to be ready..."
    # Poll until port 80 or 443 is listening (max 60 seconds)
    for i in $(seq 1 60); do
        if wget -q --spider http://localhost:80/ 2>/dev/null || \
           wget -q --spider --no-check-certificate https://localhost:443/ 2>/dev/null; then
            echo "[Railway] Apache responded after ${i}s"
            break
        fi
        sleep 1
    done

    echo "[Railway] === INTERNAL DIAGNOSTIC ==="

    echo "[Railway] Listening ports:"
    netstat -tlnp 2>/dev/null || ss -tlnp 2>/dev/null || true

    echo "[Railway] Testing localhost:80/railway-health.php ..."
    wget -q -O - --server-response http://localhost:80/railway-health.php 2>&1 | head -40 || true

    echo "[Railway] Testing localhost:443/railway-health.php ..."
    wget -q -O - --no-check-certificate --server-response https://localhost:443/railway-health.php 2>&1 | head -40 || true

    echo "[Railway] Testing localhost:80/interface/login/login.php ..."
    wget -q -O /dev/null --server-response "http://localhost:80/interface/login/login.php?site=default" 2>&1 | head -20 || true

    echo "[Railway] Apache error log:"
    for logfile in /var/log/apache2/error.log /var/log/httpd/error_log /var/log/apache2/error_log; do
        if [ -f "$logfile" ]; then
            echo "[Railway] Found: $logfile"
            tail -30 "$logfile"
            break
        fi
    done
    # Also check stderr log
    echo "[Railway] PHP errors (stderr):"
    tail -20 /tmp/php-error.log 2>/dev/null || echo "(none)"

    echo "[Railway] === END DIAGNOSTIC ==="
) &

# Hand off to the original OpenEMR entrypoint (PID 1)
exec ./openemr.sh
