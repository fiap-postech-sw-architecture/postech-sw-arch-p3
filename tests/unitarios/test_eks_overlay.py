from pathlib import Path

import yaml

ROOT = Path(__file__).parents[2]


def test_overlay_eks_usa_nlb_interno() -> None:
    patch = yaml.safe_load(
        (ROOT / "k8s/overlays/eks/patch-api-service.yaml").read_text()
    )
    annotations = patch["metadata"]["annotations"]

    assert annotations["service.beta.kubernetes.io/aws-load-balancer-type"] == "nlb"
    assert (
        annotations["service.beta.kubernetes.io/aws-load-balancer-internal"] == "true"
    )
    assert (
        annotations[
            "service.beta.kubernetes.io/"
            "aws-load-balancer-cross-zone-load-balancing-enabled"
        ]
        == "true"
    )
    assert patch["spec"]["type"] == "LoadBalancer"


def test_cd_valida_api_por_port_forward() -> None:
    workflow = (ROOT / ".github/workflows/cd.yml").read_text()

    assert "port-forward service/pytstop-api 18000:8000" in workflow
    assert "curl --fail --silent --max-time 5" in workflow
    assert "http://127.0.0.1:18000/api/v1/saude" in workflow
    assert "status.loadBalancer.ingress" not in workflow
