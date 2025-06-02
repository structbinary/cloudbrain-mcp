import shutil
from typing import List, Optional
import os
import yaml
import boto3
import base64
from botocore.signers import RequestSigner
from helm_mcp_server.utils.logger import logger


def get_dangerous_patterns() -> List[str]:
    """Get a list of dangerous patterns for command injection detection.

    Returns:
        List of dangerous patterns to check for
    """
    patterns = [
        '|', ';', '&', '&&', '||',  # Command chaining
        '>', '>>', '<',  # Redirection
        '`', '$(',  # Command substitution
        '--',  # Double dash options
        '/bin/', '/usr/bin/',  # Path references
        '../', './',  # Directory traversal
        # Unix/Linux specific dangerous patterns
        'sudo', 'chmod', 'chown', 'su', 'bash', 'sh', 'zsh',
        'curl', 'wget', 'ssh', 'scp', 'eval', 'source',
        # Windows specific dangerous patterns
        'cmd', 'powershell', 'pwsh', 'net', 'reg', 'runas',
        'del', 'rmdir', 'taskkill', 'sc', 'schtasks', 'wmic',
        '%SYSTEMROOT%', '%WINDIR%', '.bat', '.cmd', '.ps1',
    ]
    return patterns


def is_helm_installed() -> bool:
    """Check if the helm binary is available in the system PATH.

    Returns:
        True if helm is found, False otherwise
    """
    return shutil.which('helm') is not None


def check_for_dangerous_patterns(args: List[str], log_prefix: Optional[str] = None) -> Optional[str]:
    """Check a list of command arguments for dangerous patterns, with logging."""
    patterns = get_dangerous_patterns()
    # Log the command being checked
    logger.debug(f"{log_prefix or ''}Checking command for dangerous patterns: {args}")
    for arg in args:
        for pattern in patterns:
            if pattern == '--':
                if arg == '--':  # Only flag if the argument is exactly '--'
                    logger.warning(f"{log_prefix or ''}Dangerous pattern detected: '{pattern}' in arg: '{arg}' (full cmd: {args})")
                    return pattern
            else:
                if pattern in arg:
                    logger.warning(f"{log_prefix or ''}Dangerous pattern detected: '{pattern}' in arg: '{arg}' (full cmd: {args})")
                    return pattern
    return None


def get_kube_config(
    kubeconfig_path: Optional[str] = None,
    context_name: Optional[str] = None,
    eks_cluster_name: Optional[str] = None,
) -> dict:
    """
    Load Kubernetes configuration for a specific cluster/context in a production-ready, flexible way.

    Order of precedence:
    1. Explicit AWS EKS cluster (eks_cluster_name argument or AWS_EKS_CLUSTER_NAME env)
    2. Explicit kubeconfig path (kubeconfig_path argument or KUBECONFIG env)
    3. Explicit context name (context_name argument, used with kubeconfig)
    4. Default kubeconfig path (~/.kube/config)
    5. In-cluster service account (if running in a pod)

    Args:
        kubeconfig_path: Path to kubeconfig file to use (optional)
        context_name: Name of context to use from kubeconfig (optional)
        eks_cluster_name: Name of AWS EKS cluster to use (optional)

    Returns:
        Kubernetes config as a dict
    Raises:
        FileNotFoundError: If no kubeconfig or service account token is found
        Exception: For other errors (e.g., invalid YAML, AWS errors)
    """
    # 1. AWS EKS (IAM authentication)
    cluster_name = eks_cluster_name or os.environ.get('AWS_EKS_CLUSTER_NAME')
    if cluster_name:
        try:
            eks = boto3.client('eks')
            cluster_info = eks.describe_cluster(name=cluster_name)['cluster']
            endpoint = cluster_info['endpoint']
            ca_data = cluster_info['certificateAuthority']['data']
            session = boto3.session.Session()
            service_id = eks.meta.service_model.service_id
            signer = RequestSigner(
                service_id,
                session.region_name,
                'sts',
                'v4',
                session.get_credentials(),
                session.events,
            )
            params = {
                'method': 'GET',
                'url': f'https://sts.{session.region_name}.amazonaws.com/?Action=GetCallerIdentity&Version=2011-06-15',
                'body': {},
                'headers': {'x-k8s-aws-id': cluster_name},
                'context': {},
            }
            signed_url = signer.generate_presigned_url(params, region_name=session.region_name, expires_in=60, operation_name='')
            token = 'k8s-aws-v1.' + base64.urlsafe_b64encode(signed_url.encode('utf-8')).decode('utf-8').rstrip('=')
            return {
                'eks': True,
                'endpoint': endpoint,
                'ca_data': ca_data,
                'token': token,
                'cluster_name': cluster_name,
            }
        except Exception as e:
            raise Exception(f'Failed to load AWS EKS credentials: {e}')
    # 2. KUBECONFIG path (explicit or env)
    path = kubeconfig_path or os.environ.get('KUBECONFIG')
    if path:
        if not os.path.exists(path):
            raise FileNotFoundError(f'kubeconfig path {path} does not exist')
        with open(path, 'r') as f:
            kubeconfig = yaml.safe_load(f)
        # 3. Context name (explicit or current-context)
        if context_name:
            contexts = {c['name']: c for c in kubeconfig.get('contexts', [])}
            if context_name not in contexts:
                raise ValueError(f'Context {context_name} not found in kubeconfig {path}')
            kubeconfig['current-context'] = context_name
        return kubeconfig
    # 4. Default kubeconfig
    default_path = os.path.expanduser('~/.kube/config')
    if os.path.exists(default_path):
        with open(default_path, 'r') as f:
            kubeconfig = yaml.safe_load(f)
        if context_name:
            contexts = {c['name']: c for c in kubeconfig.get('contexts', [])}
            if context_name not in contexts:
                raise ValueError(f'Context {context_name} not found in default kubeconfig')
            kubeconfig['current-context'] = context_name
        return kubeconfig
    # 5. In-cluster service account
    service_account_token = '/var/run/secrets/kubernetes.io/serviceaccount/token'
    service_account_ca = '/var/run/secrets/kubernetes.io/serviceaccount/ca.crt'
    service_account_ns = '/var/run/secrets/kubernetes.io/serviceaccount/namespace'
    if os.path.exists(service_account_token) and os.path.exists(service_account_ca):
        with open(service_account_token, 'r') as f:
            token = f.read().strip()
        with open(service_account_ca, 'r') as f:
            ca_cert = f.read().strip()
        namespace = None
        if os.path.exists(service_account_ns):
            with open(service_account_ns, 'r') as f:
                namespace = f.read().strip()
        return {
            'in_cluster': True,
            'token': token,
            'ca_cert': ca_cert,
            'namespace': namespace,
            'server': os.environ.get('KUBERNETES_SERVICE_HOST', 'kubernetes.default.svc'),
            'port': os.environ.get('KUBERNETES_SERVICE_PORT', '443'),
        }
    raise FileNotFoundError('No kubeconfig found in AWS_EKS_CLUSTER_NAME, KUBECONFIG, ~/.kube/config, or in-cluster service account.') 