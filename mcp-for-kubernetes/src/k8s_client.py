# k8s_client.py — thin Kubernetes API client
# Handles pod status, failing pods, and recent events.
from kubernetes import client, config
from typing import Optional


class KubernetesClient:
    def __init__(self, in_cluster: bool = None):
        if in_cluster is None:
            # Auto-detect: if running inside a cluster, the service account token exists
            import os
            in_cluster = os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount/token")

        if in_cluster:
            config.load_incluster_config()
        else:
            config.load_kube_config()
        self.v1 = client.CoreV1Api()
        self.apps_v1 = client.AppsV1Api()

    def get_pod_status(self, namespace: str, pod_name: str) -> dict:
        pod = self.v1.read_namespaced_pod(name=pod_name, namespace=namespace)
        return {
            "name": pod.metadata.name,
            "namespace": pod.metadata.namespace,
            "phase": pod.status.phase,
            "conditions": [
                {"type": c.type, "status": c.status, "reason": c.reason}
                for c in (pod.status.conditions or [])
            ],
            "container_statuses": [
                {
                    "name": cs.name,
                    "ready": cs.ready,
                    "restart_count": cs.restart_count,
                    "state": str(cs.state)
                }
                for cs in (pod.status.container_statuses or [])
            ]
        }

    def list_failing_pods(self, namespace: Optional[str] = None) -> list[dict]:
        # AUTHOR: In large clusters, add field_selector or label_selector
        # to avoid expensive full-cluster list calls.
        if namespace:
            pods = self.v1.list_namespaced_pod(namespace=namespace)
        else:
            pods = self.v1.list_pod_for_all_namespaces()

        failing = []
        for pod in pods.items:
            if pod.status.phase not in ("Running", "Succeeded"):
                failing.append({
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "phase": pod.status.phase,
                    "reason": pod.status.reason
                })
        return failing

    def get_recent_events(self, namespace: str, limit: int = 20) -> list[dict]:
        events = self.v1.list_namespaced_event(
            namespace=namespace,
            limit=limit
        )
        return [
            {
                "type": e.type,
                "reason": e.reason,
                "message": e.message,
                "involved_object": e.involved_object.name,
                "count": e.count,
                "last_timestamp": str(e.last_timestamp)
            }
            for e in sorted(
                events.items,
                key=lambda x: x.last_timestamp or "",
                reverse=True
            )
        ]
