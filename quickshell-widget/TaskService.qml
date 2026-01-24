import QtQuick
import Quickshell.Io

QtObject {
    id: service

    property var updateManager: null

    // === API Settings ===
    property string apiUrl: "http://localhost:8000/api"
    property string apiKey: ""  // Set this in your config

    // === Current State ===
    property var currentTask: null
    property string currentTaskDesc: ""
    property string currentTaskShort: ""
    property string currentTaskProject: ""
    property int currentTaskEnergy: 3
    property bool isRestDay: false
    property bool pendingMood: false

    // === Stats ===
    property int tasksDone: 0
    property int tasksTotal: 0
    property int habitsDone: 0
    property int habitsTotal: 0
    property bool allTasksDone: false

    // === Timer ===
    property bool timerRunning: false
    property int timerSeconds: 0
    property int timerTotal: 0
    property string timerDisplay: "00:00"

    // === Models ===
    property var todayTasksModel: ListModel {}
    property var todayHabitsModel: ListModel {}

    // === API Calls ===

    function refresh() {
        _fetchStats();
        _fetchCurrentTask();
        _fetchSettings();
        _fetchTodayTasks();
        _fetchTodayHabits();
    }

    function startTask(id) {
        _apiPost("/tasks/" + id + "/start", null, function() {
            refresh();
        });
    }

    function stopCurrentTask() {
        if (!currentTask) return;
        _apiPost("/tasks/" + currentTask.id + "/stop", null, function() {
            stopTimer();
            refresh();
        });
    }

    function completeTask() {
        if (!currentTask) return;
        _apiPost("/tasks/" + currentTask.id + "/complete", null, function() {
            stopTimer();
            refresh();
        });
    }

    function completeRoll(mood) {
        _apiPost("/tasks/complete-roll?mood=" + mood, null, function() {
            pendingMood = false;
            refresh();
            _notify("Morning Check-in Complete", "Tasks scheduled for E" + mood);
        });
    }

    function toggleTimer() {
        if (!currentTask) return;

        if (timerRunning) {
            timerRunning = false;
        } else {
            timerRunning = true;
            timerSeconds = 0;
            timerTotal = currentTaskEnergy * 20 * 60;  // 20 min per energy level
        }
    }

    function stopTimer() {
        timerRunning = false;
        timerSeconds = 0;
        timerTotal = 0;
    }

    // === Private Methods ===

    function _fetchStats() {
        _apiGet("/stats", function(data) {
            tasksDone = data.done_today || 0;
            tasksTotal = data.total_pending || 0;
            habitsDone = data.habits_done || 0;
            habitsTotal = data.habits_total || 0;
            allTasksDone = tasksDone >= tasksTotal && tasksTotal > 0;
        });
    }

    function _fetchCurrentTask() {
        _apiGet("/tasks/current", function(data) {
            if (data && data.id) {
                currentTask = data;
                currentTaskDesc = data.description || "No description";
                currentTaskShort = currentTaskDesc.length > 20
                    ? currentTaskDesc.substring(0, 19) + "…"
                    : currentTaskDesc;
                currentTaskProject = data.project || "";
                currentTaskEnergy = data.energy || 3;
            } else {
                currentTask = null;
                currentTaskDesc = "";
                currentTaskShort = "";
                currentTaskProject = "";
                currentTaskEnergy = 3;
            }
        });
    }

    function _fetchSettings() {
        _apiGet("/settings", function(data) {
            pendingMood = data.pending_roll || false;
        });
    }

    function _fetchTodayTasks() {
        todayTasksModel.clear();
        _apiGet("/tasks/today", function(data) {
            if (Array.isArray(data)) {
                for (let i = 0; i < data.length; i++) {
                    let task = data[i];
                    if (!task.is_habit) {
                        todayTasksModel.append({
                            id: task.id,
                            description: task.description,
                            project: task.project || "",
                            energy: task.energy || 3,
                            status: task.status || "pending",
                            priority: task.priority || 5
                        });
                    }
                }
            }
        });
    }

    function _fetchTodayHabits() {
        todayHabitsModel.clear();
        _apiGet("/habits/today", function(data) {
            if (Array.isArray(data)) {
                for (let i = 0; i < data.length; i++) {
                    let habit = data[i];
                    todayHabitsModel.append({
                        id: habit.id,
                        description: habit.description,
                        status: habit.status || "pending",
                        daily_target: habit.daily_target || 1,
                        daily_completed: habit.daily_completed || 0,
                        streak: habit.streak || 0
                    });
                }
            }
        });
    }

    function _fetchRestDays() {
        _apiGet("/rest-days", function(data) {
            let today = new Date().toISOString().split('T')[0];
            isRestDay = false;
            if (Array.isArray(data)) {
                for (let i = 0; i < data.length; i++) {
                    if (data[i].date === today) {
                        isRestDay = true;
                        break;
                    }
                }
            }
        });
    }

    function _tick() {
        if (!timerRunning) return;

        timerSeconds++;

        let remaining = Math.max(0, timerTotal - timerSeconds);
        let m = Math.floor(remaining / 60);
        let s = remaining % 60;
        timerDisplay = (m < 10 ? "0" : "") + m + ":" + (s < 10 ? "0" : "") + s;

        if (remaining === 0) {
            timerRunning = false;
            _notify("Time's Up!", "Pomodoro session completed");
        }
    }

    function _update() {
        _tick();
        // Refresh every 30 seconds
        if (timerSeconds % 30 === 0) {
            refresh();
        }
    }

    // === HTTP Helpers ===

    function _apiGet(endpoint, callback) {
        let proc = Qt.createQmlObject(`
            import Quickshell.Io
            Process {
                command: ["curl", "-s", "-H", "X-API-Key: ${apiKey}", "${apiUrl}${endpoint}"]
                stdout: SplitParser {
                    onRead: data => {
                        try {
                            let json = JSON.parse(data);
                            callback(json);
                        } catch (e) {
                            console.error("JSON parse error:", e);
                        }
                    }
                }
            }
        `, service);
        proc.running = true;
    }

    function _apiPost(endpoint, body, callback) {
        let proc = Qt.createQmlObject(`
            import Quickshell.Io
            Process {
                command: ["curl", "-s", "-X", "POST",
                         "-H", "X-API-Key: ${apiKey}",
                         "-H", "Content-Type: application/json",
                         "${apiUrl}${endpoint}"]
                stdout: SplitParser {
                    onRead: data => {
                        try {
                            let json = JSON.parse(data);
                            if (callback) callback(json);
                        } catch (e) {
                            console.error("JSON parse error:", e);
                        }
                    }
                }
            }
        `, service);
        proc.running = true;
    }

    function _notify(title, msg) {
        let proc = Qt.createQmlObject(`
            import Quickshell.Io
            Process {
                command: ["notify-send", "-u", "low", "${title}", "${msg}"]
            }
        `, service);
        proc.running = true;
    }

    // === Initialization ===

    Component.onCompleted: {
        if (updateManager) {
            updateManager.register(service, 1, _update, "TaskService");
        }
        refresh();
        _fetchRestDays();
    }
}
