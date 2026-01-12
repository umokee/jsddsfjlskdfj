# Caddy Layer4 SNI Router для Task Manager + Sing-box
# Один Caddy роутит по SNI на порту 443

{
  pkgs,
  lib,
  helpers,
  ...
}:

let
  enable = helpers.hasIn "services" "caddy-sni-router";

  # Настройки
  taskManagerDomain = "tasks.umkcloud.xyz";
  taskManagerBackend = "127.0.0.1:8000";
  taskManagerFrontend = "/var/lib/task-manager/frontend/dist";

  singboxBackend = "127.0.0.1:8444";  # sing-box будет слушать здесь

  # Caddy с layer4 плагином
  caddyWithLayer4 = pkgs.caddy.override {
    externalPlugins = [
      {
        name = "layer4";
        repo = "github.com/mholt/caddy-l4";
        version = "0a280e96e5a51fd6f7bb51d47a68f7ce6dd72cf5";
      }
    ];
    vendorHash = "sha256-VeZdHmJ99TqQbWwcCUELGk0dlTa7UNjhGPILrGa9xHY=";
  };

in
{
  config = lib.mkIf enable {
    # Переопределить Caddy на версию с layer4
    services.caddy.package = caddyWithLayer4;

    services.caddy = {
      enable = true;

      # Layer4 конфигурация для SNI routing
      globalConfig = ''
        layer4 {
          :443 {
            @tasks tls sni ${taskManagerDomain}
            route @tasks {
              proxy {
                upstream localhost:8889
              }
            }

            route {
              proxy {
                upstream ${singboxBackend}
              }
            }
          }
        }
      '';

      # HTTP сервер для task manager (внутренний)
      virtualHosts."${taskManagerDomain}" = {
        serverAliases = [ ];
        extraConfig = ''
          bind 127.0.0.1:8889

          handle /api/* {
            reverse_proxy ${taskManagerBackend}
          }

          handle {
            root * ${taskManagerFrontend}
            try_files {path} /index.html
            file_server
          }
        '';
      };
    };

    networking.firewall.allowedTCPPorts = [ 443 ];
  };
}
