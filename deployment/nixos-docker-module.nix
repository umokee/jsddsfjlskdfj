# NixOS module для Task Manager с Docker
# Полностью автоматизированный деплой с Git, Docker Compose и автообновлением

{
  pkgs,
  lib,
  config,
  ...
}:

let
  cfg = config.services.task-manager-docker;

  # ==== НАСТРОЙКИ - ИЗМЕНИТЕ ПОД СЕБЯ ====

  # API ключ - ОБЯЗАТЕЛЬНО ИЗМЕНИТЕ!
  defaultApiKey = "your-super-secret-api-key-change-me";

  # Git репозиторий
  defaultGitRepo = "https://github.com/umokee/jsddsfjlskdfj.git";
  defaultGitBranch = "main";

  # Порты
  defaultPublicPort = 8080;  # Публичный порт (443 занят VPN)

  # Пути
  defaultProjectPath = "/var/lib/task-manager-docker";
  defaultSecretsDir = "/var/lib/task-manager-secrets";

  # Пользователь
  defaultUser = "task-manager";
  defaultGroup = "task-manager";

  # ==== КОНЕЦ НАСТРОЕК ====

  # Скрипт для обновления
  updateScript = pkgs.writeScriptBin "task-manager-update" ''
    #!${pkgs.bash}/bin/bash
    set -e

    echo "🔄 Обновление Task Manager..."

    # Git pull
    echo "📥 Получение обновлений из Git..."
    cd ${cfg.projectPath}
    ${pkgs.git}/bin/git fetch origin
    ${pkgs.git}/bin/git checkout ${cfg.gitBranch}
    ${pkgs.git}/bin/git pull origin ${cfg.gitBranch}

    # Rebuild и restart через systemd
    echo "🔨 Пересборка Docker контейнеров..."
    ${pkgs.systemd}/bin/systemctl restart task-manager-docker-rebuild.service

    echo "✅ Обновление завершено!"
    echo "📊 Статус сервисов:"
    ${pkgs.systemd}/bin/systemctl status task-manager-docker.service --no-pager
  '';

