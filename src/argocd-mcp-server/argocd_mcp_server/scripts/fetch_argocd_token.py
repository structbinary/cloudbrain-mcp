import os
import sys
import json
import logging
import requests
from typing import Optional, Dict, Any, List
from urllib.parse import urljoin
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ArgoCDTokenFetcher:
    """Helper class to fetch ArgoCD authentication token and perform basic CRUD operations."""
    
    def __init__(self, server_url: str, username: str, password: str, verify_tls: bool = True):
        """
        Initialize the ArgoCD token fetcher.
        
        Args:
            server_url (str): ArgoCD server URL (e.g., https://argocd.example.com)
            username (str): ArgoCD username
            password (str): ArgoCD password
            verify_tls (bool): Whether to verify TLS certificates (default: True)
        """
        self.server_url = server_url.rstrip('/')
        self.username = username
        self.password = password
        self.verify_tls = verify_tls
        self.session = requests.Session()
        self.token = None
        
    def fetch_token(self) -> Optional[str]:
        """
        Fetch authentication token from ArgoCD server.
        
        Returns:
            Optional[str]: JWT token if successful, None otherwise
            
        Raises:
            requests.exceptions.RequestException: If the request fails
            ValueError: If the response is invalid
        """
        try:
            session_url = urljoin(self.server_url, '/api/v1/session')
            payload = {
                'username': self.username,
                'password': self.password
            }
            
            logger.info(f"Attempting to fetch token from {session_url}")
            response = self.session.post(
                session_url,
                json=payload,
                verify=self.verify_tls,
                timeout=30  # 30 seconds timeout
            )
            response.raise_for_status()
            data = response.json()
            if 'token' not in data:
                raise ValueError("Token not found in response")
                
            self.token = data['token']
            logger.info("Successfully fetched ArgoCD token")
            return self.token
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch token: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise
        except (KeyError, json.JSONDecodeError) as e:
            logger.error(f"Invalid response format: {str(e)}")
            raise ValueError(f"Invalid response format: {str(e)}")
            
    def validate_token(self, token: str) -> bool:
        """
        Validate the fetched token by making a test API call.
        
        Args:
            token (str): JWT token to validate
            
        Returns:
            bool: True if token is valid, False otherwise
        """
        try:
            test_url = urljoin(self.server_url, '/api/v1/applications')
            
            headers = {
                'Authorization': f'Bearer {token}'
            }
            response = self.session.get(
                test_url,
                headers=headers,
                verify=self.verify_tls,
                timeout=30
            )
            
            response.raise_for_status()
            return True
            
        except requests.exceptions.RequestException:
            return False

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with authentication token."""
        if not self.token:
            raise ValueError("No token available. Please fetch token first.")
        return {
            'Authorization': f'Bearer {self.token}',
            'Content-Type': 'application/json'
        }

    def list_applications(self, project: Optional[str] = None, namespace: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        List all ArgoCD applications with optional filtering.
        
        Args:
            project (str, optional): Filter by project name
            namespace (str, optional): Filter by namespace
            
        Returns:
            List[Dict[str, Any]]: List of applications
            
        Raises:
            requests.exceptions.RequestException: If the request fails
            ValueError: If no token is available
        """
        try:
            url = urljoin(self.server_url, '/api/v1/applications')
            params = {}
            if project:
                params['project'] = project
            if namespace:
                params['namespace'] = namespace

            response = self.session.get(
                url,
                headers=self._get_headers(),
                params=params,
                verify=self.verify_tls,
                timeout=30
            )
            response.raise_for_status()
            
            # Parse response and handle potential None values
            data = response.json()
            if not isinstance(data, dict):
                logger.warning(f"Unexpected response format: {data}")
                return []
                
            items = data.get('items')
            if items is None:
                logger.warning("No 'items' field in response")
                return []
                
            if not isinstance(items, list):
                logger.warning(f"Expected list of items, got {type(items)}")
                return []
                
            return items
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list applications: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            return []
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse response JSON: {str(e)}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error in list_applications: {str(e)}")
            return []

    def get_application(self, name: str) -> Dict[str, Any]:
        """
        Get details of a specific ArgoCD application.
        
        Args:
            name (str): Name of the application
            
        Returns:
            Dict[str, Any]: Application details
            
        Raises:
            requests.exceptions.RequestException: If the request fails
            ValueError: If no token is available
        """
        try:
            url = urljoin(self.server_url, f'/api/v1/applications/{name}')
            response = self.session.get(
                url,
                headers=self._get_headers(),
                verify=self.verify_tls,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get application {name}: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise

    def create_application(self, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new ArgoCD application.
        
        Args:
            application_data (Dict[str, Any]): Application configuration
            
        Returns:
            Dict[str, Any]: Created application details
            
        Raises:
            requests.exceptions.RequestException: If the request fails
            ValueError: If no token is available
        """
        try:
            url = urljoin(self.server_url, '/api/v1/applications')
            response = self.session.post(
                url,
                headers=self._get_headers(),
                json=application_data,
                verify=self.verify_tls,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create application: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise

    def update_application(self, name: str, application_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing ArgoCD application.
        
        Args:
            name (str): Name of the application
            application_data (Dict[str, Any]): Updated application configuration
            
        Returns:
            Dict[str, Any]: Updated application details
            
        Raises:
            requests.exceptions.RequestException: If the request fails
            ValueError: If no token is available
        """
        try:
            url = urljoin(self.server_url, f'/api/v1/applications/{name}')
            response = self.session.put(
                url,
                headers=self._get_headers(),
                json=application_data,
                verify=self.verify_tls,
                timeout=30
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update application {name}: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise

    def delete_application(self, name: str, cascade: bool = True) -> bool:
        """
        Delete an ArgoCD application.
        
        Args:
            name (str): Name of the application
            cascade (bool): Whether to cascade delete (default: True)
            
        Returns:
            bool: True if deletion was successful
            
        Raises:
            requests.exceptions.RequestException: If the request fails
            ValueError: If no token is available
        """
        try:
            url = urljoin(self.server_url, f'/api/v1/applications/{name}')
            params = {'cascade': str(cascade).lower()}
            response = self.session.delete(
                url,
                headers=self._get_headers(),
                params=params,
                verify=self.verify_tls,
                timeout=30
            )
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to delete application {name}: {str(e)}")
            if hasattr(e.response, 'text'):
                logger.error(f"Response: {e.response.text}")
            raise

    def perform_sanity_check(self) -> Dict[str, Any]:
        """
        Perform a sanity check of the ArgoCD connection and token.
        
        Returns:
            Dict[str, Any]: Sanity check results including:
                - token_valid (bool): Whether the token is valid
                - applications_count (int): Number of applications found
                - sample_application (Dict[str, Any]): Details of first application if any
                - error (str): Error message if any
        """
        result = {
            'token_valid': False,
            'applications_count': 0,
            'sample_application': None,
            'error': None
        }

        try:
            # First ensure we have a token
            if not self.token:
                self.fetch_token()

            # Validate token
            if not self.validate_token(self.token):
                result['error'] = "Token validation failed"
                return result

            result['token_valid'] = True

            # Try to list applications
            applications = self.list_applications()
            if applications is None:
                result['error'] = "Failed to list applications"
                return result
                
            result['applications_count'] = len(applications)

            # If we have applications, get details of the first one
            if applications and len(applications) > 0:
                first_app = applications[0]
                app_name = first_app.get('metadata', {}).get('name')
                if app_name:
                    try:
                        result['sample_application'] = self.get_application(app_name)
                    except Exception as e:
                        result['error'] = f"Failed to get sample application details: {str(e)}"

            return result

        except Exception as e:
            result['error'] = str(e)
            return result

def main():
    """Main function to demonstrate token fetching and sanity check."""
    server_url = os.getenv('ARGOCD_SERVER')
    username = os.getenv('ARGOCD_USERNAME')
    password = os.getenv('ARGOCD_PASSWORD')
    verify_tls = os.getenv('ARGOCD_VERIFY_TLS', 'true').lower() == 'true'
    
    if not all([server_url, username, password]):
        logger.error("Missing required environment variables")
        logger.error("Please set ARGOCD_SERVER, ARGOCD_USERNAME, and ARGOCD_PASSWORD")
        sys.exit(1)
    
    try:
        fetcher = ArgoCDTokenFetcher(
            server_url=server_url,
            username=username,
            password=password,
            verify_tls=verify_tls
        )
        
        # Fetch token
        token = fetcher.fetch_token()
        if not token:
            logger.error("Failed to fetch token")
            sys.exit(1)
            
        # Print token
        print("\nArgoCD Token:")
        print(f"{token}")
            
        # Perform sanity check
        sanity_check = fetcher.perform_sanity_check()
        print("\nSanity Check Results:")
        print(f"Token Valid: {sanity_check['token_valid']}")
        print(f"Applications Count: {sanity_check['applications_count']}")
        if sanity_check['error']:
            print(f"Error: {sanity_check['error']}")
        if sanity_check['sample_application']:
            print("\nSample Application Details:")
            print(json.dumps(sanity_check['sample_application'], indent=2))
            
        sys.exit(0)
                
    except Exception as e:
        logger.error(f"Error: {str(e)}")
        sys.exit(1)

if __name__ == '__main__':
    main()
