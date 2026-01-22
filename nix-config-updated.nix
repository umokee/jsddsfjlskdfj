{
  pkgs,
  lib,
  helpers,
  ...
}:

let
  enable = helpers.hasIn "services" "task-manager";

  apiKey = "662a8fd07c07e64ddcae78a7d869603f";

  gitRepo = "https://github.com/umokee/jsddsfjlskdfj.git";
  gitBranch = "claude/fix-auto-backup-NvYox";

  domain = "tasks.umkcloud.xyz";
  useHttpOnly = true;
  publicPort = 8888;
  backendPort = 8000;
  backendHost = "127.0.0.1";

  projectPath = "/var/lib/task-manager";
  secretsDir = "/var/lib/task-manager-secrets";
  logDir = "/var/log/task-manager";
  apiKeyFile = "${secretsDir}/api-key";
  frontendBuildDir = "${projectPath}/frontend/dist";

  reverseProxy = "caddy";

  enableFail2ban = true;
  fail2banMaxRetry = 2;
  fail2banFindTime = "1d";
  fail2banBanTime = "52w";

  user = "task-manager";
  group = "task-manager";

  nodeDeps = with pkgs; [
    nodejs
    nodePackages.npm
  ];
in
{
  config = lib.mkIf enable {
    users.users.${user} = {
      isSystemUser = true;
      group = group;
      description = "Task Manager service user";
      home = projectPath;
    };
    users.groups.${group} = { };

    networking.firewall.allowedTCPPorts = [
      publicPort
    ]
    ++ lib.optionals (!useHttpOnly) [
      80
    ];

    systemd.tmpfiles.rules = [
      "d ${projectPath} 0755 ${user} ${group} -"
      "d ${secretsDir} 0700 ${user} ${group} -"
      "d ${logDir} 0750 ${user} ${group} -"
      "f ${apiKeyFile} 0600 ${user} ${group} -"
    ];

    systemd.services.task-manager-git-sync = {
      description = "Sync Task Manager from Git";
      wantedBy = [ "multi-user.target" ];
      after = [
        "systemd-tmpfiles-setup.service"
        "network-online.target"
      ];
      wants = [ "network-online.target" ];
      requires = [ "systemd-tmpfiles-setup.service" ];
      path = [
        pkgs.git
        pkgs.coreutils
        pkgs.bash
      ];

      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        User = user;
        Group = group;
      };

      script = ''
        set -e

        mkdir -p ${projectPath}
        chmod 755 ${projectPath}

        if [ -d ${projectPath}/.git ]; then
          cd ${projectPath}
          ${pkgs.git}/bin/git fetch origin
          ${pkgs.git}/bin/git checkout ${gitBranch}
          ${pkgs.git}/bin/git reset --hard origin/${gitBranch}
          ${pkgs.git}/bin/git pull origin ${gitBranch}
        else
          rm -rf ${projectPath}/*
          rm -rf ${projectPath}/.* 2>/dev/null || true
          cd ${projectPath}
          ${pkgs.git}/bin/git clone -b ${gitBranch} ${gitRepo} .
        fi

        chmod -R u+w ${projectPath}
        echo "Git sync completed successfully"
      '';
    };

    systemd.services.task-manager-api-key-init = {
      description = "Initialize API key for Task Manager";
      wantedBy = [ "multi-user.target" ];
      after = [ "systemd-tmpfiles-setup.service" ];
      requires = [ "systemd-tmpfiles-setup.service" ];
      path = [ pkgs.coreutils ];

      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        User = user;
        Group = group;
      };

      script = ''
        mkdir -p ${secretsDir}
        chmod 700 ${secretsDir}

        echo "TASK_MANAGER_API_KEY=${apiKey}" > ${apiKeyFile}
        chmod 600 ${apiKeyFile}
        chown ${user}:${group} ${apiKeyFile}
        echo "API key initialized"
      '';
    };

    systemd.services.task-manager-frontend-build = {
      description = "Build Task Manager Frontend";
      after = [ "task-manager-git-sync.service" ];
      requires = [ "task-manager-git-sync.service" ];
      wantedBy = [ "multi-user.target" ];
      path = nodeDeps ++ [
        pkgs.coreutils
        pkgs.bash
      ];

      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        User = user;
        Group = group;
        WorkingDirectory = "${projectPath}/frontend";
      };

      script = ''
        set -e

        if [ ! -d ${projectPath}/frontend ]; then
          echo "Error: Frontend directory does not exist"
          exit 1
        fi

        cd ${projectPath}/frontend

        echo "Installing frontend dependencies..."
        ${pkgs.nodejs}/bin/npm install

        echo "Building frontend..."
        ${pkgs.nodejs}/bin/npm run build

        echo "Frontend build completed successfully"
        ls -la dist/
      '';
    };

    systemd.services.task-manager-backend = {
      description = "Task Manager API Backend";
      after = [
        "task-manager-git-sync.service"
        "task-manager-api-key-init.service"
        "network-online.target"
      ];
      wants = [ "network-online.target" ];
      requires = [
        "task-manager-git-sync.service"
        "task-manager-api-key-init.service"
      ];
      wantedBy = [ "multi-user.target" ];

      environment = {
        TASK_MANAGER_LOG_DIR = logDir;
        TASK_MANAGER_LOG_FILE = "app.log";
        PYTHONPATH = projectPath;
      };

      path = [
        pkgs.python312
        pkgs.gcc
        pkgs.stdenv.cc
        pkgs.zlib
      ];

      serviceConfig = {
        Type = "simple";
        User = user;
        Group = group;
        WorkingDirectory = projectPath;
        TimeoutStartSec = "infinity";

        EnvironmentFile = apiKeyFile;
        ExecStart = "${projectPath}/venv/bin/uvicorn backend.main:app --host ${backendHost} --port ${toString backendPort}";
        Restart = "always";
        RestartSec = "10";

        NoNewPrivileges = true;
        PrivateTmp = true;
        ProtectSystem = "full";
        ProtectHome = true;
        ReadWritePaths = [
          logDir
          projectPath
        ];

        StandardOutput = "journal";
        StandardError = "journal";
        SyslogIdentifier = "task-manager-backend";
      };

      preStart = ''
        if [ ! -d ${projectPath} ]; then
          echo "Error: ${projectPath} does not exist"
          exit 1
        fi

        if [ ! -f ${apiKeyFile} ]; then
          echo "Error: API key file does not exist"
          exit 1
        fi

        if [ ! -d ${projectPath}/venv ]; then
          echo "Creating virtualenv..."
          ${pkgs.python312}/bin/python -m venv ${projectPath}/venv
        fi

        echo "Installing dependencies from requirements.txt..."
        ${projectPath}/venv/bin/pip install --upgrade pip
        ${projectPath}/venv/bin/pip install -r ${projectPath}/backend/requirements.txt
      '';
    };

    # Улучшенный сервис обновления
    systemd.services.task-manager-update = {
      description = "Update Task Manager (pull, rebuild, restart)";

      path = [
        pkgs.coreutils
        pkgs.systemd
      ];

      serviceConfig = {
        Type = "oneshot";
      };

      script = ''
        set -e
        echo "=== Task Manager Update ==="

        # 1. Остановить backend (APScheduler завершится корректно)
        echo "[1/7] Stopping backend..."
        ${pkgs.systemd}/bin/systemctl stop task-manager-backend

        # 2. Обновить код из Git
        echo "[2/7] Updating code from Git..."
        ${pkgs.systemd}/bin/systemctl restart task-manager-git-sync
        sleep 2

        # 3. Удалить старый venv (избежать конфликтов зависимостей)
        echo "[3/7] Recreating Python environment..."
        if [ -d ${projectPath}/venv ]; then
          echo "Removing old venv..."
          rm -rf ${projectPath}/venv
        fi

        # 4. Пересобрать frontend
        echo "[4/7] Rebuilding frontend..."
        ${pkgs.systemd}/bin/systemctl restart task-manager-frontend-build
        sleep 3

        # 5. Запустить backend (venv пересоздастся в preStart)
        echo "[5/7] Starting backend..."
        ${pkgs.systemd}/bin/systemctl start task-manager-backend
        sleep 5

        # 6. Проверить что backend запустился
        echo "[6/7] Checking backend status..."
        if ! ${pkgs.systemd}/bin/systemctl is-active --quiet task-manager-backend; then
          echo "ERROR: Backend failed to start!"
          ${pkgs.systemd}/bin/systemctl status task-manager-backend --no-pager || true
          exit 1
        fi

        # 7. Перезагрузить reverse proxy
        echo "[7/7] Reloading reverse proxy..."
        ${pkgs.systemd}/bin/systemctl reload caddy

        echo ""
        echo "✅ Update completed successfully!"
        echo ""
        echo "Check logs:"
        echo "  journalctl -u task-manager-backend -n 100 --no-pager"
        echo ""
        echo "Check APScheduler:"
        echo "  journalctl -u task-manager-backend | grep -i scheduler"
      '';
    };

    services.caddy = lib.mkIf (reverseProxy == "caddy") {
      enable = true;

      virtualHosts."${
        if useHttpOnly then "http://:${toString publicPort}" else "${domain}:${toString publicPort}"
      }" =
        {
          extraConfig = ''
            # API endpoints
            handle /api/* {
              reverse_proxy ${backendHost}:${toString backendPort}
            }

            # Frontend static files (всё остальное)
            handle {
              root * ${frontendBuildDir}
              try_files {path} /index.html
              file_server
            }
          '';
        };
    };

    services.nginx = lib.mkIf (reverseProxy == "nginx") {
      enable = true;

      virtualHosts."localhost" = {
        listen = [
          {
            addr = "0.0.0.0";
            port = publicPort;
          }
        ];

        locations."/api/" = {
          proxyPass = "http://${backendHost}:${toString backendPort}";
          extraConfig = ''
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
          '';
        };

        locations."/" = {
          root = frontendBuildDir;
          tryFiles = "$uri $uri/ /index.html";
          extraConfig = ''
            add_header Cache-Control "public, max-age=3600";
          '';
        };
      };
    };

    environment.etc."fail2ban/filter.d/task-manager-api.conf" = lib.mkIf enableFail2ban {
      text = ''
        [Definition]
        failregex = ^.*Invalid API key attempt from <HOST>.*$
        ignoreregex =
      '';
    };

    services.fail2ban = lib.mkIf enableFail2ban {
      enable = true;

      jails.task-manager-api = {
        settings = {
          enabled = true;
          filter = "task-manager-api";
          logpath = "${logDir}/app.log";
          backend = "auto";
          action = "iptables-allports";
          maxretry = fail2banMaxRetry;
          findtime = fail2banFindTime;
          bantime = fail2banBanTime;
        };
      };
    };
  };
}
