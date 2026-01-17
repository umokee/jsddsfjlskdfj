# NixOS module для Task Manager с Docker
# Полностью автоматизированный деплой с Git, Docker Compose и автообновлением

{ pkgs, lib, ... }:

let
  # ==== НАСТРОЙКИ - ИЗМЕНИТЕ ПОД СЕБЯ ====

  # Включить сервис (true/false)
  enable = true;

  # API ключ - ОБЯЗАТЕЛЬНО ИЗМЕНИТЕ!
  apiKey = "your-super-secret-api-key-change-me";

  # Git репозиторий
  gitRepo = "https://github.com/umokee/jsddsfjlskdfj.git";
  gitBranch = "main";

  # Порты
  publicPort = 8080;  # Публичный порт (443 занят VPN)

  # Пути
  projectPath = "/var/lib/task-manager-docker";
  secretsDir = "/var/lib/task-manager-secrets";

  # Пользователь
  user = "task-manager";
  group = "task-manager";

  # Fail2ban для защиты от брутфорса
  enableFail2ban = true;
  fail2banMaxRetry = 2;
  fail2banFindTime = "1d";
  fail2banBanTime = "52w";

  # ==== КОНЕЦ НАСТРОЕК ====

  # Скрипт для обновления
  updateScript = pkgs.writeScriptBin "task-manager-update" ''
    #!${pkgs.bash}/bin/bash
    set -e

    echo "🔄 Обновление Task Manager..."

    # Git pull
    echo "📥 Получение обновлений из Git..."
    cd ${projectPath}
    ${pkgs.git}/bin/git fetch origin
    ${pkgs.git}/bin/git checkout ${gitBranch}
    ${pkgs.git}/bin/git pull origin ${gitBranch}

    # Rebuild и restart через systemd
    echo "🔨 Пересборка Docker контейнеров..."
    ${pkgs.systemd}/bin/systemctl restart task-manager-docker-rebuild.service

    echo "✅ Обновление завершено!"
    echo "📊 Статус сервисов:"
    ${pkgs.systemd}/bin/systemctl status task-manager-docker.service --no-pager
  '';

in {
  config = lib.mkIf enable {
    # Включить Docker
    virtualisation.docker = {
      enable = true;
      autoPrune = {
        enable = true;
        dates = "weekly";
      };
    };

    # Создать пользователя и группу
    users.users.${user} = {
      isSystemUser = true;
      group = group;
      description = "Task Manager Docker service user";
      home = projectPath;
      extraGroups = [ "docker" ];  # Доступ к Docker
    };

    users.groups.${group} = {};

    # Открыть порт
    networking.firewall.allowedTCPPorts = [ publicPort ];

    # Создать директории
    systemd.tmpfiles.rules = [
      "d ${projectPath} 0755 ${user} ${group} -"
      "d ${secretsDir} 0700 ${user} ${group} -"
      "d ${projectPath}/data 0755 ${user} ${group} -"
      "d ${projectPath}/logs 0755 ${user} ${group} -"
    ];

    # Установить docker-compose и команду обновления
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
        User = user;
        Group = group;
      };

      script = ''
        set -e

        mkdir -p ${projectPath}
        chmod 755 ${projectPath}

        if [ -d ${projectPath}/.git ]; then
          echo "📥 Обновление из Git..."
          cd ${projectPath}
          ${pkgs.git}/bin/git fetch origin
          ${pkgs.git}/bin/git checkout ${gitBranch}
          ${pkgs.git}/bin/git reset --hard origin/${gitBranch}
          ${pkgs.git}/bin/git pull origin ${gitBranch}
        else
          echo "📦 Клонирование репозитория..."
          rm -rf ${projectPath}/*
          rm -rf ${projectPath}/.* 2>/dev/null || true
          ${pkgs.git}/bin/git clone -b ${gitBranch} ${gitRepo} ${projectPath}
        fi

        chmod -R u+w ${projectPath}
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
        User = user;
        Group = group;
      };

      script = ''
        set -e

        mkdir -p ${secretsDir}
        chmod 700 ${secretsDir}

        # Создать .env файл
        cat > ${projectPath}/.env <<EOF
TASK_MANAGER_API_KEY=${apiKey}
PUBLIC_PORT=${toString publicPort}
TASK_MANAGER_LOG_DIR=/var/log/task-manager
DATABASE_URL=sqlite:////app/data/task_manager.db
EOF

        chmod 600 ${projectPath}/.env
        chown ${user}:${group} ${projectPath}/.env

        # Создать директории для volumes
        mkdir -p ${projectPath}/data
        mkdir -p ${projectPath}/logs
        chmod 755 ${projectPath}/data
        chmod 755 ${projectPath}/logs

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
        User = user;
        Group = group;
        WorkingDirectory = projectPath;
      };

      script = ''
        set -e

        if [ ! -f ${projectPath}/docker-compose.yml ]; then
          echo "❌ Error: docker-compose.yml не найден"
          exit 1
        fi

        echo "🔨 Сборка Docker контейнеров..."
        cd ${projectPath}
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
        WorkingDirectory = projectPath;
        User = user;
        Group = group;

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
        if [ ! -f ${projectPath}/docker-compose.yml ]; then
          echo "❌ Error: docker-compose.yml не найден"
          exit 1
        fi

        if [ ! -f ${projectPath}/.env ]; then
          echo "❌ Error: .env файл не найден"
          exit 1
        fi

        echo "🐳 Запуск Docker Compose..."
      '';

      postStart = ''
        echo "✅ Task Manager запущен на порту ${toString publicPort}"
        echo "🌐 Доступ: http://localhost:${toString publicPort}"

        # Показать статус контейнеров
        sleep 5
        ${pkgs.docker-compose}/bin/docker-compose ps
      '';
    };

    # 5. Fail2ban для защиты от брутфорса API ключа
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
          logpath = "${projectPath}/logs/app.log";
          backend = "auto";
          action = "iptables-allports";
          maxretry = fail2banMaxRetry;
          findtime = fail2banFindTime;
          bantime = fail2banBanTime;
        };
      };
    };

    # Логирование
    services.journald.extraConfig = ''
      SystemMaxUse=1G
      MaxRetentionSec=30day
    '';
  };
}
