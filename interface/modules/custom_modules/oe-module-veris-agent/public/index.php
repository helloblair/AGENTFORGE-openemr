<?php

/**
 * Veris Agent — Embedded Chat View
 *
 * Renders the Veris Next.js frontend in an iframe, passing the current
 * patient/encounter/user context from the OpenEMR session as URL parameters.
 *
 * @package   OpenEMR
 * @link      https://www.open-emr.org
 * @author    Veris <veris@example.com>
 * @copyright Copyright (c) 2026 Veris
 * @license   https://github.com/openemr/openemr/blob/master/LICENSE GNU General Public License 3
 */

require_once dirname(__FILE__, 5) . '/globals.php';

use OpenEMR\Core\Header;

// Read session context
$pid = $_SESSION['pid'] ?? '';
$encounter = $_SESSION['encounter'] ?? '';
$authUser = $_SESSION['authUser'] ?? '';

// Veris frontend URL — override via Admin > Globals > veris_agent_url
$verisUrl = $GLOBALS['veris_agent_url'] ?? 'http://localhost:3000';

// Build iframe URL with EHR context query params
$iframeParams = http_build_query([
    'embedded' => 'true',
    'patient_pid' => $pid,
    'encounter_id' => $encounter,
    'ehr_user' => $authUser,
]);
$iframeSrc = $verisUrl . '/?' . $iframeParams;
?>
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title><?php echo xlt('Veris Agent'); ?></title>
    <?php Header::setupHeader(['common']); ?>
    <style>
        body { margin: 0; padding: 0; overflow: hidden; }
        .veris-container {
            display: flex;
            flex-direction: column;
            height: 100vh;
            width: 100%;
        }
        .veris-toolbar {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 4px 12px;
            background: var(--light, #f8f9fa);
            border-bottom: 1px solid var(--secondary, #dee2e6);
            font-size: 13px;
        }
        .veris-toolbar .context-info {
            color: var(--gray600, #6c757d);
        }
        .veris-iframe {
            flex: 1;
            width: 100%;
            border: none;
        }
    </style>
</head>
<body>
    <div class="veris-container">
        <div class="veris-toolbar">
            <span>
                <strong><?php echo xlt('Veris Agent'); ?></strong>
            </span>
            <span class="context-info">
                <?php if (!empty($pid)) : ?>
                    <?php echo xlt('Patient'); ?>: <?php echo text($pid); ?>
                    <?php if (!empty($encounter)) : ?>
                        | <?php echo xlt('Encounter'); ?>: <?php echo text($encounter); ?>
                    <?php endif; ?>
                <?php else : ?>
                    <?php echo xlt('No patient selected'); ?>
                <?php endif; ?>
            </span>
        </div>
        <iframe
            id="veris-agent-frame"
            class="veris-iframe"
            src="<?php echo attr($iframeSrc); ?>"
            allow="clipboard-write"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
            title="<?php echo xla('Veris Clinical Intelligence Agent'); ?>"
        ></iframe>
    </div>
    <script>
        // Keep OpenEMR session alive when navigating within the iframe
        if (typeof top.restoreSession === 'function') {
            top.restoreSession();
        }
    </script>
</body>
</html>
