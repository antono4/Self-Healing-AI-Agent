"""Memory Store - Persistent storage untuk knowledge dan context."""

import json
import sqlite3
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import structlog

from .bug_detector import BugReport, BugType
from .code_analyzer import RootCauseAnalysis
from .self_repair import FixCandidate, VerifiedFix

logger = structlog.get_logger()


@dataclass
class FixKnowledge:
    """Knowledge about a successful fix."""

    fix_id: str
    bug_type: BugType
    root_cause: str
    original_pattern: str
    fixed_pattern: str
    file_path: str
    success_rate: float
    times_used: int
    last_used: datetime
    created_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)


class MemoryStore:
    """Persistent memory store untuk menyimpan knowledge tentang fixes."""

    def __init__(self, db_path: str | Path | None = None):
        if db_path is None:
            db_path = Path.home() / ".self_healing_agent" / "memory.db"

        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.logger = logger.bind(component="MemoryStore")
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database schema."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Bug reports table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS bug_reports (
                bug_id TEXT PRIMARY KEY,
                bug_type TEXT NOT NULL,
                severity TEXT NOT NULL,
                message TEXT,
                file_path TEXT,
                line_number INTEGER,
                stack_trace TEXT,
                source TEXT,
                timestamp TEXT,
                metadata TEXT
            )
        """)

        # Root cause analyses table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS root_cause_analyses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bug_id TEXT,
                root_cause TEXT,
                suggested_fix_strategy TEXT,
                confidence REAL,
                related_code TEXT,
                FOREIGN KEY (bug_id) REFERENCES bug_reports(bug_id)
            )
        """)

        # Fix candidates table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fix_candidates (
                fix_id TEXT PRIMARY KEY,
                bug_id TEXT,
                description TEXT,
                original_code TEXT,
                fixed_code TEXT,
                file_path TEXT,
                line_start INTEGER,
                line_end INTEGER,
                confidence REAL,
                strategy TEXT,
                applied INTEGER DEFAULT 0,
                FOREIGN KEY (bug_id) REFERENCES bug_reports(bug_id)
            )
        """)

        # Fix knowledge table (learned patterns)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS fix_knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bug_type TEXT NOT NULL,
                root_cause_pattern TEXT,
                original_pattern TEXT,
                fixed_pattern TEXT,
                file_path_pattern TEXT,
                success_rate REAL DEFAULT 0.0,
                times_used INTEGER DEFAULT 0,
                last_used TEXT,
                created_at TEXT,
                metadata TEXT
            )
        """)

        # Create indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bug_type ON bug_reports(bug_type)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_fix_knowledge_type ON fix_knowledge(bug_type)")

        conn.commit()
        conn.close()

    def store_bug_report(self, bug: BugReport) -> None:
        """Store bug report in memory."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO bug_reports 
            (bug_id, bug_type, severity, message, file_path, line_number, stack_trace, source, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                bug.bug_id,
                bug.bug_type.value,
                bug.severity.value,
                bug.message,
                bug.file_path,
                bug.line_number,
                bug.stack_trace,
                bug.source,
                bug.timestamp.isoformat(),
                json.dumps(bug.metadata),
            ),
        )

        conn.commit()
        conn.close()
        self.logger.info("Stored bug report", bug_id=bug.bug_id)

    def store_analysis(self, bug_id: str, analysis: RootCauseAnalysis) -> None:
        """Store root cause analysis."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT INTO root_cause_analyses
            (bug_id, root_cause, suggested_fix_strategy, confidence, related_code)
            VALUES (?, ?, ?, ?, ?)
        """,
            (
                bug_id,
                analysis.root_cause,
                analysis.suggested_fix_strategy,
                analysis.confidence,
                analysis.related_code,
            ),
        )

        conn.commit()
        conn.close()

    def store_fix(self, fix: FixCandidate, applied: bool = False) -> None:
        """Store fix candidate."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            INSERT OR REPLACE INTO fix_candidates
            (fix_id, bug_id, description, original_code, fixed_code, file_path, line_start, line_end, confidence, strategy, applied)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
            (
                fix.fix_id,
                fix.fix_id.split("-")[1] + "-" + fix.fix_id.split("-")[2],
                fix.description,
                fix.original_code,
                fix.fixed_code,
                fix.file_path,
                fix.line_start,
                fix.line_end,
                fix.confidence,
                fix.strategy,
                1 if applied else 0,
            ),
        )

        conn.commit()
        conn.close()
        self.logger.info("Stored fix candidate", fix_id=fix.fix_id)

    def store_successful_fix(self, fix: FixCandidate, bug: BugReport) -> None:
        """Store successful fix and learn from it."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Extract pattern from the fix
        original_pattern = self._extract_pattern(fix.original_code)
        fixed_pattern = self._extract_pattern(fix.fixed_code)

        # Check if similar fix exists
        cursor.execute(
            """
            SELECT id, times_used, success_rate FROM fix_knowledge
            WHERE bug_type = ? AND original_pattern = ?
        """,
            (bug.bug_type.value, original_pattern),
        )

        existing = cursor.fetchone()

        if existing:
            # Update existing pattern
            knowledge_id, times_used, success_rate = existing
            new_times_used = times_used + 1
            new_success_rate = (success_rate * times_used + 1.0) / new_times_used

            cursor.execute(
                """
                UPDATE fix_knowledge
                SET times_used = ?, success_rate = ?, last_used = ?
                WHERE id = ?
            """,
                (new_times_used, new_success_rate, datetime.now().isoformat(), knowledge_id),
            )
        else:
            # Create new pattern
            cursor.execute(
                """
                INSERT INTO fix_knowledge
                (bug_type, root_cause_pattern, original_pattern, fixed_pattern, file_path_pattern, success_rate, times_used, last_used, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
                (
                    bug.bug_type.value,
                    bug.message[:200] if bug.message else "",
                    original_pattern,
                    fixed_pattern,
                    str(Path(fix.file_path).suffix) if fix.file_path else "",
                    1.0,
                    1,
                    datetime.now().isoformat(),
                    datetime.now().isoformat(),
                ),
            )

        conn.commit()
        conn.close()
        self.logger.info("Stored successful fix", fix_id=fix.fix_id, bug_type=bug.bug_type.value)

    def get_similar_fixes(self, bug_type: BugType, pattern: str, limit: int = 5) -> list[FixKnowledge]:
        """Find similar successful fixes."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT fix_id, bug_type, root_cause_pattern, original_pattern, fixed_pattern, 
                   file_path_pattern, success_rate, times_used, last_used, created_at, metadata
            FROM fix_knowledge
            WHERE bug_type = ? AND (original_pattern LIKE ? OR root_cause_pattern LIKE ?)
            ORDER BY success_rate DESC, times_used DESC
            LIMIT ?
        """,
            (bug_type.value, f"%{pattern[:50]}%", f"%{pattern[:50]}%", limit),
        )

        rows = cursor.fetchall()
        conn.close()

        fixes = []
        for row in rows:
            fixes.append(
                FixKnowledge(
                    fix_id=row[0],
                    bug_type=BugType(row[1]),
                    root_cause=row[2] or "",
                    original_pattern=row[3] or "",
                    fixed_pattern=row[4] or "",
                    file_path=row[5] or "",
                    success_rate=row[6],
                    times_used=row[7],
                    last_used=datetime.fromisoformat(row[8]),
                    created_at=datetime.fromisoformat(row[9]),
                    metadata=json.loads(row[10]) if row[10] else {},
                )
            )

        return fixes

    def get_fix_statistics(self) -> dict[str, Any]:
        """Get statistics about stored fixes."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Total bugs
        cursor.execute("SELECT COUNT(*) FROM bug_reports")
        total_bugs = cursor.fetchone()[0]

        # Bugs by type
        cursor.execute("SELECT bug_type, COUNT(*) FROM bug_reports GROUP BY bug_type")
        bugs_by_type = dict(cursor.fetchall())

        # Total fixes
        cursor.execute("SELECT COUNT(*) FROM fix_candidates")
        total_fixes = cursor.fetchone()[0]

        # Applied fixes
        cursor.execute("SELECT COUNT(*) FROM fix_candidates WHERE applied = 1")
        applied_fixes = cursor.fetchone()[0]

        # Learned patterns
        cursor.execute("SELECT COUNT(*) FROM fix_knowledge")
        learned_patterns = cursor.fetchone()[0]

        # Top fix strategies
        cursor.execute(
            """
            SELECT strategy, COUNT(*) as cnt 
            FROM fix_candidates 
            WHERE applied = 1 
            GROUP BY strategy 
            ORDER BY cnt DESC 
            LIMIT 5
        """
        )
        top_strategies = cursor.fetchall()

        conn.close()

        return {
            "total_bugs": total_bugs,
            "bugs_by_type": bugs_by_type,
            "total_fixes": total_fixes,
            "applied_fixes": applied_fixes,
            "fix_success_rate": applied_fixes / total_fixes if total_fixes > 0 else 0,
            "learned_patterns": learned_patterns,
            "top_strategies": [{"strategy": s, "count": c} for s, c in top_strategies],
        }

    def _extract_pattern(self, code: str, max_length: int = 200) -> str:
        """Extract a simplified pattern from code."""
        if not code:
            return ""

        # Remove variable names and literals, keep structure
        pattern = code.strip()
        pattern = pattern[:max_length]

        return pattern

    def search_knowledge(self, query: str, limit: int = 10) -> list[FixKnowledge]:
        """Search knowledge base with query."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            """
            SELECT fix_id, bug_type, root_cause_pattern, original_pattern, fixed_pattern,
                   file_path_pattern, success_rate, times_used, last_used, created_at, metadata
            FROM fix_knowledge
            WHERE root_cause_pattern LIKE ? OR original_pattern LIKE ? OR fixed_pattern LIKE ?
            ORDER BY success_rate DESC
            LIMIT ?
        """,
            (f"%{query}%", f"%{query}%", f"%{query}%", limit),
        )

        rows = cursor.fetchall()
        conn.close()

        fixes = []
        for row in rows:
            fixes.append(
                FixKnowledge(
                    fix_id=row[0],
                    bug_type=BugType(row[1]),
                    root_cause=row[2] or "",
                    original_pattern=row[3] or "",
                    fixed_pattern=row[4] or "",
                    file_path=row[5] or "",
                    success_rate=row[6],
                    times_used=row[7],
                    last_used=datetime.fromisoformat(row[8]),
                    created_at=datetime.fromisoformat(row[9]),
                    metadata=json.loads(row[10]) if row[10] else {},
                )
            )

        return fixes

    def clear_old_entries(self, days: int = 90) -> int:
        """Clear entries older than specified days."""
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)

        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute(
            "DELETE FROM bug_reports WHERE timestamp < ?",
            (cutoff.isoformat(),),
        )
        bugs_deleted = cursor.rowcount

        cursor.execute(
            "DELETE FROM fix_knowledge WHERE created_at < ? AND times_used = 0",
            (cutoff.isoformat(),),
        )
        patterns_deleted = cursor.rowcount

        conn.commit()
        conn.close()

        self.logger.info(
            "Cleared old entries",
            bugs_deleted=bugs_deleted,
            patterns_deleted=patterns_deleted,
        )

        return bugs_deleted + patterns_deleted
