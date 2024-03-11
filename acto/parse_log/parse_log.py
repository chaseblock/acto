import json
import logging
import re

from acto.common import get_thread_logger

klog_regex = r'^\s*'
klog_regex += r'(\w)'  # group 1: level
# group 2-7: timestamp
klog_regex += r'(\d{2})(\d{2})\s(\d{2}):(\d{2}):(\d{2})\.(\d{6})'
klog_regex += r'\s+'
klog_regex += r'(\d+)'  # group 8
klog_regex += r'\s'
klog_regex += r'(.+):'  # group 9: filename
klog_regex += r'(\d+)'  # group 10: lineno
klog_regex += r'\]\s'
klog_regex += r'(.*?)'  # group 11: message
klog_regex += r'\s*$'

logr_regex = r'^\s*'
# group 1: timestamp
logr_regex += r'(\d{4}\-\d{2}\-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z)'
logr_regex += r'\s+([A-Z]+)'  # group 2: level
logr_regex += r'\s+(\S+)'  # group 3: source
logr_regex += r'\s+(.*?)'  # group 4: message
logr_regex += r'\s*$'

# 1.6599427639039357e+09	INFO	controllers.CassandraDatacenter	Reconcile loop completed	{"cassandradatacenter": "cass-operator/test-cluster", "requestNamespace": "cass-operator", "requestName": "test-cluster", "loopID": "be419d0c-c7d0-4dfa-8596-af94ea15d4f6", "duration": 0.253729569}
logr_special_regex = r'^\s*'
logr_special_regex += r'(\d{1}\.\d+e\+\d{2})'  # group 1: timestamp
logr_special_regex += r'\s+([A-Z]+)'  # group 2: level
logr_special_regex += r'\s+(\S+)'  # group 3: source
logr_special_regex += r'\s+(.*?)'  # group 4: message
logr_special_regex += r'\s*$'

# time="2022-08-08T03:21:28Z" level=debug msg="Sentinel is not monitoring the correct master, changing..." src="checker.go:175"
# time="2022-08-08T03:21:56Z" level=info msg="deployment updated" deployment=rfs-test-cluster namespace=acto-namespace service=k8s.deployment src="deployment.go:102"
logrus_regex = r'^\s*'
# group 1: timestamp
logrus_regex += r'time="(\d{4}\-\d{2}\-\d{2}T\d{2}:\d{2}:\d{2}Z)"'
logrus_regex += r'\s+level=([a-z]+)'  # group 2: level
logrus_regex += r'\s+msg="(.*?[^\\])"'  # group 3: message
logrus_regex += r'.*'
logrus_regex += r'\s+(src="(.*?)")?'  # group 4: src
logrus_regex += r'\s*$'
# this is semi-auto generated by copilot, holy moly

# This one is similar to logr_special_regex and logrus_regex, but with some differences
# 2024-03-05T10:07:17Z	ERROR	GrafanaReconciler	reconciler error in stage	{"controller": "grafana", "controllerGroup": "grafana.integreatly.org", "controllerKind": "Grafana", "Grafana": {"name":"test-cluster","namespace":"grafana"}, "namespace": "grafana", "name": "test-cluster", "reconcileID": "5aa39e3e-d5d3-47fc-848d-c3d15dfbcc3d", "stage": "deployment", "error": "Deployment.apps \"test-cluster-deployment\" is invalid: [spec.template.spec.containers[0].image: Required value, spec.template.spec.affinity.podAntiAffinity.requiredDuringSchedulingIgnoredDuringExecution[0].topologyKey: Required value: can not be empty, spec.template.spec.affinity.podAntiAffinity.requiredDuringSchedulingIgnoredDuringExecution[0].topologyKey: Invalid value: \"\": name part must be non-empty, spec.template.spec.affinity.podAntiAffinity.requiredDuringSchedulingIgnoredDuringExecution[0].topologyKey: Invalid value: \"\": name part must consist of alphanumeric characters, '-', '_' or '.', and must start and end with an alphanumeric character (e.g. 'MyName',  or 'my.name',  or '123-abc', regex used for validation is '([A-Za-z0-9][-A-Za-z0-9_.]*)?[A-Za-z0-9]')]"}
grafana_logr_regex  = r'^\s*'
grafana_logr_regex += r'(\d{4}\-\d{2}\-\d{2}T\d{2}:\d{2}:\d{2}Z)' # Group 1: timestamp
grafana_logr_regex += r'\s+([A-Z]+)'                              # Group 2: level
grafana_logr_regex += r'\s+(\S+)'                                 # Group 3: Source
grafana_logr_regex += r'\s+(.*?)'                                 # Group 4: Message
grafana_logr_regex += r'\s*$'                                     # Take up any remaining whitespace

