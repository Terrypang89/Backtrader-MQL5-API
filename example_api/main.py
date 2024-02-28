from src import try_import

try_import("pyfiglet")
try_import("rich")

import pyfiglet
import json
import time
import os
import logging

from rich import print as cprint
from rich import traceback
from datetime import datetime, timezone
from queue import Queue
# from bs4 import BeautifulSoup

# from . import EmailListener
from src import config, send_post_request, StoppableThread
from src import log , create_logger
# from src import project_main_directory
from src import event_subscribe, event_unsubscribe, event_post
# from src import plan_to_run_run_at

traceback.install()

# ---------------* Config *---------------
mode_traditional = config.get("mode_traditional", True)

email_address = config.get("email_address")
login_password = config.get("login_password")
imap_server_address = config.get("imap_server_address")
imap_server_port = config.get("imap_server_port")
imap_auto_reconnect = config.get("imap_auto_reconnect")
imap_auto_reconnect_wait = config.get("imap_auto_reconnect_wait")

ngrok_auth_token = config.get("ngrok_auth_token")

webhook_urls = config.get("webhook_urls")

discord_log = config.get("discord_log")
discord_webhook_url = config.get("discord_webhook_url")

log_with_colors = config.get("log_color")
log_with_time_zone = config.get("log_time_zone")
save_log = config.get("log_save")
log_with_full_colors = config.get("log_full_color")

config_version = config.get("config_version")

tradingview_alert_email_address = ["noreply@tradingview.com"]

retry_after_header = "Retry-After"

# ---------------* Main *---------------
__version__ = "2.6.3"
expect_config_version = "1.0.0"
github_config_toml_url = "https://github.com/soranoo/TradingView-Free-Webhook-Alerts/blob/main/config.example.toml"

if not mode_traditional:
    try_import("pyngrok")
    from pyngrok import ngrok, conf as ngrok_conf
    from . import api_server_start

class NgrokSignalRedirect:
    class _EventID:
        API_PORT = "api-port"
        API_REV = "api-rev"
    
    
    def on_data_received(self, data:dict):
        print(f"on_data_received data = {data}\n")
        if not isinstance(data, dict):
            log.info(f"Incorrect data({data}) format received, SKIP.")
            return
        from_address = data.get("from")
        email_subject = data.get("subject")
        email_content = data.get("content")
        receive_datetime = data.get("receive_datetime")
        # print(receive_datetime)

        # validate the data
        # if not from_address or not email_subject or not email_content or not receive_datetime:
        #     log.error(f"Received data is not valid, data: {data}")
        #     return
        # elif from_address not in tradingview_alert_email_address:
        #     log.info(f"Email from {from_address} is not from TradingView, SKIP.")
        #     return         

        log.info(f"Sending webhook alert<{email_subject}>, content: {email_content}")
        try:
            send_webhook(email_content)
            log.info(f"The whole process taken .\n")
        except Exception as err:
            log.error(f"Sent webhook failed, reason: {err}")
        
    def setup_ngrok(self, port=int):
        log.info("Setting up ngrok...")
        ngrok.set_auth_token(ngrok_auth_token)
        ngrok_conf.get_default().log_event_callback = None # mute ngrok log
        http_tunnel = ngrok.connect(port, "http")
        log.info(f"Your ngrok URL: {http_tunnel.public_url}")
        event_unsubscribe(self._EventID.API_PORT, self.setup_ngrok)
        
    def setup_api_server(self):
        thread = StoppableThread(target=api_server_start, args=(self._EventID.API_PORT,))
        thread.start()
        
    def main(self):
        if not ngrok_auth_token:
            log.error("Missing ngrok auth token, please set it in the config file.")
            shutdown()
        event_subscribe(self._EventID.API_PORT, self.setup_ngrok)
        event_subscribe(self._EventID.API_REV, self.on_data_received)
        thread = StoppableThread(target=api_server_start, args=(self._EventID.API_PORT, self._EventID.API_REV))
        thread.start()
        thread.join()

def shutdown(seconds:float = 10):
    log.warning(f"The program will shut down after {seconds}s...")
    time.sleep(seconds)
    log.thread.stop()
    exit()

def send_webhook(payload:str or dict):
    headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11"
        }
    for webhook_url in webhook_urls:
        res = send_post_request(webhook_url, payload, headers)
        if res.status_code in [200, 201, 202, 203, 204]:
            log.ok(f"Sent webhook to {webhook_url} successfully, response code: {res.status_code}")
        elif retry_after := res.headers.get("Retry-After"):
            if res.status_code == 429:
                log.warning(f"Sent webhook to {webhook_url} failed, response code: {res.status_code}, Content: {payload}, Retry-After header({retry_after_header}) found, auto retry after {retry_after}s...")
                plan_to_run_run_at(time.time() + float(retry_after), send_webhook, payload)
                continue
            log.error(f"Sent webhook to {webhook_url} failed, response code: {res.status_code}, Content: {payload}.")

def main():
    log.debug(f"Traditional mode: {mode_traditional}")
    create_logger(
        save_log=save_log, color_print=log_with_colors,
        print_log_msg_color=log_with_full_colors,
        included_timezone=log_with_time_zone,
        log_level=logging.DEBUG, rebuild_mode=True,
        rebuild_logger=log
    )
    # if discord_log:
    #     log.addHandler(DiscordLogHandler())
    if mode_traditional:
        EmailSignalExtraction().main()
    else:
        NgrokSignalRedirect().main()

if __name__ == "__main__":
    # welcome message
    cprint(pyfiglet.figlet_format("TradingView\nFree Webhook"))
    # startup check
    print(f"Version: {__version__}  |  Config Version: {config_version}")
    if(config_version != expect_config_version):
        log.error(f"The config file is outdated. Please update it to the latest version. (visit {github_config_toml_url})")
        shutdown()
    main()