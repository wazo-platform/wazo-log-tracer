#!/usr/bin/python3

import argparse
import csv
import json
import re
import sys
import urllib.parse

MAGIC_REGEX = (
    ".*?(GET|HEAD|POST|PUT|OPTIONS|DELETE|PATCH) (\S+) "
    'HTTP/\d+\.\d+" (\d+) \d+ ".*?" "(.*?)" "(.*?)" \d+ '
    "(\d+\.\d+) (\d+\.\d+) .*"
)


class Record:
    def __init__(
        self,
        id,
        method,
        uri,
        status,
        user_agent,
        service,
        record_time,
        request_start,
        request_duration,
        record_type,
    ):
        self.id = id
        self.method = method
        self.uri = uri
        self.status = status
        self.user_agent = user_agent
        self.service = service
        self.record_time = record_time
        self.request_start = request_start
        self.request_duration = request_duration
        self.type = record_type


def format_uri(url):
    return re.sub(r"(\w+)-\w+-\w+-\w+-\w+", r"\1", url)


def format_user_agent(user_agent):
    return user_agent.split()[0]


def parse_logs(input):
    records = []

    id = 1
    for log in input.readlines():
        m = re.search(MAGIC_REGEX, log)
        (
            method,
            uri,
            status,
            user_agent,
            service,
            log_time,
            request_duration,
        ) = m.groups()
        request_duration = float(request_duration)
        log_time = float(log_time)
        status = int(status)
        request_start = log_time - request_duration
        record = Record(
            id,
            method,
            uri,
            status,
            user_agent,
            service,
            request_start,
            request_start,
            request_duration,
            "request",
        )
        records.append(record)
        record = Record(
            id,
            method,
            uri,
            status,
            user_agent,
            service,
            log_time,
            request_start,
            request_duration,
            "response",
        )
        records.append(record)
        id = id + 1

    return records


def output_uml(records, output):
    records.sort(key=lambda r: r.record_time)

    output.write("@startuml\n")

    for record in records:
        if record.type == "request":
            output.write(
                '"%s" -[#red]> "%s": %s %d %s ( <b>%d</b> Start: %d ms)\n'
                % (
                    format_user_agent(record.user_agent),
                    record.service,
                    record.method,
                    record.status,
                    format_uri(record.uri),
                    len(records) / 2 - record.id + 1,
                    (record.request_start - records[0].request_start) * 1000,
                )
            )
        else:
            output.write(
                '"%s" <-[#blue]- "%s": %s %d %s ( <b>%d</b> Duration: %d ms)\n'
                % (
                    format_user_agent(record.user_agent),
                    record.service,
                    record.method,
                    record.status,
                    format_uri(record.uri),
                    len(records) / 2 - record.id + 1,
                    record.request_duration * 1000,
                )
            )

    output.write("@enduml\n")


def output_csv(records, output):
    csv_writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL)

    csv_writer.writerow(
        [
            "ID",
            "Method",
            "Path",
            "Query",
            "Status",
            "User Agent",
            "Service",
            "Request start",
            "Duration",
        ]
    )
    for record in records:
        if record.type == "request":
            result = urllib.parse.urlparse(record.uri)
            csv_writer.writerow(
                [
                    record.id,
                    record.method,
                    result.path,
                    result.query,
                    record.status,
                    record.user_agent,
                    record.service,
                    record.request_start,
                    record.request_duration,
                ]
            )


def output_stats(records):
    records.sort(key=lambda r: r.record_time)

    status, calls, times = dict(), dict(), dict()

    for record in records:
        status[record.status] = status.get(record.status, 0) + 1

        key = "%s %s" % (record.method, record.service)
        calls[key] = calls.get(key, 0) + 1
        times[key] = times.get(key, 0) + record.request_duration

    stats = {
        "status": status,
        "calls": calls,
        "times": times,
        "duration": records[-1].record_time - records[0].record_time,
    }

    print(json.dumps(stats, indent=4, sort_keys=True))


def main(input, output, format):
    records = parse_logs(input)

    if format == "uml":
        output_uml(records, output)
    elif format == "csv":
        output_csv(records, output)
    elif format == "stats":
        output_stats(records)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--format", default="uml",
                        help="output format (csv, uml, stats)")
    parser.add_argument("--output", default="-",
                        help="output file (defaults to standard output)")
    parser.add_argument("--input", default="-",
                        help="input file (defaults to standard input)")
    args = parser.parse_args()

    if args.input == "-":
        input_file = sys.stdin
    else:
        input_file = open(args.input)

    if args.output == "-":
        output_file = sys.stdout
    else:
        output_file = open(args.output, "w", newline="")

    main(input_file, output_file, args.format)