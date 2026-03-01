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

# Send PHP errors to stderr so Railway logs capture them
echo "[Railway] Enabling PHP error logging to stderr..."
PHP_INI="/etc/php82/conf.d/railway.ini"
if [ -d "/etc/php82/conf.d" ]; then
    cat > "$PHP_INI" <<'EOINI'
display_errors = On
error_reporting = E_ALL
log_errors = On
error_log = /dev/stderr
EOINI
    echo "[Railway] PHP error display enabled via $PHP_INI"
elif [ -d "/etc/php81/conf.d" ]; then
    cat > "/etc/php81/conf.d/railway.ini" <<'EOINI'
display_errors = On
error_reporting = E_ALL
log_errors = On
error_log = /dev/stderr
EOINI
    echo "[Railway] PHP error display enabled via /etc/php81/conf.d/railway.ini"
elif [ -d "/etc/php8/conf.d" ]; then
    cat > "/etc/php8/conf.d/railway.ini" <<'EOINI'
display_errors = On
error_reporting = E_ALL
log_errors = On
error_log = /dev/stderr
EOINI
    echo "[Railway] PHP error display enabled via /etc/php8/conf.d/railway.ini"
else
    echo "[Railway] WARNING: Could not find PHP conf.d directory for error logging."
fi

# Hand off to the original OpenEMR entrypoint
exec ./openemr.sh
