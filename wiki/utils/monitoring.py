from datetime import datetime
import json
from zoneinfo import ZoneInfo
import redis

def get_aws_log_data(request=None):
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    reports = [
        "aws_compute_resource_usage",
        "aws_cpucredit_balance",
        "valgalinn_access_log_requests_total",
        "valgalinn_access_log_requests_403",
        "valgalinn_access_log_requests_bots"
    ]
    aws_data = {}
    for report in reports:
        if report in ["aws_compute_resource_usage", "aws_cpucredit_balance"]:
            data = json.loads(r.get(report))
            aws_data[report] = {
                str(int(el['Timestamp'])): el
                for el
                in data
            }
        else:
            aws_data[report] = json.loads(r.get(report))

    monitoring_data = []
    AWS_CPUCREDIT_BALANCE_MAX = 576

    for timestamp in sorted(aws_data["aws_compute_resource_usage"].keys(), reverse=True):
        dt_local = datetime.fromtimestamp(int(timestamp) / 1000).astimezone(ZoneInfo('Europe/Tallinn')).isoformat()

        try:
            aws_compute_resource_usage = aws_data["aws_compute_resource_usage"][timestamp]['Average']
        except:
            aws_compute_resource_usage = None

        try:
            aws_cpucredit_balance = aws_data["aws_cpucredit_balance"][timestamp][
                                        'Average'] / AWS_CPUCREDIT_BALANCE_MAX * 100
        except:
            aws_cpucredit_balance = None

        try:
            valgalinn_access_log_requests_total = aws_data["valgalinn_access_log_requests_total"][timestamp]['ip']
        except:
            valgalinn_access_log_requests_total = None

        try:
            valgalinn_access_log_requests_403 = aws_data["valgalinn_access_log_requests_403"][timestamp]['ip']
        except:
            valgalinn_access_log_requests_403 = None

        try:
            valgalinn_access_log_requests_bots = aws_data["valgalinn_access_log_requests_bots"][timestamp]['ip']
        except:
            valgalinn_access_log_requests_bots = None

        monitoring_data.append(
            [
                dt_local,
                aws_compute_resource_usage,
                aws_cpucredit_balance,
                valgalinn_access_log_requests_total,
                valgalinn_access_log_requests_403,
                valgalinn_access_log_requests_bots,
            ]
        )
    return monitoring_data

def get_aws_restarts_data(request=None):
    r = redis.Redis(host='localhost', port=6379, decode_responses=True)
    report = 'restarts_from_journal'
    data = json.loads(r.get(report))
    aws_data = {}
    aws_data[report] = {
        el: el
        for el
        in data
    }
    return aws_data