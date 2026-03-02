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
                \"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = '${MYSQL_DATABASE:-openemr}' AND table_type = 'BASE TABLE'\"
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
            # Check install state:
            # - ready: globals/users_secure tables exist and can be counted
            # - incomplete: one or both critical tables do not exist yet
            # - error: SQL check failed
            INSTALL_STATE=$(php -r "
                try {
                    \$p = new PDO(
                        'mysql:host=${MYSQL_HOST};port=${MYSQL_PORT};dbname=${MYSQL_DATABASE:-openemr}',
                        '${MYSQL_USER}', '${MYSQL_PASS}', [PDO::ATTR_TIMEOUT => 10]
                    );
                    \$glTable = (int)(\$p->query(\"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${MYSQL_DATABASE:-openemr}' AND table_name='globals'\")->fetchColumn() ?? 0);
                    \$usTable = (int)(\$p->query(\"SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='${MYSQL_DATABASE:-openemr}' AND table_name='users_secure'\")->fetchColumn() ?? 0);
                    if (\$glTable === 0 || \$usTable === 0) {
                        echo \"state=incomplete,globals_table=\$glTable,users_table=\$usTable\";
                        exit;
                    }
                    \$gl = (int)(\$p->query('SELECT COUNT(*) FROM globals')->fetchColumn() ?? 0);
                    \$us = (int)(\$p->query('SELECT COUNT(*) FROM users_secure')->fetchColumn() ?? 0);
                    echo \"state=ready,globals=\$gl,users=\$us\";
                } catch (Exception \$e) {
                    echo 'state=error';
                }
            " 2>/dev/null)

            echo "[Railway] Install check: ${INSTALL_STATE}"

            STATE=$(echo "$INSTALL_STATE" | sed -n 's/.*state=\([^,]*\).*/\1/p')
            GLOBALS_COUNT=$(echo "$INSTALL_STATE" | sed -n 's/.*globals=\([0-9]*\).*/\1/p')
            USERS_COUNT=$(echo "$INSTALL_STATE" | sed -n 's/.*users=\([0-9]*\).*/\1/p')

            if [ "$STATE" = "ready" ] && { [ "$GLOBALS_COUNT" = "0" ] || [ "$USERS_COUNT" = "0" ]; }; then
                echo "[Railway] WARNING: ${TABLE_COUNT} tables but globals=${GLOBALS_COUNT}, users=${USERS_COUNT} — broken install detected."
                echo "[Railway] Dropping all tables so auto_configure can rebuild properly..."
                php -r "
                    \$p = new PDO(
                        'mysql:host=${MYSQL_HOST};port=${MYSQL_PORT};dbname=${MYSQL_DATABASE:-openemr}',
                        '${MYSQL_USER}', '${MYSQL_PASS}', [PDO::ATTR_TIMEOUT => 10]
                    );
                    \$p->exec('SET FOREIGN_KEY_CHECKS = 0');
                    \$objects = \$p->query(\"SELECT table_name, table_type FROM information_schema.tables WHERE table_schema = '${MYSQL_DATABASE:-openemr}'\")->fetchAll(PDO::FETCH_NUM);
                    foreach (\$objects as \$obj) {
                        \$name = str_replace(chr(96), chr(96) . chr(96), \$obj[0]);
                        \$type = strtoupper(\$obj[1]);
                        if (\$type === 'VIEW') {
                            \$p->exec(\"DROP VIEW IF EXISTS \`{\$name}\`\");
                        } else {
                            \$p->exec(\"DROP TABLE IF EXISTS \`{\$name}\`\");
                        }
                    }
                    \$p->exec('SET FOREIGN_KEY_CHECKS = 1');
                    echo count(\$objects) . ' objects dropped.';
                " 2>/dev/null
                echo "[Railway] Tables dropped. Letting openemr.sh run auto_configure."
                export MYSQL_ROOT_PASS="${MYSQL_ROOT_PASS:-${MYSQL_PASS}}"
                # Fall through to openemr.sh without writing sqlconf.php
            elif [ "$STATE" = "ready" ]; then
                echo "[Railway] Database has ${TABLE_COUNT} tables, ${GLOBALS_COUNT} globals, ${USERS_COUNT} users — writing sqlconf.php."
            cat > "$SQLCONF" <<EOPHP
<?php
//  OpenEMR
//  MySQL Config
//  Written by Railway entrypoint — existing database, skip auto_configure.

global \$disable_utf8_flag;
\$disable_utf8_flag = false;

\$host	= '${MYSQL_HOST}';
\$port	= '${MYSQL_PORT}';
\$login	= '${MYSQL_USER}';
\$pass	= '${MYSQL_PASS}';
\$dbase	= '${MYSQL_DATABASE:-openemr}';
\$db_encoding = 'utf8mb4';

\$sqlconf = array();
global \$sqlconf;
\$sqlconf["host"]= \$host;
\$sqlconf["port"] = \$port;
\$sqlconf["login"] = \$login;
\$sqlconf["pass"] = \$pass;
\$sqlconf["dbase"] = \$dbase;
\$sqlconf["db_encoding"] = \$db_encoding;

//////////////////////////
//////////////////////////
//////////////////////////
//////DO NOT TOUCH THIS///
\$config = 1; /////////////
//////////////////////////
//////////////////////////
//////////////////////////
EOPHP
            echo "[Railway] sqlconf.php written with \$config=1 — skipping auto_configure."
            else
                echo "[Railway] Install state is ${STATE:-unknown}; database appears mid-install."
                echo "[Railway] Skipping destructive reset and letting openemr.sh continue auto_configure."
                export MYSQL_ROOT_PASS="${MYSQL_ROOT_PASS:-${MYSQL_PASS}}"
            fi
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

# globals.php: make kernel + module init non-fatal
# The base image (7.0.2) has two catch blocks with die():
#   Line ~295: catch (\Exception $e) { error_log(...); die(); }  — kernel init
#   Line ~666: catch (\Exception $ex) { error_log(...); die(); } — module init
# PHP 8.2 undefined-global errors propagate here and kill every page.
# Comment out both die() calls so pages continue loading.
#
# NOTE: The LOCAL repo's globals.php uses \Throwable (newer code) but the
# base Docker image (7.0.2) uses \Exception. This patcher targets the IMAGE.
cat > /tmp/patch-globals.php <<'PATCHEOF'
<?php
$file = '/var/www/localhost/htdocs/openemr/interface/globals.php';
$lines = file($file);
$patched = 0;
$in_catch = false;

foreach ($lines as $i => &$line) {
    // Match catch (\Exception ...) — but NOT AccessDeniedException
    if (strpos($line, 'catch') !== false
        && strpos($line, 'Exception') !== false
        && strpos($line, 'AccessDenied') === false) {
        $in_catch = true;
        continue;
    }
    // Also match catch (\Throwable ...) in case image is updated
    if (strpos($line, 'catch') !== false && strpos($line, 'Throwable') !== false) {
        $in_catch = true;
        continue;
    }
    if ($in_catch && strpos($line, 'die()') !== false) {
        $line = str_replace('die();', '// die(); // [Railway] removed — non-fatal', $line);
        $patched++;
        $in_catch = false;
    }
    // Reset if we hit another catch or closing brace without finding die()
    if ($in_catch && (strpos($line, 'catch') !== false || trim($line) === '}')) {
        $in_catch = false;
    }
}

file_put_contents($file, implode('', $lines));
echo $patched
    ? "[Railway] Patched globals.php OK — removed $patched die() calls from catch blocks\n"
    : "[Railway] WARNING: no catch die() found in globals.php\n";
PATCHEOF
php /tmp/patch-globals.php
rm -f /tmp/patch-globals.php

# Hand off to the original OpenEMR entrypoint (PID 1)
exec ./openemr.sh
