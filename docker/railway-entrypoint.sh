#!/bin/sh
# Railway entrypoint — detects whether the database has OpenEMR tables.
#   • If tables exist  → write sqlconf.php with $config=1 (skip setup)
#   • If tables missing → let openemr.sh run auto_configure (first boot)
#
# Required env vars: MYSQL_HOST, MYSQL_USER, MYSQL_PASS, MYSQL_DATABASE
# Optional: MYSQL_PORT (default 3306), OE_USER, OE_PASS

set -e

SQLCONF="/var/www/localhost/htdocs/openemr/sites/default/sqlconf.php"
MYSQL_PORT="${MYSQL_PORT:-3306}"

# ── PHP error logging ───────────────────────────────────────────────
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

# ── Database check ──────────────────────────────────────────────────
if [ -n "$MYSQL_HOST" ] && [ -n "$MYSQL_USER" ] && [ -n "$MYSQL_PASS" ]; then
    echo "[Railway] Checking database ${MYSQL_DATABASE:-openemr} at ${MYSQL_HOST}:${MYSQL_PORT}..."

    TABLE_COUNT=$(php -r "
        try {
            \$p = new PDO(
                'mysql:host=${MYSQL_HOST};port=${MYSQL_PORT};dbname=${MYSQL_DATABASE:-openemr}',
                '${MYSQL_USER}',
                '${MYSQL_PASS}',
                [PDO::ATTR_TIMEOUT => 10]
            );
            \$count = \$p->query(
                \"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '${MYSQL_DATABASE:-openemr}'\"
            )->fetchColumn();
            echo \$count;
        } catch (Exception \$e) {
            echo 'ERR:' . \$e->getMessage();
        }
    " 2>/dev/null)

    echo "[Railway] Table count result: ${TABLE_COUNT}"

    case "$TABLE_COUNT" in
        ERR:*)
            echo "[Railway] DB connection failed: ${TABLE_COUNT#ERR:}"
            echo "[Railway] Will let openemr.sh handle setup."
            ;;
        0|"")
            echo "[Railway] Database is EMPTY — first boot detected."
            echo "[Railway] Letting openemr.sh run auto_configure to create tables."
            echo "[Railway] This will take a minute on first boot."
            # Do NOT write sqlconf.php — let openemr.sh handle everything.
            # openemr.sh needs these env vars (already set by Railway):
            #   MYSQL_HOST, MYSQL_ROOT_PASS, MYSQL_USER, MYSQL_PASS, MYSQL_DATABASE
            #   OE_USER, OE_PASS
            # Set MYSQL_ROOT_PASS = MYSQL_PASS if not separately defined
            # (Railway MariaDB uses root as the default user)
            export MYSQL_ROOT_PASS="${MYSQL_ROOT_PASS:-${MYSQL_PASS}}"
            echo "[Railway] MYSQL_ROOT_PASS set for auto_configure."
            ;;
        *)
            echo "[Railway] Database has ${TABLE_COUNT} tables — writing sqlconf.php."
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
            echo "[Railway] sqlconf.php written with \$config=1 — skipping auto_configure."
            ;;
    esac
else
    echo "[Railway] WARNING: MYSQL_HOST/USER/PASS not all set."
    echo "[Railway]   MYSQL_HOST=${MYSQL_HOST:-<unset>}"
    echo "[Railway]   MYSQL_USER=${MYSQL_USER:-<unset>}"
    echo "[Railway]   MYSQL_PASS=${MYSQL_PASS:+<set>}${MYSQL_PASS:-<unset>}"
fi

# ── PHP 8.2 compatibility patches ───────────────────────────────────
# The base openemr/openemr:7.0.2 image has code that accesses undefined
# globals, which PHP 8.2 treats as errors. These get caught by the
# try/catch in globals.php → http_response_code(500) → die().
# Patch the offending files at runtime so the login page renders.
WEBROOT="/var/www/localhost/htdocs/openemr"

# PatientFlowBoardEventsSubscriber: $GLOBALS['drug_screen'] → !empty(...)
PFBS="$WEBROOT/interface/modules/zend_modules/module/PatientFlowBoard/src/PatientFlowBoard/Listener/PatientFlowBoardEventsSubscriber.php"
if [ -f "$PFBS" ]; then
    sed -i "s/if (\$GLOBALS\['drug_screen'\])/if (!empty(\$GLOBALS['drug_screen']))/" "$PFBS"
    echo "[Railway] Patched PatientFlowBoardEventsSubscriber.php (drug_screen)"
fi

# globals.php: make module init non-fatal (don't die on \Throwable)
# The try/catch at ~line 764 calls http_response_code(500) + die() on ANY
# error during module loading. On PHP 8.2, errors during module init kill
# every page load. Log and continue instead.
cat > /tmp/patch-globals.php <<'PATCHEOF'
<?php
$file = '/var/www/localhost/htdocs/openemr/interface/globals.php';
$lines = file($file);
$patched = 0;
$in_throwable = false;

foreach ($lines as $i => &$line) {
    if (strpos($line, 'Throwable') !== false && strpos($line, 'catch') !== false) {
        $in_throwable = true;
        continue;
    }
    if ($in_throwable) {
        if (strpos($line, 'http_response_code(500)') !== false) {
            $line = str_replace(
                'http_response_code(500);',
                'error_log("[Railway] Module init error (non-fatal): " . $ex->getMessage() . " in " . $ex->getFile() . ":" . $ex->getLine());',
                $line
            );
            $patched++;
        }
        if (strpos($line, 'die()') !== false) {
            $line = str_replace('die();', '// die(); // [Railway] removed — continue loading', $line);
            $patched++;
            $in_throwable = false;
        }
    }
}

file_put_contents($file, implode('', $lines));
echo $patched >= 2
    ? "[Railway] Patched globals.php OK — module init errors are now non-fatal ($patched changes)\n"
    : "[Railway] WARNING: globals.php patch found only $patched/2 targets\n";
PATCHEOF
php /tmp/patch-globals.php
rm -f /tmp/patch-globals.php

# Hand off to the original OpenEMR entrypoint (PID 1)
exec ./openemr.sh
