<?php

/**
 * Config Module.
 * Called by Module Manager during registration/install.
 * Renders in a Laminas-created iframe.
 *
 * @package   OpenEMR
 * @link      https://www.open-emr.org
 * @author    Veris <veris@example.com>
 * @copyright Copyright (c) 2026 Veris
 * @license   https://github.com/openemr/openemr/blob/master/LICENSE GNU General Public License 3
 */

use OpenEMR\Core\ModulesClassLoader;

require_once dirname(__FILE__, 4) . '/globals.php';

$classLoader = new ModulesClassLoader($GLOBALS['fileroot']);
$classLoader->registerNamespaceIfNotExists('OpenEMR\\Modules\\VerisAgent\\', __DIR__ . DIRECTORY_SEPARATOR . 'src');

$module_config = 1;
?>
<div style="padding: 20px; font-family: sans-serif;">
    <h3>Veris Agent Module</h3>
    <p>This module embeds the Veris AI clinical intelligence agent into OpenEMR.</p>
    <p>After enabling, access it via <strong>Miscellaneous &gt; Veris Agent</strong> in the top menu.</p>
</div>
<?php
exit;
