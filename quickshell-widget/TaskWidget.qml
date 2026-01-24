import QtQuick
import QtQuick.Layouts
import Quickshell
import "../theme"

Item {
    id: root

    required property var service
    required property var panelWindow

    implicitWidth: box.width
    implicitHeight: box.height

    // === Colors (Terminal Theme) ===
    readonly property color accentColor: Theme.green || "#00ff88"
    readonly property color dangerColor: Theme.red || "#ff4444"
    readonly property color warningColor: Theme.yellow || "#ffaa00"
    readonly property color mutedColor: Theme.muted || "#888888"
    readonly property color bgColor: Theme.bg || "#0a0a0a"
    readonly property color bgSecondary: "#141414"
    readonly property color borderColor: "#2a2a2a"

    readonly property color statusColor: {
        if (service.isRestDay) return warningColor
        if (service.pendingMood) return warningColor
        if (service.currentTask) return accentColor
        if (service.allTasksDone) return accentColor
        return mutedColor
    }

    readonly property color boxBorderColor: {
        if (service.isRestDay) return warningColor
        if (service.pendingMood) return warningColor
        if (service.timerRunning) return dangerColor
        if (service.currentTask) return accentColor
        return borderColor
    }

    // === Handlers ===
    HoverHandler { id: hover }

    TapHandler {
        acceptedButtons: Qt.LeftButton
        onTapped: {
            if (service.pendingMood) {
                moodPopup.visible = !moodPopup.visible
            } else {
                mainPopup.visible = !mainPopup.visible
            }
        }
    }

    TapHandler {
        acceptedButtons: Qt.RightButton
        onTapped: {
            service.refresh()
        }
    }

    // === Progress ===
    readonly property real progressPos: {
        if (service.timerRunning && service.timerTotal > 0) {
            return 1.0 - (service.timerSeconds / service.timerTotal)
        }
        if (service.tasksTotal > 0) {
            return service.tasksDone / service.tasksTotal
        }
        return 0.0
    }

    // === Main Box ===
    Rectangle {
        id: box
        width: content.width + 20
        height: 26
        radius: 0
        border.width: 1
        border.color: root.boxBorderColor
        color: "transparent"

        // Progress gradient
        Rectangle {
            anchors.fill: parent
            anchors.margins: 1
            radius: 0
            opacity: 0.3

            gradient: Gradient {
                orientation: Gradient.Horizontal
                GradientStop {
                    position: 0.0
                    color: root.statusColor
                }
                GradientStop {
                    position: Math.max(0, Math.min(1, root.progressPos))
                    color: root.statusColor
                }
                GradientStop {
                    position: Math.min(1, root.progressPos + 0.001)
                    color: "transparent"
                }
                GradientStop {
                    position: 1.0
                    color: "transparent"
                }
            }
        }

        Behavior on width { NumberAnimation { duration: 200 } }

        RowLayout {
            id: content
            anchors.centerIn: parent
            spacing: 8

            // Status indicator
            Rectangle {
                width: 8
                height: 8
                radius: 0
                color: root.statusColor
                border.width: 1
                border.color: root.statusColor

                // Blink animation for pending mood
                SequentialAnimation on opacity {
                    running: service.pendingMood
                    loops: Animation.Infinite
                    NumberAnimation { to: 0.3; duration: 800 }
                    NumberAnimation { to: 1.0; duration: 800 }
                }
            }

            // Main text
            Text {
                text: {
                    if (service.isRestDay) return "[REST_DAY]"
                    if (service.pendingMood) return "[MORNING_CHECK-IN]"
                    if (service.currentTask) return service.currentTaskShort
                    if (service.allTasksDone) return "[ALL_DONE]"
                    return "[NO_TASKS]"
                }
                color: {
                    if (service.isRestDay) return root.warningColor
                    if (service.pendingMood) return root.warningColor
                    if (service.currentTask) return Theme.fg
                    if (service.allTasksDone) return root.accentColor
                    return root.mutedColor
                }
                font.family: "monospace"
                font.pixelSize: 11
                font.bold: true
                Layout.maximumWidth: 180
                elide: Text.ElideRight
            }

            // Stats/Timer
            Rectangle {
                visible: !service.isRestDay && !service.pendingMood
                implicitWidth: statsText.width + 12
                implicitHeight: 16
                radius: 0
                color: statsHover.hovered ? Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.2) : "transparent"
                border.width: 1
                border.color: service.timerRunning ? root.dangerColor : root.borderColor

                Text {
                    id: statsText
                    anchors.centerIn: parent
                    text: {
                        if (service.timerRunning) {
                            return service.timerDisplay
                        }
                        return service.tasksDone + "/" + service.tasksTotal
                    }
                    color: {
                        if (service.timerRunning) return root.dangerColor
                        let ratio = service.tasksTotal > 0 ? service.tasksDone / service.tasksTotal : 0
                        return ratio >= 0.8 ? root.accentColor : root.mutedColor
                    }
                    font.family: "monospace"
                    font.pixelSize: 10
                    font.bold: true
                }

                HoverHandler { id: statsHover }

                TapHandler {
                    acceptedButtons: Qt.LeftButton
                    onTapped: {
                        if (service.currentTask) {
                            service.toggleTimer()
                        }
                    }
                }

                TapHandler {
                    acceptedButtons: Qt.MiddleButton
                    onTapped: service.stopTimer()
                }
            }
        }
    }

    // === Tooltip ===
    PopupWindow {
        id: tooltip
        parentWindow: root.panelWindow
        visible: hover.hovered && !mainPopup.visible && !moodPopup.visible
        relativeX: box.mapToItem(null, box.width/2, 0).x - width/2
        relativeY: box.mapToItem(null, 0, 0).y - height - 6
        width: tooltipBg.width
        height: tooltipBg.height
        color: "transparent"

        Rectangle {
            id: tooltipBg
            width: tooltipCol.width + 16
            height: tooltipCol.height + 12
            radius: 0
            color: root.bgColor
            border.width: 1
            border.color: root.borderColor

            Column {
                id: tooltipCol
                anchors.centerIn: parent
                spacing: 4

                Text {
                    visible: service.isRestDay
                    text: "REST DAY - NO PENALTIES"
                    color: root.warningColor
                    font.family: "monospace"
                    font.pixelSize: 10
                    font.bold: true
                }

                Text {
                    visible: service.pendingMood
                    text: "MORNING CHECK-IN REQUIRED"
                    color: root.warningColor
                    font.family: "monospace"
                    font.pixelSize: 10
                    font.bold: true
                }

                Text {
                    visible: service.currentTask
                    text: service.currentTaskDesc
                    color: Theme.fg
                    font.family: "monospace"
                    font.pixelSize: 10
                    width: Math.min(implicitWidth, 250)
                    wrapMode: Text.WordWrap
                }

                Text {
                    visible: service.currentTask && service.currentTaskProject
                    text: "[" + service.currentTaskProject + "]"
                    color: root.mutedColor
                    font.family: "monospace"
                    font.pixelSize: 9
                }

                Text {
                    visible: service.currentTask
                    text: "ENERGY: " + service.currentTaskEnergy + "/5"
                    color: root.accentColor
                    font.family: "monospace"
                    font.pixelSize: 9
                }

                Text {
                    visible: !service.currentTask && !service.isRestDay && !service.pendingMood
                    text: "TASKS: " + service.tasksDone + "/" + service.tasksTotal + " | HABITS: " + service.habitsDone + "/" + service.habitsTotal
                    color: root.mutedColor
                    font.family: "monospace"
                    font.pixelSize: 9
                }
            }
        }
    }

    // === Main Popup ===
    PopupWindow {
        id: mainPopup
        parentWindow: root.panelWindow
        visible: false
        relativeX: box.mapToItem(null, box.width/2, 0).x - width/2
        relativeY: box.mapToItem(null, 0, 0).y - height - 6
        width: popupBg.width
        height: popupBg.height
        color: "transparent"

        HoverHandler {
            onHoveredChanged: {
                if (!hovered && !hover.hovered) {
                    mainPopup.visible = false
                }
            }
        }

        Rectangle {
            id: popupBg
            width: 280
            height: Math.min(popupContent.implicitHeight + 16, 400)
            radius: 0
            color: root.bgColor
            border.width: 2
            border.color: root.accentColor

            Column {
                id: popupContent
                anchors.fill: parent
                anchors.margins: 8
                spacing: 6

                // Header
                Rectangle {
                    width: parent.width
                    height: 24
                    color: root.bgSecondary
                    border.width: 1
                    border.color: root.borderColor

                    Text {
                        anchors.centerIn: parent
                        text: "[TASK_MANAGER]"
                        color: root.accentColor
                        font.family: "monospace"
                        font.pixelSize: 11
                        font.bold: true
                    }
                }

                // Current task section
                Column {
                    visible: service.currentTask
                    width: parent.width
                    spacing: 4

                    Text {
                        text: "> CURRENT_TASK"
                        color: root.accentColor
                        font.family: "monospace"
                        font.pixelSize: 10
                        font.bold: true
                    }

                    Rectangle {
                        width: parent.width
                        height: currentTaskText.height + 12
                        color: Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.1)
                        border.width: 1
                        border.color: root.accentColor

                        Column {
                            id: currentTaskText
                            anchors.centerIn: parent
                            width: parent.width - 12
                            spacing: 2

                            Text {
                                text: service.currentTaskDesc
                                color: Theme.fg
                                font.family: "monospace"
                                font.pixelSize: 10
                                width: parent.width
                                wrapMode: Text.WordWrap
                            }

                            Text {
                                visible: service.currentTaskProject
                                text: "[" + service.currentTaskProject + "]"
                                color: root.mutedColor
                                font.family: "monospace"
                                font.pixelSize: 9
                            }
                        }
                    }

                    // Actions for current task
                    Row {
                        width: parent.width
                        spacing: 4

                        Rectangle {
                            width: (parent.width - 4) / 2
                            height: 22
                            radius: 0
                            color: completeHover.hovered ? Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.2) : root.bgSecondary
                            border.width: 1
                            border.color: root.accentColor

                            Text {
                                anchors.centerIn: parent
                                text: "[COMPLETE]"
                                color: root.accentColor
                                font.family: "monospace"
                                font.pixelSize: 9
                                font.bold: true
                            }

                            HoverHandler { id: completeHover }
                            TapHandler {
                                onTapped: {
                                    service.completeTask()
                                    mainPopup.visible = false
                                }
                            }
                        }

                        Rectangle {
                            width: (parent.width - 4) / 2
                            height: 22
                            radius: 0
                            color: stopHover.hovered ? Qt.rgba(root.dangerColor.r, root.dangerColor.g, root.dangerColor.b, 0.2) : root.bgSecondary
                            border.width: 1
                            border.color: root.mutedColor

                            Text {
                                anchors.centerIn: parent
                                text: "[STOP]"
                                color: root.mutedColor
                                font.family: "monospace"
                                font.pixelSize: 9
                                font.bold: true
                            }

                            HoverHandler { id: stopHover }
                            TapHandler {
                                onTapped: {
                                    service.stopCurrentTask()
                                    mainPopup.visible = false
                                }
                            }
                        }
                    }
                }

                // Today's tasks
                Column {
                    visible: service.todayTasksModel.count > 0
                    width: parent.width
                    spacing: 4

                    Text {
                        text: "> TODAY_TASKS [" + service.todayTasksModel.count + "]"
                        color: root.accentColor
                        font.family: "monospace"
                        font.pixelSize: 10
                        font.bold: true
                    }

                    Repeater {
                        model: service.todayTasksModel

                        Rectangle {
                            required property var model

                            width: popupContent.width - 16
                            height: 20
                            radius: 0
                            color: taskHover.hovered ? Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.1) : root.bgSecondary
                            border.width: 1
                            border.color: model.status === "active" ? root.accentColor : root.borderColor

                            Row {
                                anchors.fill: parent
                                anchors.margins: 4
                                spacing: 6

                                Text {
                                    text: model.status === "completed" ? "[X]" : "[ ]"
                                    color: model.status === "completed" ? root.accentColor : root.mutedColor
                                    font.family: "monospace"
                                    font.pixelSize: 9
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: model.description
                                    color: model.status === "active" ? root.accentColor : Theme.fg
                                    font.family: "monospace"
                                    font.pixelSize: 9
                                    elide: Text.ElideRight
                                    width: parent.width - 40
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: "E" + model.energy
                                    color: root.mutedColor
                                    font.family: "monospace"
                                    font.pixelSize: 8
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            HoverHandler { id: taskHover }
                            TapHandler {
                                onTapped: {
                                    if (model.status === "pending") {
                                        service.startTask(model.id)
                                    }
                                    mainPopup.visible = false
                                }
                            }
                        }
                    }
                }

                // Today's habits
                Column {
                    visible: service.todayHabitsModel.count > 0
                    width: parent.width
                    spacing: 4

                    Text {
                        text: "> HABITS [" + service.todayHabitsModel.count + "]"
                        color: root.accentColor
                        font.family: "monospace"
                        font.pixelSize: 10
                        font.bold: true
                    }

                    Repeater {
                        model: service.todayHabitsModel

                        Rectangle {
                            required property var model

                            width: popupContent.width - 16
                            height: 20
                            radius: 0
                            color: habitHover.hovered ? Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.1) : root.bgSecondary
                            border.width: 1
                            border.color: model.status === "active" ? root.accentColor : root.borderColor

                            Row {
                                anchors.fill: parent
                                anchors.margins: 4
                                spacing: 6

                                Text {
                                    text: "[" + model.daily_completed + "/" + model.daily_target + "]"
                                    color: model.daily_completed >= model.daily_target ? root.accentColor : root.mutedColor
                                    font.family: "monospace"
                                    font.pixelSize: 9
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    text: model.description
                                    color: model.status === "active" ? root.accentColor : Theme.fg
                                    font.family: "monospace"
                                    font.pixelSize: 9
                                    elide: Text.ElideRight
                                    width: parent.width - 50
                                    anchors.verticalCenter: parent.verticalCenter
                                }

                                Text {
                                    visible: model.streak > 0
                                    text: "~" + model.streak
                                    color: root.accentColor
                                    font.family: "monospace"
                                    font.pixelSize: 8
                                    anchors.verticalCenter: parent.verticalCenter
                                }
                            }

                            HoverHandler { id: habitHover }
                            TapHandler {
                                onTapped: {
                                    if (model.daily_completed < model.daily_target) {
                                        service.startTask(model.id)
                                    }
                                    mainPopup.visible = false
                                }
                            }
                        }
                    }
                }

                // Empty state
                Text {
                    visible: !service.currentTask && service.todayTasksModel.count === 0 && service.todayHabitsModel.count === 0 && !service.isRestDay
                    text: "> NO_TASKS_TODAY"
                    color: root.mutedColor
                    font.family: "monospace"
                    font.pixelSize: 10
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                    topPadding: 12
                }
            }
        }
    }

    // === Mood Selection Popup ===
    PopupWindow {
        id: moodPopup
        parentWindow: root.panelWindow
        visible: false
        relativeX: box.mapToItem(null, box.width/2, 0).x - width/2
        relativeY: box.mapToItem(null, 0, 0).y - height - 6
        width: moodBg.width
        height: moodBg.height
        color: "transparent"

        HoverHandler {
            onHoveredChanged: {
                if (!hovered && !hover.hovered) {
                    moodPopup.visible = false
                }
            }
        }

        Rectangle {
            id: moodBg
            width: 240
            height: moodContent.implicitHeight + 16
            radius: 0
            color: root.bgColor
            border.width: 2
            border.color: root.warningColor

            Column {
                id: moodContent
                anchors.fill: parent
                anchors.margins: 8
                spacing: 6

                // Header
                Rectangle {
                    width: parent.width
                    height: 24
                    color: Qt.rgba(root.warningColor.r, root.warningColor.g, root.warningColor.b, 0.2)
                    border.width: 1
                    border.color: root.warningColor

                    Text {
                        anchors.centerIn: parent
                        text: "[MORNING_CHECK-IN]"
                        color: root.warningColor
                        font.family: "monospace"
                        font.pixelSize: 11
                        font.bold: true
                    }
                }

                Text {
                    text: "SELECT_ENERGY_LEVEL:"
                    color: root.accentColor
                    font.family: "monospace"
                    font.pixelSize: 9
                    font.bold: true
                    width: parent.width
                    horizontalAlignment: Text.AlignHCenter
                }

                // Mood buttons
                Repeater {
                    model: [
                        { value: 0, label: "E0 EXHAUSTED" },
                        { value: 1, label: "E1 TIRED" },
                        { value: 2, label: "E2 OKAY" },
                        { value: 3, label: "E3 GOOD" },
                        { value: 4, label: "E4 STRONG" },
                        { value: 5, label: "E5 PEAK" }
                    ]

                    Rectangle {
                        required property var modelData

                        width: moodContent.width - 16
                        height: 22
                        radius: 0
                        color: moodBtnHover.hovered ? Qt.rgba(root.accentColor.r, root.accentColor.g, root.accentColor.b, 0.2) : root.bgSecondary
                        border.width: 1
                        border.color: moodBtnHover.hovered ? root.accentColor : root.borderColor

                        Text {
                            anchors.centerIn: parent
                            text: "[" + modelData.label + "]"
                            color: moodBtnHover.hovered ? root.accentColor : Theme.fg
                            font.family: "monospace"
                            font.pixelSize: 9
                            font.bold: moodBtnHover.hovered
                        }

                        HoverHandler { id: moodBtnHover }
                        TapHandler {
                            onTapped: {
                                service.completeRoll(modelData.value)
                                moodPopup.visible = false
                            }
                        }
                    }
                }
            }
        }
    }
}
