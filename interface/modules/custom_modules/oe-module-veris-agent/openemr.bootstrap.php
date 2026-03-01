<?php

/**
 * Veris Agent Module Bootstrap
 *
 * Registers the module namespace and adds a "Veris Agent" menu item
 * under Miscellaneous so clinicians can launch the embedded chat.
 *
 * @package   OpenEMR
 * @link      https://www.open-emr.org
 * @author    Veris <veris@example.com>
 * @copyright Copyright (c) 2026 Veris
 * @license   https://github.com/openemr/openemr/blob/master/LICENSE GNU General Public License 3
 */

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
