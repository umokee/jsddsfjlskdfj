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
    property string effectiveDate: ""  // Effective date from server (respects day_start_time)

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
            effectiveDate = data.effective_date || "";
            // Check rest day using effective date from server
            _checkRestDay();
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
        _apiGet("/tasks/today-habits", function(data) {
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

    function _checkRestDay() {
        // Use effective date from server (respects day_start_time setting)
        if (!effectiveDate) return;
        _apiGet("/rest-days", function(data) {
            isRestDay = false;
            if (Array.isArray(data)) {
                for (let i = 0; i < data.length; i++) {
                    if (data[i].date === effectiveDate) {
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

    // Callback registry for async operations
    property var _callbacks: ({})
    property int _callbackId: 0

    function _registerCallback(callback) {
        let id = _callbackId++;
        _callbacks[id] = callback;
        return id;
    }

    function _executeCallback(id, data) {
        if (_callbacks[id]) {
            _callbacks[id](data);
            delete _callbacks[id];
        }
    }

    function _apiGet(endpoint, callback) {
        let cbId = _registerCallback(callback);
        let url = apiUrl + endpoint;
        let key = apiKey;

        let proc = Qt.createQmlObject(`
            import QtQuick
            import Quickshell.Io
            Process {
                id: proc
                property string responseData: ""
                command: ["curl", "-s", "--connect-timeout", "5", "-H", "X-API-Key: ` + key + `", "` + url + `"]
                stdout: SplitParser {
                    onRead: data => {
                        proc.responseData += data;
                    }
                }
                stderr: SplitParser {
                    onRead: data => {
                        console.error("TaskService: curl error for ` + endpoint + `:", data);
                    }
                }
                onRunningChanged: {
                    if (!running) {
                        if (responseData) {
                            try {
                                let json = JSON.parse(responseData);
                                service._executeCallback(` + cbId + `, json);
                            } catch (e) {
                                console.error("TaskService: JSON parse error for ` + endpoint + `:", e, "Data:", responseData.substring(0, 100));
                            }
                        } else {
                            console.warn("TaskService: Empty response for ` + endpoint + ` - API may be unreachable");
                        }
                    }
                }
            }
        `, service);
        proc.running = true;
    }

    function _apiPost(endpoint, body, callback) {
        let cbId = callback ? _registerCallback(callback) : -1;
        let url = apiUrl + endpoint;
        let key = apiKey;

        let proc = Qt.createQmlObject(`
            import QtQuick
            import Quickshell.Io
            Process {
                id: proc
                property string responseData: ""
                command: ["curl", "-s", "--connect-timeout", "5", "-X", "POST",
                         "-H", "X-API-Key: ` + key + `",
                         "-H", "Content-Type: application/json",
                         "` + url + `"]
                stdout: SplitParser {
                    onRead: data => {
                        proc.responseData += data;
                    }
                }
                stderr: SplitParser {
                    onRead: data => {
                        console.error("TaskService: curl POST error for ` + endpoint + `:", data);
                    }
                }
                onRunningChanged: {
                    if (!running && responseData && ` + cbId + ` >= 0) {
                        try {
                            let json = JSON.parse(responseData);
                            service._executeCallback(` + cbId + `, json);
                        } catch (e) {
                            console.error("TaskService: JSON parse error for POST ` + endpoint + `:", e);
                        }
                    }
                }
            }
        `, service);
        proc.running = true;
    }

    function _notify(title, msg) {
        // Escape quotes for shell safety
        let safeTitle = title.replace(/"/g, '\\"');
        let safeMsg = msg.replace(/"/g, '\\"');

        let proc = Qt.createQmlObject(`
            import Quickshell.Io
            Process {
                command: ["notify-send", "-u", "low", "` + safeTitle + `", "` + safeMsg + `"]
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
        // Rest day check is now done inside _fetchSettings using effective_date
    }
}
