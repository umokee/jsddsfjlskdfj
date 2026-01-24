// Example QuickShell configuration for Task Manager Widget
// Copy this to your QuickShell config and adjust paths/API key

import QtQuick
import Quickshell
import Quickshell.Services.SystemTray

ShellRoot {
    // Your existing panel configuration
    PanelWindow {
        id: panel

        anchors {
            top: true
            left: true
            right: true
        }

        height: 32
        color: "transparent"

        // Task Manager Service
        TaskService {
            id: taskService

            // IMPORTANT: Set your API key here
            apiKey: "your-api-key-here"

            // Optional: Change if running on different port
            apiUrl: "http://localhost:8000/api"

            // Connect to update manager if you have one
            updateManager: updateManager  // or null
        }

        // Panel content
        Rectangle {
            anchors.fill: parent
            color: Theme.bg || "#0a0a0a"
            border.width: 1
            border.color: Theme.border || "#2a2a2a"

            Row {
                anchors.fill: parent
                spacing: 8

                // Your other widgets here...

                // Task Manager Widget
                TaskWidget {
                    service: taskService
                    panelWindow: panel
                    anchors.verticalCenter: parent.verticalCenter
                }

                // More widgets...
            }
        }
    }

    // Optional: Update manager for periodic refresh
    QtObject {
        id: updateManager

        property var registered: []

        function register(obj, interval, callback, name) {
            registered.push({
                obj: obj,
                interval: interval,
                callback: callback,
                name: name
            });
        }

        Timer {
            interval: 1000  // 1 second
            running: true
            repeat: true

            property int ticks: 0

            onTriggered: {
                ticks++;
                for (let i = 0; i < updateManager.registered.length; i++) {
                    let item = updateManager.registered[i];
                    if (ticks % item.interval === 0) {
                        item.callback.call(item.obj);
                    }
                }
            }
        }
    }
}
