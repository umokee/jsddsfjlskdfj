# NixOS module для Task Manager API
# Полностью автоматизированный деплой с Git, билдом фронтенда и fail2ban интеграцией

{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.task-manager;

  # Пути
  projectPath = cfg.dataDir;
  apiKeyFile = "${cfg.secretsDir}/api-key";
  logDir = cfg.logDir;
  frontendBuildDir = "${projectPath}/frontend/dist";

  # Python окружение с зависимостями
  pythonEnv = pkgs.python3.withPackages (ps: with ps; [
    fastapi
    uvicorn
    sqlalchemy
    pydantic
    python-multipart
  ]);

  # Node.js для сборки фронтенда
  nodeDeps = with pkgs; [ nodejs nodePackages.npm ];

in {
  options.services.task-manager = {
    enable = mkEnableOption "Task Manager API service";

    gitRepo = mkOption {
      type = types.str;
      description = "Git repository URL";
      default = "https://github.com/umokee/umtask.git";
    };

    gitBranch = mkOption {
      type = types.str;
      description = "Git branch to deploy";
      default = "claude/task-manager-fastapi-hYjWx";
    };

    host = mkOption {
      type = types.str;
      description = "Host to bind backend to";
      default = "127.0.0.1";
    };

    port = mkOption {
      type = types.int;
      description = "Port for backend API";
      default = 8000;
    };

    frontendPort = mkOption {
      type = types.int;
      description = "Port for frontend (nginx/caddy)";
      default = 3000;
    };

    publicPort = mkOption {
      type = types.int;
      description = "Public port for the application";
      default = 8080;
    };

    dataDir = mkOption {
      type = types.str;
      description = "Directory for application code and database";
      default = "/var/lib/task-manager";
    };

    secretsDir = mkOption {
      type = types.str;
      description = "Directory for secrets (API key)";
      default = "/var/lib/task-manager-secrets";
    };

    logDir = mkOption {
      type = types.str;
      description = "Directory for log files (for fail2ban integration)";
      default = "/var/log/task-manager";
    };

    user = mkOption {
      type = types.str;
      description = "User account under which task-manager runs";
      default = "task-manager";
    };

    group = mkOption {
      type = types.str;
      description = "Group under which task-manager runs";
      default = "task-manager";
    };

    enableFail2ban = mkOption {
      type = types.bool;
      description = "Enable fail2ban integration for API protection";
      default = true;
    };

    fail2banMaxRetry = mkOption {
      type = types.int;
      description = "Maximum number of failed API key attempts before ban";
      default = 2;
    };

    fail2banFindTime = mkOption {
      type = types.str;
      description = "Time window to count failed attempts";
      default = "1d";
    };

    fail2banBanTime = mkOption {
      type = types.str;
      description = "Duration of IP ban";
      default = "52w";
    };

    reverseProxy = mkOption {
      type = types.enum [ "caddy" "nginx" "none" ];
      description = "Reverse proxy to use (caddy, nginx, or none)";
      default = "caddy";
    };
  };

  config = mkIf cfg.enable {
    # Создать пользователя и группу
    users.users.${cfg.user} = {
      isSystemUser = true;
      group = cfg.group;
      description = "Task Manager service user";
      home = cfg.dataDir;
    };

    users.groups.${cfg.group} = {};

    # Открыть порты
    networking.firewall.allowedTCPPorts = [ cfg.publicPort ];

    # Создать директории
    systemd.tmpfiles.rules = [
      "d ${cfg.dataDir} 0755 ${cfg.user} ${cfg.group} -"
      "d ${cfg.secretsDir} 0700 ${cfg.user} ${cfg.group} -"
      "d ${cfg.logDir} 0750 ${cfg.user} ${cfg.group} -"
      "f ${apiKeyFile} 0600 ${cfg.user} ${cfg.group} -"
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
        User = cfg.user;
        Group = cfg.group;
      };

      script = ''
        set -e

        mkdir -p ${cfg.dataDir}
        chmod 755 ${cfg.dataDir}

        if [ -d ${cfg.dataDir}/.git ]; then
          cd ${cfg.dataDir}
          ${pkgs.git}/bin/git fetch origin
          ${pkgs.git}/bin/git checkout ${cfg.gitBranch}
          ${pkgs.git}/bin/git reset --hard origin/${cfg.gitBranch}
          ${pkgs.git}/bin/git pull origin ${cfg.gitBranch}
        else
          rm -rf ${cfg.dataDir}/*
          rm -rf ${cfg.dataDir}/.* 2>/dev/null || true
          cd ${cfg.dataDir}
          ${pkgs.git}/bin/git clone -b ${cfg.gitBranch} ${cfg.gitRepo} .
        fi

        chmod -R u+w ${cfg.dataDir}
        echo "Git sync completed successfully"
      '';
    };

    # 2. Генерация API ключа
    systemd.services.task-manager-api-key-init = {
      description = "Generate API key for Task Manager";
      wantedBy = [ "multi-user.target" ];
      after = [ "systemd-tmpfiles-setup.service" ];
      requires = [ "systemd-tmpfiles-setup.service" ];
      path = [ pkgs.openssl pkgs.coreutils ];

      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        User = cfg.user;
        Group = cfg.group;
      };

      script = ''
        mkdir -p ${cfg.secretsDir}
        chmod 700 ${cfg.secretsDir}

        if [ ! -s ${apiKeyFile} ]; then
          echo "TASK_MANAGER_API_KEY=$(${pkgs.openssl}/bin/openssl rand -base64 32)" > ${apiKeyFile}
          chmod 600 ${apiKeyFile}
          chown ${cfg.user}:${cfg.group} ${apiKeyFile}
          echo "Generated new API key"
        else
          echo "API key already exists"
        fi
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
        User = cfg.user;
        Group = cfg.group;
        WorkingDirectory = "${cfg.dataDir}/frontend";
      };

      script = ''
        set -e

        if [ ! -d ${cfg.dataDir}/frontend ]; then
          echo "Error: Frontend directory does not exist"
          exit 1
        fi

        cd ${cfg.dataDir}/frontend

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

    # 4. Backend API сервис
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
        TASK_MANAGER_LOG_DIR = cfg.logDir;
        TASK_MANAGER_LOG_FILE = "app.log";
        PYTHONPATH = cfg.dataDir;
      };

      serviceConfig = {
        Type = "simple";
        User = cfg.user;
        Group = cfg.group;
        WorkingDirectory = cfg.dataDir;
        EnvironmentFile = apiKeyFile;
        ExecStart = "${pythonEnv}/bin/uvicorn backend.main:app --host ${cfg.host} --port ${toString cfg.port}";
        Restart = "always";
        RestartSec = "10";

        # Security hardening
        NoNewPrivileges = true;
        PrivateTmp = true;
        ProtectSystem = "strict";
        ProtectHome = true;
        ReadWritePaths = [ cfg.logDir cfg.dataDir ];

        # Logging
        StandardOutput = "journal";
        StandardError = "journal";
        SyslogIdentifier = "task-manager-backend";
      };

      preStart = ''
        if [ ! -d ${cfg.dataDir} ]; then
          echo "Error: ${cfg.dataDir} does not exist"
          exit 1
        fi

        if [ ! -f ${apiKeyFile} ]; then
          echo "Error: API key file does not exist"
          exit 1
        fi
      '';
    };

    # 5. Reverse Proxy (Caddy)
    services.caddy = mkIf (cfg.reverseProxy == "caddy") {
      enable = true;

      virtualHosts.":${toString cfg.publicPort}" = {
        extraConfig = ''
          # API endpoints
          handle /api/* {
            reverse_proxy ${cfg.host}:${toString cfg.port}
          }

          # Health check
          handle / {
            reverse_proxy ${cfg.host}:${toString cfg.port}
          }

          # Frontend static files
          handle {
            root * ${frontendBuildDir}
            try_files {path} /index.html
            file_server
          }
        '';
      };
    };

    # 5. Reverse Proxy (Nginx альтернатива)
    services.nginx = mkIf (cfg.reverseProxy == "nginx") {
      enable = true;

      virtualHosts."localhost" = {
        listen = [{ addr = "0.0.0.0"; port = cfg.publicPort; }];

        locations."/api/" = {
          proxyPass = "http://${cfg.host}:${toString cfg.port}";
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

    # 6. Fail2ban интеграция
    environment.etc."fail2ban/filter.d/task-manager-api.conf" = mkIf cfg.enableFail2ban {
      text = ''
        [Definition]
        failregex = ^.*Invalid API key attempt from <HOST>.*$
        ignoreregex =
      '';
    };

    services.fail2ban = mkIf cfg.enableFail2ban {
      enable = true;

      jails.task-manager-api = {
        settings = {
          enabled = true;
          filter = "task-manager-api";
          logpath = "${cfg.logDir}/app.log";
          backend = "auto";
          action = "iptables-allports";
          maxretry = cfg.fail2banMaxRetry;
          findtime = cfg.fail2banFindTime;
          bantime = cfg.fail2banBanTime;
        };
      };
    };
  };
}
