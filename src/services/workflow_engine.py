import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime
from sqlalchemy.orm import Session
from src.models.workflow import WorkflowDefinition, WorkflowDependency, WorkflowExecution, WorkflowAuditLog

class WorkflowEngine:

    @staticmethod
    def create_workflow(db: Session, name: str, trigger_type: str) -> WorkflowDefinition:
        wf = WorkflowDefinition(name=name, trigger_type=trigger_type, enabled=True)
        db.add(wf)
        db.commit()
        db.refresh(wf)
        return wf

    @staticmethod
    def add_dependency(db: Session, parent_id: uuid.UUID, child_id: uuid.UUID, dep_type: str = "triggers") -> WorkflowDependency:
        dep = WorkflowDependency(parent_workflow_id=parent_id, child_workflow_id=child_id, dependency_type=dep_type)
        db.add(dep)
        db.commit()
        return dep

    @staticmethod
    def detect_cycles(db: Session, workflow_id: uuid.UUID) -> bool:
        # DFS to detect loops starting from workflow_id
        visited = set()
        rec_stack = set()

        def dfs(node_id: uuid.UUID) -> bool:
            visited.add(node_id)
            rec_stack.add(node_id)

            # Find child deps
            deps = db.query(WorkflowDependency).filter(WorkflowDependency.parent_workflow_id == node_id).all()
            for d in deps:
                child = d.child_workflow_id
                if child not in visited:
                    if dfs(child):
                        return True
                elif child in rec_stack:
                    return True

            rec_stack.remove(node_id)
            return False

        return dfs(workflow_id)

    @staticmethod
    def trigger_workflow(
        db: Session,
        workflow_id: uuid.UUID,
        trigger_context: dict,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None
    ) -> WorkflowExecution:
        wf = db.query(WorkflowDefinition).filter(WorkflowDefinition.id == workflow_id).first()
        if not wf:
            raise ValueError("Workflow definition not found")

        # Validate cycles
        has_cycle = WorkflowEngine.detect_cycles(db, workflow_id)
        val_status = "VALID"
        val_msg = None
        if has_cycle:
            val_status = "CYCLE_DETECTED"
            val_msg = "Recursive cycle loop detected in dependency chain."

        execution = WorkflowExecution(
            workflow_id=workflow_id,
            status="RUNNING",
            workflow_validation_status=val_status,
            validation_message=val_msg,
            retry_count=0,
            max_retries=3,
            trace_id=trace_id,
            span_id=span_id
        )
        db.add(execution)
        db.commit()
        db.refresh(execution)

        # Log start audit
        WorkflowEngine.log_audit(db, execution.id, "workflow_started", f"Workflow {wf.name} started.", trace_id, span_id)

        if has_cycle:
            execution.status = "FAILED"
            execution.last_error = val_msg
            execution.completed_at = datetime.utcnow()
            db.commit()
            WorkflowEngine.log_audit(db, execution.id, "workflow_failed", val_msg, trace_id, span_id)
            return execution

        # Simulate executing actions
        try:
            # Assume successful execute
            execution.status = "SUCCESS"
            execution.result_json = {"actions_executed": ["create_investigation", "run_quality_checks"]}
            execution.completed_at = datetime.utcnow()
            db.commit()
            WorkflowEngine.log_audit(db, execution.id, "workflow_completed", "All actions finished successfully.", trace_id, span_id)
        except Exception as e:
            execution.status = "FAILED"
            execution.last_error = str(e)
            execution.completed_at = datetime.utcnow()
            db.commit()
            WorkflowEngine.log_audit(db, execution.id, "workflow_failed", f"Error: {str(e)}", trace_id, span_id)

        return execution

    @staticmethod
    def log_audit(
        db: Session,
        execution_id: uuid.UUID,
        event_type: str,
        message: str,
        trace_id: Optional[str] = None,
        span_id: Optional[str] = None
    ) -> WorkflowAuditLog:
        log = WorkflowAuditLog(
            workflow_execution_id=execution_id,
            event_type=event_type,
            event_message=message,
            trace_id=trace_id,
            span_id=span_id
        )
        db.add(log)
        db.commit()
        return log
