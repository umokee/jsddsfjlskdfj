# NixOS module для Task Manager API
# Полностью автоматизированный деплой с Git, билдом фронтенда и fail2ban интеграцией

{
  pkgs,
  lib,
  helpers,
  ...
}:

let
  enable = helpers.hasIn "services" "task-manager";

  # ==== НАСТРОЙКИ - ИЗМЕНИТЕ ПОД СЕБЯ ====

  # API ключ - ОБЯЗАТЕЛЬНО ИЗМЕНИТЕ!
  apiKey = "your-super-secret-api-key-change-me";

  # Git репозиторий
  gitRepo = "https://github.com/umokee/umtask.git";
  gitBranch = "claude/task-manager-fastapi-hYjWx";

  # Домен и порты
  domain = "tasks.umkcloud.xyz";  # Ваш домен (Caddy автоматически получит HTTPS)
  useHttpOnly = true;             # ВРЕМЕННО: HTTP вместо HTTPS (для доступа по IP)
  publicPort = 8888;              # Публичный порт (будет в URL)
  backendPort = 8000;             # Backend (внутренний)
  backendHost = "127.0.0.1";

  # Пути
  projectPath = "/var/lib/task-manager";
  secretsDir = "/var/lib/task-manager-secrets";
  logDir = "/var/log/task-manager";
  apiKeyFile = "${secretsDir}/api-key";
  frontendBuildDir = "${projectPath}/frontend/dist";

  # Reverse proxy: "caddy", "nginx" или "none"
  reverseProxy = "caddy";

  # Fail2ban
  enableFail2ban = true;
  fail2banMaxRetry = 2;
  fail2banFindTime = "1d";
  fail2banBanTime = "52w";

  # Пользователь
  user = "task-manager";
  group = "task-manager";

  # ==== КОНЕЦ НАСТРОЕК ====

  # Python окружение с зависимостями
  pythonEnv = pkgs.python3.withPackages (ps: with ps; [
    fastapi
    uvicorn
    sqlalchemy
    pydantic
    python-multipart
    apscheduler  # Для автоматического управления временем
  ]);

  # Node.js для сборки фронтенда
  nodeDeps = with pkgs; [ nodejs nodePackages.npm ];

in {
  config = lib.mkIf enable {
    # Создать пользователя и группу
    users.users.${user} = {
      isSystemUser = true;
      group = group;
      description = "Task Manager service user";
      home = projectPath;
    };

    users.groups.${group} = {};

    # Открыть порты
    networking.firewall.allowedTCPPorts = [
      publicPort      # Публичный порт приложения
    ] ++ lib.optionals (!useHttpOnly) [
      80              # Для ACME HTTP-01 challenge (Let's Encrypt)
    ];

    # Создать директории
    systemd.tmpfiles.rules = [
      "d ${projectPath} 0755 ${user} ${group} -"
      "d ${secretsDir} 0700 ${user} ${group} -"
      "d ${logDir} 0750 ${user} ${group} -"
      "f ${apiKeyFile} 0600 ${user} ${group} -"
    ];

    # 1. Синхронизация из Git
    systemd.services.task-manager-git-sync = {
      description = "Sync Task Manager from Git";
      wantedBy = [ "multi-user.target" ];
      after = [ "systemd-tmpfiles-setup.service" "network-online.target" ];
      wants = [ "network-online.target" ];
      requires = [ "systemd-tmpfiles-setup.service" ];
      path = [ pkgs.git pkgs.coreutils pkgs.bash ];

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

    # 2. Создание API ключа (пользователь задает сам)
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

        # Записать API ключ из конфигурации
        echo "TASK_MANAGER_API_KEY=${apiKey}" > ${apiKeyFile}
        chmod 600 ${apiKeyFile}
        chown ${user}:${group} ${apiKeyFile}
        echo "API key initialized"
      '';
    };

    # 3. Сборка фронтенда
    systemd.services.task-manager-frontend-build = {
      description = "Build Task Manager Frontend";
      after = [ "task-manager-git-sync.service" ];
      requires = [ "task-manager-git-sync.service" ];
      wantedBy = [ "multi-user.target" ];
      path = nodeDeps ++ [ pkgs.coreutils pkgs.bash ];

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

        # Установить зависимости
        echo "Installing frontend dependencies..."
        ${pkgs.nodejs}/bin/npm install

        # Собрать фронтенд
        echo "Building frontend..."
        ${pkgs.nodejs}/bin/npm run build

        echo "Frontend build completed successfully"
        ls -la dist/
      '';
    };

    # 4. Инициализация базы данных
    systemd.services.task-manager-db-init = {
      description = "Initialize Task Manager Database";
      after = [ "task-manager-git-sync.service" ];
      requires = [ "task-manager-git-sync.service" ];
      wantedBy = [ "multi-user.target" ];
      path = [ pythonEnv pkgs.coreutils ];

      environment = {
        TASK_MANAGER_DB_DIR = projectPath;
        PYTHONPATH = projectPath;
      };

      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        User = user;
        Group = group;
        WorkingDirectory = projectPath;
      };

      script = ''
        set -e

        # Запустить инициализацию базы данных
        if [ -f ${projectPath}/backend/init_db.py ]; then
          echo "Initializing database..."
          ${pythonEnv}/bin/python ${projectPath}/backend/init_db.py
          echo "Database initialization completed"
        else
          echo "Warning: init_db.py not found, skipping database initialization"
        fi
      '';
    };

    # 5. Backend API сервис
    systemd.services.task-manager-backend = {
      description = "Task Manager API Backend";
      after = [
        "task-manager-git-sync.service"
        "task-manager-api-key-init.service"
        "task-manager-db-init.service"
        "network-online.target"
      ];
      wants = [ "network-online.target" ];
      requires = [
        "task-manager-git-sync.service"
        "task-manager-api-key-init.service"
        "task-manager-db-init.service"
      ];
      wantedBy = [ "multi-user.target" ];

      environment = {
        TASK_MANAGER_LOG_DIR = logDir;
        TASK_MANAGER_LOG_FILE = "app.log";
        PYTHONPATH = projectPath;
      };

      serviceConfig = {
        Type = "simple";
        User = user;
        Group = group;
        WorkingDirectory = projectPath;
        EnvironmentFile = apiKeyFile;
        ExecStart = "${pythonEnv}/bin/uvicorn backend.main:app --host ${backendHost} --port ${toString backendPort}";
        Restart = "always";
        RestartSec = "10";

        # Security hardening
        NoNewPrivileges = true;
        PrivateTmp = true;
        ProtectSystem = "strict";
        ProtectHome = true;
        ReadWritePaths = [ logDir projectPath ];

        # Logging
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
      '';
    };

    # 6. Reverse Proxy (Caddy)
    services.caddy = lib.mkIf (reverseProxy == "caddy") {
      enable = true;

      # ВРЕМЕННО: HTTP по IP, когда DNS настроится - убери useHttpOnly
      virtualHosts."${if useHttpOnly then "http://:${toString publicPort}" else "${domain}:${toString publicPort}"}" = {
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

    # 7. Reverse Proxy (Nginx альтернатива)
    services.nginx = lib.mkIf (reverseProxy == "nginx") {
      enable = true;

      virtualHosts."localhost" = {
        listen = [{ addr = "0.0.0.0"; port = publicPort; }];

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

    # 8. Fail2ban интеграция
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
