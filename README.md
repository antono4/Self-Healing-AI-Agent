# Self-Healing AI Agent

AI Agent yang bisa mendeteksi dan memperbaiki bug secara otomatis.

## Overview

Self-Healing Agent adalah sistem AI yang mampu:

- **Mendeteksi Bug** dari berbagai sumber (logs, test failures, exceptions)
- **Menganalisis Root Cause** menggunakan AST parsing dan LLM
- **Generate Fixes** dengan berbagai strategi perbaikan
- **Verify Fixes** dengan running tests
- **Apply Fixes** secara otomatis dengan safety checks
- **Learn from Fixes** menyimpan knowledge untuk reuse

## C4 Model Architecture

Lihat `c4.yml` untuk arsitektur lengkap:

- **Level 1 (Context)**: User, External APIs, Version Control
- **Level 2 (Containers)**: Orchestrator, Bug Detector, Code Analyzer, Self-Repair, Verification, Memory
- **Level 3 (Components)**: Detail setiap komponen
- **Level 4 (Code)**: Self-healing workflow

## Installation

```bash
# Clone repository
git clone <repo-url>
cd self-healing-agent

# Install dependencies
pip install -e .

# Install development dependencies
pip install -e ".[dev]"
```

## Usage

### Basic Usage

```python
from self_healing_agent import SelfHealingOrchestrator, BugDetector

# Create orchestrator
orchestrator = SelfHealingOrchestrator()

# Process an exception
try:
    result = risky_operation()
except Exception as e:
    fix_result = orchestrator.process_exception(e)
    print(f"Fix status: {fix_result.success}")
```

### Configuration

Edit `c4.yml` untuk konfigurasi:

```yaml
self_healing:
  enabled: true
  auto_fix: true
  max_retries: 3
  
detection_sources:
  - type: "log_file"
    path: "/var/log/app.log"
  - type: "test_failure"
    command: "pytest"
```

### Demo

```bash
# Run demo
python examples/demo.py
```

## Components

### BugDetector
Mendeteksi bug dari:
- Log files
- Test failures
- Runtime exceptions
- Static analysis

### CodeAnalyzer
Menganalisis kode untuk:
- Root cause identification
- Dependency analysis
- AST parsing

### SelfRepairEngine
Generate fixes untuk:
- Syntax errors
- Import errors
- Type errors
- Value errors
- Logic errors
- Runtime errors

### VerificationSuite
Verify fixes dengan:
- Test execution
- Linting
- Quality gates
- Coverage checks

### MemoryStore
Simpan dan retrieve:
- Bug reports
- Fix patterns
- Success rates
- Learned knowledge

## Testing

```bash
# Run all tests
pytest tests/

# Run with coverage
pytest --cov=self_healing_agent tests/

# Run specific test file
pytest tests/test_orchestrator.py
```

## Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    User/External                         │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│              SelfHealingOrchestrator                     │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐   │
│  │TaskManager  │  │AgentCoord    │  │ResultAgg    │   │
│  └─────────────┘  └─────────────┘  └─────────────┘   │
└─────────────────┬───────────────────────────────────────┘
                  │
        ┌─────────┼─────────┬──────────┐
        ▼         ▼         ▼          ▼
┌──────────┐ ┌────────┐ ┌────────┐ ┌──────────┐
│BugDetector│ │CodeAn  │ │SelfFix │ │Verification│
└──────────┘ └────────┘ └────────┘ └──────────┘
        │         │         │          │
        └─────────┴─────────┴──────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│                    MemoryStore                           │
└─────────────────────────────────────────────────────────┘
```

## License

MIT
