#!/usr/bin/env python3
"""
Self-Healing AI Agent Web Server
Serves the dashboard and runs the self-healing workflow every 10 minutes.
"""

import json
import os
import sys
import threading
import time
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration
PORT = 8080
INTERVAL_MINUTES = 10
WORKFLOW_STATUS_FILE = "workflow_status.json"


class WorkflowScheduler:
    """Scheduler that runs the self-healing workflow every X minutes."""
    
    def __init__(self):
        self.is_running = False
        self.interval_seconds = INTERVAL_MINUTES * 60
        self.remaining_seconds = self.interval_seconds
        self.thread = None
        self.stats = {
            "bugs_detected": 0,
            "bugs_fixed": 0,
            "total_runs": 0,
            "last_run": None,
            "next_run": None,
            "status": "stopped"
        }
        self.load_status()
    
    def load_status(self):
        """Load workflow status from file."""
        if Path(WORKFLOW_STATUS_FILE).exists():
            try:
                with open(WORKFLOW_STATUS_FILE, 'r') as f:
                    self.stats = json.load(f)
            except Exception as e:
                logger.warning(f"Could not load status: {e}")
    
    def save_status(self):
        """Save workflow status to file."""
        try:
            with open(WORKFLOW_STATUS_FILE, 'w') as f:
                json.dump(self.stats, f, indent=2)
        except Exception as e:
            logger.error(f"Could not save status: {e}")
    
    def run_workflow(self):
        """Execute the self-healing workflow."""
        from self_healing_agent import SelfHealingOrchestrator
        
        logger.info("🔄 Starting self-healing workflow...")
        
        try:
            orchestrator = SelfHealingOrchestrator()
            
            # Simulate a bug detection scenario
            from self_healing_agent.bug_detector import BugReport, BugType, BugSeverity
            
            # Create sample bugs to process
            sample_bugs = [
                BugReport(
                    bug_id=f"BUG-{datetime.now().strftime('%Y%m%d-%H%M%S')}-001",
                    bug_type=BugType.TYPE_ERROR,
                    severity=BugSeverity.MEDIUM,
                    message="Simulated TypeError for demonstration",
                    file_path=None,
                    line_number=10,
                    stack_trace=None,
                    source="scheduler"
                ),
                BugReport(
                    bug_id=f"BUG-{datetime.now().strftime('%Y%m%d-%H%M%S')}-002",
                    bug_type=BugType.VALUE_ERROR,
                    severity=BugSeverity.HIGH,
                    message="Simulated ValueError for demonstration",
                    file_path=None,
                    line_number=25,
                    stack_trace=None,
                    source="scheduler"
                )
            ]
            
            bugs_processed = 0
            bugs_fixed = 0
            
            for bug in sample_bugs:
                result = orchestrator.process_bug(bug)
                bugs_processed += 1
                if result.success:
                    bugs_fixed += 1
            
            # Update statistics
            self.stats["bugs_detected"] += bugs_processed
            self.stats["bugs_fixed"] += bugs_fixed
            self.stats["total_runs"] += 1
            self.stats["last_run"] = datetime.now().isoformat()
            self.stats["status"] = "completed"
            self.save_status()
            
            logger.info(f"✅ Workflow completed: {bugs_fixed}/{bugs_processed} bugs fixed")
            
        except Exception as e:
            logger.error(f"❌ Workflow failed: {e}")
            self.stats["status"] = "failed"
            self.save_status()
    
    def scheduler_loop(self):
        """Main scheduler loop."""
        logger.info(f"Scheduler started - running every {INTERVAL_MINUTES} minutes")
        
        while self.is_running:
            # Countdown
            for remaining in range(self.remaining_seconds, 0, -1):
                if not self.is_running:
                    break
                self.stats["remaining_seconds"] = remaining
                self.stats["next_run"] = datetime.now().isoformat()
                time.sleep(1)
            
            if self.is_running:
                self.run_workflow()
                self.remaining_seconds = self.interval_seconds
    
    def start(self):
        """Start the scheduler."""
        if self.is_running:
            return
        
        self.is_running = True
        self.remaining_seconds = self.interval_seconds
        self.stats["status"] = "running"
        self.save_status()
        
        self.thread = threading.Thread(target=self.scheduler_loop, daemon=True)
        self.thread.start()
        
        # Run immediately on start
        self.run_workflow()
        
        logger.info("✅ Scheduler started")
    
    def stop(self):
        """Stop the scheduler."""
        self.is_running = False
        self.stats["status"] = "stopped"
        self.save_status()
        
        if self.thread:
            self.thread.join(timeout=2)
        
        logger.info("⏹️ Scheduler stopped")
    
    def get_status(self):
        """Get current scheduler status."""
        return {
            **self.stats,
            "is_running": self.is_running,
            "interval_minutes": INTERVAL_MINUTES,
            "remaining_seconds": self.remaining_seconds
        }


