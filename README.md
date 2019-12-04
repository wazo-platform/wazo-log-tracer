# Tools to help analyzing Wazo service logs

## wazo-log-tracer

This tool aims at showing the interactions between Wazo services.
It parses nginx logs to produce a sequence diagrams of all HTTP calls.

Example:

[Example sequence diagram](example.png)

### Setting up

* Edit nginx config for log formatting. In `/etc/nginx/sites-available/wazo`:

  * Add the following:
    ```
    log_format main
      '$remote_addr - $remote_user [$time_local] "$request" '
      '$status $body_bytes_sent "$http_referer" "$http_user_agent" "$sent_http_x_powered_by" '
      '$request_length $msec $request_time $upstream_addr '
      '$upstream_response_length $upstream_response_time $upstream_status';
    ```

* Add a header in the response for each service: In `/etc/nginx/locations/https-enabled/<service name>`
  ```
  add_header          X-Powered-By        <service name> always;
  ```
* Reload nginx: `systemctl reload nginx`
* Redirect all HTTP calls to nginx:
  * Create `/etc/wazo.yml`:
    ```
    amid:
      port: 443
      prefix: /api/amid
      verify_certificate: false
    auth:
      port: 443
      timeout: 30
      prefix: /api/auth
      verify_certificate: false
    call-logd:
      port: 443
      prefix: /api/call-logd
      verify_certificate: false
    confd:
      port: 443
      prefix: /api/confd
      verify_certificate: false
    dird:
      port: 443
      prefix: /api/dird
      verify_certificate: false
    plugind:
      port: 443
      prefix: /api/plugind
      verify_certificate: false
    provd:
      port: 443
      prefix: /api/provd
      verify_certificate: false
    webhookd:
      port: 443
      prefix: /api/webhookd
      verify_certificate: false
    ```

  * Apply it to all Wazo services:
    ```
    for service in /etc/wazo-*
    do
        sudo ln -s /etc/wazo.yml $service/conf.d/wazo-log-tracer.yml
    done
    ```
* Patch `wazo-lib-rest-client`: 
  ```
  patch -p1 -d /usr/lib/python3/dist-packages < wazo-lib-rest-client-user-agent.patch
  patch -p1 -d /usr/lib/python2.7/dist-packages < wazo-lib-rest-client-user-agent.patch
  ```
* Restart services: `wazo-service restart`

### Usage

* Capture nginx logs in `/var/log/nginx/wazo.access.log`
* You can use `logrotate -f /etc/logrotate.d/nginx` to purge the log file
* Use it: `wazo-log-tracer wazo.access.log wazo.puml`
* Generate PNG file `wazo.png`: `plantuml wazo.puml`

### Advanced usage

* Use max-connections=1 in Firefox to see sequential calls

* Use a spreadsheet to analyse which requests are the more costly: the ones initiated from the browser which are the longest. Then analyse them in the call graph.

## extractor.py

This tool re arrage Wazo service logs in order to extract
backtraces and provide a single file for request/response that
can be analyze with goaccess.

```
python extractor.py wazo-auth.log*
```

This command generated 3 files:

* wazo-auth-nobt.log: log file with all the backtraces removed
* wazo-auth-bt.log: log file with only the backtraces
* wazo-auth-req.log: log file with request and response merged, can be analyzed with goaccess

## detokenize.py

Replace tokens from the log by a unique placeholder. This can be applied before goaccess
analysis.

```
cat wazo-auth-req.log | python detokenize.py > detokenized.log
```

## mkgoaccess

This short shell script call goaccess with the required format to read *-req.log" files

```
mkgoaccess wazo-auth-req.log
```

or 

```
mkgoaccess detokenized.log
```
