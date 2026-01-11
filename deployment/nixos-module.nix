# NixOS module for Task Manager API
# Usage: Import this in your configuration.nix

{ config, lib, pkgs, ... }:

with lib;

let
  cfg = config.services.task-manager;

  pythonEnv = pkgs.python3.withPackages (ps: with ps; [
    fastapi
    uvicorn
    sqlalchemy
    pydantic
  ]);

in {
  options.services.task-manager = {
    enable = mkEnableOption "Task Manager API service";

    apiKey = mkOption {
      type = types.str;
      description = "API key for authentication (use secrets management in production!)";
      default = "your-secret-key-change-me";
    };

    host = mkOption {
      type = types.str;
      description = "Host to bind to";
      default = "127.0.0.1";
    };

    port = mkOption {
      type = types.int;
      description = "Port to listen on";
      default = 8000;
    };

    dataDir = mkOption {
      type = types.str;
      description = "Directory for SQLite database";
      default = "/var/lib/task-manager";
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
  };

  config = mkIf cfg.enable {
    # Create user and group
    users.users.${cfg.user} = {
      isSystemUser = true;
      group = cfg.group;
      description = "Task Manager service user";
      home = cfg.dataDir;
    };

    users.groups.${cfg.group} = {};

    # Create directories
    systemd.tmpfiles.rules = [
      "d ${cfg.dataDir} 0750 ${cfg.user} ${cfg.group} -"
      "d ${cfg.logDir} 0750 ${cfg.user} ${cfg.group} -"
    ];

    # Systemd service
    systemd.services.task-manager = {
      description = "Task Manager API Service";
      after = [ "network.target" ];
      wantedBy = [ "multi-user.target" ];

      environment = {
        TASK_MANAGER_API_KEY = cfg.apiKey;
        TASK_MANAGER_LOG_DIR = cfg.logDir;
        PYTHONPATH = "/path/to/your/task-manager/repo";  # UPDATE THIS!
      };

      serviceConfig = {
        Type = "simple";
        User = cfg.user;
        Group = cfg.group;
        WorkingDirectory = cfg.dataDir;
        ExecStart = "${pythonEnv}/bin/uvicorn backend.main:app --host ${cfg.host} --port ${toString cfg.port}";
        Restart = "always";
        RestartSec = "10";

        # Security hardening
        NoNewPrivileges = true;
        PrivateTmp = true;
        ProtectSystem = "strict";
        ProtectHome = true;
        ReadWritePaths = [ cfg.logDir cfg.dataDir ];

        # Logging to journald (для fail2ban с backend=systemd)
        StandardOutput = "journal";
        StandardError = "journal";
        SyslogIdentifier = "task-manager";
      };
    };
  };
}
