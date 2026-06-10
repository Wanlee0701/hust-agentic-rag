"""
Performance Logger - Theo dõi thời gian chi tiết từng step
Giúp identify bottleneck trong inference pipeline
"""
import logging
import time
from contextlib import contextmanager
from datetime import datetime
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict

logger = logging.getLogger(__name__)


@dataclass
class TimingRecord:
    """Record cho một operation"""
    step_name: str
    start_time: float
    end_time: float
    duration_ms: float
    details: Dict[str, Any]
    
    def __post_init__(self):
        if self.end_time and self.start_time:
            self.duration_ms = (self.end_time - self.start_time) * 1000


class PerformanceTracker:
    """Tracker toàn bộ quá trình inference"""
    
    def __init__(self, query: str):
        self.query = query[:100]  # Lưu query (truncate dài)
        self.start_time = time.time()
        self.records: List[TimingRecord] = []
        self.current_step = None
        
    @contextmanager
    def track(self, step_name: str, details: Dict[str, Any] = None):
        """Context manager để track một step"""
        details = details or {}
        start = time.time()
        
        logger.debug(f"⏱️  START: {step_name}")
        
        try:
            yield
        finally:
            end = time.time()
            duration_ms = (end - start) * 1000
            
            record = TimingRecord(
                step_name=step_name,
                start_time=start,
                end_time=end,
                duration_ms=duration_ms,
                details=details,
            )
            self.records.append(record)
            
            # Log với cảnh báo nếu quá lâu
            if duration_ms > 10000:  # > 10 giây
                logger.warning(f"🐢 SLOW STEP ({duration_ms:.0f}ms): {step_name}")
            elif duration_ms > 5000:  # > 5 giây
                logger.info(f"⏱️  DONE ({duration_ms:.0f}ms): {step_name}")
            else:
                logger.debug(f"✅ DONE ({duration_ms:.0f}ms): {step_name}")
    
    def get_total_duration(self) -> float:
        """Tổng thời gian (ms)"""
        end = time.time()
        return (end - self.start_time) * 1000
    
    def get_summary(self) -> str:
        """Summary text cho log"""
        total = self.get_total_duration()
        
        summary = f"\n{'='*80}\n"
        summary += f"📊 PERFORMANCE REPORT - Query: '{self.query}'\n"
        summary += f"{'='*80}\n"
        summary += f"⏱️  TOTAL TIME: {total:.0f}ms ({total/1000:.1f}s)\n"
        summary += f"\n{'Step Name':<40} {'Duration':<15} {'%':<8}\n"
        summary += f"{'-'*60}\n"
        
        for record in self.records:
            pct = (record.duration_ms / total * 100) if total > 0 else 0
            summary += f"{record.step_name:<40} {record.duration_ms:>7.0f}ms   {pct:>6.1f}%\n"
            
            # Log thêm chi tiết nếu có
            if record.details:
                for key, val in record.details.items():
                    summary += f"  ↳ {key}: {val}\n"
        
        summary += f"{'-'*60}\n"
        summary += f"{'TOTAL':<40} {total:>7.0f}ms   {100:>6.1f}%\n"
        summary += f"{'='*80}\n"
        
        return summary
    
    def log_summary(self):
        """Log summary to logger"""
        logger.info(self.get_summary())
    
    def get_breakdown(self) -> Dict[str, float]:
        """Breakdown time by category"""
        breakdown = {}
        for record in self.records:
            if record.step_name not in breakdown:
                breakdown[record.step_name] = 0
            breakdown[record.step_name] += record.duration_ms
        return breakdown
    
    def get_slowest_steps(self, top_n: int = 5) -> List[TimingRecord]:
        """Get top N slowest steps"""
        return sorted(self.records, key=lambda r: r.duration_ms, reverse=True)[:top_n]


class IterationTracker:
    """Track từng iteration của ReACT loop"""
    
    def __init__(self):
        self.iterations: List[Dict[str, Any]] = []
        self.current_iteration = None
    
    def start_iteration(self, iter_num: int):
        """Bắt đầu iteration mới"""
        self.current_iteration = {
            "iteration": iter_num,
            "start_time": time.time(),
            "steps": [],
            "duration_ms": 0,
        }
        logger.info(f"\n🔄 ITERATION {iter_num} START")
    
    def add_step(self, action: str, details: Dict[str, Any] = None):
        """Thêm step vào iteration"""
        if not self.current_iteration:
            return
        
        details = details or {}
        self.current_iteration["steps"].append({
            "action": action,
            "timestamp": time.time(),
            "details": details,
        })
    
    def end_iteration(self):
        """Kết thúc iteration"""
        if not self.current_iteration:
            return
        
        end = time.time()
        duration = (end - self.current_iteration["start_time"]) * 1000
        self.current_iteration["duration_ms"] = duration
        
        self.iterations.append(self.current_iteration)
        
        logger.info(f"🔄 ITERATION {self.current_iteration['iteration']} END ({duration:.0f}ms)\n")
    
    def get_summary(self) -> str:
        """Summary of all iterations"""
        summary = f"\n{'='*80}\n"
        summary += f"🔄 REACT ITERATIONS SUMMARY\n"
        summary += f"{'='*80}\n"
        
        total_duration = 0
        for it in self.iterations:
            duration = it["duration_ms"]
            total_duration += duration
            
            summary += f"\nIteration {it['iteration']}: {duration:.0f}ms\n"
            for step in it["steps"]:
                summary += f"  • {step['action']}"
                if step["details"]:
                    summary += f" — {step['details']}"
                summary += "\n"
        
        summary += f"\n{'='*80}\n"
        summary += f"Total ReACT time: {total_duration:.0f}ms ({total_duration/1000:.1f}s)\n"
        summary += f"Number of iterations: {len(self.iterations)}\n"
        summary += f"Avg time per iteration: {total_duration/len(self.iterations):.0f}ms\n"
        summary += f"{'='*80}\n"
        
        return summary
    
    def log_summary(self):
        """Log summary"""
        logger.info(self.get_summary())


@contextmanager
def track_operation(operation_name: str, details: Dict[str, Any] = None):
    """
    Standalone context manager để track một operation
    Usage:
        with track_operation("Vector Search", {"k": 3}):
            results = db.search(...)
    """
    details = details or {}
    start = time.time()
    
    logger.debug(f"START: {operation_name}")
    
    try:
        yield
    finally:
        duration_ms = (time.time() - start) * 1000
        logger.info(f"DONE: {operation_name} ({duration_ms:.0f}ms) {details}")