in {
  options.services.task-manager-docker = {
    enable = lib.mkEnableOption "Task Manager Docker Service";

    apiKey = lib.mkOption {
      type = lib.types.str;
      default = defaultApiKey;
      description = "API ключ для Task Manager";
    };

    gitRepo = lib.mkOption {
      type = lib.types.str;
      default = defaultGitRepo;
      description = "URL Git репозитория";
    };

    gitBranch = lib.mkOption {
      type = lib.types.str;
      default = defaultGitBranch;
      description = "Git ветка для деплоя";
    };

    publicPort = lib.mkOption {
      type = lib.types.int;
      default = defaultPublicPort;
      description = "Публичный порт для доступа";
    };

    projectPath = lib.mkOption {
      type = lib.types.str;
      default = defaultProjectPath;
      description = "Путь к проекту";
    };

    secretsDir = lib.mkOption {
      type = lib.types.str;
      default = defaultSecretsDir;
      description = "Путь к секретам";
    };

    user = lib.mkOption {
      type = lib.types.str;
      default = defaultUser;
      description = "Пользователь для запуска сервиса";
    };

    group = lib.mkOption {
      type = lib.types.str;
      default = defaultGroup;
      description = "Группа для запуска сервиса";
    };

    autoUpdate = lib.mkOption {
      type = lib.types.bool;
      default = false;
      description = "Автоматическое обновление из Git (каждый день в 3:00)";
    };
  };

  config = lib.mkIf cfg.enable {
    # Включить Docker
    virtualisation.docker = {
      enable = true;
      autoPrune = {
        enable = true;
        dates = "weekly";
      };
    };

    # Создать пользователя и группу
    users.users.${cfg.user} = {
      isSystemUser = true;
      group = cfg.group;
      description = "Task Manager Docker service user";
      home = cfg.projectPath;
      extraGroups = [ "docker" ];  # Доступ к Docker
    };

    users.groups.${cfg.group} = {};

    # Открыть порт
    networking.firewall.allowedTCPPorts = [ cfg.publicPort ];

    # Создать директории
    systemd.tmpfiles.rules = [
      "d ${cfg.projectPath} 0755 ${cfg.user} ${cfg.group} -"
      "d ${cfg.secretsDir} 0700 ${cfg.user} ${cfg.group} -"
      "d ${cfg.projectPath}/data 0755 ${cfg.user} ${cfg.group} -"
      "d ${cfg.projectPath}/logs 0755 ${cfg.user} ${cfg.group} -"
    ];

    # Установить docker-compose
    environment.systemPackages = with pkgs; [
      docker
      docker-compose
      git
      updateScript  # Команда task-manager-update
    ];

    # 1. Git Sync - клонирование/обновление репозитория
    systemd.services.task-manager-docker-git-sync = {
      description = "Sync Task Manager from Git";
      wantedBy = [ "multi-user.target" ];
      after = [ "docker.service" "network-online.target" ];
      wants = [ "network-online.target" ];
      requires = [ "docker.service" ];
      path = [ pkgs.git pkgs.coreutils ];

      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        User = cfg.user;
        Group = cfg.group;
      };

      script = ''
        set -e

        mkdir -p ${cfg.projectPath}
        chmod 755 ${cfg.projectPath}

        if [ -d ${cfg.projectPath}/.git ]; then
          echo "📥 Обновление из Git..."
          cd ${cfg.projectPath}
          ${pkgs.git}/bin/git fetch origin
          ${pkgs.git}/bin/git checkout ${cfg.gitBranch}
          ${pkgs.git}/bin/git reset --hard origin/${cfg.gitBranch}
          ${pkgs.git}/bin/git pull origin ${cfg.gitBranch}
        else
          echo "📦 Клонирование репозитория..."
          rm -rf ${cfg.projectPath}/*
          rm -rf ${cfg.projectPath}/.* 2>/dev/null || true
          ${pkgs.git}/bin/git clone -b ${cfg.gitBranch} ${cfg.gitRepo} ${cfg.projectPath}
        fi

        chmod -R u+w ${cfg.projectPath}
        echo "✅ Git sync завершен"
      '';
    };

    # 2. Создание .env файла
    systemd.services.task-manager-docker-env-setup = {
      description = "Setup Task Manager Docker environment";
      wantedBy = [ "multi-user.target" ];
      after = [ "task-manager-docker-git-sync.service" ];
      requires = [ "task-manager-docker-git-sync.service" ];
      path = [ pkgs.coreutils ];

      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        User = cfg.user;
        Group = cfg.group;
      };

      script = ''
        set -e

        mkdir -p ${cfg.secretsDir}
        chmod 700 ${cfg.secretsDir}

        # Создать .env файл
        cat > ${cfg.projectPath}/.env <<EOF
TASK_MANAGER_API_KEY=${cfg.apiKey}
PUBLIC_PORT=${toString cfg.publicPort}
TASK_MANAGER_LOG_DIR=/var/log/task-manager
DATABASE_URL=sqlite:////app/data/task_manager.db
EOF

        chmod 600 ${cfg.projectPath}/.env
        chown ${cfg.user}:${cfg.group} ${cfg.projectPath}/.env

        # Создать директории для volumes
        mkdir -p ${cfg.projectPath}/data
        mkdir -p ${cfg.projectPath}/logs
        chmod 755 ${cfg.projectPath}/data
        chmod 755 ${cfg.projectPath}/logs

        echo "✅ Environment setup завершен"
      '';
    };

    # 3. Docker Compose Build - сборка контейнеров
    systemd.services.task-manager-docker-rebuild = {
      description = "Rebuild Task Manager Docker containers";
      after = [
        "task-manager-docker-git-sync.service"
        "task-manager-docker-env-setup.service"
        "docker.service"
      ];
      requires = [
        "task-manager-docker-git-sync.service"
        "task-manager-docker-env-setup.service"
        "docker.service"
      ];
      wantedBy = [ "multi-user.target" ];
      path = [ pkgs.docker-compose pkgs.docker ];

      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        User = cfg.user;
        Group = cfg.group;
        WorkingDirectory = cfg.projectPath;
      };

      script = ''
        set -e

        if [ ! -f ${cfg.projectPath}/docker-compose.yml ]; then
          echo "❌ Error: docker-compose.yml не найден"
          exit 1
        fi

        echo "🔨 Сборка Docker контейнеров..."
        cd ${cfg.projectPath}
        ${pkgs.docker-compose}/bin/docker-compose build --no-cache

        echo "✅ Сборка завершена"
      '';
    };

    # 4. Docker Compose Up - запуск контейнеров
    systemd.services.task-manager-docker = {
      description = "Task Manager Docker Compose";
      after = [
        "task-manager-docker-rebuild.service"
        "docker.service"
        "network.target"
      ];
      requires = [
        "task-manager-docker-rebuild.service"
        "docker.service"
      ];
      wantedBy = [ "multi-user.target" ];

      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = "yes";
        WorkingDirectory = cfg.projectPath;
        User = cfg.user;
        Group = cfg.group;

        ExecStart = "${pkgs.docker-compose}/bin/docker-compose up -d";
        ExecStop = "${pkgs.docker-compose}/bin/docker-compose down";
        ExecReload = "${pkgs.docker-compose}/bin/docker-compose restart";

        Restart = "on-failure";
        RestartSec = "10s";

        # Security
        PrivateTmp = true;
        NoNewPrivileges = true;
      };

      preStart = ''
        if [ ! -f ${cfg.projectPath}/docker-compose.yml ]; then
          echo "❌ Error: docker-compose.yml не найден"
          exit 1
        fi

        if [ ! -f ${cfg.projectPath}/.env ]; then
          echo "❌ Error: .env файл не найден"
          exit 1
        fi

        echo "🐳 Запуск Docker Compose..."
      '';

      postStart = ''
        echo "✅ Task Manager запущен на порту ${toString cfg.publicPort}"
        echo "🌐 Доступ: http://localhost:${toString cfg.publicPort}"

        # Показать статус контейнеров
        sleep 5
        ${pkgs.docker-compose}/bin/docker-compose ps
      '';
    };

    # 5. Автоматическое обновление (опционально)
    systemd.services.task-manager-docker-auto-update = lib.mkIf cfg.autoUpdate {
      description = "Auto-update Task Manager from Git";
      serviceConfig = {
        Type = "oneshot";
        User = cfg.user;
        Group = cfg.group;
        WorkingDirectory = cfg.projectPath;
      };

      script = ''
        set -e
        echo "🔄 Автоматическое обновление Task Manager..."
        ${updateScript}/bin/task-manager-update
      '';
    };

    systemd.timers.task-manager-docker-auto-update = lib.mkIf cfg.autoUpdate {
      description = "Auto-update Task Manager timer";
      wantedBy = [ "timers.target" ];

      timerConfig = {
        OnCalendar = "daily";
        OnCalendar = "03:00";  # Каждый день в 3:00
        Persistent = true;
      };
    };

    # Логирование
    services.journald.extraConfig = ''
      SystemMaxUse=1G
      MaxRetentionSec=30day
    '';
  };
}
