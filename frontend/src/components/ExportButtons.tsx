/**
 * ExportButtons -- a small, reusable toolbar of CSV / JSON export buttons.
 *
 * It is used by the Home page result card and the standalone query-execute
 * page so that export styling and behaviour stay consistent across the app.
 */
import React from "react";
import { Button, Space, Dropdown, Tooltip } from "antd";
import { DownloadOutlined, FileTextOutlined, FileExcelOutlined } from "@ant-design/icons";
import type { ExportFormat } from "../services/export";

interface ExportButtonsProps {
  /** Called with the chosen format when the user clicks an export button. */
  onExport: (format: ExportFormat) => void;
  /** Disable buttons when there is no data / an export is in flight. */
  disabled?: boolean;
  /** Render a single "Export" dropdown instead of two separate buttons. */
  compact?: boolean;
  /** Size passed through to antd buttons. */
  size?: "small" | "middle" | "large";
}

/**
 * CSV / JSON export buttons.
 *
 * Two visual modes:
 *  - `compact={false}` (default): two explicit buttons (CSV, JSON)
 *  - `compact={true}`: a single "Export" dropdown menu
 */
export const ExportButtons: React.FC<ExportButtonsProps> = ({
  onExport,
  disabled = false,
  compact = false,
  size = "small",
}) => {
  if (compact) {
    const items = [
      {
        key: "csv",
        label: "Export as CSV",
        icon: <FileExcelOutlined />,
        onClick: () => onExport("csv"),
      },
      {
        key: "json",
        label: "Export as JSON",
        icon: <FileTextOutlined />,
        onClick: () => onExport("json"),
      },
    ];
    return (
      <Dropdown menu={{ items }} disabled={disabled} placement="bottomRight">
        <Button size={size} icon={<DownloadOutlined />} disabled={disabled}>
          EXPORT
        </Button>
      </Dropdown>
    );
  }

  return (
    <Space size={8}>
      <Tooltip title="Download as CSV (Excel-compatible, UTF-8)">
        <Button
          size={size}
          icon={<FileExcelOutlined />}
          onClick={() => onExport("csv")}
          disabled={disabled}
          style={{ fontSize: 12, fontWeight: 700 }}
        >
          CSV
        </Button>
      </Tooltip>
      <Tooltip title="Download as structured JSON with metadata">
        <Button
          size={size}
          icon={<FileTextOutlined />}
          onClick={() => onExport("json")}
          disabled={disabled}
          style={{ fontSize: 12, fontWeight: 700 }}
        >
          JSON
        </Button>
      </Tooltip>
    </Space>
  );
};
