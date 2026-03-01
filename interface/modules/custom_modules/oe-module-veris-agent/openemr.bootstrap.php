<?php

/**
 * Veris Agent Module Bootstrap
 *
 * Registers the module namespace, adds a "Veris Agent" menu item under
 * Miscellaneous, and injects a floating chat widget into the main tabs
 * shell so clinicians can open the agent from any page.
 *
 * @package   OpenEMR
 * @link      https://www.open-emr.org
 * @author    Veris <veris@example.com>
 * @copyright Copyright (c) 2026 Veris
 * @license   https://github.com/openemr/openemr/blob/master/LICENSE GNU General Public License 3
 */

use OpenEMR\Events\Main\Tabs\RenderEvent;
use OpenEMR\Menu\MenuEvent;

/**
 * @var \OpenEMR\Core\ModulesClassLoader $classLoader
 * @var \Symfony\Component\EventDispatcher\EventDispatcherInterface $eventDispatcher
 */

// Guard: $classLoader and $eventDispatcher are injected by ModulesApplication.
// If this file is included outside that context, bail silently.
if (empty($classLoader) || empty($eventDispatcher)) {
    return;
}

$classLoader->registerNamespaceIfNotExists(
    'OpenEMR\\Modules\\VerisAgent\\',
    __DIR__ . DIRECTORY_SEPARATOR . 'src'
);

// ---------------------------------------------------------------------------
// 1. Menu item (fallback — opens Veris Agent as a full-page tab)
// ---------------------------------------------------------------------------
function oe_module_veris_agent_add_menu_item(MenuEvent $event)
{
    $menu = $event->getMenu();

    $menuItem = new stdClass();
    $menuItem->requirement = 0;
    $menuItem->target = 'mod';
    $menuItem->menu_id = 'veris0';
    $menuItem->label = xlt('Veris Agent');
    $menuItem->url = '/interface/modules/custom_modules/oe-module-veris-agent/public/index.php';
    $menuItem->children = [];
    $menuItem->acl_req = ['patients', 'docs'];
    $menuItem->global_req = [];

    foreach ($menu as $item) {
        if ($item->menu_id == 'misimg') {
            $item->children[] = $menuItem;
            break;
        }
    }

    $event->setMenu($menu);

    return $event;
}

$eventDispatcher->addListener(MenuEvent::MENU_UPDATE, 'oe_module_veris_agent_add_menu_item');

// ---------------------------------------------------------------------------
// 2. Floating chat widget (injected into the main tabs shell)
// ---------------------------------------------------------------------------
function oe_module_veris_agent_render_widget()
{
    // Session context
    $pid = $_SESSION['pid'] ?? '';
    $encounter = $_SESSION['encounter'] ?? '';
    $authUser = $_SESSION['authUser'] ?? '';

    // Veris frontend URL
    $verisUrl = $GLOBALS['veris_agent_url'] ?? 'https://veris-teal.vercel.app';

    $iframeParams = http_build_query([
        'embedded' => 'true',
        'patient_pid' => $pid,
        'encounter_id' => $encounter,
        'ehr_user' => $authUser,
    ]);
    $iframeSrc = attr($verisUrl . '/?' . $iframeParams);

    // Context display
    $ctxLabel = '';
    if (!empty($pid)) {
        $ctxLabel = xlt('Patient') . ': ' . text($pid);
        if (!empty($encounter)) {
            $ctxLabel .= ' | ' . xlt('Enc') . ': ' . text($encounter);
        }
    } else {
        $ctxLabel = xlt('No patient selected');
    }
    ?>
    <!-- Veris Agent Floating Widget -->
    <style>
        #veris-widget-btn {
            position: fixed;
            bottom: 24px;
            right: 24px;
            z-index: 99999;
            width: 56px;
            height: 56px;
            border-radius: 50%;
            border: none;
            background: #1a1a2e;
            color: #ffffff;
            font-size: 22px;
            font-weight: 700;
            cursor: pointer;
            box-shadow: 0 4px 16px rgba(0, 0, 0, 0.3);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        #veris-widget-btn:hover {
            transform: scale(1.08);
            box-shadow: 0 6px 24px rgba(0, 0, 0, 0.4);
        }
        #veris-widget-panel {
            position: fixed;
            top: 0;
            right: 0;
            width: 420px;
            height: 100vh;
            z-index: 99998;
            background: #ffffff;
            box-shadow: -4px 0 24px rgba(0, 0, 0, 0.15);
            transform: translateX(100%);
            transition: transform 0.3s ease;
            display: flex;
            flex-direction: column;
        }
        #veris-widget-panel.veris-open {
            transform: translateX(0);
        }
        .veris-widget-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 16px;
            background: #1a1a2e;
            color: #ffffff;
            font-size: 13px;
            flex-shrink: 0;
        }
        .veris-widget-header .veris-title {
            font-weight: 700;
            font-size: 15px;
            letter-spacing: 0.5px;
        }
        .veris-widget-header .veris-ctx {
            opacity: 0.7;
            font-size: 12px;
        }
        .veris-widget-close {
            background: none;
            border: none;
            color: #ffffff;
            font-size: 22px;
            cursor: pointer;
            padding: 0 4px;
            line-height: 1;
            opacity: 0.7;
            transition: opacity 0.15s;
        }
        .veris-widget-close:hover {
            opacity: 1;
        }
        #veris-widget-iframe {
            flex: 1;
            width: 100%;
            border: none;
        }
    </style>

    <button id="veris-widget-btn" title="<?php echo xla('Open Veris Agent'); ?>">V</button>

    <div id="veris-widget-panel">
        <div class="veris-widget-header">
            <span class="veris-title"><?php echo xlt('Veris Agent'); ?></span>
            <span class="veris-ctx"><?php echo $ctxLabel; ?></span>
            <button class="veris-widget-close" id="veris-widget-close" title="<?php echo xla('Close'); ?>">&times;</button>
        </div>
        <iframe
            id="veris-widget-iframe"
            src="<?php echo $iframeSrc; ?>"
            allow="clipboard-write"
            sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
            title="<?php echo xla('Veris Clinical Intelligence Agent'); ?>"
        ></iframe>
    </div>

    <script>
        (function () {
            var btn = document.getElementById('veris-widget-btn');
            var panel = document.getElementById('veris-widget-panel');
            var closeBtn = document.getElementById('veris-widget-close');

            btn.addEventListener('click', function () {
                panel.classList.add('veris-open');
                btn.style.display = 'none';
                if (typeof top.restoreSession === 'function') {
                    top.restoreSession();
                }
            });

            closeBtn.addEventListener('click', function () {
                panel.classList.remove('veris-open');
                btn.style.display = 'flex';
            });
        })();
    </script>
    <?php
}

$eventDispatcher->addListener(RenderEvent::EVENT_BODY_RENDER_POST, 'oe_module_veris_agent_render_widget');
