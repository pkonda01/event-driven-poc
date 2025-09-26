# tests/api_tests_fixed.py - CORRECTED VERSION with proper environment detection

import json
import requests
import time
import os
import uuid
from datetime import datetime, timezone
from typing import List, Dict, Any

# Try to import Service Bus client
try:
    from azure.servicebus import ServiceBusClient, ServiceBusMessage
    HAS_SERVICE_BUS = True
except ImportError:
    print("⚠️ azure-servicebus not installed, results won't be sent to Service Bus")
    HAS_SERVICE_BUS = False

class APITestRunner:
    def __init__(self):
        self.test_id = f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
        self.service_bus_connection = os.environ.get('SERVICE_BUS_CONNECTION_STRING')
        self.results = []
        
        # PROPER ENVIRONMENT DETECTION
        self.environment = self.detect_environment()
        self.runner_label = self.get_runner_label()
        
        print(f"🚀 {self.runner_label} - Initializing API test runner")
        print(f"📋 Test ID: {self.test_id}")
        print(f"🌍 Environment: {self.environment}")
        print(f"🏃‍♂️ Running on: {self.runner_label}")
        
    def detect_environment(self) -> str:
        """Detect the actual runtime environment"""
        # Check for Kubernetes environment variables
        if os.path.exists('/var/run/secrets/kubernetes.io'):
            return 'kubernetes'
        
        # Check for specific environment variables
        env_indicators = {
            'KUBERNETES_SERVICE_HOST': 'kubernetes',
            'GITHUB_ACTIONS': 'github-actions',
            'AZURE_HTTP_USER_AGENT': 'azure-cloud-shell',
            'TEST_ENVIRONMENT': os.environ.get('TEST_ENVIRONMENT', 'unknown')
        }
        
        for var, env_type in env_indicators.items():
            if var in os.environ:
                if var == 'TEST_ENVIRONMENT':
                    return os.environ[var]
                return env_type
        
        # Check if running in Docker
        if os.path.exists('/.dockerenv'):
            return 'docker-container'
        
        # Default to local
        return 'local-machine'
    
    def get_runner_label(self) -> str:
        """Get the appropriate runner label based on environment"""
        labels = {
            'kubernetes': 'Minikube/Kubernetes (Test Runner)',
            'docker-container': 'Docker Container (Test Runner)', 
            'github-actions': 'GitHub Actions Runner',
            'azure-cloud-shell': 'Azure Cloud Shell',
            'minikube': 'Minikube (Test Runner)',
            'local-machine': 'Local Machine'
        }
        return labels.get(self.environment, f'Unknown Environment ({self.environment})')
    
    def load_test_config(self) -> List[Dict]:
        """Load test configuration from JSON file"""
        # Try different possible paths based on environment
        if self.environment == 'kubernetes':
            config_paths = [
                '/config/test_config.json',
                '/workspace/tests/test_config.json',
                'tests/test_config.json',
                'test_config.json'
            ]
        else:
            config_paths = [
                'tests/test_config.json',
                'test_config.json',
                '../tests/test_config.json'
            ]
        
        config_data = None
        for path in config_paths:
            try:
                with open(path, 'r') as f:
                    config_data = json.load(f)
                    print(f"📄 Loaded test config from: {path}")
                    break
            except FileNotFoundError:
                continue
        
        if not config_data:
            # Fallback to hardcoded config
            print(f"⚠️ No config file found in {self.environment}, using default tests")
            config_data = {
                "api_tests": [
                    {
                        "name": "HTTPBin Status Check",
                        "url": "https://httpbin.org/status/200",
                        "method": "GET",
                        "expected_status": 200,
                        "timeout": 10
                    },
                    {
                        "name": "HTTPBin JSON Test",
                        "url": "https://httpbin.org/json",
                        "method": "GET",
                        "expected_status": 200,
                        "timeout": 10,
                        "validate_json": True
                    }
                ]
            }
        
        return config_data['api_tests']
    
    def run_single_test(self, test_config: Dict) -> Dict[str, Any]:
        """Run a single API test"""
        print(f"🧪 {self.runner_label} - Running test: {test_config['name']}")
        
        start_time = time.time()
        test_result = {
            'test_name': test_config['name'],
            'test_id': self.test_id,
            'url': test_config['url'],
            'method': test_config['method'],
            'status': 'failed',
            'start_time': datetime.now(timezone.utc).isoformat(),
            'duration_ms': 0,
            'error': None,
            'response_status': None,
            'response_time_ms': 0,
            'environment': self.environment,  # Track where test ran
            'runner': self.runner_label
        }
        
        try:
            # Prepare request
            method = test_config['method'].upper()
            url = test_config['url']
            timeout = test_config.get('timeout', 30)
            payload = test_config.get('payload')
            
            # Make request
            print(f"  📡 Making {method} request to {url}")
            if method == 'GET':
                response = requests.get(url, timeout=timeout)
            elif method == 'POST':
                response = requests.post(url, json=payload, timeout=timeout)
            elif method == 'PUT':
                response = requests.put(url, json=payload, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")
            
            duration = int((time.time() - start_time) * 1000)
            
            # Update result
            test_result.update({
                'duration_ms': duration,
                'response_status': response.status_code,
                'response_time_ms': duration
            })
            
            # Validate response
            expected_status = test_config.get('expected_status', 200)
            if response.status_code == expected_status:
                test_result['status'] = 'passed'
                print(f"  ✅ PASSED - {test_config['name']} ({duration}ms)")
            else:
                test_result['status'] = 'failed'
                test_result['error'] = f"Expected {expected_status}, got {response.status_code}"
                print(f"  ❌ FAILED - {test_config['name']} (Expected {expected_status}, got {response.status_code})")
            
            # Additional JSON validation
            if test_config.get('validate_json', False):
                try:
                    response.json()
                    print(f"  ✅ JSON validation passed")
                except json.JSONDecodeError:
                    test_result['status'] = 'failed'
                    test_result['error'] = 'Invalid JSON response'
                    print(f"  ❌ JSON validation failed")
            
        except requests.exceptions.Timeout:
            test_result['error'] = f'Request timeout after {timeout}s'
            test_result['duration_ms'] = int((time.time() - start_time) * 1000)
            print(f"  ⏰ TIMEOUT - {test_config['name']} (after {timeout}s)")
            
        except Exception as e:
            test_result['error'] = str(e)
            test_result['duration_ms'] = int((time.time() - start_time) * 1000)
            print(f"  ❌ ERROR - {test_config['name']}: {str(e)}")
        
        return test_result
    
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all API tests"""
        print(f"🚀 {self.runner_label} - Starting API Test Suite")
        print(f"📋 Test ID: {self.test_id}")
        
        test_configs = self.load_test_config()
        suite_start_time = time.time()
        
        print(f"📊 Running {len(test_configs)} tests...")
        
        for test_config in test_configs:
            result = self.run_single_test(test_config)
            self.results.append(result)
        
        # Calculate summary
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r['status'] == 'passed'])
        failed_tests = total_tests - passed_tests
        total_duration = int((time.time() - suite_start_time) * 1000)
        success_rate = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        summary = {
            'test_suite_id': self.test_id,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'total_tests': total_tests,
            'passed_tests': passed_tests,
            'failed_tests': failed_tests,
            'success_rate': success_rate,
            'total_duration_ms': total_duration,
            'environment': self.environment,
            'runner': self.runner_label,
            'git_commit': os.environ.get('GITHUB_SHA', 'unknown'),
            'git_branch': os.environ.get('GITHUB_REF', 'unknown'),
            'github_run_id': os.environ.get('GITHUB_RUN_ID', 'unknown'),
            'github_repository': os.environ.get('GITHUB_REPOSITORY', 'unknown'),
            'test_results': self.results
        }
        
        print(f"\n📊 {self.runner_label} - Test Suite Summary:")
        print(f"   🏃‍♂️ Executed on: {self.runner_label}")
        print(f"   🌍 Environment: {self.environment}")
        print(f"   📊 Total Tests: {total_tests}")
        print(f"   ✅ Passed: {passed_tests}")
        print(f"   ❌ Failed: {failed_tests}")
        print(f"   📈 Success Rate: {success_rate:.1f}%")
        print(f"   ⏱️ Total Duration: {total_duration}ms")
        
        return summary
    
    def send_results_to_service_bus(self, summary: Dict[str, Any]):
        """Send test results to Azure Service Bus (Messaging)"""
        if not HAS_SERVICE_BUS:
            print("⚠️ Azure Service Bus client not available, skipping message send")
            return
            
        if not self.service_bus_connection:
            print("⚠️ SERVICE_BUS_CONNECTION_STRING not set, skipping Service Bus notification")
            return
        
        try:
            print(f"📤 {self.runner_label} → Azure Service Bus (Messaging) - Sending results...")
            
            with ServiceBusClient.from_connection_string(self.service_bus_connection) as client:
                sender = client.get_topic_sender("api-test-results")
                message = ServiceBusMessage(json.dumps(summary))
                sender.send_messages(message)
                
                print(f"✅ {self.runner_label} → Azure Service Bus (Messaging) - Results sent successfully!")
                print("🔄 Next: Azure Service Bus (Messaging) → Azure Function (Results Processor)")
                
        except Exception as e:
            print(f"❌ Failed to send results to Azure Service Bus: {e}")
            print("⚠️ Results processing will not occur")
            
            # Additional context for the error
            if "timed out" in str(e).lower() or "amqp:socket-error" in str(e):
                print(f"💡 Network connectivity issue detected from {self.runner_label}")
                if self.environment == 'local-machine':
                    print("   This is expected on local machine due to firewall/network restrictions")
                    print("   Try running from Azure Cloud Shell or GitHub Actions")

def main():
    """Main entry point"""
    runner = APITestRunner()
    
    print("=" * 80)
    print(f"🏁 STARTING API TEST EXECUTION")
    print(f"🏃‍♂️ Runner: {runner.runner_label}")
    print(f"🌍 Environment: {runner.environment}")
    print("=" * 80)
    
    summary = runner.run_all_tests()
    runner.send_results_to_service_bus(summary)
    
    # Save results locally for debugging
    try:
        with open('test_results.json', 'w') as f:
            json.dump(summary, f, indent=2)
        print("💾 Results saved locally to test_results.json")
    except Exception as e:
        print(f"⚠️ Could not save results locally: {e}")
    
    print("\n" + "=" * 80)
    print(f"🏁 TEST EXECUTION COMPLETE")
    print(f"🏃‍♂️ Executed on: {runner.runner_label}")
    print(f"🌍 Environment: {runner.environment}")
    print("=" * 80)
    
    # Exit with appropriate code
    if summary['failed_tests'] > 0:
        print(f"❌ Exiting with failure code - {summary['failed_tests']} test(s) failed")
        exit(1)
    else:
        print("✅ Exiting with success code - all tests passed!")
        exit(0)

if __name__ == "__main__":
    main()