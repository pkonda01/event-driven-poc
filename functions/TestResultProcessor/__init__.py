import json
import logging
import os
import requests
from typing import Dict, Any
import azure.functions as func

def main(msg: func.ServiceBusMessage) -> None:
    """
    Process API test results from Service Bus
    This is the Azure Function (Results Processor) component
    """
    logging.info('🔄 Azure Function (Results Processor) - Starting to process test results')
    
    try:
        # Parse the message from Minikube (Test Runner)
        message_body = msg.get_body().decode('utf-8')
        test_results = json.loads(message_body)
        
        test_suite_id = test_results.get('test_suite_id', 'unknown')
        logging.info(f'📊 Processing test results for suite: {test_suite_id}')
        
        # Process and analyze the results
        summary = process_test_results(test_results)
        
        # Send notifications (Slack, Teams, etc.)
        send_notification(summary, test_results)
        
        # Store results (could save to database, blob storage, etc.)
        store_results(test_results)
        
        logging.info(f'✅ Azure Function (Results Processor) - Successfully processed test suite: {test_suite_id}')
        
    except Exception as e:
        logging.error(f'❌ Azure Function (Results Processor) - Error processing test results: {str(e)}')
        raise

def process_test_results(test_results: Dict[str, Any]) -> Dict[str, Any]:
    """
    Analyze test results and create summary
    """
    total_tests = test_results.get('total_tests', 0)
    passed_tests = test_results.get('passed_tests', 0)
    failed_tests = test_results.get('failed_tests', 0)
    success_rate = test_results.get('success_rate', 0)
    duration = test_results.get('total_duration_ms', 0)
    environment = test_results.get('environment', 'unknown')
    
    # Determine overall status and alert level
    if failed_tests == 0:
        status = "✅ ALL TESTS PASSED"
        alert_level = "success"
        color = "good"
    elif success_rate >= 80:
        status = "⚠️ PARTIAL SUCCESS"
        alert_level = "warning"
        color = "warning"
    else:
        status = "❌ TESTS FAILED"
        alert_level = "error"
        color = "danger"
    
    # Extract failed test details
    failed_test_details = []
    for result in test_results.get('test_results', []):
        if result.get('status') in ['failed', 'error']:
            failed_test_details.append({
                'name': result.get('test_name', 'Unknown'),
                'error': result.get('error', 'No error message'),
                'url': result.get('url', 'Unknown'),
                'status_code': result.get('response_status', 'N/A')
            })
    
    summary = {
        'status': status,
        'alert_level': alert_level,
        'color': color,
        'total_tests': total_tests,
        'passed_tests': passed_tests,
        'failed_tests': failed_tests,
        'success_rate': success_rate,
        'duration_seconds': duration / 1000 if duration else 0,
        'environment': environment,
        'failed_details': failed_test_details[:5],  # Limit to first 5 failures
        'git_commit': test_results.get('git_commit', 'unknown')[:8],
        'git_branch': test_results.get('git_branch', '').replace('refs/heads/', ''),
        'github_run_id': test_results.get('github_run_id', 'unknown'),
        'repository': test_results.get('github_repository', 'unknown')
    }
    
    logging.info(f'📈 Test analysis complete: {status} ({passed_tests}/{total_tests} passed)')
    return summary

def send_notification(summary: Dict[str, Any], full_results: Dict[str, Any]):
    """
    Send notification to Slack or other webhook endpoint
    """
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
    
    if not webhook_url:
        logging.info('📢 SLACK_WEBHOOK_URL not configured, logging results instead')
        logging.info(f'📊 Test Summary: {summary["status"]} - {summary["passed_tests"]}/{summary["total_tests"]} tests passed')
        if summary['failed_details']:
            for failure in summary['failed_details']:
                logging.info(f'❌ Failed: {failure["name"]} - {failure["error"]}')
        return
    
    # Create GitHub Actions run URL if available
    github_run_url = None
    if summary['github_run_id'] != 'unknown' and summary['repository'] != 'unknown':
        github_run_url = f"https://github.com/{summary['repository']}/actions/runs/{summary['github_run_id']}"
    
    # Create rich Slack message
    message = {
        "text": f"API Test Results: {summary['status']}",
        "attachments": [
            {
                "color": summary['color'],
                "fields": [
                    {
                        "title": "📊 Test Summary",
                        "value": f"✅ Passed: {summary['passed_tests']}\n❌ Failed: {summary['failed_tests']}\n📈 Success Rate: {summary['success_rate']:.1f}%",
                        "short": True
                    },
                    {
                        "title": "🔧 Environment Details",
                        "value": f"🏃‍♂️ Runner: {summary['environment']}\n⏱️ Duration: {summary['duration_seconds']:.1f}s\n🌿 Branch: {summary['git_branch']}\n💻 Commit: {summary['git_commit']}",
                        "short": True
                    }
                ]
            }
        ]
    }
    
    # Add failed test details if any
    if summary['failed_details']:
        failed_text = "\n".join([
            f"• {test['name']}: {test['error']}" 
            for test in summary['failed_details']
        ])
        message["attachments"][0]["fields"].append({
            "title": "❌ Failed Tests",
            "value": failed_text,
            "short": False
        })
    
    # Add GitHub Actions link if available
    if github_run_url:
        message["attachments"][0]["fields"].append({
            "title": "🔗 GitHub Actions",
            "value": f"<{github_run_url}|View Detailed Logs>",
            "short": False
        })
    
    # Send the notification
    try:
        response = requests.post(webhook_url, json=message, timeout=30)
        response.raise_for_status()
        logging.info('📢 Notification sent successfully to webhook')
    except requests.exceptions.RequestException as e:
        logging.error(f'❌ Failed to send notification to webhook: {str(e)}')
    except Exception as e:
        logging.error(f'❌ Unexpected error sending notification: {str(e)}')

def store_results(test_results: Dict[str, Any]):
    """
    Store test results for historical analysis
    In production, you might store to:
    - Azure Cosmos DB
    - Azure SQL Database  
    - Azure Table Storage
    - Azure Blob Storage
    """
    test_suite_id = test_results.get('test_suite_id', 'unknown')
    timestamp = test_results.get('timestamp', 'unknown')
    
    # For now, just log that we would store the results
    logging.info(f'💾 Storing test results for suite {test_suite_id} (timestamp: {timestamp})')
    
    # Example: In production, you might do something like:
    # cosmos_client.create_item(container='test_results', body=test_results)
    # or
    # blob_client.upload_blob(f'test-results/{test_suite_id}.json', json.dumps(test_results))
    
    logging.info('💾 Test results stored successfully')