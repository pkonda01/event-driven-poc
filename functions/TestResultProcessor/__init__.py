import json
import logging
import os
import requests
from typing import Dict, Any
import azure.functions as func

def main(msg: func.ServiceBusMessage) -> None:
    """Process API test results from Service Bus"""
    logging.info('TestResultProcessor function started')
    
    try:
        # Parse message
        message_body = msg.get_body().decode('utf-8')
        test_results = json.loads(message_body)
        
        logging.info(f"Processing test results for suite: {test_results.get('test_suite_id')}")
        
        # Process results
        summary = process_test_results(test_results)
        
        # Send notifications
        send_notification(summary, test_results)
        
        logging.info("Test results processed successfully")
        
    except Exception as e:
        logging.error(f"Error processing test results: {str(e)}")
        raise

def process_test_results(test_results: Dict[str, Any]) -> Dict[str, Any]:
    """Process and analyze test results"""
    total_tests = test_results.get('total_tests', 0)
    passed_tests = test_results.get('passed_tests', 0)
    failed_tests = test_results.get('failed_tests', 0)
    success_rate = test_results.get('success_rate', 0)
    duration = test_results.get('total_duration_ms', 0)
    
    # Determine status
    if failed_tests == 0:
        status = "✅ SUCCESS"
        color = "good"
    elif success_rate >= 80:
        status = "⚠️ PARTIAL SUCCESS"
        color = "warning"
    else:
        status = "❌ FAILURE"
        color = "danger"
    
    # Analyze failed tests
    failed_test_details = []
    for result in test_results.get('test_results', []):
        if result.get('status') == 'failed':
            failed_test_details.append({
                'name': result.get('test_name'),
                'error': result.get('error'),
                'url': result.get('url')
            })
    
    return {
        'status': status,
        'color': color,
        'total_tests': total_tests,
        'passed_tests': passed_tests,
        'failed_tests': failed_tests,
        'success_rate': success_rate,
        'duration_seconds': duration / 1000,
        'failed_details': failed_test_details,
        'git_commit': test_results.get('git_commit', 'unknown')[:8],
        'git_branch': test_results.get('git_branch', '').replace('refs/heads/', ''),
        'github_run_id': test_results.get('github_run_id')
    }

def send_notification(summary: Dict[str, Any], full_results: Dict[str, Any]):
    """Send notification to Slack or other webhook"""
    webhook_url = os.environ.get('SLACK_WEBHOOK_URL')
    
    if not webhook_url:
        logging.info("SLACK_WEBHOOK_URL not configured, skipping notification")
        return
    
    # Create Slack message
    github_run_url = f"https://github.com/your-repo/actions/runs/{summary['github_run_id']}" if summary['github_run_id'] != 'unknown' else None
    
    message = {
        "text": f"API Test Results: {summary['status']}",
        "attachments": [
            {
                "color": summary['color'],
                "fields": [
                    {
                        "title": "Test Summary",
                        "value": f"✅ Passed: {summary['passed_tests']}\n❌ Failed: {summary['failed_tests']}\n📊 Success Rate: {summary['success_rate']:.1f}%",
                        "short": True
                    },
                    {
                        "title": "Details",
                        "value": f"⏱️ Duration: {summary['duration_seconds']:.1f}s\n🌿 Branch: {summary['git_branch']}\n💻 Commit: {summary['git_commit']}",
                        "short": True
                    }
                ]
            }
        ]
    }
    
    # Add failed test details
    if summary['failed_details']:
        failed_text = "\n".join([f"• {test['name']}: {test['error']}" for test in summary['failed_details'][:5]])
        message["attachments"][0]["fields"].append({
            "title": "Failed Tests",
            "value": failed_text,
            "short": False
        })
    
    # Add GitHub link
    if github_run_url:
        message["attachments"][0]["fields"].append({
            "title": "GitHub Actions",
            "value": f"<{github_run_url}|View Run Details>",
            "short": False
        })
    
    # Send to webhook
    try:
        response = requests.post(webhook_url, json=message, timeout=30)
        response.raise_for_status()
        logging.info("Notification sent successfully")
    except Exception as e:
        logging.error(f"Failed to send notification: {str(e)}")