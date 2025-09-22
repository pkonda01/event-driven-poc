import json
import requests
import time
import os
import uuid
from datetime import datetime, timezone
from azure.servicebus import ServiceBusClient, ServiceBusMessage
from typing import List, Dict, Any


class APITestRunner:
    def __init__(self):
        self.test_id = (
            f"test-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{uuid.uuid4().hex[:8]}"
        )
        self.service_bus_connection = os.environ.get("SERVICE_BUS_CONNECTION_STRING")
        self.results = []

    def load_test_config(
        self, config_path: str = "tests/test_config.json"
    ) -> List[Dict]:
        """Load test configuration from JSON file"""
        with open(config_path, "r") as f:
            config = json.load(f)
        return config["api_tests"]

    def run_single_test(self, test_config: Dict) -> Dict[str, Any]:
        """Run a single API test"""
        print(f" Running test: {test_config['name']}")

        start_time = time.time()
        test_result = {
            "test_name": test_config["name"],
            "test_id": self.test_id,
            "url": test_config["url"],
            "method": test_config["method"],
            "status": "failed",
            "start_time": datetime.now(timezone.utc).isoformat(),
            "duration_ms": 0,
            "error": None,
            "response_status": None,
            "response_time_ms": 0,
        }

        try:
            # Prepare request
            method = test_config["method"].upper()
            url = test_config["url"]
            timeout = test_config.get("timeout", 30)
            payload = test_config.get("payload")

            # Make request
            if method == "GET":
                response = requests.get(url, timeout=timeout)
            elif method == "POST":
                response = requests.post(url, json=payload, timeout=timeout)
            elif method == "PUT":
                response = requests.put(url, json=payload, timeout=timeout)
            elif method == "DELETE":
                response = requests.delete(url, timeout=timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")

            duration = int((time.time() - start_time) * 1000)

            # Update result
            test_result.update(
                {
                    "duration_ms": duration,
                    "response_status": response.status_code,
                    "response_time_ms": duration,
                }
            )

            # Validate response
            expected_status = test_config.get("expected_status", 200)
            if response.status_code == expected_status:
                test_result["status"] = "passed"
                print(f" {test_config['name']} - PASSED ({duration}ms)")
            else:
                test_result["status"] = "failed"
                test_result["error"] = (
                    f"Expected {expected_status}, got {response.status_code}"
                )
                print(
                    f" {test_config['name']} - FAILED (Expected {expected_status}, got {response.status_code})"
                )

            # Additional JSON validation
            if test_config.get("validate_json", False):
                try:
                    response.json()
                    print(f" JSON validation passed for {test_config['name']}")
                except json.JSONDecodeError:
                    test_result["status"] = "failed"
                    test_result["error"] = "Invalid JSON response"
                    print(f" JSON validation failed for {test_config['name']}")

        except requests.exceptions.Timeout:
            test_result["error"] = "Request timeout"
            test_result["duration_ms"] = int((time.time() - start_time) * 1000)
            print(f" {test_config['name']} - TIMEOUT")

        except Exception as e:
            test_result["error"] = str(e)
            test_result["duration_ms"] = int((time.time() - start_time) * 1000)
            print(f" {test_config['name']} - ERROR: {str(e)}")

        return test_result

    def run_all_tests(self) -> Dict[str, Any]:
        """Run all API tests"""
        print(f" Starting API Test Suite - Test ID: {self.test_id}")

        test_configs = self.load_test_config()
        suite_start_time = time.time()

        for test_config in test_configs:
            result = self.run_single_test(test_config)
            self.results.append(result)

        # Calculate summary
        total_tests = len(self.results)
        passed_tests = len([r for r in self.results if r["status"] == "passed"])
        failed_tests = total_tests - passed_tests
        total_duration = int((time.time() - suite_start_time) * 1000)

        summary = {
            "test_suite_id": self.test_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "success_rate": (
                (passed_tests / total_tests * 100) if total_tests > 0 else 0
            ),
            "total_duration_ms": total_duration,
            "environment": os.environ.get("TEST_ENVIRONMENT", "minikube"),
            "git_commit": os.environ.get("GITHUB_SHA", "unknown"),
            "git_branch": os.environ.get("GITHUB_REF", "unknown"),
            "github_run_id": os.environ.get("GITHUB_RUN_ID", "unknown"),
            "test_results": self.results,
        }

        print(f"\nTest Suite Summary:")
        print(f"   Total Tests: {total_tests}")
        print(f"   Passed: {passed_tests}")
        print(f"   Failed: {failed_tests}")
        print(f"   Success Rate: {summary['success_rate']:.1f}%")
        print(f"   Total Duration: {total_duration}ms")

        return summary

    def send_results_to_service_bus(self, summary: Dict[str, Any]):
        """Send test results to Azure Service Bus"""
        if not self.service_bus_connection:
            print(
                "⚠️  SERVICE_BUS_CONNECTION_STRING not set, skipping Service Bus notification"
            )
            return

        try:
            with ServiceBusClient.from_connection_string(
                self.service_bus_connection
            ) as client:
                sender = client.get_topic_sender("api-test-results")
                message = ServiceBusMessage(json.dumps(summary))
                sender.send_messages(message)
                print(f"📤 Test results sent to Service Bus")
        except Exception as e:
            print(f" Failed to send results to Service Bus: {e}")


def main():
    """Main entry point"""
    runner = APITestRunner()
    summary = runner.run_all_tests()
    # runner.send_results_to_service_bus(summary)

    # Exit with appropriate code
    if summary["failed_tests"] > 0:
        print(f"\n Test suite failed with {summary['failed_tests']} failures")
        exit(1)
    else:
        print(f"\n All tests passed!")
        exit(0)


if __name__ == "__main__":
    main()
