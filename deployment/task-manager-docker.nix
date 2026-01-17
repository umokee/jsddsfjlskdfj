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
  gitBranch = "claude/debug-task-habit-api-X194g";

  domain = "tasks.umkcloud.xyz";
  useHttpOnly = true;
  publicPort = 8888;

  # Docker internal ports
  dockerFrontendPort = 3080;  # Map Docker port 80 to host 3080
  dockerBackendPort = 3000;   # Map Docker port 8000 to host 3000

  projectPath = "/var/lib/task-manager";
  secretsDir = "/var/lib/task-manager-secrets";
  logDir = "/var/log/task-manager";
  envFile = "${projectPath}/.env";

  reverseProxy = "caddy";

  enableFail2ban = true;
  fail2banMaxRetry = 2;
  fail2banFindTime = "1d";
  fail2banBanTime = "52w";

  user = "task-manager";
  group = "task-manager";

in
{
  config = lib.mkIf enable {
    # Enable Docker
    virtualisation.docker = {
      enable = true;
      autoPrune.enable = true;
    };

    # Add user to docker group
    users.users.${user} = {
      isSystemUser = true;
      group = group;
      description = "Task Manager service user";
      home = projectPath;
      extraGroups = [ "docker" ];
    };
    users.groups.${group} = { };

    networking.firewall.allowedTCPPorts = [
      publicPort
    ]
    ++ lib.optionals (!useHttpOnly) [
      80
      443
    ];

    systemd.tmpfiles.rules = [
      "d ${projectPath} 0755 ${user} ${group} -"
      "d ${secretsDir} 0700 ${user} ${group} -"
      "d ${logDir} 0750 ${user} ${group} -"
    ];

    # Sync code from Git
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

    # Create .env file for Docker
    systemd.services.task-manager-env-init = {
      description = "Initialize environment file for Task Manager Docker";
      wantedBy = [ "multi-user.target" ];
      after = [
        "systemd-tmpfiles-setup.service"
        "task-manager-git-sync.service"
      ];
      requires = [
        "systemd-tmpfiles-setup.service"
        "task-manager-git-sync.service"
      ];
      path = [ pkgs.coreutils ];

      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        User = user;
        Group = group;
      };

      script = ''
        set -e

        mkdir -p ${projectPath}

        cat > ${envFile} <<EOF
# Docker Environment Configuration
TASK_MANAGER_API_KEY=${apiKey}
EOF

        chmod 600 ${envFile}
        chown ${user}:${group} ${envFile}
        echo "Environment file initialized at ${envFile}"
      '';
    };

    # Main Docker Compose service
    systemd.services.task-manager-docker = {
      description = "Task Manager Docker Compose Stack";
      after = [
        "docker.service"
        "task-manager-git-sync.service"
        "task-manager-env-init.service"
        "network-online.target"
      ];
      wants = [ "network-online.target" ];
      requires = [
        "docker.service"
        "task-manager-git-sync.service"
        "task-manager-env-init.service"
      ];
      wantedBy = [ "multi-user.target" ];

      path = [
        pkgs.docker
        pkgs.docker-compose
      ];

      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        User = user;
        Group = group;
        WorkingDirectory = projectPath;

        # Stop timeout for graceful shutdown
        TimeoutStopSec = 60;
      };

      script = ''
        set -e

        if [ ! -f ${projectPath}/docker-compose.yml ]; then
          echo "Error: docker-compose.yml not found in ${projectPath}"
          exit 1
        fi

        if [ ! -f ${envFile} ]; then
          echo "Error: .env file not found"
          exit 1
        fi

        cd ${projectPath}

        # Override ports in docker-compose to avoid conflicts
        export DOCKER_FRONTEND_PORT=${toString dockerFrontendPort}
        export DOCKER_BACKEND_PORT=${toString dockerBackendPort}

        echo "Starting Docker Compose stack..."
        ${pkgs.docker-compose}/bin/docker-compose up -d --remove-orphans

        echo "Waiting for services to be healthy..."
        sleep 5

        echo "Docker Compose stack started successfully"
        ${pkgs.docker-compose}/bin/docker-compose ps
      '';

      preStop = ''
        cd ${projectPath}
        echo "Stopping Docker Compose stack..."
        ${pkgs.docker-compose}/bin/docker-compose down
      '';
    };

    # Update docker-compose.yml ports via override
    # Create docker-compose.override.yml dynamically
    systemd.services.task-manager-docker-compose-override = {
      description = "Create docker-compose.override.yml for port configuration";
      after = [ "task-manager-git-sync.service" ];
      requires = [ "task-manager-git-sync.service" ];
      wantedBy = [ "multi-user.target" ];
      before = [ "task-manager-docker.service" ];

      serviceConfig = {
        Type = "oneshot";
        RemainAfterExit = true;
        User = user;
        Group = group;
      };

      script = ''
        cat > ${projectPath}/docker-compose.override.yml <<EOF
version: '3.8'

services:
  backend:
    ports:
      - "${toString dockerBackendPort}:8000"
    environment:
      # Force logging to stdout for journald
      - PYTHONUNBUFFERED=1

  frontend:
    ports:
      - "${toString dockerFrontendPort}:80"
EOF

        chmod 644 ${projectPath}/docker-compose.override.yml
        echo "docker-compose.override.yml created"
      '';
    };

    # Reverse proxy configuration
    services.caddy = lib.mkIf (reverseProxy == "caddy") {
      enable = true;

      virtualHosts."${
        if useHttpOnly then "http://:${toString publicPort}" else "${domain}:${toString publicPort}"
      }" = {
        extraConfig = ''
          # Proxy everything to Docker frontend
          # Frontend nginx will handle /api routing internally
          reverse_proxy 127.0.0.1:${toString dockerFrontendPort}
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

        locations."/" = {
          proxyPass = "http://127.0.0.1:${toString dockerFrontendPort}";
          extraConfig = ''
            proxy_set_header Host $host;
            proxy_set_header X-Real-IP $remote_addr;
            proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
            proxy_set_header X-Forwarded-Proto $scheme;
          '';
        };
      };
    };

    # Fail2ban monitoring Docker logs
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
          # Monitor Docker container logs via journald
          backend = "systemd";
          maxretry = fail2banMaxRetry;
          findtime = fail2banFindTime;
          bantime = fail2banBanTime;
        };
      };
    };

    # Monitoring and management scripts
    environment.systemPackages = [
      (pkgs.writeScriptBin "task-manager-logs" ''
        #!${pkgs.bash}/bin/bash
        cd ${projectPath}
        ${pkgs.docker-compose}/bin/docker-compose logs -f "''${1:-backend}"
      '')

      (pkgs.writeScriptBin "task-manager-restart" ''
        #!${pkgs.bash}/bin/bash
        echo "Restarting Task Manager Docker stack..."
        sudo systemctl restart task-manager-docker
        echo "Restart complete. Check logs with: task-manager-logs"
      '')

      (pkgs.writeScriptBin "task-manager-status" ''
        #!${pkgs.bash}/bin/bash
        cd ${projectPath}
        echo "=== Docker Compose Status ==="
        ${pkgs.docker-compose}/bin/docker-compose ps
        echo ""
        echo "=== Systemd Service Status ==="
        systemctl status task-manager-docker --no-pager
      '')

      (pkgs.writeScriptBin "task-manager-update" ''
        #!${pkgs.bash}/bin/bash
        echo "Updating Task Manager from Git..."
        sudo systemctl restart task-manager-git-sync
        echo "Rebuilding and restarting Docker containers..."
        cd ${projectPath}
        ${pkgs.docker-compose}/bin/docker-compose up -d --build
        echo "Update complete!"
      '')

      (pkgs.writeScriptBin "task-manager-backup" ''
        #!${pkgs.bash}/bin/bash
        BACKUP_DIR="${projectPath}/manual-backups"
        mkdir -p "$BACKUP_DIR"
        TIMESTAMP=$(date +%Y%m%d_%H%M%S)

        echo "Creating backup of Docker volumes..."
        ${pkgs.docker}/bin/docker run --rm \
          -v task-manager-db:/data/db:ro \
          -v task-manager-backups:/data/backups:ro \
          -v task-manager-logs:/data/logs:ro \
          -v "$BACKUP_DIR":/backup \
          alpine tar czf "/backup/task-manager-backup-$TIMESTAMP.tar.gz" /data

        echo "Backup created: $BACKUP_DIR/task-manager-backup-$TIMESTAMP.tar.gz"
      '')
    ];
  };
}
