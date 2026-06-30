from nimbusware_console.explainer_core.generic_workflow_explainer import install_explainer_metrics
from nimbusware_console.explainer_core.workflow_explainer_registry import (
    install_package_workflow_explainer_exports,
)
from nimbusware_console.explainer_core.workflow_exports import (
    workflow_explainer_payload_export_json,
)
from nimbusware_console.workflow_explainers.integration_adapter_writer.captions import (
    integration_adapter_writer_effective_caption,
    integration_adapter_writer_env_gate_caption,
)
from nimbusware_console.workflow_explainers.integration_adapter_writer.events import (
    integration_adapter_writer_from_events,
    integration_adapter_writer_run_caption,
    integration_adapter_writer_run_table_rows,
)
from nimbusware_console.workflow_explainers.integration_adapter_writer.payload import (
    integration_adapter_writer_fleet_manifest_count,
    integration_adapter_writer_workflow_explainer_payload,
)

install_explainer_metrics("integration_adapter_writer", globals())

integration_adapter_writer_explainer_export_json = workflow_explainer_payload_export_json

__all__ = [
    "_integration_adapter_writer_explainer_cell",
    "integration_adapter_writer_effective_caption",
    "integration_adapter_writer_env_gate_caption",
    "integration_adapter_writer_explainer_export_json",
    "integration_adapter_writer_explainer_table_rows",
    "integration_adapter_writer_explainer_table_rows_csv",
    "integration_adapter_writer_export_filename_slug",
    "integration_adapter_writer_fleet_manifest_count",
    "integration_adapter_writer_from_events",
    "integration_adapter_writer_run_caption",
    "integration_adapter_writer_run_table_rows",
    "integration_adapter_writer_workflow_explainer_operator_metrics",
    "integration_adapter_writer_workflow_explainer_operator_metrics_caption",
    "integration_adapter_writer_workflow_explainer_operator_metrics_export_filename_slug",
    "integration_adapter_writer_workflow_explainer_operator_metrics_export_json",
    "integration_adapter_writer_workflow_explainer_operator_metrics_table_rows",
    "integration_adapter_writer_workflow_explainer_operator_metrics_table_rows_csv",
    "integration_adapter_writer_workflow_explainer_payload",
]

install_package_workflow_explainer_exports(
    globals(), "integration_adapter_writer"
)  # workflow-explainer-exports
