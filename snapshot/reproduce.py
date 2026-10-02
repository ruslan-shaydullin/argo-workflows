#!/usr/bin/env python3
"""Disposable #17024 ordering experiment; stdlib, kubectl, preloaded controller image.

Creates one NEW namespaced installation; leaves resources/evidence and scales its
controller to zero on exit. Never edits Workflow status or Pod finalizers.
"""
import argparse
import datetime
import json
from pathlib import Path
import subprocess
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--kubeconfig', required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--namespace', required=True)
    parser.add_argument('--image', required=True)
    parser.add_argument('--expect', choices=['baseline-loss', 'candidate-capture'], required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--executor-image', default='quay.io/argoproj/argoexec@sha256:6aa5cf3452b12c8498eccc62455e460e94e6d092931932aa4dbda6bb1512036c')
    args = parser.parse_args()
    if not args.namespace.startswith('argo-17024-repro-'):
        parser.error('use a new namespace prefixed argo-17024-repro-')
    args.output.mkdir(mode=0o700, parents=True, exist_ok=False)
    role = args.source / 'manifests/namespace-install/workflow-controller-rbac/workflow-controller-role.yaml'
    if not role.is_file():
        parser.error('--source must be an Argo Workflows checkout')
    kubectl = ['kubectl', '--kubeconfig', args.kubeconfig]
    ns = args.namespace
    owned = False

    def call(command, payload=None, checked=True):
        result = subprocess.run(command, input=None if payload is None else json.dumps(payload), text=True, capture_output=True, timeout=180)
        with (args.output / 'commands.jsonl').open('a') as stream:
            stream.write(json.dumps({'at': datetime.datetime.now(datetime.timezone.utc).isoformat(), 'command': command,
                                     'exit': result.returncode, 'stdout': result.stdout, 'stderr': result.stderr}) + '\n')
        if checked and result.returncode:
            raise RuntimeError(result.stderr)
        return result

    def kube(*command, payload=None, checked=True):
        return call(kubectl + ['-n', ns, *command], payload, checked)

    def get(kind, name):
        response = kube('get', kind, name, '-o', 'json', '--ignore-not-found=true')
        return json.loads(response.stdout) if response.stdout.strip() else None

    def save(name, value):
        (args.output / (name + '.json')).write_text(json.dumps(value, indent=2) + '\n')

    def wait(description, predicate, timeout=240):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            value = predicate()
            if value:
                return value
            time.sleep(1)
        raise TimeoutError(description)

    def node(wf):
        return (wf or {}).get('status', {}).get('nodes', {}).get('capture-repro', {})

    def scale(replicas):
        kube('scale', 'deployment/workflow-controller', '--replicas=' + str(replicas))
        if not replicas:
            wait('controller stopped', lambda: not json.loads(kube('get', 'pods', '-l', 'app=workflow-controller', '-o', 'json').stdout)['items'])

    def workers(count):
        kube('patch', 'deployment/workflow-controller', '--type=json', '-p',
             json.dumps([{'op': 'replace', 'path': '/spec/template/spec/containers/0/args/2', 'value': '--workflow-workers=' + str(count)}]))

    result = {'status': 'INCONCLUSIVE', 'expected': args.expect, 'namespace': ns, 'image': args.image}
    try:
        # create fails if the namespace already exists; never adopt another installation.
        call(kubectl + ['create', 'namespace', ns])
        owned = True
        kube('apply', '-f', str(role))
        objects = [{'apiVersion': 'v1', 'kind': 'ServiceAccount', 'metadata': {'name': name}} for name in ['argo', 'workflow-runner']]
        objects.append({'apiVersion': 'rbac.authorization.k8s.io/v1', 'kind': 'Role', 'metadata': {'name': 'workflow-runner'},
                        'rules': [{'apiGroups': ['argoproj.io'], 'resources': ['workflowtaskresults'], 'verbs': ['create', 'patch']}]})
        for name, role_name in [('argo', 'argo-role'), ('workflow-runner', 'workflow-runner')]:
            objects.append({'apiVersion': 'rbac.authorization.k8s.io/v1', 'kind': 'RoleBinding', 'metadata': {'name': name},
                            'subjects': [{'kind': 'ServiceAccount', 'name': name, 'namespace': ns}],
                            'roleRef': {'kind': 'Role', 'name': role_name, 'apiGroup': 'rbac.authorization.k8s.io'}})
        objects.append({'apiVersion': 'v1', 'kind': 'ConfigMap', 'metadata': {'name': 'workflow-controller-configmap'}, 'data': {'config': 'instanceID: ' + ns + '\n'}})
        objects.append({'apiVersion': 'apps/v1', 'kind': 'Deployment', 'metadata': {'name': 'workflow-controller'}, 'spec': {
            'replicas': 1, 'strategy': {'type': 'Recreate'}, 'selector': {'matchLabels': {'app': 'workflow-controller'}},
            'template': {'metadata': {'labels': {'app': 'workflow-controller'}}, 'spec': {
                'serviceAccountName': 'argo', 'terminationGracePeriodSeconds': 1,
                'containers': [{'name': 'controller', 'image': args.image, 'imagePullPolicy': 'Never', 'command': ['workflow-controller'],
                                'args': ['--namespaced', '--namespace=' + ns, '--workflow-workers=2', '--executor-image=' + args.executor_image,
                                         '--executor-image-pull-policy=IfNotPresent', '--loglevel=info'],
                                'env': [{'name': 'ARGO_POD_STATUS_CAPTURE_FINALIZER', 'value': 'true'}, {'name': 'LEADER_ELECTION_DISABLE', 'value': 'true'}],
                                'resources': {'requests': {'cpu': '25m', 'memory': '64Mi'}, 'limits': {'memory': '512Mi'}}}]}}}})
        setup = {'apiVersion': 'v1', 'kind': 'List', 'items': objects}
        save('setup', setup)
        kube('apply', '-f', '-', payload=setup)
        kube('rollout', 'status', 'deployment/workflow-controller', '--timeout=120s')
        wf = {'apiVersion': 'argoproj.io/v1alpha1', 'kind': 'Workflow', 'metadata': {'name': 'capture-repro', 'labels': {'workflows.argoproj.io/controller-instanceid': ns}},
              'spec': {'serviceAccountName': 'workflow-runner', 'entrypoint': 'main', 'templates': [{'name': 'main', 'container': {
                  'image': 'busybox:1.37.0', 'command': ['sh', '-c'], 'args': ['sleep 60; echo capture-ok']}}]}}
        save('workflow-input', wf)
        kube('create', '-f', '-', payload=wf)
        wait('persisted Running', lambda: node(get('workflow', 'capture-repro')).get('phase') == 'Running')
        pods = json.loads(kube('get', 'pods', '-l', 'workflows.argoproj.io/workflow=capture-repro', '-o', 'json').stdout)['items']
        assert len(pods) == 1
        pod_name, uid = pods[0]['metadata']['name'], pods[0]['metadata']['uid']
        result['podUID'] = uid
        scale(0)
        wait('real successful Pod', lambda: get('pod', pod_name)['status'].get('phase') == 'Succeeded')
        pod = get('pod', pod_name)
        assert pod['metadata']['uid'] == uid and 'workflows.argoproj.io/status' in pod['metadata'].get('finalizers', [])
        assert all(c.get('state', {}).get('terminated', {}).get('exitCode') == 0 for c in pod['status']['containerStatuses'])
        save('completed-pod-before-delete', pod)
        save('workflow-before-delete', get('workflow', 'capture-repro'))
        transitions = [datetime.datetime.fromisoformat(c['lastTransitionTime'].replace('Z', '+00:00')) for c in pod['status'].get('conditions', [])]
        assert transitions
        wait('aged Pod conditions', lambda: (datetime.datetime.now(datetime.timezone.utc) - max(transitions)).total_seconds() >= 190, 220)
        kube('delete', 'pod', pod_name, '--wait=false')
        held = get('pod', pod_name)
        assert held['metadata']['uid'] == uid and held['metadata'].get('deletionTimestamp')
        save('pod-held-before-controller', held)
        workers(0)
        scale(1)
        kube('rollout', 'status', 'deployment/workflow-controller', '--timeout=120s')
        if args.expect == 'baseline-loss':
            wait('baseline Pod loss', lambda: get('pod', pod_name) is None, 90)
            assert node(get('workflow', 'capture-repro'))['phase'] == 'Running'
        else:
            deadline = time.monotonic() + 40
            while time.monotonic() < deadline:
                pod = get('pod', pod_name)
                assert pod and pod['metadata']['uid'] == uid and 'workflows.argoproj.io/status' in pod['metadata']['finalizers']
                current = node(get('workflow', 'capture-repro'))
                assert current['phase'] == 'Running' and not current.get('capturedPodUID')
                time.sleep(2)
            save('held-after-retry', pod)
        scale(0)
        workers(2)
        scale(1)
        wait('completed Workflow', lambda: get('workflow', 'capture-repro').get('status', {}).get('phase') in ['Succeeded', 'Failed', 'Error'])
        finished = get('workflow', 'capture-repro')
        save('workflow-final', finished)
        actual = node(finished)
        if args.expect == 'baseline-loss':
            assert actual['phase'] == 'Error' and 'pod deleted' in actual.get('message', '')
        else:
            assert actual['phase'] == 'Succeeded' and actual['capturedPodUID'] == uid and actual['taskResultSynced'] is True
            wait('candidate Pod cleaned', lambda: get('pod', pod_name) is None)
        result['status'] = 'PASS'
    except Exception as error:
        result['error'] = repr(error)
        raise
    finally:
        try:
            if owned and get('deployment', 'workflow-controller') is not None:
                kube('logs', 'deployment/workflow-controller', '--tail=300', checked=False)
                scale(0)
        except Exception as cleanup_error:
            result['cleanupError'] = repr(cleanup_error)
            result['status'] = 'INCONCLUSIVE'
        save('result', result)
        print(json.dumps(result, indent=2))
        if result.get('cleanupError'):
            raise RuntimeError('controller cleanup failed; inspect result.json')


if __name__ == '__main__':
    main()