def parse_log(line: str) -> dict:
    '''Try to parse the log line with some predefined format

    Currently only support three formats:
    - klog
    - logr
    - json

    Returns:
        a dict containing 'level' and 'message'
        'level' will always be a lowercase string
    '''
    logger = get_thread_logger(with_prefix=True)

    log_line = {}
    if re.search(klog_regex, line) != None:
        # log is in klog format
        match = re.search(klog_regex, line)
        if match.group(1) == 'E':
            log_line['level'] = 'error'
        elif match.group(1) == 'I':
            log_line['level'] = 'info'
        elif match.group(1) == 'W':
            log_line['level'] = 'warn'
        elif match.group(1) == 'F':
            log_line['level'] = 'fatal'

        log_line['msg'] = match.group(11)
    elif re.search(logr_regex, line) != None:
        # log is in logr format
        match = re.search(logr_regex, line)
        log_line['level'] = match.group(2).lower()
        log_line['msg'] = match.group(4)
    elif re.search(logr_special_regex, line) != None:
        # log is in logr special format
        match = re.search(logr_special_regex, line)
        log_line['level'] = match.group(2).lower()
        log_line['msg'] = match.group(4)
    elif re.search(logrus_regex, line) != None:
        # log is in logrus format
        match = re.search(logrus_regex, line)
        log_line['level'] = match.group(2)
        log_line['msg'] = match.group(3)
    elif re.search(grafana_logr_regex, line) != None:
        match = re.search(grafana_logr_regex, line)
        log_line['level'] = match.group(2).lower()
        log_line['msg'] = match.group(4)
    else:
        try:
            log_line = json.loads(line)
            if 'level' not in log_line:
                log_line['level'] = log_line['severity']

                del log_line['severity']
            log_line['level'] = log_line['level'].lower()
        except Exception as e:
            logger.debug(f"parse_log() cannot parse line {line} due to {e}")
            pass

    return log_line


if __name__ == '__main__':
    # line = '  	Ports: []v1.ServicePort{'
    # line = 'E0714 23:11:19.386396       1 pd_failover.go:70] PD failover replicas (0) reaches the limit (0), skip failover'
    # line = '{"level":"error","ts":1655678404.9488907,"logger":"controller-runtime.injectors-warning","msg":"Injectors are deprecated, and will be removed in v0.10.x"}'

    # line = 'time="2022-08-08T03:21:56Z" level=info msg="deployment updated" deployment=rfs-test-cluster namespace=acto-namespace service=k8s.deployment src="deployment.go:102"'
    # print(logrus_regex)
    # print(parse_log(line)['msg'])

    with open('testrun-2022-08-10-15-59/trial-01-0000/operator-0.log', 'r') as f:
        for line in f.readlines():
            print(f"Parsing log: {line}")

            if parse_log(line) == {} or parse_log(line)['level'].lower() != 'error' and parse_log(line)['level'].lower() != 'fatal':
                print(f'Test passed: {line} {parse_log(line)}')
            else:
                print(f"Message Raw: {line}, Parsed {parse_log(line)}")
                break
