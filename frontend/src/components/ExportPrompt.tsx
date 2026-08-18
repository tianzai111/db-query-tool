/**
 * ExportPrompt -- an "AI assistant" style nudge that appears after a query
 * successfully returns rows, proactively asking the user whether they want
 * to export the result.
 *
 * The assignment requires that "after querying, the AI assistant proactively
 * asks 'Do you want to export this query result as CSV or JSON?'". This
 * component is the in-UI implementation of that requirement: it renders a
 * small, dismissible banner with two one-click format buttons.
 */
import React from "react";
import { Alert, Button, Space } from "antd";
import { RobotOutlined, FileExcelOutlined, FileTextOutlined } from "@ant-design/icons";
import type { ExportFormat } from "../services/export";

interface ExportPromptProps {
  /** Number of rows returned by the latest query. */
  rowCount: number;
  /** Called when the user picks a format. */
  onExport: (format: ExportFormat) => void;
  /** Called when the user dismisses the prompt. */
  onDismiss: () => void;
}

export const ExportPrompt: React.FC<ExportPromptProps> = ({
  rowCount,
  onExport,
  onDismiss,
}) => {
  return (
    <Alert
      icon={<RobotOutlined />}
      type="info"
      showIcon
      closable
      onClose={onDismiss}
      style={{
        marginBottom: 12,
        borderWidth: 2,
        borderColor: "#000000",
        background: "#FFF8E1",
        fontWeight: 500,
      }}
      message={
        <span style={{ fontSize: 13 }}>
          <strong>AI Assistant:</strong> Your query returned{" "}
          <strong>{rowCount.toLocaleString()}</strong> row
          {rowCount === 1 ? "" : "s"}. Would you like to export this result as{" "}
          <strong>CSV</strong> or <strong>JSON</strong>?
        </span>
      }
      action={
        <Space direction="vertical" size={4}>
          <Space size={4}>
            <Button
              size="small"
              type="primary"
              icon={<FileExcelOutlined />}
              onClick={() => onExport("csv")}
              style={{ fontWeight: 700 }}
            >
              Export CSV
            </Button>
            <Button
              size="small"
              icon={<FileTextOutlined />}
              onClick={() => onExport("json")}
              style={{ fontWeight: 700 }}
            >
              Export JSON
            </Button>
          </Space>
        </Space>
      }
    />
  );
};