class DashboardHandler(SimpleHTTPRequestHandler):
    """HTTP handler with API endpoints for the dashboard."""
    
    scheduler = None
    
    def do_GET(self):
        """Handle GET requests."""
        if self.path == '/api/status':
            self.send_json_response(self.scheduler.get_status())
        elif self.path == '/api/config':
            self.send_json_response(self.load_c4_config())
        elif self.path == '/':
            self.path = '/index.html'
            super().do_GET()
        else:
            super().do_GET()
    
    def do_POST(self):
        """Handle POST requests."""
        if self.path == '/api/start':
            self.scheduler.start()
            self.send_json_response({"success": True, "message": "Scheduler started"})
        elif self.path == '/api/stop':
            self.scheduler.stop()
            self.send_json_response({"success": True, "message": "Scheduler stopped"})
        elif self.path == '/api/run':
            threading.Thread(target=self.scheduler.run_workflow, daemon=True).start()
            self.send_json_response({"success": True, "message": "Workflow triggered"})
        else:
            self.send_error(404)
    
    def send_json_response(self, data):
        """Send JSON response."""
        response = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', len(response))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(response)
    
    def load_c4_config(self):
        """Load c4.yml configuration."""
        import yaml
        
        config_path = Path(__file__).parent / 'c4.yml'
        
        if config_path.exists():
            try:
                with open(config_path, 'r') as f:
                    config = yaml.safe_load(f)
                
                # Convert to serializable format
                def make_serializable(obj):
                    if isinstance(obj, dict):
                        return {k: make_serializable(v) for k, v in obj.items()}
                    elif isinstance(obj, list):
                        return [make_serializable(item) for item in obj]
                    elif hasattr(obj, '__str__') and not isinstance(obj, (str, int, float, bool, type(None))):
                        return str(obj)
                    return obj
                
                return make_serializable(config)
            except Exception as e:
                return {"error": str(e), "raw": open(config_path).read()}
        
        return {"error": "c4.yml not found"}
    
    def log_message(self, format, *args):
        """Override to customize logging."""
        logger.info(f"{self.address_string()} - {format % args}")


def create_handler(scheduler):
    """Create handler class with scheduler reference."""
    class Handler(DashboardHandler):
        pass
    Handler.scheduler = scheduler
    return Handler


def main():
    """Main entry point."""
    # Change to script directory
    os.chdir(Path(__file__).parent)
    
    # Initialize scheduler
    scheduler = WorkflowScheduler()
    
    # Create server
    handler = create_handler(scheduler)
    server = HTTPServer(('0.0.0.0', PORT), handler)
    
    print(f"""
╔══════════════════════════════════════════════════════════════╗
║           Self-Healing AI Agent Dashboard                   ║
╠══════════════════════════════════════════════════════════════╣
║  🌐 Dashboard:  http://localhost:{PORT}                      ║
║  ⏰ Schedule:    Every {INTERVAL_MINUTES} minutes                                 ║
║  📁 Config:     c4.yml                                       ║
╠══════════════════════════════════════════════════════════════╣
║  API Endpoints:                                             ║
║    GET  /api/status     - Get scheduler status               ║
║    GET  /api/config     - Get c4.yml configuration           ║
║    POST /api/start      - Start scheduler                   ║
║    POST /api/stop       - Stop scheduler                    ║
║    POST /api/run        - Run workflow immediately          ║
╚══════════════════════════════════════════════════════════════╝
    """)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 Shutting down...")
        scheduler.stop()
        server.shutdown()


if __name__ == '__main__':
    main()
